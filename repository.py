"""DB 읽기/쓰기 함수. 판정·만료일 계산은 항상 logic 모듈을 거친다."""
from __future__ import annotations

import sqlite3
from datetime import date

import pandas as pd

import logic


def add_welder(conn, welder_no, name, birth_date, company, role, status="재직") -> int:
    cur = conn.execute(
        "INSERT INTO welders (welder_no, name, birth_date, company, role, status) VALUES (?,?,?,?,?,?)",
        (welder_no.strip(), name.strip(), birth_date, company, role, status),
    )
    conn.commit()
    return cur.lastrowid


def list_welders(conn, status: str | None = None) -> pd.DataFrame:
    sql, args = "SELECT * FROM welders", []
    if status and status != "전체":
        sql += " WHERE status = ?"
        args.append(status)
    return pd.read_sql_query(sql + " ORDER BY welder_no", conn, params=args)


def add_test(conn, welder_id, project_name, welding_date: date, process, joint_type, thickness,
             position, filler_material, backing, vt, rt_ut, macro_bend,
             issue_date: date | None = None) -> int:
    cur = conn.execute(
        """INSERT INTO test_records (welder_id, project_name, welding_date, process, joint_type,
           thickness, position, filler_material, backing) VALUES (?,?,?,?,?,?,?,?,?)""",
        (welder_id, project_name, welding_date.isoformat(), process, joint_type, thickness,
         position, filler_material, backing),
    )
    test_id = cur.lastrowid
    status = logic.judge(joint_type, vt, rt_ut, macro_bend)
    conn.execute(
        """INSERT INTO test_results_and_certs (test_id, vt_result, rt_ut_result, macro_bend_result,
           final_status, issue_date, expire_date, renewal_count) VALUES (?,?,?,?,?,?,?,0)""",
        (test_id, vt, rt_ut, macro_bend, status,
         issue_date.isoformat() if issue_date else None,
         logic.calc_expire_date(welding_date).isoformat()),
    )
    conn.commit()
    return test_id


def update_results(conn, test_id, vt, rt_ut, macro_bend) -> str:
    joint = conn.execute("SELECT joint_type FROM test_records WHERE id=?", (test_id,)).fetchone()[0]
    status = logic.judge(joint, vt, rt_ut, macro_bend)
    conn.execute(
        "UPDATE test_results_and_certs SET vt_result=?, rt_ut_result=?, macro_bend_result=?, final_status=? WHERE test_id=?",
        (vt, rt_ut, macro_bend, status, test_id),
    )
    conn.commit()
    return status


def add_renewal(conn, test_id) -> bool:
    """6개월 서명 갱신 1회 기록. 최대 5회."""
    cur = conn.execute(
        "UPDATE test_results_and_certs SET renewal_count = renewal_count + 1 WHERE test_id=? AND renewal_count < ?",
        (test_id, logic.MAX_RENEWALS),
    )
    conn.commit()
    return cur.rowcount > 0


TEST_SELECT = """
SELECT t.id AS test_id, w.id AS welder_id, w.welder_no, w.name, w.company, w.status AS welder_status,
       t.project_name, t.welding_date, t.process, t.joint_type, t.thickness, t.position,
       t.filler_material, t.backing,
       r.vt_result, r.rt_ut_result, r.macro_bend_result, r.final_status,
       r.issue_date, r.expire_date, r.renewal_count
FROM test_records t
JOIN welders w ON w.id = t.welder_id
JOIN test_results_and_certs r ON r.test_id = t.id
"""


def list_tests(conn, welder_id: int | None = None) -> pd.DataFrame:
    sql, args = TEST_SELECT, []
    if welder_id:
        sql += " WHERE w.id = ?"
        args.append(welder_id)
    return pd.read_sql_query(sql + " ORDER BY t.welding_date DESC, t.id DESC", conn, params=args)


def get_test(conn, test_id) -> sqlite3.Row:
    return conn.execute(TEST_SELECT + " WHERE t.id = ?", (test_id,)).fetchone()


def dashboard(conn, today: date, active_only: bool = True) -> dict:
    """합격 인증서 기준 유효/만료 통계와 알림 리스트.

    용접사는 '만료되지 않은 합격 인증서를 1건이라도 가지면' 자격 유효로 본다.
    알림(만료/갱신)은 인증서 단위로 표시한다.
    """
    df = list_tests(conn)
    df = df[df["final_status"] == "합격"].copy()
    if active_only:
        df = df[df["welder_status"] != "퇴사"]
    if df.empty:
        return {"valid_welders": 0, "expired_welders": 0, "alerts": df, "total_certs": 0}
    df["wd"] = pd.to_datetime(df["welding_date"]).dt.date
    df["ed"] = pd.to_datetime(df["expire_date"]).dt.date
    df["alert"] = [logic.cert_alert(w, e, int(n), today)
                   for w, e, n in zip(df["wd"], df["ed"], df["renewal_count"])]
    valid_ids = set(df.loc[df["ed"] >= today, "welder_id"])
    all_ids = set(df["welder_id"])
    alerts = df[df["alert"].notna()].copy()
    alerts["표시"] = alerts["alert"].map({"expired": "🔴 만료", "renewal": "🟡 6개월 서명 갱신 필요"})
    alerts["경과개월"] = [logic.months_between(w, today) for w in alerts["wd"]]
    return {"valid_welders": len(valid_ids), "expired_welders": len(all_ids - valid_ids),
            "alerts": alerts, "total_certs": len(df)}
