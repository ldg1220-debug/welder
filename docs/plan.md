# 용접사 인증서 발행 앱 — 계획/결정 사항

## 확정된 결정
- **구조**: 단일 HTML 파일(`welder-cert.html`), 오프라인, 1인 사용, 빌드/CDN 없음
- **저장**: 브라우저 IndexedDB + JSON 백업/복원 (백업 안 하면 브라우저 데이터 삭제 시 소실)
- **PDF**: 인증서 HTML을 A4 인쇄 CSS로 렌더 → 브라우저 "PDF로 저장" (jsPDF/html2canvas 미사용: 오프라인·한글 폰트 문제 회피)
- **범위(1차)**: ISO 9606-1, 용접사 CRUD, WQT 입력 + 승인범위 자동 산출, 인증서 출력, 대시보드(만료/6개월 서명 갱신)
- **2차 이후**: ASME IX / AWS D1.1(플러그인), QR 검증, OCR, 다중 사용자

## 규격 엔진 (`calculateRangeOfApproval(input, standard)`)
순수 함수. 각 결과 항목에 `source`(근거 표)와 `confidence`(`high` / `check`)를 붙인다.
지원하지 않는 조합은 `manual_review_required: true`를 반환하고 UI에서 경고한다 (틀린 값보다 "모름"이 안전).

| 항목 | 규칙 | 신뢰도 |
|---|---|---|
| 두께 BW | t<3: t~2t / 3≤t<12: 3~2t / t≥12: ≥3 | high (샘플·사용자 예시 2.3→2.3~4.6) |
| 두께 FW | t<3: t~2t / t≥3: ≥3 | high |
| 유효기간 | 용접일 + 3년 − 1일 (9.3 a) | high (샘플) |
| 판재→파이프 | P는 P, T(F:D≥500mm / R:D≥75mm) | high (샘플) |
| FM1 | FM1, FM2 | high (샘플) |
| 용가재 S | S, M | high (샘플) |
| 배킹 ss nb | ss nb, ss mb, bs | high (샘플) |
| 자세 BW PA/PC/PF | PA→PA, PC→PA·PC, PF→PA·PF | high |
| 자세 PE/PG, FW 전체 | 표 기반 | **check** |
| 파이프 외경 | D≤25: D~2D / D>25: ≥0.5D(최소 25) | **check** |
| FM2 이상, S 외 용가재 종류, ss mb/bs 등 | | **check** |

**IWE 자격자가 Table 3~9 원문과 대조해야 하는 항목은 `check`로 표시**된다. 확정되면 `confidence`를 `high`로 바꾸면 된다.

## 판정 기준
- 기본: ISO 9606-1 Table 1 — BW: VT + (RT/UT 또는 Bend/Fracture), FW: VT + (Macro 또는 Fracture). Fail이 하나라도 있으면 불합격
- 설정에서 "사내 엄격 기준" 선택 시 BW: VT+RT/UT+Bend, FW: VT+Macro (샘플 인증서는 VT+RT만으로 발행되어 있어 기본값은 ISO)

## 테스트
`node tests/engine.test.mjs` — HTML 안의 ENGINE 블록을 꺼내 검증 (19개)
