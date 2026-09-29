# 실제 검증 결과 — seo-auditor v0.1.0

검증일: 2026-09-29. 환경: Python 3.13.5, Linux x86_64.

## 완료

- 구조 검증 통과: 독립 플러그인 1개, 스킬 1개, 상대 경로, JSON/Python 문법.
- 자동 테스트 **44개 통과**, 실패 0개.
- 설치/업데이트/삭제 테스트는 임시 홈 폴더에서만 실행. 실제 사용자 앱 설정은 변경하지 않음.
- 공개 업로드 파일 목록 생성(`--plan`) 성공. 해당 명령은 GitHub 네트워크 호출 없이 실행.
- 기능별 검증: 메타·제목·canonical·noindex·JSON-LD 검사, 장식 이미지 예외, 인코딩, 사설 주소 차단, 리다이렉트·robots·요청 제한, 원문 보존 보고서.

## 검증하지 않은 범위

- 실제 사용자의 macOS/Windows, 다른 GPT 계정, ChatGPT/Codex UI 설치·활성화.
- 실제 LLM의 스킬 선택·출처 해석·스캔 정확도·이미지 생성 품질.
- 외부 이미지 API 호출, 실사이트 부하·렌더링·검색엔진 순위, 모든 OS/버전 조합.
- GitHub 저장소 생성/업로드와 공개 디렉터리 제출·승인.

예제 데이터는 합성 자료입니다. 자동 테스트 통과가 제품 사진의 상업적 정확성이나
실제 검색 노출·모든 호스트의 호환성을 보증하지 않습니다.

## Test output

```text
test_absent_canonical_is_not_critical (test_audit.HtmlTests.test_absent_canonical_is_not_critical) ... ok
test_basic_page (test_audit.HtmlTests.test_basic_page) ... ok
test_body_canonical_not_head_canonical (test_audit.HtmlTests.test_body_canonical_not_head_canonical) ... ok
test_duplicate_titles_limited_to_sample (test_audit.HtmlTests.test_duplicate_titles_limited_to_sample) ... ok
test_empty_alt_is_not_missing (test_audit.HtmlTests.test_empty_alt_is_not_missing) ... ok
test_invalid_encoding_fails_not_mojibake (test_audit.HtmlTests.test_invalid_encoding_fails_not_mojibake) ... ok
test_invalid_jsonld_is_syntax_error (test_audit.HtmlTests.test_invalid_jsonld_is_syntax_error) ... ok
test_legacy_korean_charset (test_audit.HtmlTests.test_legacy_korean_charset) ... ok
test_missing_alt_observed (test_audit.HtmlTests.test_missing_alt_observed) ... ok
test_multiple_h1_not_penalty (test_audit.HtmlTests.test_multiple_h1_not_penalty) ... ok
test_noindex_header (test_audit.HtmlTests.test_noindex_header) ... ok
test_noindex_intent_matters (test_audit.HtmlTests.test_noindex_intent_matters) ... ok
test_offline_status_is_unknown (test_audit.HtmlTests.test_offline_status_is_unknown) ... ok
test_relative_canonical_review (test_audit.HtmlTests.test_relative_canonical_review) ... ok
test_report_has_limits_and_text_snapshots (test_audit.HtmlTests.test_report_has_limits_and_text_snapshots) ... ok
test_script_does_not_create_fake_heading (test_audit.HtmlTests.test_script_does_not_create_fake_heading) ... ok
test_429_stops (test_audit.NetworkSafetyTests.test_429_stops) ... ok
test_crawl_budget_and_external_link_exclusion (test_audit.NetworkSafetyTests.test_crawl_budget_and_external_link_exclusion) ... ok
test_cross_origin_redirect_not_followed (test_audit.NetworkSafetyTests.test_cross_origin_redirect_not_followed) ... ok
test_fragment_removed_and_unicode_encoded (test_audit.NetworkSafetyTests.test_fragment_removed_and_unicode_encoded) ... ok
test_mixed_public_and_private_dns_rejected (test_audit.NetworkSafetyTests.test_mixed_public_and_private_dns_rejected) ... ok
test_no_page_budget_over_50 (test_audit.NetworkSafetyTests.test_no_page_budget_over_50) ... ok
test_private_dns_rejected (test_audit.NetworkSafetyTests.test_private_dns_rejected) ... ok
test_redirect_robots_checked_before_request (test_audit.NetworkSafetyTests.test_redirect_robots_checked_before_request) ... ok
test_robot_disallow_does_not_fetch_page (test_audit.NetworkSafetyTests.test_robot_disallow_does_not_fetch_page) ... ok
test_robots_403_stops_before_pages (test_audit.NetworkSafetyTests.test_robots_403_stops_before_pages) ... ok
test_robots_wildcard_stops_crawl (test_audit.NetworkSafetyTests.test_robots_wildcard_stops_crawl) ... ok
test_url_schemes_ports_credentials_blocked (test_audit.NetworkSafetyTests.test_url_schemes_ports_credentials_blocked) ... ok
test_conflicting_catalog_refused (test_package.PackageTests.test_conflicting_catalog_refused) ... ok
test_exactly_one_skill (test_package.PackageTests.test_exactly_one_skill) ... ok
test_existing_install_requires_replace (test_package.PackageTests.test_existing_install_requires_replace) ... ok
test_failed_copy_does_not_delete_existing (test_package.PackageTests.test_failed_copy_does_not_delete_existing) ... ok
test_install_preserves_other_settings (test_package.PackageTests.test_install_preserves_other_settings) ... ok
test_lock_prevents_concurrent_install (test_package.PackageTests.test_lock_prevents_concurrent_install) ... ok
test_publisher_excludes_runtime_data (test_package.PackageTests.test_publisher_excludes_runtime_data) ... ok
test_publisher_plan_is_offline (test_package.PackageTests.test_publisher_plan_is_offline) ... ok
test_publisher_rejects_secret (test_package.PackageTests.test_publisher_rejects_secret) ... ok
test_skill_mode_is_standalone (test_package.PackageTests.test_skill_mode_is_standalone) ... ok
test_structure (test_package.PackageTests.test_structure) ... ok
test_symlink_parent_refused (test_package.PackageTests.test_symlink_parent_refused) ... ok
test_uninstall_needs_confirmation (test_package.PackageTests.test_uninstall_needs_confirmation) ... ok
test_uninstall_only_own_plugin (test_package.PackageTests.test_uninstall_only_own_plugin) ... ok
test_unmanaged_folder_refused (test_package.PackageTests.test_unmanaged_folder_refused) ... ok
test_update_backs_up_outside_discovery (test_package.PackageTests.test_update_backs_up_outside_discovery) ... ok

----------------------------------------------------------------------
Ran 44 tests in 0.051s

OK
```
