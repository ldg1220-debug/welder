"""용접사 자격 통합 관리 시스템 (Streamlit). 실행: streamlit run app.py"""
from datetime import date

import streamlit as st

import database
import logic
import pdf_generator
import repository as repo

st.set_page_config(page_title="용접사 자격 관리", page_icon="🔧", layout="wide")




def db():
    c = database.get_conn()
    database.init_db(c)
    return c


RESULT_OPTS = [None, logic.PASS, logic.FAIL]
RESULT_LABEL = {None: "미확정", logic.PASS: "Pass", logic.FAIL: "Fail"}

page = st.sidebar.radio("메뉴", ["대시보드", "용접사 관리", "시험 기록 관리"])
c = db()

# ---------------------------------------------------------------- 대시보드
if page == "대시보드":
    st.title("대시보드")
    today = st.sidebar.date_input("기준일", date.today())
    active_only = st.sidebar.checkbox("재직자만 보기", True)
    d = repo.dashboard(c, today, active_only)
    a, b, x = st.columns(3)
    a.metric("자격 유효 인원", d["valid_welders"])
    b.metric("자격 만료 인원", d["expired_welders"])
    x.metric("합격 인증서 수", d["total_certs"])
    st.caption("유효 = 만료되지 않은 합격 인증서를 1건 이상 보유. 만료일 = 용접일 + 3년 - 1일 (EN ISO 9606-1 9.3 a)")
    al = d["alerts"]
    if al.empty:
        st.success("알림 대상이 없습니다.")
    else:
        cols = ["표시", "welder_no", "name", "company", "joint_type", "process", "position",
                "welding_date", "expire_date", "renewal_count", "경과개월"]
        for label, key in (("🔴 만료", "expired"), ("🟡 6개월 서명 갱신 필요", "renewal")):
            sub = al[al["alert"] == key]
            st.subheader(f"{label} ({len(sub)})")
            st.dataframe(sub[cols], width="stretch", hide_index=True)

# ---------------------------------------------------------------- 용접사 관리
elif page == "용접사 관리":
    st.title("용접사 관리")
    with st.form("new_welder", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        no = c1.text_input("용접사 번호 (예: RM-WD-24001)")
        name = c2.text_input("성명")
        birth = c3.date_input("생년월일", date(1980, 1, 1), min_value=date(1940, 1, 1), max_value=date.today())
        c4, c5, c6 = st.columns(3)
        company = c4.text_input("소속")
        role = c5.selectbox("직무", ["용접사", "취부사", "LBW 용접 오퍼레이터"])
        status = c6.selectbox("상태", ["재직", "퇴사"])
        if st.form_submit_button("등록"):
            if not no.strip() or not name.strip():
                st.error("용접사 번호와 성명은 필수입니다.")
            else:
                try:
                    repo.add_welder(c, no, name, birth.isoformat(), company, role, status)
                    st.success(f"{name} 등록 완료")
                except Exception as e:  # 중복 번호 등
                    st.error(f"등록 실패: {e}")
    flt = st.radio("상태 필터", ["전체", "재직", "퇴사", "미확인"], horizontal=True)
    st.dataframe(repo.list_welders(c, flt), width="stretch", hide_index=True)

# ---------------------------------------------------------------- 시험 기록 관리
else:
    st.title("시험 기록 관리")
    welders = repo.list_welders(c)
    if welders.empty:
        st.info("먼저 용접사를 등록하세요.")
        st.stop()
    labels = {int(r.id): f"{r.welder_no} · {r['name']} ({r.company or '-'})" for _, r in welders.iterrows()}
    wid = st.selectbox("용접사", list(labels), format_func=labels.get)

    with st.expander("새 시험 기록 입력", expanded=False):
        with st.form("new_test", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            wdate = c1.date_input("시험재 용접일자 (Date of Welding)", date.today())
            project = c2.text_input("프로젝트 및 제작품목")
            process = c3.selectbox("용접 방법", ["135 MAG", "141 TIG", "521 LBW"])
            c4, c5, c6, c7 = st.columns(4)
            joint = c4.selectbox("시편 형태", ["BW", "FW"])
            thick = c5.number_input("두께 t (mm)", 0.0, 100.0, 12.0, 0.1)
            pos = c6.selectbox("용접 자세", ["PA", "PB", "PC", "PD", "PF", "PG"])
            filler = c7.text_input("용가재", "FM 1")
            backing = st.selectbox("배킹", ["nb", "mb", "Ceramic", "N/A"])
            st.markdown("**검사 결과** (BW: VT + RT/UT + Bend, FW: VT + Macro)")
            r1, r2, r3 = st.columns(3)
            vt = r1.selectbox("VT 육안", RESULT_OPTS, format_func=RESULT_LABEL.get)
            rt = r2.selectbox("RT/UT 체적", RESULT_OPTS, format_func=RESULT_LABEL.get)
            mb = r3.selectbox("Bend(BW) / Macro(FW)", RESULT_OPTS, format_func=RESULT_LABEL.get)
            if st.form_submit_button("저장"):
                tid = repo.add_test(c, wid, project, wdate, process, joint, thick, pos, filler, backing, vt, rt, mb)
                row = repo.get_test(c, tid)
                st.success(f"저장 완료 · 판정 {row['final_status']} · 만료일 {row['expire_date']}")

    tests = repo.list_tests(c, wid)
    st.subheader(f"시험 기록 ({len(tests)})")
    if tests.empty:
        st.info("등록된 시험 기록이 없습니다.")
    for _, t in tests.iterrows():
        icon = {"합격": "✅", "불합격": "❌"}.get(t.final_status, "⏳")
        head = f"{icon} {t.welding_date} · {t.joint_type} · {t.process} · {t.thickness:g}t · {t.position} · {t.final_status}"
        with st.expander(head):
            st.write(f"{t.project_name or ''} — 만료일 **{t.expire_date}**, 서명 갱신 {t.renewal_count}/{logic.MAX_RENEWALS}회")
            k = f"t{t.test_id}"
            r1, r2, r3, r4 = st.columns([1, 1, 1, 1])
            cur = [t.vt_result, t.rt_ut_result, t.macro_bend_result]
            new = [col.selectbox(lbl, RESULT_OPTS, RESULT_OPTS.index(v if v in RESULT_OPTS else None),
                                 format_func=RESULT_LABEL.get, key=f"{k}{i}")
                   for i, (col, lbl, v) in enumerate(zip((r1, r2, r3), ("VT", "RT/UT", "Bend/Macro"), cur))]
            if r4.button("결과 저장", key=f"{k}s"):
                st.toast(f"판정: {repo.update_results(c, t.test_id, *new)}")
                st.rerun()
            b1, b2 = st.columns(2)
            if t.final_status == "합격":
                row = repo.get_test(c, t.test_id)
                birth = welders.loc[welders.id == wid, "birth_date"].iloc[0]
                b1.download_button("📄 인증서 다운로드", pdf_generator.build_certificate(row, birth),
                                   file_name=f"cert_{t.welder_no}_{t.welding_date}_{t.joint_type}_{t.position}.pdf",
                                   mime="application/pdf", key=f"{k}d")
                if b2.button("6개월 서명 갱신 기록", key=f"{k}r"):
                    if repo.add_renewal(c, t.test_id):
                        st.rerun()
                    else:
                        st.warning("갱신은 최대 5회까지 기록할 수 있습니다.")
