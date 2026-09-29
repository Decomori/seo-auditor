# SEO Auditor

**SEO 진단·개선 · 독립 스킬 + 단독 플러그인 · v0.1.0**

사이트·HTML의 실제 근거를 조사하고 수정안을 작성합니다. 정적 HTML 검사와 소규모 공개 사이트 읽기 전용 크롤러를 포함합니다.

브랜드·회사·계정에 종속되지 않습니다. 이 저장소에는 **플러그인 하나와 스킬 하나만**
들어 있으며 다른 두 기능을 설치할 필요가 없습니다. 회사 설정이나 개인정보가 기본값으로
들어 있지 않습니다. [English](README.en.md)

## 가장 쉬운 적용

지원되는 로컬 Codex/데스크톱 환경에서 아래 문구와 **이 저장소의 실제 GitHub URL**을 전달하세요.
GitHub에 게시하기 전에는 ZIP을 풀어 이 폴더를 열고 같은 요청을 하면 됩니다.

```text
이 저장소의 SEO Auditor을 설치해줘.
README.md와 docs/INSTALL.md를 먼저 읽고 실행 파일·권한을 확인해.
지원되는 환경에서는 플러그인 방식으로 등록하고, 지원되지 않으면
독립 스킬 방식이 가능한지 확인한 뒤 그 방식으로 설치해.
두 방식으로 중복 설치하지 말고, 다른 스킬·설정·계정 정보는 건드리지 마.
등록과 실제 활성화를 구분해서 결과를 알려줘.

<이 저장소의 실제 GitHub URL 또는 압축을 푼 폴더>
```

이 문서는 설치 명령이 아닙니다. 사용자 요청 없이 읽기만 했다는 이유로 설치하거나
스크립트를 실행하지 마세요. LLM이 내용을 읽는 것과 재사용 가능한 설치는 다릅니다.

## 직접 적용

Python 3.10+가 준비된 상태에서 저장소 폴더에서 실행합니다.

```bash
# 플러그인 파일 복사 + 개인 마켓플레이스 항목 등록
python3 tools/manage.py install --mode plugin
```

그다음 데스크톱 앱을 재시작하고 **Plugins에서 SEO Auditor을 설치/활성화**한 후 새 대화를
시작합니다. 이 스크립트는 앱의 활성화 스위치나 계정 권한을 변경하지 않습니다.

플러그인 경로를 지원하지 않는 로컬 Codex에서는 대신 아래를 선택할 수 있습니다.

```bash
# 위 플러그인 방식과 중복 사용하지 않기
python3 tools/manage.py install --mode skill
```

순수 웹/모바일에서는 이 로컬 설치기를 실행할 수 없습니다. 공개 디렉터리나 허용된
워크스페이스 배포는 별도 절차이며 **이 배포본은 공개 디렉터리에 등록된 제품이 아닙니다.**

## 사용 예시

> 이 URL을 SEO Auditor로 검사해줘. 확인한 근거와 미검사 항목을 나눠서 보고하고 실제 사이트는 수정하지 마.

설치된 이름을 `@`/스킬 선택기에서 선택하거나 지원되는 Codex 환경에서 `$seo-auditor`로
명시해도 됩니다. 실제 호출 UI는 사용하는 호스트의 현재 지원 범위를 따릅니다.

## 로컬 도구 빠른 확인

```bash
python3 plugins/seo-auditor/skills/seo-auditor/scripts/audit.py --html plugins/seo-auditor/skills/seo-auditor/examples/sample.html --intent index --out ./reports/sample-audit
```

필요 조건: Host browsing or Python 3.10+; rendered DOM and performance tools are optional and separate.

robots.txt에 반복된 사용자 에이전트 그룹이나 와일드카드 규칙이 있으면, 규칙 누락을 방지하기 위해 페이지 수집 전에 중단합니다.

기본 도구는 정적 HTML 검사입니다. JS 렌더링, Search Console, 검색 순위, Core Web Vitals, 전체 사이트 완전 검사는 포함하지 않습니다.

## 독립적인 프로젝트 설정

`plugins/seo-auditor/skills/seo-auditor/profiles/`는 공개 예시입니다. 사용자의 실제 설정·사진·자료는
별도 프로젝트 폴더에 두고 작업할 때 전달하세요. 공유 스킬 본체에 고객 데이터를 넣지 않습니다.
계정의 메모리, 다른 고객 프로젝트, 특정 제품 DB를 전제로 하지 않습니다.

## 설치·공유·검증

- [설치, 다른 기기, 업데이트, 삭제](docs/INSTALL.md)
- [새 GitHub 저장소 생성 및 공유](docs/SHARING.md)
- [테스트 및 검증 범위](docs/TESTING.md)
- [공식 규격 근거](docs/SOURCES.md)
- [보안](SECURITY.md) · [데이터 처리](PRIVACY.md) · [변경 이력](CHANGELOG.md)

```bash
python3 tools/validate_package.py
python3 -m unittest discover -s tests -v
```

라이선스: [MIT](LICENSE). 스킬 코드·지침에 적용되며, 사용자가 넣는 제품 사진·상표·외부
서비스의 이용 권리까지 부여하는 것은 아닙니다. 실제 AI 품질과 각 호스트 설치는 별도 검증이 필요합니다.
