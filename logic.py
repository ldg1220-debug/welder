"""비즈니스 로직 (EN ISO 9606-1 9.3 a). UI/DB와 분리해 단위 테스트 가능하게 유지."""
from __future__ import annotations

import calendar
from datetime import date, timedelta

PASS, FAIL = "Pass", "Fail"
MAX_RENEWALS = 5


def _add_years(d: date, years: int) -> date:
    try:
        return d.replace(year=d.year + years)
    except ValueError:  # 2/29 -> 비윤년
        return d.replace(year=d.year + years, day=28)


def calc_expire_date(welding_date: date) -> date:
    """만료일 = 용접일 + 3년 - 1일 (예: 2024-08-21 -> 2027-08-20)."""
    return _add_years(welding_date, 3) - timedelta(days=1)


def validity_text(welding_date: date, expire_date: date) -> str:
    return f"{welding_date:%Y-%m-%d} ~ {expire_date:%Y-%m-%d} (refer to 9.3 a)"


def judge(joint_type: str, vt: str | None, rt_ut: str | None, macro_bend: str | None) -> str:
    """BW: VT+RT/UT+Bend, FW: VT+Macro 모두 Pass -> 합격. 하나라도 Fail -> 불합격. 그 외 진행중."""
    required = [vt, rt_ut, macro_bend] if joint_type == "BW" else [vt, macro_bend]
    if any(r == FAIL for r in required):
        return "불합격"
    if all(r == PASS for r in required):
        return "합격"
    return "진행중"


def months_between(start: date, end: date) -> int:
    """start~end 사이의 '꽉 찬' 개월 수 (일자 미달이면 1개월 차감)."""
    months = (end.year - start.year) * 12 + (end.month - start.month)
    # 말일 보정: 1/31 -> 2/28 은 꽉 찬 1개월로 본다
    end_day_needed = min(start.day, calendar.monthrange(end.year, end.month)[1])
    if end.day < end_day_needed:
        months -= 1
    return max(months, 0)


def cert_alert(welding_date: date, expire_date: date, renewal_count: int, today: date) -> str | None:
    """'expired'(적색) / 'renewal'(황색) / None."""
    if today > expire_date:
        return "expired"
    if months_between(welding_date, today) > renewal_count * 6 + 6:
        return "renewal"
    return None
