"""EN ISO 9606-1 용접사 승인 시험 인증서 PDF 생성 (reportlab, A4)."""
from __future__ import annotations

import io
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle

import logic

# 한글 폰트 파일 없이도 동작하는 내장 CID 폰트
pdfmetrics.registerFont(UnicodeCIDFont("HYGothic-Medium"))
FONT = "HYGothic-Medium"

PROCESS_CODE = {"GMAW": "135", "MAG": "135", "GTAW": "141", "TIG": "141", "LBW": "521"}


def _fmt_t(t) -> str:
    return "" if t is None else (f"{t:g}")


def designation(row) -> str:
    """예: EN ISO 9606-1 135 P BW FM1 S t12 PC ss nb"""
    code = (row["process"] or "").split(" ")[0]
    parts = ["EN ISO 9606-1", code, "P", row["joint_type"],
             (row["filler_material"] or "").replace(" ", ""), "S", f"t{_fmt_t(row['thickness'])}", row["position"] or ""]
    if row["joint_type"] == "BW":
        parts.append("ss " + ("mb" if (row["backing"] or "").lower() in ("mb", "ceramic") else "nb"))
    return " ".join(p for p in parts if p)


def _mark(v) -> str:
    return {"Pass": "o", "Fail": "X"}.get(v, "-")


def build_certificate(row, birth_date: str | None = None, issue_date: date | None = None) -> bytes:
    """합격 건에 대한 인증서 PDF 바이트를 반환한다. 합격이 아니면 ValueError."""
    if row["final_status"] != "합격":
        raise ValueError("합격 처리된 시험 기록만 인증서를 발행할 수 있습니다.")
    wd = date.fromisoformat(row["welding_date"])
    ed = date.fromisoformat(row["expire_date"])
    issued = date.fromisoformat(row["issue_date"]) if row["issue_date"] else (issue_date or date.today())
    bw = row["joint_type"] == "BW"

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4
    c.setTitle(f"Welder's Approval Test Certificate - {row['welder_no']}")
    c.setFont(FONT, 16)
    c.drawCentredString(W / 2, H - 45, "용접사 승인 시험 인증서")
    c.setFont(FONT, 12)
    c.drawCentredString(W / 2, H - 63, "Welder's Approval test certificate")

    info = [
        ["Designation", designation(row)],
        ["용접사 성명 Welder's Name", row["name"]],
        ["용접사 번호 Welder's ID No.", row["welder_no"]],
        ["생년월일 Date of birth", birth_date or ""],
        ["소속 Employer", row["company"] or ""],
        ["프로젝트 Project", row["project_name"] or ""],
        ["Code/Testing Standard", "EN ISO 9606-1"],
    ]
    t = Table(info, colWidths=[150, W - 80 - 150], rowHeights=18)
    t.setStyle(TableStyle([("FONT", (0, 0), (-1, -1), FONT, 9), ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                           ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke)]))
    tw, th = t.wrapOn(c, W, H)
    y = H - 85 - th
    t.drawOn(c, 40, y)

    detail = [
        ["Division", "Weld Test Detail"],
        ["용접방법 Welding process", row["process"] or ""],
        ["용접 유형 Type of Weld", row["joint_type"]],
        ["용가재 Filler material", row["filler_material"] or ""],
        ["시험재 두께 Material Thickness", _fmt_t(row["thickness"])],
        ["용접자세 Welding Position", row["position"] or ""],
        ["가우징/배킹 Gouging/Backing", row["backing"] or "N/A"],
    ]
    t2 = Table(detail, colWidths=[200, W - 80 - 200], rowHeights=18)
    t2.setStyle(TableStyle([("FONT", (0, 0), (-1, -1), FONT, 9), ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey), ("ALIGN", (1, 0), (1, -1), "CENTER")]))
    _, th2 = t2.wrapOn(c, W, H)
    y -= th2 + 14
    t2.drawOn(c, 40, y)

    tests = [["Type of test", "Performed and accepted"],
             ["육안검사 Visual Testing", _mark(row["vt_result"])]]
    if bw:
        tests += [["X-ray or UT 방사선/초음파", _mark(row["rt_ut_result"])], ["굽힘 시험 Bend Test", _mark(row["macro_bend_result"])]]
    else:
        tests += [["단면검사 Macroscopic examination", _mark(row["macro_bend_result"])]]
    t3 = Table(tests, colWidths=[200, 130], rowHeights=18)
    t3.setStyle(TableStyle([("FONT", (0, 0), (-1, -1), FONT, 9), ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey), ("ALIGN", (1, 0), (1, -1), "CENTER")]))
    _, th3 = t3.wrapOn(c, W, H)
    y -= th3 + 14
    t3.drawOn(c, 40, y)

    c.setFont(FONT, 9)
    c.drawString(390, y + th3 - 12, f"용접일자 Date of Welding : {wd:%Y-%m-%d}")
    c.drawString(390, y + th3 - 28, f"발행일자 Date of issue : {issued:%Y-%m-%d}")
    c.drawString(390, y + th3 - 44, "Examiner / 서명 Signature :")

    y -= 30
    c.setFont(FONT, 10)
    c.drawString(40, y, "유효기간 Validity of approval :")
    c.setFont(FONT, 11)
    c.drawString(190, y, logic.validity_text(wd, ed))

    y -= 26
    c.setFont(FONT, 9)
    c.drawString(40, y, "Prolongation for approval by employer/coordinator following 6months (refer to 9.2)")
    rows = [["Date", "Signature", "Position or title"]] + [["", "", ""]] * 5
    t4 = Table(rows, colWidths=[110, 200, W - 80 - 310], rowHeights=20)
    t4.setStyle(TableStyle([("FONT", (0, 0), (-1, -1), FONT, 9), ("GRID", (0, 0), (-1, -1), 0.5, colors.black)]))
    _, th4 = t4.wrapOn(c, W, H)
    t4.drawOn(c, 40, y - 8 - th4)

    c.showPage()
    c.save()
    return buf.getvalue()
