#!/usr/bin/env python3
"""Read-only static SEO evidence collector. Offline HTML or a bounded public same-origin crawl.
No JS rendering, Search Console access, rank measurement or automatic site edits.
"""
from __future__ import annotations
import argparse
from collections import deque
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import http.client
import ipaddress
import json
from pathlib import Path
import re
import socket
import ssl
import sys
import time
from urllib.parse import urljoin, urlsplit, urlunsplit, urldefrag
from urllib.robotparser import RobotFileParser
from typing import Any

USER_AGENT = 'IndependentSEOAuditor/0.1.1'
MAX_BYTES = 3_000_000
MAX_REDIRECTS = 5


def reject_json_constant(value: str):
    raise ValueError(f'Invalid JSON number: {value}')


def check_robots_support(text: str) -> None:
    """Stop before fetching pages when robotparser cannot preserve all rules.

    Python's parser uses the first matching group rather than merging repeated
    groups. Keep the same fail-closed policy as unsupported wildcard rules.
    """
    seen: set[str] = set()
    group: set[str] = set()
    has_rules = False
    for line in text.splitlines():
        clean = line.split('#', 1)[0].strip()
        key, separator, value = clean.partition(':')
        if not separator:
            continue
        key, value = key.strip().lower(), value.strip()
        if key == 'user-agent':
            if has_rules:
                seen.update(group)
                group = set()
                has_rules = False
            agent = value.lower()
            if agent in seen:
                raise ValueError('robots.txt contains repeated user-agent groups requiring a fuller parser. No pages crawled; use supplied HTML or a crawler that merges matching groups.')
            group.add(agent)
        elif key in {'allow', 'disallow', 'crawl-delay', 'request-rate'}:
            has_rules = bool(group)
            if key in {'allow', 'disallow'} and any(c in value for c in '*$'):
                raise ValueError('robots.txt contains wildcard/end-anchor rules requiring a fuller parser. No pages crawled; use approved browser inspection or supplied HTML.')


