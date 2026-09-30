# 용접사 자격 통합 관리 시스템

EN ISO 9606-1 기준 용접사 자격 시험 기록 관리, 유효기간 계산(9.3 a), 인증서 PDF 발행.

## 실행
```
pip install -r requirements.txt
python importer.py <기존_엑셀.xlsx> --reset   # 선택: 기존 엑셀 임포트 (data/welder.db 생성)
streamlit run app.py
python -m pytest
```
DB 경로는 환경변수 `WELDER_DB`로 변경할 수 있습니다. 엑셀/DB에는 개인정보가 있어 `.gitignore`로 제외되어 있습니다.

## 구성
- `database.py` 스키마(sqlite3) · `logic.py` 만료일/합불/갱신 알림 규칙 · `repository.py` DB 접근
- `importer.py` 엑셀 임포트 · `pdf_generator.py` 인증서 PDF · `app.py` Streamlit UI · `tests/`

## 규칙
- 만료일 = 용접일 + 3년 - 1일. 합격: BW = VT + RT/UT + Bend, FW = VT + Macro 모두 Pass
- 🔴 만료일 경과 / 🟡 용접일 이후 경과 개월 > 갱신횟수×6+6 (갱신 최대 5회)
