from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
SKILL=ROOT/'plugins/seo-auditor/skills/seo-auditor'
spec=importlib.util.spec_from_file_location('audit',SKILL/'scripts/audit.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

GOOD='''<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Useful page</title>
<meta name="description" content="A helpful description"><link rel="canonical" href="https://example.com/">
<script type="application/ld+json">{"@context":"https://schema.org","@type":"WebPage"}</script>
</head><body><h1>A <span>useful</span> page</h1><img src="decor.png" alt=""></body></html>'''

def response(url,body=GOOD,status=200,headers=None):
    return {'url':url,'status':status,'headers':headers or {'content-type':'text/html; charset=utf-8'},
            'body':body.encode('utf-8'),'fetched_at':'2026-09-29T00:00:00+00:00','redirects':[]}

class HtmlTests(unittest.TestCase):
    def codes(self,html=GOOD,**kw):return {f['code']:f for f in m.audit_html(html,'https://example.com/',**kw)['findings']}
    def test_basic_page(self):
        report=m.audit_html(GOOD,'https://example.com/');self.assertEqual(report['title'],['Useful page'])
        self.assertEqual(report['h1'],['A useful page']);self.assertEqual(report['empty_alt_count'],1)
        self.assertEqual(report['findings'],[])
    def test_empty_alt_is_not_missing(self):self.assertNotIn('IMG_ALT_MISSING',self.codes())
    def test_missing_alt_observed(self):self.assertIn('IMG_ALT_MISSING',self.codes(GOOD.replace('alt=""','')))
    def test_body_canonical_not_head_canonical(self):
        text='<html><head><title>Hi</title></head><body><link rel="canonical" href="https://example.com/"></body></html>'
        self.assertIn('CANONICAL_ABSENT',self.codes(text))
    def test_relative_canonical_review(self):self.assertIn('CANONICAL_RELATIVE',self.codes(GOOD.replace('href="https://example.com/"','href="/"')))
    def test_absent_canonical_is_not_critical(self):
        finding=self.codes(GOOD.replace('<link rel="canonical" href="https://example.com/">',''))['CANONICAL_ABSENT']
        self.assertEqual(finding['severity'],'info')
    def test_multiple_h1_not_penalty(self):
        item=self.codes(GOOD.replace('</body>','<h1>Other section</h1></body>'))['H1_MULTIPLE_REVIEW']
        self.assertEqual(item['state'],'needs_review');self.assertEqual(item['severity'],'info')
    def test_noindex_intent_matters(self):
        text=GOOD.replace('</head>','<meta name="robots" content="noindex"></head>')
        self.assertEqual(self.codes(text,intent='index')['NOINDEX_META']['severity'],'high')
        self.assertEqual(self.codes(text,intent='exclude')['NOINDEX_META']['severity'],'info')
    def test_noindex_header(self):self.assertIn('NOINDEX_HEADER',self.codes(headers={'x-robots-tag':'noindex'},intent='index'))
    def test_invalid_jsonld_is_syntax_error(self):
        codes=self.codes(GOOD.replace('"@type":"WebPage"','"@type":"WebPage",'))
        self.assertIn('JSONLD_PARSE_ERROR',codes)
    def test_script_does_not_create_fake_heading(self):
        report=m.audit_html(GOOD.replace('</head>','<script>const text="<h1>not a heading</h1>";</script></head>'),'https://example.com/')
        self.assertEqual(report['h1'],['A useful page'])
    def test_offline_status_is_unknown(self):self.assertIsNone(m.audit_html(GOOD,'https://example.com/')['http_status'])
    def test_legacy_korean_charset(self):
        source='<meta charset="euc-kr"><title>제품 안내</title>'
        text,encoding=m.decode(source.encode('euc-kr'),{});self.assertIn('제품 안내',text);self.assertEqual(encoding,'euc-kr')
    def test_invalid_encoding_fails_not_mojibake(self):
        with self.assertRaises(ValueError):m.decode(b'\xff\xfe\xff',{})
    def test_report_has_limits_and_text_snapshots(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'report';pages=[m.audit_html(GOOD,'https://example.com/')]
            m.write_report(pages,[],{'mode':'offline-html'},out,[{'body':GOOD.encode()}])
            data=json.loads((out/'audit.json').read_text());self.assertIn('not_checked',data)
            self.assertTrue((out/'sources/page-001.html.txt').exists())
            with self.assertRaises(FileExistsError):m.write_report([],[],{},out,[])
    def test_duplicate_titles_limited_to_sample(self):
        with tempfile.TemporaryDirectory() as d:
            pages=[m.audit_html(GOOD,'https://example.com/'),m.audit_html(GOOD,'https://example.com/two')]
            m.write_report(pages,[],{},Path(d)/'r',[])
            report=json.loads((Path(d)/'r/audit.json').read_text())
            self.assertEqual(len(report['duplicate_titles_in_sample']['Useful page']),2)

class NetworkSafetyTests(unittest.TestCase):
    def test_url_schemes_ports_credentials_blocked(self):
        for url in ['file:///etc/passwd','ftp://example.com/','https://user:pass@example.com/','https://example.com:8080/']:
            with self.assertRaises(ValueError):m.normalize(url)
    def test_fragment_removed_and_unicode_encoded(self):
        self.assertEqual(m.normalize('https://example.com/제품#part'),'https://example.com/%EC%A0%9C%ED%92%88')
    def test_private_dns_rejected(self):
        for ip in ['127.0.0.1','10.0.0.1','169.254.169.254','192.168.1.1','::1','::ffff:127.0.0.1']:
            with patch.object(m.socket,'getaddrinfo',return_value=[(socket.AF_INET,socket.SOCK_STREAM,6,'',(ip,443))]):
                with self.assertRaises(ValueError):m.public_addresses('host.example',443)
    def test_mixed_public_and_private_dns_rejected(self):
        answers=[(socket.AF_INET,socket.SOCK_STREAM,6,'',('8.8.8.8',443)),(socket.AF_INET,socket.SOCK_STREAM,6,'',('10.0.0.1',443))]
        with patch.object(m.socket,'getaddrinfo',return_value=answers):
            with self.assertRaises(ValueError):m.public_addresses('host.example',443)
    def test_cross_origin_redirect_not_followed(self):
        r=response('https://example.com/',status=302,headers={'location':'http://127.0.0.1/'})
        with patch.object(m,'single_get',return_value=r) as fetch,patch.object(m.time,'sleep'):
            with self.assertRaises(ValueError):m.Fetcher('https://example.com/').get('https://example.com/')
            self.assertEqual(fetch.call_count,1)
    def test_redirect_robots_checked_before_request(self):
        r=response('https://example.com/',status=302,headers={'location':'/private'})
        with patch.object(m,'single_get',return_value=r) as fetch,patch.object(m.time,'sleep'):
            with self.assertRaises(ValueError):m.Fetcher('https://example.com/').get('https://example.com/',lambda u:not u.endswith('/private'))
            self.assertEqual(fetch.call_count,1)
    def test_robots_wildcard_stops_crawl(self):
        r=response('https://example.com/robots.txt','User-agent: *\nDisallow: /*?*',headers={'content-type':'text/plain'})
        with patch.object(m.Fetcher,'get',return_value=r) as fetch:
            with self.assertRaises(ValueError):m.crawl('https://example.com/')
            self.assertEqual(fetch.call_count,1)
    def test_robots_403_stops_before_pages(self):
        with patch.object(m.Fetcher,'get',return_value=response('https://example.com/robots.txt',status=403)) as fetch:
            with self.assertRaises(ValueError):m.crawl('https://example.com/')
            self.assertEqual(fetch.call_count,1)
    def test_robot_disallow_does_not_fetch_page(self):
        r=response('https://example.com/robots.txt','User-agent: *\nDisallow: /',headers={'content-type':'text/plain'})
        with patch.object(m.Fetcher,'get',return_value=r) as fetch:
            pages,events,meta,_=m.crawl('https://example.com/')
            self.assertEqual(pages,[]);self.assertEqual(fetch.call_count,1);self.assertEqual(events[0]['state'],'not_fetched')
    def test_crawl_budget_and_external_link_exclusion(self):
        seen=[]
        def fake(self,url,authorize=None):
            seen.append(url)
            if url.endswith('/robots.txt'):return response(url,'',status=404)
            return response(url,GOOD.replace('</body>','<a href="/two">two</a><a href="/three">three</a><a href="https://other.example/">other</a><a href="/?page=2">q</a></body>'))
        with patch.object(m.Fetcher,'get',fake):
            pages,events,meta,_=m.crawl('https://example.com/',max_pages=2)
        self.assertEqual(len(pages),2);self.assertEqual(meta['urls_attempted'],2)
        self.assertTrue(all('other.example' not in url and '?' not in url for url in seen))
    def test_429_stops(self):
        def fake(self,url,authorize=None):return response(url,'',status=404 if url.endswith('/robots.txt') else 429)
        with patch.object(m.Fetcher,'get',fake):
            pages,events,_,_=m.crawl('https://example.com/')
        self.assertEqual(pages,[]);self.assertEqual(events[0]['state'],'stopped')
    def test_no_page_budget_over_50(self):
        with self.assertRaises(ValueError):m.crawl('https://example.com/',max_pages=51)

if __name__=='__main__':unittest.main()