class Collector(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.titles: list[dict] = []
        self.h1: list[dict] = []
        self.meta: list[dict] = []
        self.canonical: list[dict] = []
        self.images: list[dict] = []
        self.links: list[dict] = []
        self.hreflang: list[dict] = []
        self.jsonld: list[dict] = []
        self.lang = None
        self.base = None
        self.capture = None
        self.script = None
        self.in_head = False
        self.head_count = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {key.lower(): value for key, value in attrs}
        line = self.getpos()[0]
        if tag == 'html': self.lang = a.get('lang')
        if tag == 'head': self.in_head = True; self.head_count += 1
        if tag == 'base' and self.in_head and self.base is None: self.base = a.get('href')
        if tag == 'title' and self.in_head:
            item = {'text': '', 'line': line}; self.titles.append(item); self.capture = ('title', item)
        if tag == 'h1':
            item = {'text': '', 'line': line}; self.h1.append(item); self.capture = ('h1', item)
        if tag == 'meta' and self.in_head: self.meta.append({**a, 'line': line})
        if tag == 'link' and self.in_head:
            rel = (a.get('rel') or '').lower().split()
            if 'canonical' in rel: self.canonical.append({**a, 'line': line})
            if 'alternate' in rel and a.get('hreflang'): self.hreflang.append({**a, 'line': line})
        if tag == 'img': self.images.append({**a, 'line': line})
        if tag == 'a' and a.get('href'): self.links.append({**a, 'line': line})
        if tag == 'script':
            self.script = {'text': '', 'line': line} if (a.get('type') or '').split(';')[0].strip().lower() == 'application/ld+json' else None

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag == 'head': self.in_head = False
        if self.capture and self.capture[0] == tag:
            self.capture[1]['text'] = ' '.join(self.capture[1]['text'].split()); self.capture = None
        if tag == 'script' and self.script is not None:
            self.jsonld.append(self.script); self.script = None

    def handle_data(self, data: str) -> None:
        if self.capture: self.capture[1]['text'] += data
        if self.script is not None: self.script['text'] += data


def origin(url: str) -> tuple[str, str, int]:
    p = urlsplit(url)
    return p.scheme.lower(), (p.hostname or '').lower(), p.port or (443 if p.scheme.lower() == 'https' else 80)


def normalize(url: str) -> str:
    p = urlsplit(urldefrag(url)[0])
    if p.scheme.lower() not in {'http', 'https'} or not p.hostname:
        raise ValueError('Only absolute HTTP/HTTPS URLs are supported.')
    if p.username is not None or p.password is not None:
        raise ValueError('Credentials in URLs are forbidden.')
    if p.port not in {None, 80, 443}:
        raise ValueError('Only standard public web ports are supported.')
    if any(ord(c) < 32 for c in url):
        raise ValueError('Control characters in URLs are forbidden.')
    host = p.hostname.encode('idna').decode('ascii').lower()
    host_display = f'[{host}]' if ':' in host else host
    port = p.port
    netloc = host_display + (f':{port}' if port and port != (443 if p.scheme.lower() == 'https' else 80) else '')
    from urllib.parse import quote
    path = quote(p.path or '/', safe="/%:@!$&'()*+,;=-._~")
    query = quote(p.query, safe="%:@!$&'()*+,;=/?-._~")
    return urlunsplit((p.scheme.lower(), netloc, path, query, ''))


def public_addresses(host: str, port: int) -> list[tuple]:
    results = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    if not results:
        raise ValueError('DNS returned no addresses.')
    for _, _, _, _, address in results:
        ip = ipaddress.ip_address(address[0])
        mapped = getattr(ip, 'ipv4_mapped', None)
        if not ip.is_global or (mapped is not None and not mapped.is_global):
            raise ValueError('Private, loopback, link-local, reserved or non-global destinations are blocked.')
    return results


def single_get(url: str, timeout: float = 12) -> dict:
    """Pin to the verified numeric IP and preserve the original TLS hostname (no DNS rebind)."""
    url = normalize(url)
    p = urlsplit(url); port = p.port or (443 if p.scheme == 'https' else 80)
    addresses = public_addresses(p.hostname, port)
    sock = None; last_error = None
    for family, kind, proto, _, address in addresses:
        candidate = socket.socket(family, kind, proto); candidate.settimeout(timeout)
        try:
            candidate.connect(address)
            sock = candidate; break
        except OSError as exc:
            last_error = exc; candidate.close()
    if sock is None: raise OSError(f'Connection failed: {last_error}')
    conn = http.client.HTTPConnection(p.hostname, port, timeout=timeout)
    try:
        if p.scheme == 'https':
            sock = ssl.create_default_context().wrap_socket(sock, server_hostname=p.hostname)
        conn.sock = sock
        target = p.path or '/'
        if p.query: target += '?' + p.query
        conn.request('GET', target, headers={'Host': p.netloc, 'User-Agent': USER_AGENT,
                                            'Accept': 'text/html,text/plain,application/xhtml+xml;q=0.9',
                                            'Accept-Encoding': 'identity', 'Connection': 'close'})
        response = conn.getresponse()
        body = response.read(MAX_BYTES + 1)
        if len(body) > MAX_BYTES: raise ValueError('Response exceeds the 3 MB inspection limit.')
        # Combine repeated headers; do not silently drop a second X-Robots-Tag or Link.
        headers: dict[str, str] = {}
        for key, value in response.getheaders():
            key = key.lower(); headers[key] = headers[key] + ', ' + value if key in headers else value
        if headers.get('content-encoding', 'identity').lower() not in {'identity', ''}:
            raise ValueError('Compressed response despite identity request; not inspected.')
        return {'url': url, 'status': response.status, 'headers': headers, 'body': body,
                'fetched_at': datetime.now(timezone.utc).isoformat()}
    finally:
        conn.close()
        if sock is not None: sock.close()


def decode(body: bytes, headers: dict) -> tuple[str, str]:
    content_type = headers.get('content-type', '')
    match = re.search(r'charset\s*=\s*["\']?([^;\s"\']+)', content_type, re.I)
    encoding = match.group(1) if match else 'utf-8'
    if not match:
        # Legacy Korean HTML commonly declares encoding only in its head.
        sniff = body[:4096].decode('ascii', errors='ignore')
        meta = re.search(r'<meta\b[^>]*charset\s*=\s*["\']?\s*([\w-]+)', sniff, re.I)
        if meta: encoding = meta.group(1)
    try:
        return body.decode(encoding), encoding
    except (LookupError, UnicodeDecodeError) as exc:
        raise ValueError(f'Cannot decode source reliably as {encoding}; provide a correctly encoded HTML copy.') from exc


class Fetcher:
    def __init__(self, base: str, delay: float = 1.0):
        self.base = normalize(base); self.origin = origin(self.base)
        self.delay = max(1.0, delay); self.last = 0.0; self.requests = 0

    def get(self, url: str, authorize=None) -> dict:
        current = normalize(url); chain = []
        for step in range(MAX_REDIRECTS + 1):
            if origin(current) != self.origin:
                raise ValueError('Cross-origin redirect/link blocked. Audit the final public origin in a separate run.')
            if authorize is not None and not authorize(current):
                raise ValueError('Redirect or target disallowed by robots.txt.')
            time.sleep(max(0.0, self.delay - (time.monotonic() - self.last)))
            result = single_get(current); self.requests += 1; self.last = time.monotonic()
            if result['status'] not in {301, 302, 303, 307, 308}:
                result['redirects'] = chain; return result
            location = result['headers'].get('location')
            if not location: raise ValueError('Redirect without Location.')
            chain.append({'url': current, 'status': result['status']})
            current = normalize(urljoin(current, location))
        raise ValueError('Too many redirects.')


def audit_html(html: str, url: str, intent: str = 'unknown', headers: dict | None = None, status: int | None = None) -> dict:
    parser = Collector(); parser.feed(html); parser.close()
    headers = headers or {}
    findings: list[dict] = []
    def add(code: str, severity: str, state: str, evidence: str, recommendation: str, line: int | None = None):
        findings.append({'code': code, 'severity': severity, 'state': state, 'evidence': evidence,
                         'line': line, 'recommendation': recommendation})
    if status is not None and status >= 400:
        add('HTTP_ERROR', 'high', 'observed', str(status), 'Verify whether this URL should be reachable; fix links or the origin response.')
    if not parser.titles or not any(t['text'] for t in parser.titles):
        add('TITLE_MISSING', 'medium', 'observed', 'No nonempty <head><title> in inspected source.', 'Add a descriptive, page-specific title in the actual template.')
    if len(parser.titles) > 1:
        add('TITLE_MULTIPLE', 'medium', 'observed', str(parser.titles), 'Keep one intentional title element.')
    descriptions = [x for x in parser.meta if (x.get('name') or '').lower() == 'description']
    if not descriptions or not any((x.get('content') or '').strip() for x in descriptions):
        add('DESCRIPTION_MISSING', 'low', 'observed', 'No nonempty meta description.', 'Consider a useful page-specific summary; no fixed character count or ranking guarantee.')
    if len(descriptions) > 1:
        add('DESCRIPTION_MULTIPLE', 'low', 'observed', str(descriptions), 'Resolve duplicate template metadata.')
    if not parser.h1:
        add('H1_REVIEW', 'low', 'needs_review', 'No h1 in static HTML.', 'Review page structure; this alone does not prove an SEO penalty.')
    elif len(parser.h1) > 1:
        add('H1_MULTIPLE_REVIEW', 'info', 'needs_review', str(parser.h1), 'Review semantic structure; multiple h1 elements are not automatically a ranking error.')
    if not parser.lang:
        add('LANG_REVIEW', 'low', 'needs_review', 'No html lang attribute.', 'Set an appropriate document language for accessibility and tooling; not an automatic ranking verdict.')
    if not parser.canonical:
        add('CANONICAL_ABSENT', 'info', 'needs_review', 'No HTML canonical in inspected head.', 'Review duplicates and HTTP Link headers. A canonical preference is not mandatory on every page.')
    elif len(parser.canonical) > 1:
        add('CANONICAL_MULTIPLE', 'medium', 'observed', str(parser.canonical), 'Ensure the page has one consistent canonical preference.')
    for item in parser.canonical:
        href = item.get('href') or ''
        if not href:
            add('CANONICAL_EMPTY', 'medium', 'observed', str(item), 'Remove the empty canonical or set the actual intended URL.', item['line'])
        elif not urlsplit(href).scheme:
            add('CANONICAL_RELATIVE', 'low', 'observed', href, 'Prefer an absolute canonical to avoid environment-dependent resolution.', item['line'])
        elif urlsplit(href).fragment:
            add('CANONICAL_FRAGMENT', 'medium', 'observed', href, 'Review and use the intended canonical URL without a fragment.', item['line'])
    robot_meta = [x for x in parser.meta if (x.get('name') or '').lower() in {'robots', 'googlebot', 'bingbot'}]
    for item in robot_meta:
        value = item.get('content') or ''
        if 'noindex' in value.lower() or re.search(r'\bnone\b', value, re.I):
            add('NOINDEX_META', 'high' if intent == 'index' else 'info', 'observed', str(item),
                'Compare with intended indexability. Do not remove noindex without checking page purpose.', item['line'])
    xr = headers.get('x-robots-tag', '')
    if re.search(r'\b(noindex|none)\b', xr, re.I):
        add('NOINDEX_HEADER', 'high' if intent == 'index' else 'info', 'observed', xr, 'Check crawler scope and intended page visibility before changing the header.')
    missing_alt = [i for i in parser.images if 'alt' not in i]
    if missing_alt:
        add('IMG_ALT_MISSING', 'low', 'observed', str(missing_alt[:10]), 'Give informative images descriptive alt; decorative images may deliberately use alt="".')
    structured = []
    for item in parser.jsonld:
        try:
            value = json.loads(item['text'], parse_constant=reject_json_constant)
            if not isinstance(value, (dict, list)):
                raise ValueError('JSON-LD root is not an object or array.')
            structured.append({'line': item['line'], 'json_parsed': True})
        except (ValueError, TypeError) as exc:
            add('JSONLD_PARSE_ERROR', 'medium', 'observed', str(exc), 'Fix JSON syntax, then separately check schema meaning and current rich-result requirements.', item['line'])
    if not parser.jsonld:
        add('STRUCTURED_DATA_REVIEW', 'info', 'needs_review', 'No JSON-LD script in source.', 'Check whether structured data is appropriate; microdata/RDFa and rendered JS were not validated.')
    return {'url': url, 'http_status': status, 'intent': intent, 'title': [i['text'] for i in parser.titles],
            'h1': [i['text'] for i in parser.h1], 'canonical': parser.canonical, 'hreflang': parser.hreflang,
            'base_href': parser.base, 'links': parser.links, 'image_count': len(parser.images),
            'empty_alt_count': sum(i.get('alt') == '' for i in parser.images), 'jsonld': structured,
            'findings': findings, 'header_evidence': {k: headers[k] for k in ('x-robots-tag', 'link', 'content-type') if k in headers},
            'limitations': ['Static source only; rendered DOM not checked.',
                            'JSON parsing is not schema validation or rich-result eligibility.',
                            'Canonical destination status and search-engine-selected canonical not verified.',
                            'Unvisited links are not verified as working or broken.',
                            'No keyword volume, ranking, actual indexing, field Core Web Vitals or performance measurements.']}


def crawl(url: str, max_pages: int = 10, intent: str = 'unknown', include_query: bool = False) -> tuple[list[dict], list[dict], dict, list[dict]]:
    if not 1 <= max_pages <= 50:
        raise ValueError('max_pages must be 1..50.')
    fetcher = Fetcher(url)
    p = urlsplit(fetcher.base)
    robots_url = urlunsplit((p.scheme, p.netloc, '/robots.txt', '', ''))
    robots = fetcher.get(robots_url)
    if robots['status'] in {404, 410}:
        robot_text = ''
        robots_note = 'No robots file at inspection time (404/410); crawler allowed.'
    elif robots['status'] == 200:
        robot_text, _ = decode(robots['body'], robots['headers'])
        check_robots_support(robot_text)
        robots_note = 'Evaluated for this audit user agent using Python robotparser, NOT a Googlebot simulation.'
    else:
        raise ValueError(f'robots.txt returned {robots["status"]}; no pages crawled. Do not bypass the restriction.')
    rp = RobotFileParser(); rp.parse(robot_text.splitlines())
    delay = rp.crawl_delay(USER_AGENT)
    if delay: fetcher.delay = max(fetcher.delay, float(delay))
    rate = rp.request_rate(USER_AGENT)
    if rate and rate.requests: fetcher.delay = max(fetcher.delay, rate.seconds / rate.requests)
    sitemap_urls = [line.split(':', 1)[1].strip() for line in robot_text.splitlines() if line.lower().startswith('sitemap:')]
    queue = deque([fetcher.base]); seen: set[str] = set(); pages = []; snapshots = []; events = []
    while queue and len(seen) < max_pages:
        current = queue.popleft()
        if current in seen: continue
        seen.add(current)
        if not rp.can_fetch(USER_AGENT, current):
            events.append({'url': current, 'state': 'not_fetched', 'reason': 'robots.txt disallow'}); continue
        try:
            result = fetcher.get(current, authorize=lambda target: rp.can_fetch(USER_AGENT, target))
            if result['status'] in {401, 403, 429} or result['status'] >= 500:
                events.append({'url': current, 'state': 'stopped', 'reason': f'HTTP {result["status"]}; crawl stopped without bypass or retries.'}); break
            content_type = result['headers'].get('content-type', '').lower()
            if not any(mime in content_type for mime in ('text/html', 'application/xhtml+xml')):
                events.append({'url': current, 'state': 'not_inspected', 'reason': 'Not declared HTML: ' + content_type}); continue
            html, encoding = decode(result['body'], result['headers'])
            report = audit_html(html, result['url'], intent, result['headers'], result['status'])
            report.update({'fetched_at': result['fetched_at'], 'encoding': encoding,
                           'source_sha256': hashlib.sha256(result['body']).hexdigest(), 'redirects': result['redirects']})
            pages.append(report); snapshots.append({'url': result['url'], 'body': result['body']})
            base = urljoin(result['url'], report['base_href']) if report['base_href'] else result['url']
            for link in report['links']:
                if 'nofollow' in (link.get('rel') or '').lower().split(): continue
                try: target = normalize(urljoin(base, link['href']))
                except ValueError: continue
                if origin(target) != fetcher.origin or target in seen or target in queue: continue
                if urlsplit(target).query and not include_query: continue
                if re.search(r'/(?:logout|signout|admin|checkout|cart|account|login|delete)(?:/|\?|$)', target, re.I): continue
                if re.search(r'\.(?:pdf|zip|png|jpe?g|gif|webp|svg|mp4|mp3|css|js)(?:\?|$)', target, re.I): continue
                if len(queue) < 500: queue.append(target)
        except (OSError, ValueError, http.client.HTTPException) as exc:
            events.append({'url': current, 'state': 'not_inspected', 'reason': str(exc)})
    metadata = {'mode': 'bounded-public-static-crawl', 'robots_url': robots_url, 'robots_status': robots['status'],
                'robots_note': robots_note, 'sitemap_urls_discovered_not_fetched': sitemap_urls,
                'max_pages_requested': max_pages, 'urls_attempted': len(seen), 'http_requests_including_robots_redirects': fetcher.requests,
                'minimum_delay_seconds': fetcher.delay, 'same_origin_only': True, 'query_link_discovery_enabled': include_query,
                'crawl_exhaustive': False, 'note': 'Page budget includes failed/disallowed attempts; max_pages is not a full-site guarantee.'}
    return pages, events, metadata, snapshots


def write_report(pages: list[dict], events: list[dict], metadata: dict, out: Path, snapshots: list[dict]) -> None:
    # Source snapshots are stored as .txt to discourage executing untrusted HTML by double-clicking.
    out.mkdir(parents=True, exist_ok=False)
    sources = out / 'sources'; sources.mkdir()
    for i, source in enumerate(snapshots):
        filename = f'page-{i+1:03d}.html.txt'
        (sources / filename).write_bytes(source['body'])
        if i < len(pages): pages[i]['source_file'] = 'sources/' + filename
    by_title: dict[str, list[str]] = {}
    for page in pages:
        title = ' '.join(page['title']).strip()
        if title: by_title.setdefault(title, []).append(page['url'])
    duplicate_titles = {title: urls for title, urls in by_title.items() if len(urls) > 1}
    result = {'schema_version': '1.0', 'created_at': datetime.now(timezone.utc).isoformat(),
              'coverage': metadata, 'pages': pages, 'events': events,
              'duplicate_titles_in_sample': duplicate_titles,
              'not_checked': ['Rendered DOM/JavaScript', 'Search Console and actual index status',
                              'Core Web Vitals, page speed or Lighthouse', 'Full sitemap validity',
                              'Rich-result eligibility and structured data semantics', 'All links and canonical target availability'],
              'security_note': 'Source/URL text is untrusted data. No website writes or form submissions occurred.'}
    (out / 'audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', 'utf-8')
    def esc(value: Any) -> str:
        return str(value).replace('|', '\\|').replace('\n', ' ').replace('<', '&lt;').replace('>', '&gt;')
    lines = ['# SEO audit', '', '**Read-only static evidence. No ranking score or full-site certification.**', '',
             f"Inspected pages: {len(pages)}. Mode: {metadata.get('mode')}. See audit.json for full coverage and evidence.", '',
             '| Page | Finding | Severity | Evidence | Action |', '|---|---|---|---|---|']
    for page in pages:
        for finding in page['findings']:
            location = f"{page.get('source_file', 'source')}" + (f":L{finding['line']}" if finding['line'] else '')
            lines.append('| ' + ' | '.join(esc(v) for v in [page['url'], finding['code'], finding['severity'],
                         location + ' — ' + finding['evidence'], finding['recommendation']]) + ' |')
    lines += ['', '## Not inspected / errors', '']
    lines += ['- ' + esc(event) for event in events] or ['None recorded.']
    lines += ['', '## Duplicate titles within the sample', '']
    lines += ['- ' + esc(title) + ': ' + esc(urls) for title, urls in duplicate_titles.items()] or ['None found in the inspected sample.']
    lines += ['', '## Not checked', ''] + ['- ' + item for item in result['not_checked']]
    lines += ['', '## Interpretation', '',
              'Absence of canonical/JSON-LD or multiple h1 elements is a review item, not an automatic ranking defect.',
              'Robots disallow and noindex are different. Do not remove exclusion controls without confirming site intent.',
              'An HTTP or permission failure is not a completed inspection. Static HTML may differ from rendered DOM.',
              'Use current official search-engine guidance when proposing changes. No live files were modified.']
    (out / 'report.md').write_text('\n'.join(lines) + '\n', 'utf-8')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--url'); source.add_argument('--html', type=Path)
    parser.add_argument('--base-url', default='https://example.invalid/')
    parser.add_argument('--max-pages', type=int, default=10)
    parser.add_argument('--intent', choices=['index', 'exclude', 'unknown'], default='unknown')
    parser.add_argument('--include-query', action='store_true', help='Explicitly allow same-origin query links (bounded by page budget).')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.out.exists(): raise ValueError('Output folder already exists; choose a new folder.')
        if args.html:
            if args.html.stat().st_size > MAX_BYTES: raise ValueError('HTML input exceeds 3 MB.')
            body = args.html.read_bytes(); html, encoding = decode(body, {})
            page = audit_html(html, normalize(args.base_url), args.intent)
            page.update({'source_sha256': hashlib.sha256(body).hexdigest(), 'encoding': encoding})
            pages, events, metadata, snapshots = [page], [], {'mode': 'offline-html', 'http_status': 'not_checked', 'robots': 'not_checked'}, [{'body': body}]
        else:
            pages, events, metadata, snapshots = crawl(args.url, args.max_pages, args.intent, args.include_query)
        write_report(pages, events, metadata, args.out, snapshots)
        print(f'Inspected {len(pages)} page(s). Report: {args.out}/report.md; raw evidence: audit.json and sources/.')
        return 0 if pages else 3
    except (OSError, ValueError, http.client.HTTPException) as exc:
        print(f'ERROR: {exc}', file=sys.stderr); return 2

if __name__ == '__main__':
    raise SystemExit(main())
