# 설치 / 업데이트 / 제거

## 먼저 확인

이 배포본은 서로 독립적인 세 프로젝트 중 **SEO Auditor 하나**입니다. 다른 두 패키지는 필요하지
않습니다. 로컬 파일/명령 실행이 가능한 환경이 대상이며 앱 버전·조직 정책에 따라
플러그인 등록이 제한될 수 있습니다. 셸 명령은 시스템 권한을 우회하지 않습니다.
Python 3.10+를 확인하세요: `python3 --version`. Windows에서는 설치 상태에 따라
아래의 `python3` 대신 `py -3` 또는 `python`을 사용합니다.

## A. 플러그인 등록 (지원되는 데스크톱 환경)

1. ZIP을 풀거나 저장소를 가져옵니다. README와 스크립트를 검토합니다.
2. 저장소 폴더에서 `python3 tools/manage.py install --mode plugin`을 실행합니다.
3. 앱을 재시작합니다. Plugins의 개인 소스에서 **SEO Auditor**을 찾아 설치/활성화합니다.
4. 새 대화에서 사용합니다. 목록에 보이는 것과 활성화·도구 실행 성공은 별개입니다.

설치기는 `~/.codex/plugins/seo-auditor/`에 이 플러그인의 파일만 복사하고
`~/.agents/plugins/marketplace.json`에서 이 이름의 항목만 추가합니다. 기존 항목·계정
인증·전역 정책은 유지합니다. 동일 이름의 다른 경로가 있으면 덮어쓰지 않고 중단합니다.
`source.path`는 마켓플레이스의 루트(개인형에서는 홈 폴더) 기준 상대 경로입니다.

## B. 스킬만 설치 (플러그인과 중복 사용 금지)

```bash
python3 tools/manage.py install --mode skill
```

목적지: `~/.agents/skills/seo-auditor/`. 스킬 본체·참고자료·도구만 복사됩니다.
새 대화 또는 재시작 후 선택합니다. 계정이 아니라 해당 OS 홈의 파일입니다.
공식 `$skill-installer`를 사용하는 호스트에는 저장소의
`plugins/seo-auditor/skills/seo-auditor` 경로를 지정할 수도 있습니다.

## GitHub 마켓플레이스 방식

공식 문서에 나온 명령을 지원하는 Codex CLI에서, 실제 게시 후 사용할 수 있습니다.
`OWNER/REPOSITORY`는 실제 저장소 이름으로 바꾸고 아직 없는 태그를 입력하지 마세요.

```bash
codex plugin marketplace add OWNER/REPOSITORY
```

지원되는 앱의 Plugins에서 해당 소스를 선택합니다. CLI의 `/plugins` UI는 사용하는
버전에서 제공되는지 확인합니다. 명령이 없다면 최신 지원 범위를 확인하거나 A/B 방식을
선택합니다. GitHub 소스 등록은 공개 디렉터리 등록이나 모든 기기의 동기화가 아닙니다.

## 도구 준비

Host browsing or Python 3.10+; rendered DOM and performance tools are optional and separate.

이미지 로컬 도구가 필요한 경우에만, 별도 가상환경에서 승인 후 설치합니다.

```bash
python3 -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows PowerShell uses .venv\Scripts\Activate.ps1 (subject to local policy).
python -m pip install -r requirements.txt
```

설치기는 패키지 설치, 이미지 생성 과금, 외부 앱 로그인, MCP 연결을 자동 실행하지 않습니다.

## 업데이트

새 소스를 내려받고 변경 내역과 코드를 검토한 다음 같은 설치 방식으로 실행합니다.

```bash
python3 tools/manage.py install --mode plugin --replace
# standalone mode instead: --mode skill --replace
```

이전 파일은 `~/.agents/independent-skill-backups/`로 이동합니다. 이 경로는 스킬 검색
폴더 밖이므로 백업이 두 번째 스킬로 등록되지 않습니다. 앱을 재시작해 파일 갱신을 확인하고
설치된 캐시가 이전 버전이면 Plugins에서 해당 항목만 다시 설치합니다. 자동 동기화는 없습니다.
GitHub 마켓플레이스로 관리하는 경우 공식 `codex plugin marketplace upgrade`의 지원 여부와
적용 범위를 확인하고 해당 소스만 갱신하세요. 서로 다른 관리 방식을 섞지 마세요.

## 제거

먼저 앱에서 이 플러그인을 비활성화/제거합니다. 로컬 등록 파일 제거:

```bash
python3 tools/manage.py uninstall --mode plugin --confirm
# standalone mode instead: --mode skill --confirm
```

설치기의 영수증이 있는 자기 폴더만 삭제합니다. 고객 데이터·다른 스킬·백업은 건드리지
않습니다. 앱 관리자가 캐시한 설치본은 앱 UI에서 따로 제거해야 할 수 있습니다.

## 다른 계정 / 기기 / 별도 프로필

다른 기기는 같은 저장소/ZIP으로 다시 설치합니다. 같은 OS 계정의 로컬 스킬은 동일한
폴더를 읽는 실행 환경에서만 재사용됩니다. 별도 앱 프로필이 반드시 같은 위치를 읽는다고
가정하지 않습니다. `CODEX_HOME` 변경이 모든 스킬 경로를 바꾸는 것도 전제하지 마세요.
`tools/manage.py status --mode plugin`으로 파일 위치를 확인하고 실제 호스트의 로딩 경로를
점검합니다. `--home`은 명시적 OS 홈 기준 경로 지정/테스트용이며 GPT 계정 전환 기능이 아닙니다.
외부 앱 연결과 유료 기능 사용 권한은 계정마다 별도입니다.

## 웹 / 모바일

이 ZIP이나 GitHub URL을 일반 대화에 넣는 것만으로 영구 설치되지는 않습니다. 공개
디렉터리 게시 또는 허용되는 워크스페이스 공유가 별도로 필요합니다. 로컬 스크립트와
데스크톱 전용 앱 기능이 모든 모바일 환경에서 작동한다고 표시하지 마세요.
