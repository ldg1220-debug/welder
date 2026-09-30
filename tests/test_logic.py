from datetime import date

import pytest

import database
import logic
import pdf_generator
import repository as repo


def test_expire_date_matches_sample_certificate():
    assert logic.calc_expire_date(date(2024, 8, 21)) == date(2027, 8, 20)
    assert logic.validity_text(date(2024, 8, 21), date(2027, 8, 20)) == "2024-08-21 ~ 2027-08-20 (refer to 9.3 a)"


def test_expire_date_leap_day():
    assert logic.calc_expire_date(date(2024, 2, 29)) == date(2027, 2, 27)


@pytest.mark.parametrize("joint,vt,rt,mb,expected", [
    ("BW", "Pass", "Pass", "Pass", "합격"),
    ("BW", "Pass", "Pass", None, "진행중"),
    ("BW", "Pass", "Fail", "Pass", "불합격"),
    ("FW", "Pass", None, "Pass", "합격"),   # FW는 RT/UT 불필요
    ("FW", "Pass", "Fail", "Pass", "합격"),
    ("FW", "Fail", None, "Pass", "불합격"),
])
def test_judge(joint, vt, rt, mb, expected):
    assert logic.judge(joint, vt, rt, mb) == expected


def test_months_between():
    assert logic.months_between(date(2024, 8, 21), date(2025, 2, 20)) == 5
    assert logic.months_between(date(2024, 8, 21), date(2025, 2, 21)) == 6
    assert logic.months_between(date(2024, 1, 31), date(2024, 2, 29)) == 1


def test_alerts():
    w, e = date(2024, 8, 21), date(2027, 8, 20)
    assert logic.cert_alert(w, e, 0, date(2025, 2, 21)) is None          # 정확히 6개월: 아직 초과 아님
    assert logic.cert_alert(w, e, 0, date(2025, 3, 21)) == "renewal"     # 7개월
    assert logic.cert_alert(w, e, 1, date(2025, 3, 21)) is None          # 1회 갱신 -> 12개월까지
    assert logic.cert_alert(w, e, 5, date(2027, 8, 20)) is None
    assert logic.cert_alert(w, e, 5, date(2027, 8, 21)) == "expired"


@pytest.fixture
def conn():
    c = database.get_conn(":memory:")
    database.init_db(c)
    return c


def _seed(conn, joint="BW", vt="Pass", rt="Pass", mb="Pass", wdate=date(2024, 8, 21)):
    wid = repo.add_welder(conn, f"RM-WD-{joint}{wdate.year}", "홍길동", "1980-01-01", "로만시스㈜", "용접사")
    return repo.add_test(conn, wid, "테스트", wdate, "135 MAG", joint, 12, "PC", "FM 1", "nb", vt, rt, mb)


def test_add_test_sets_expiry_and_status(conn):
    row = repo.get_test(conn, _seed(conn))
    assert row["final_status"] == "합격" and row["expire_date"] == "2027-08-20"


def test_update_results_and_renewal_cap(conn):
    tid = _seed(conn, mb=None)
    assert repo.get_test(conn, tid)["final_status"] == "진행중"
    assert repo.update_results(conn, tid, "Pass", "Pass", "Pass") == "합격"
    assert [repo.add_renewal(conn, tid) for _ in range(6)] == [True] * 5 + [False]


def test_dashboard_counts(conn):
    _seed(conn, wdate=date(2024, 8, 21))        # 만료 전, 갱신 필요
    _seed(conn, joint="FW", rt=None, wdate=date(2020, 1, 10))  # 만료
    d = repo.dashboard(conn, date(2025, 3, 21))
    assert (d["valid_welders"], d["expired_welders"]) == (1, 1)
    assert sorted(d["alerts"]["alert"]) == ["expired", "renewal"]


def test_certificate_pdf(conn):
    tid = _seed(conn)
    pdf = pdf_generator.build_certificate(repo.get_test(conn, tid), "1980-01-01")
    assert pdf.startswith(b"%PDF")
    with pytest.raises(ValueError):
        pdf_generator.build_certificate(repo.get_test(conn, _seed(conn, joint="FW", vt="Fail", wdate=date(2025, 1, 1))))


def test_designation(conn):
    assert pdf_generator.designation(repo.get_test(conn, _seed(conn))) == "EN ISO 9606-1 135 P BW FM1 S t12 PC ss nb"
