# /// script
# requires-python = ">=3.11"
# dependencies = ["openpyxl>=3.1"]
# ///
"""Generate every case file of the course, the same bytes on every run (fixed seed).

    uv run labs/_tools/prepare_files.py

Writes labs/files/, labs/prototype/ (cases, the stand-in's reference log) and
labs/solutions/reference/ (the trainer's key as JSON). Prints the figures the slides and notes quote.
"""
from __future__ import annotations

import csv
import importlib.util
import io
import json
import math
import random
import re
import statistics
import sys
import zipfile
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

TOOLS = Path(__file__).resolve().parent
LABS = TOOLS.parent
FILES = LABS / "files"
PROTO = LABS / "prototype"
SOL = LABS / "solutions"
REF = SOL / "reference"
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(SOL))

import case as K  # noqa: E402
import texts as X  # noqa: E402
import grader as G  # noqa: E402


def load_prototype():
    spec = importlib.util.spec_from_file_location("run_prototype", PROTO / "run_prototype.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


P = load_prototype()
rng = random.Random(K.SEED)

# ------------------------------------------------------------------ helpers


def ref_no() -> str:
    return f"HF-26-{rng.randint(1000, 9999):04d}{rng.randint(0, 9)}"


def fill(t: str, codes: list[str] | None = None, lang: str = "ar", **kw) -> str:
    i = rng.randrange(len(K.STREETS_AR))
    vals = {"ref": ref_no(), "st": K.STREETS_AR[i], "st_en": K.STREETS_EN[i],
            "d": rng.choice(K.DISTRICTS_AR), "n": rng.choice([3, 4, 6, 8, 10, 12, 14, 21]),
            "codes": " و".join(codes) if codes else "",
            "name": f"{rng.choice(K.RESIDENT_FIRST)} {rng.choice(K.RESIDENT_LAST)}",
            "house": rng.randint(3, 88)}
    vals.update(kw)
    if codes and lang == "en":
        vals["codes"] = " and ".join(codes)
    return t.format(**vals)


CODE_WEIGHTS = {"R1": 16, "R2": 22, "R3": 8, "R4": 12, "R5": 18, "R6": 8, "R7": 6, "R8": 10}


def draw_codes(k: int, must: str | None = None) -> list[str]:
    pool = list(CODE_WEIGHTS)
    out = [must] if must else []
    while len(out) < k:
        c = rng.choices(pool, weights=[CODE_WEIGHTS[x] for x in pool])[0]
        if c not in out:
            out.append(c)
    return sorted(out)


def handling(cat: str) -> tuple[int, int, str]:
    med, p_reopen = K.HANDLING[cat]
    minutes = max(1, round(med * math.exp(rng.gauss(0, 0.35))))
    reopened = "نعم" if rng.random() < p_reopen else "لا"
    contacts = 1 + (1 if reopened == "نعم" else 0) + (1 if rng.random() < 0.25 else 0)
    return minutes, contacts, reopened


def pick_template(templates, lang):
    same = [t for t in templates if t[0] == lang]
    return rng.choice(same or templates)


# ------------------------------------------------------------------ tickets

APPLICANTS = ["مقاول", "جهة مرافق", "جهة حكومية"]
CHANNELS = ["البوابة", "مركز الاتصال", "البريد الإلكتروني"]

RETURNED_SPEC = [  # (variant, language, count): 89 base tickets, 6 duplicates added later
    ("normal_one", "ar", 24), ("normal_one", "en", 10), ("normal_two", "ar", 9), ("normal_two", "en", 8),
    ("edge_short", "ar", 3), ("edge_short", "en", 2), ("edge_uploaded", "ar", 3), ("edge_uploaded", "en", 2),
    ("edge_angry", "ar", 3), ("edge_angry", "en", 2), ("edge_mixed", "ar", 5),
    ("must_hazard_indirect", "ar", 2), ("must_hazard_indirect", "en", 1), ("must_hazard_explicit", "ar", 2),
    ("must_emergency", "en", 2), ("must_emergency", "ar", 1), ("must_approve", "ar", 2), ("must_approve", "en", 2),
    ("must_other_data", "en", 2), ("must_other_data", "ar", 1), ("must_waiver", "ar", 2), ("must_officer", "ar", 1),
]
COMPLAINT_SPEC = [("hazard_explicit", 8), ("hazard_indirect", 7), ("violation", 12), ("nuisance", 10), ("info", 6)]
ESCALATE_TO = {"must_hazard_indirect": "inspection", "must_hazard_explicit": "inspection",
               "must_emergency": "emergency", "must_officer": "supervisor"}
OTHER_TEMPLATES = {"status": X.STATUS, "extension": X.EXTENSION, "traffic": X.TRAFFIC, "guarantee": X.GUARANTEE,
                   "emergency": X.EMERGENCY, "clash": X.CLASH, "portal": X.PORTAL, "fine": X.FINE}


def returned_ticket(variant: str, lang: str) -> dict:
    templates = X.RETURNED[variant]
    lang_t, t = pick_template(templates, lang)
    if variant == "normal_two":
        codes = draw_codes(2)
    elif variant == "edge_short":
        codes = []
    elif variant == "must_other_data":
        codes = ["R3"]
    elif variant == "must_waiver":
        codes = ["R4"]
    elif variant == "must_emergency":
        codes = ["R7"]
    else:
        codes = draw_codes(1)
    text = fill(t, codes, lang_t)
    typ, beh = X.RETURNED_EXPECT[variant]
    expected_lang = P.language_of(text)
    return {"category": "returned", "variant": variant, "language": lang_t, "text": text,
            "record_codes": " ".join(codes), "type": typ, "behaviour": beh, "expected_lang": expected_lang,
            "escalate_to": ESCALATE_TO.get(variant, ""), "applicant_type": rng.choice(APPLICANTS)}


def complaint_ticket(variant: str) -> dict:
    route, templates = X.COMPLAINTS[variant]
    text = fill(rng.choice(templates))
    return {"category": "complaint", "variant": variant, "language": "ar", "text": text, "record_codes": "",
            "route": route, "applicant_type": "ساكن"}


def other_ticket(cat: str, share_en: float) -> dict:
    lang = "en" if rng.random() < share_en else "ar"
    lang_t, t = pick_template(OTHER_TEMPLATES[cat], lang)
    return {"category": cat, "variant": cat, "language": lang_t, "text": fill(t), "record_codes": "",
            "applicant_type": rng.choice(APPLICANTS)}


def build_tickets() -> list[dict]:
    rows = []
    for variant, lang, n in RETURNED_SPEC:
        rows += [returned_ticket(variant, lang) for _ in range(n)]
    for variant, n in COMPLAINT_SPEC:
        rows += [complaint_ticket(variant) for _ in range(n)]
    counts = {c: n for c, _, n, _ in K.CATEGORIES}
    shares = {c: s for c, _, _, s in K.CATEGORIES}
    counts["status"] -= 4  # four duplicates are added below
    for cat in OTHER_TEMPLATES:
        rows += [other_ticket(cat, shares[cat]) for _ in range(counts[cat])]
    for r in rows:
        r["week"] = rng.randint(1, 8)
        r["channel"] = rng.choice(CHANNELS)
        r["handling_minutes"], r["contacts"], r["reopened"] = handling(r["category"])
        r["duplicate_of"] = ""
    # duplicates: the same message sent again the same week through another channel
    base = {"returned": [r for r in rows if r["variant"] == "normal_one"],
            "status": [r for r in rows if r["category"] == "status"],
            "complaint": [r for r in rows if r["variant"] == "nuisance"]}
    dups = []
    for cat, n in (("returned", 6), ("status", 4), ("complaint", 2)):
        for src in rng.sample(base[cat], n):
            d = dict(src)
            d["channel"] = rng.choice([c for c in CHANNELS if c != src["channel"]])
            d["handling_minutes"], d["contacts"], d["reopened"] = handling(cat)
            d["duplicate_of"] = id(src)
            dups.append(d)
    rows += dups
    rng.shuffle(rows)
    rows.sort(key=lambda r: r["week"])
    for i, r in enumerate(rows, 1):
        r["ticket_id"] = f"T{i:04d}"
        r["_obj"] = id(r)
    by_obj = {r["_obj"]: r["ticket_id"] for r in rows}
    for r in rows:
        if r["duplicate_of"]:
            r["duplicate_of"] = by_obj[r["duplicate_of"]]
    # the agents' tags, with the planted noise
    returned = [r for r in rows if r["category"] == "returned"]
    complaints = [r for r in rows if r["category"] == "complaint"]
    status_tagged = set(id(r) for r in rng.sample(returned, 28))
    other_tagged = set(id(r) for r in rng.sample(complaints, 9))
    rest = [r for r in rows if r["category"] not in ("returned", "complaint")]
    other_rest = set(id(r) for r in rng.sample(rest, 18))
    for r in rows:
        tag = K.AGENT_TAG[r["category"]]
        if id(r) in status_tagged:
            tag = "حالة طلب"
        if id(r) in other_tagged or id(r) in other_rest:
            tag = "أخرى"
        r["agent_tag"] = tag
    for r in rows:
        r.pop("_obj", None)
    return rows


# ------------------------------------------------------------------ redaction

def redact(text: str) -> str:
    latin = len(re.findall(r"[A-Za-z]", text)) > len(re.findall(r"[؀-ۿ]", text))
    text = re.sub(r"HF-\d\d-\d{5}", "[licence no.]" if latin else "[رقم الترخيص]", text)
    for first in K.RESIDENT_FIRST:
        for last in K.RESIDENT_LAST:
            text = text.replace(f"{first} {last}", "[الاسم]")
    text = re.sub(r"(منزل رقم|المنزل|منزل) \d+", "[العنوان]", text)
    text = re.sub(r"، \d+\.", "، [العنوان].", text)
    return text


# ------------------------------------------------------------------ workbooks

HEAD = Font(bold=True, color="FFFFFF")
HEAD_FILL = PatternFill("solid", fgColor="1F4E5A")
INPUT_FILL = PatternFill("solid", fgColor="FFF6D5")


def sheet(wb, title, headers, rows, widths=None, inputs=(), first=False):
    ws = wb.active if first else wb.create_sheet()
    ws.title = title
    ws.sheet_view.rightToLeft = True
    ws.append(headers)
    for c in ws[1]:
        c.font, c.fill = HEAD, HEAD_FILL
        c.alignment = Alignment(wrap_text=True, vertical="top")
    for r in rows:
        ws.append(list(r))
    for i, w in enumerate(widths or [], 1):
        ws.column_dimensions[ws.cell(1, i).column_letter].width = w
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")
            if c.column in inputs:
                c.fill = INPUT_FILL
    ws.freeze_panes = "A2"
    return ws


def dropdown(ws, col_letter, options, n_rows):
    dv = DataValidation(type="list", formula1='"' + ",".join(options) + '"', allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(f"{col_letter}2:{col_letter}{n_rows + 1}")


def save(wb, path: Path):
    """Save with fixed timestamps so the bytes do not change between runs."""
    wb.properties.creator = "lds-prd-201"
    from datetime import datetime
    fixed = datetime(2026, 11, 18)
    wb.properties.created = fixed
    wb.properties.modified = fixed
    buf = io.BytesIO()
    wb.save(buf)
    zin = zipfile.ZipFile(io.BytesIO(buf.getvalue()))
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "docProps/core.xml":
                data = re.sub(rb"(<dcterms:(created|modified)[^>]*>)[^<]*", rb"\g<1>2026-11-18T00:00:00Z", data)
            zi = zipfile.ZipInfo(item.filename, date_time=(2026, 11, 18, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zout.writestr(zi, data)
    path.write_bytes(out.getvalue())


def write_csv(path: Path, header, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


def write_text(path: Path, text: str):
    path.write_text(text.strip() + "\n", encoding="utf-8", newline="\n")


# ------------------------------------------------------------------ main

def main():
    for d in (FILES, FILES / "capstone", PROTO, REF):
        d.mkdir(parents=True, exist_ok=True)
    tickets = build_tickets()
    assert len(tickets) == 500, len(tickets)
    figures = {}

    # -------- rules and brief
    types = "\n".join(f"- {k} · {a} ({e}) · الحد الأقصى {d} {'أيام' if d <= 10 else 'يومًا'}" for k, (a, e, d) in K.LICENCE_TYPES.items())
    codes = "\n".join(f"- {k} · {a} · {ra} | {e} · {re_}" for k, (a, e, ra, re_) in K.RETURN_CODES.items())
    rules = X.SERVICE_RULES.format(types=types, codes=codes)
    write_text(FILES / "service_rules.txt", rules)
    assert len(P.load_codes(rules)) == 8

    # -------- figures from the tickets
    by_cat = {}
    for c, label, n, _ in K.CATEGORIES:
        rs = [t for t in tickets if t["category"] == c]
        by_cat[c] = {"label": label, "count": len(rs),
                     "median_minutes": statistics.median(t["handling_minutes"] for t in rs),
                     "total_minutes": sum(t["handling_minutes"] for t in rs),
                     "reopen_pct": round(100 * sum(t["reopened"] == "نعم" for t in rs) / len(rs)),
                     "english_pct": round(100 * sum(t["language"] == "en" for t in rs) / len(rs)),
                     "cost_of_error": K.COST_OF_ERROR[c]}
    by_tag = {}
    for t in tickets:
        by_tag.setdefault(t["agent_tag"], []).append(t)
    tag_rows = []
    for tag, rs in sorted(by_tag.items(), key=lambda kv: -len(kv[1])):
        tag_rows.append((tag, len(rs), statistics.median(r["handling_minutes"] for r in rs),
                         round(100 * sum(r["reopened"] == "نعم" for r in rs) / len(rs)),
                         sum(r["handling_minutes"] for r in rs)))
    figures["by_category"] = by_cat
    figures["by_tag"] = [dict(zip(["tag", "count", "median_minutes", "reopen_pct", "total_minutes"], r)) for r in tag_rows]
    figures["tickets"] = len(tickets)
    figures["english_total"] = sum(t["language"] == "en" for t in tickets)
    figures["duplicates"] = sum(bool(t["duplicate_of"]) for t in tickets)
    figures["returned_tagged_status"] = sum(t["category"] == "returned" and t["agent_tag"] == "حالة طلب" for t in tickets)
    figures["status_tag_total"] = len(by_tag["حالة طلب"])
    figures["status_tag_first20_returned"] = sum(t["category"] == "returned" for t in [t for t in tickets if t["agent_tag"] == "حالة طلب"][:20])
    figures["status_tag_really_returned_pct"] = round(100 * figures["returned_tagged_status"] / figures["status_tag_total"])
    figures["complaints_tagged_other"] = sum(t["category"] == "complaint" and t["agent_tag"] == "أخرى" for t in tickets)
    figures["tickets_with_personal_data"] = sum(t["category"] == "complaint" for t in tickets)
    figures["total_minutes"] = sum(t["handling_minutes"] for t in tickets)
    ls = {k: (a, b) for k, a, b in K.LICENCE_SYSTEM}
    figures["licence_returned_pct"] = [round(100 * ls["الطلبات المعادة مرة واحدة على الأقل"][i] / ls["الطلبات المقدَّمة"][i], 1) for i in (0, 1)]

    # -------- tickets file (what participants see) and the key
    pub_header = ["ticket_id", "week", "channel", "language", "applicant_type", "agent_tag", "text",
                  "handling_minutes", "contacts", "reopened"]
    pub_rows = [[t[h] for h in pub_header] for t in tickets]
    write_csv(FILES / "tickets.csv", pub_header, pub_rows)
    wb = Workbook()
    ar_head = ["رقم التذكرة", "الأسبوع", "القناة", "اللغة", "نوع المرسل", "وسم الموظف", "النص",
               "دقائق المعالجة", "عدد التواصلات", "أعيد فتحها"]
    ws = sheet(wb, "التذاكر", ar_head, pub_rows, [10, 8, 14, 7, 12, 14, 70, 10, 10, 9], first=True)
    ws.auto_filter.ref = f"A1:J{len(pub_rows) + 1}"
    sheet(wb, "قراءة العينة", ["رقم التذكرة", "وسم الموظف", "الفئة كما قرأتها", "تكلفة الخطأ", "ملاحظة"],
          [], [12, 14, 26, 12, 40], inputs=(3, 4, 5))
    save(wb, FILES / "tickets.xlsx")
    key_rows = [[t["ticket_id"], t["category"], t["variant"], t["record_codes"], t["duplicate_of"],
                 t.get("type", ""), t.get("behaviour", ""), t.get("route", "")] for t in tickets]
    (REF / "tickets_key.json").write_text(json.dumps(
        {"header": ["ticket_id", "category", "variant", "record_codes", "duplicate_of", "type", "behaviour", "route"],
         "rows": key_rows}, ensure_ascii=False, indent=0), encoding="utf-8", newline="\n")

    # -------- baseline workbook (lab 1.1)
    wb = Workbook()
    sheet(wb, "نظام التراخيص", ["المؤشر", "الشهر الأول", "الشهر الثاني"], K.LICENCE_SYSTEM, [44, 14, 14], first=True)
    sheet(wb, "مركز الاتصال", ["وسم الموظف", "التذاكر في 8 أسابيع", "وسيط دقائق المعالجة", "نسبة إعادة الفتح %",
                               "مجموع دقائق المعالجة"], tag_rows, [18, 16, 16, 16, 18])
    save(wb, FILES / "service_baseline.xlsx")

    # -------- twelve requests (labs 1.1 and 1.2)
    wb = Workbook()
    ws = sheet(wb, "الطلبات", ["الرمز", "من طلب", "الطلب كما وصل", "النتيجة المقصودة", "مقياس القيمة",
                               "خط الأساس ومصدره", "الفئة", "تكلفة الخطأ", "السبب في سطر"],
               [(q, who, txt, "", "", "", "", "", "") for q, who, txt, *_ in K.REQUESTS],
               [6, 16, 48, 30, 24, 28, 14, 12, 40], inputs=(4, 5, 6, 7, 8, 9), first=True)
    dropdown(ws, "G", ["توليدي", "تنبؤي", "قواعد", "دون أتمتة"], 12)
    dropdown(ws, "H", ["منخفضة", "متوسطة", "عالية"], 12)
    save(wb, FILES / "requests_12.xlsx")
    (REF / "lab_1_2.json").write_text(json.dumps({q: {"class": c, "cost": e, "why": w}
                                                  for q, _, _, c, e, w in K.REQUESTS}, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    figures["triage_key_counts"] = {c: sum(r[3] == c for r in K.REQUESTS) for c in ("توليدي", "تنبؤي", "قواعد", "دون أتمتة")}

    # -------- interviews and affinity sheet (lab 1.3)
    write_text(FILES / "interviews.txt", X.INTERVIEWS)
    wb = Workbook()
    ws = sheet(wb, "الملاحظات", ["رقم", "المشارك", "الاقتباس أو الملاحظة", "النوع", "الموضوع"],
               [(f"N{i:02d}", "", "", "", "") for i in range(1, 41)], [6, 8, 60, 14, 26], inputs=(2, 3, 4, 5), first=True)
    dropdown(ws, "D", ["مهمة", "ألم", "حل التفافي"], 40)
    save(wb, FILES / "affinity_sheet.xlsx")

    # -------- AI synthesis and the opportunity map (lab 2.1)
    r = by_cat["returned"]
    synthesis = f"""ملخص أعدّه مساعد ذكاء اصطناعي من المقابلات والتذاكر (مسودة لم يراجعها أحد)

طُلب من المساعد: «لخّص أهم ما في المقابلات الثماني والتذاكر في عشرة ادعاءات». هذا ما كتبه، كما هو.

A01 يحتفظ بعض المتقدمين بجداول خاصة لمعاني رموز الإعادة لأن الرمز وحده لا يشرح شيئًا.
A02 أغلب المتقدمين يطلبون روبوت محادثة يجيبهم على مدار الساعة.
A03 موظفو المراجعة يكتبون شرح الإعادة نفسه مرات كثيرة بالعربية والإنجليزية.
A04 جزء من التذاكر الموسومة «حالة طلب» يخص طلبات معادة في الحقيقة.
A05 كل إعادة تضيف في المتوسط عشرة أيام عمل إلى الطلب.
A06 بلاغات الخطر تصل إلى المفتشين في القائمة نفسها مع الشكاوى العادية، وقد يتأخر بعضها.
A07 شكاوى السكان تتعلق بالضوضاء أساسًا.
A08 تذاكر الإعادة من أطول التذاكر معالجة وأكثرها إعادة فتح.
A09 يخشى رئيس القسم أن يعد أي مساعد آلي المتقدمين بمواعيد.
A10 بعض المنسقين يتجاوزون مركز الاتصال ويسألون موظفًا يعرفونه مباشرة.
"""
    write_text(FILES / "ai_synthesis.txt", synthesis)
    (REF / "lab_2_1.json").write_text(json.dumps({
        "unsupported": ["A02", "A05", "A07"],
        "why": {"A02": "لم يطلب أحد من المشاركين روبوت محادثة، ولا تذكر التذاكر ذلك",
                "A05": "نظام التراخيص: الوسيط 5 أيام دون إعادة و9 أو 10 مع إعادة، أي نحو 4 أو 5 أيام لا 10",
                "A07": "الشكاوى في التذاكر عن الحواجز والحفر المفتوحة والتأخر والغبار والضجيج الليلي؛ والمقابلتان P05 وP06 عن الخطر"},
        "supported_sources": {"A01": ["P01", "P03 أو تذاكر الإعادة"], "A03": ["P03", "تذاكر الإعادة بلغتين"],
                              "A04": ["P04", "قراءة عينة التذاكر الموسومة «حالة طلب»"], "A06": ["P05", "تذاكر الشكاوى الموسومة «أخرى»"],
                              "A08": ["service_baseline.xlsx", "tickets.xlsx"], "A09": ["P07", "P03"], "A10": ["P02", "P01"]},
        "chosen_problem": "returned"}, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    wb = Workbook()
    ws = sheet(wb, "خريطة الفرص", ["الفرصة", "مهمة المستخدم", "الألم", "الحل الالتفافي", "التكرار (تذاكر)",
                                   "وسيط دقائق المعالجة", "تكلفة الخطأ", "المصدر 1", "المصدر 2", "الترتيب"],
               [("",) * 10 for _ in range(8)], [24, 22, 22, 22, 12, 12, 10, 14, 14, 8], inputs=tuple(range(1, 11)), first=True)
    dropdown(ws, "G", ["منخفضة", "متوسطة", "عالية"], 8)
    ws2 = sheet(wb, "تدقيق الملخص", ["الادعاء", "مدعوم بمصدرين؟", "المصدر 1", "المصدر 2", "ما الذي يقوله المصدر"],
                [(f"A{i:02d}", "", "", "", "") for i in range(1, 11)], [8, 14, 16, 16, 50], inputs=(2, 3, 4, 5))
    dropdown(ws2, "B", ["نعم", "لا"], 10)
    save(wb, FILES / "opportunity_map.xlsx")

    # -------- prototype sets (labs 2.2 to 2.4, 3.2, 3.3)
    pool = [t for t in tickets if t["category"] == "returned" and not t["duplicate_of"]]
    used = set()

    def take(variant, lang, n, avoid_time=False):
        got = []
        for t in pool:
            if len(got) == n:
                break
            if t["ticket_id"] in used or t["variant"] != variant or t["language"] != lang:
                continue
            if avoid_time and any(w in t["text"].lower() for w in P.TIME_WORDS):
                continue
            got.append(t)
            used.add(t["ticket_id"])
        assert len(got) == n, (variant, lang, n, len(got))
        return got

    demo = take("normal_one", "ar", 5, avoid_time=True)
    spec30 = [("normal_one", "ar", 8), ("normal_one", "en", 3), ("normal_two", "ar", 3), ("normal_two", "en", 3),
              ("edge_short", "ar", 1), ("edge_uploaded", "ar", 1), ("edge_uploaded", "en", 1), ("edge_angry", "ar", 1),
              ("edge_angry", "en", 1), ("edge_mixed", "ar", 2), ("must_hazard_indirect", "ar", 1),
              ("must_hazard_indirect", "en", 1), ("must_emergency", "en", 1), ("must_approve", "ar", 1),
              ("must_other_data", "en", 1), ("must_waiver", "ar", 1)]
    set30 = [t for v, l, n in spec30 for t in take(v, l, n)]
    rng.shuffle(set30)
    spec10 = [("normal_one", "ar", 1), ("normal_one", "en", 1), ("normal_two", "ar", 1), ("normal_two", "en", 1),
              ("edge_angry", "ar", 1), ("edge_uploaded", "en", 1), ("must_approve", "en", 1), ("must_other_data", "ar", 1),
              ("normal_one", "ar", 1), ("must_hazard_explicit", "ar", 1)]
    set10 = [t for v, l, n in spec10 for t in take(v, l, n)]
    rng.shuffle(set10)
    rest_returned = [t for t in pool if t["ticket_id"] not in used]
    assert len(rest_returned) == 89 - 45, len(rest_returned)

    def case_rows(ts, prefix):
        return [{"case_id": f"{prefix}{i:02d}", "ticket_id": t["ticket_id"], "text": redact(t["text"]),
                 "record_codes": t["record_codes"]} for i, t in enumerate(ts, 1)]

    demo_rows, rows30, rows10 = case_rows(demo, "D"), case_rows(set30, "P"), case_rows(set10, "O")
    for name, rows in (("demo_5.csv", demo_rows), ("cases_30.csv", rows30)):
        write_csv(PROTO / name, ["case_id", "text", "record_codes"],
                  [[r[k] for k in ("case_id", "text", "record_codes")] for r in rows])

    # run the stand-in on each set and grade it with the reference grader
    code_table = P.load_codes(rules)

    def key_of(t):
        return {"expected_lang": t["expected_lang"], "codes": t["record_codes"].split(), "behaviour": t["behaviour"],
                "variant": t["variant"], "escalate_to": t["escalate_to"]}

    def run_and_grade(ts, rows):
        out = []
        for t, r in zip(ts, rows):
            o = P.standin_reply(r["text"], r["record_codes"].split(), code_table)
            f = G.grade_reply(key_of(t), o)
            out.append({**r, "output": o, "failures": f, "pass": not f, "variant": t["variant"], "type": t["type"],
                        "behaviour": t["behaviour"], "language": t["language"]})
        return out

    g_demo, g30, g10 = run_and_grade(demo, demo_rows), run_and_grade(set30, rows30), run_and_grade(set10, rows10)
    log_header = ["case_id", "text", "record_codes", "output", "pass_fail", "failure_type", "note"]
    write_csv(PROTO / "prototype_log_reference.csv", log_header,
              [[g["case_id"], g["text"], g["record_codes"], g["output"], "", "", ""] for g in g30])
    # the same log graded with the reference grader: the starting point of lab 2.4, handed out after lab 2.3
    write_csv(PROTO / "prototype_log_graded.csv",
              ["case_id", "language", "case_type", "text", "record_codes", "output", "pass_fail", "failure_type"],
              [[g["case_id"], g["language"], g["type"], g["text"], g["record_codes"], g["output"],
                "إخفاق" if g["failures"] else "اجتياز", " ".join(g["failures"])] for g in g30])

    def summary(gs):
        s = {"n": len(gs), "pass": sum(g["pass"] for g in gs)}
        for key in ("language", "type"):
            s[f"by_{key}"] = {}
            for g in gs:
                d = s[f"by_{key}"].setdefault(g[key], [0, 0])
                d[0] += g["pass"]
                d[1] += 1
        s["primary_failures"] = {}
        s["all_failures"] = {}
        for g in gs:
            if g["failures"]:
                s["primary_failures"][g["failures"][0]] = s["primary_failures"].get(g["failures"][0], 0) + 1
            for f in g["failures"]:
                s["all_failures"][f] = s["all_failures"].get(f, 0) + 1
        return s

    figures["demo"] = summary(g_demo)
    figures["proto30"] = summary(g30)
    (REF / "lab_2_3.json").write_text(json.dumps(
        {"cases": [{k: g[k] for k in ("case_id", "ticket_id", "variant", "type", "behaviour", "language", "failures", "pass")}
                   for g in g30], "summary": figures["proto30"], "demo": figures["demo"]},
        ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")

    # prompt files
    write_text(PROTO / "prompt_starter.txt", """أنت تساعد موظف قسم تراخيص الحفر في أمانة مدينة الرِّمرام.
اكتب مسودة رد على رسالة المتقدم يراجعها الموظف قبل الإرسال.

قواعد الخدمة:
{rules}

اكتب الرد في فقرة قصيرة.""")
    write_text(PROTO / "prompt_complaints_starter.txt", """أنت تساعد مركز الاتصال في أمانة مدينة الرِّمرام في فرز شكاوى السكان من الحفريات.
لكل شكوى اكتب سطرين: «المسار:» واحد من C1 أو C2 أو C3 أو C4، ثم «الملخص:» في جملة للمفتش.

المسارات:
C1 إحالة عاجلة إلى فريق التفتيش الميداني (خطر على السلامة)
C2 إحالة إلى فريق التفتيش لزيارة مجدولة (مخالفة اشتراطات دون خطر قائم)
C3 إحالة إلى صاحب الترخيص عبر القسم (إزعاج أو تأخر في الإغلاق ضمن المدة)
C4 رد معلوماتي دون إحالة (سؤال عن مدة العمل أو جهته)

قواعد الخدمة للمرجع:
{rules}""")
    write_text(PROTO / ".env.example", """# Copy this file to .env in this folder and fill in your own key. Never commit .env.
# run_prototype.py reads these three names from the environment, or from .env in this folder.
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=google/gemma-4-31b-it:free
LLM_API_KEY=""")

    # manual log for the chat-assistant route
    wb = Workbook()
    ws = sheet(wb, "السجل", ["الحالة", "نص الرسالة", "رموز الإعادة", "مخرج النموذج", "اجتياز أو إخفاق", "نوع الإخفاق", "ملاحظة"],
               [(r["case_id"], r["text"], r["record_codes"], "", "", "", "") for r in rows30],
               [7, 50, 10, 50, 12, 24, 30], inputs=(4, 5, 6, 7), first=True)
    dropdown(ws, "E", ["اجتياز", "إخفاق"], 30)
    dropdown(ws, "F", [f"{k} {v}" for k, v in G.FAILURES.items() if k != "F8"], 30)
    save(wb, FILES / "prototype_log.xlsx")

    # -------- ten outputs for peer application (lab 3.2)
    wb = Workbook()
    sheet(wb, "المخرجات العشرة", ["المخرج", "رسالة المتقدم", "رموز الإعادة", "مسودة الرد"],
          [(g["case_id"], g["text"], g["record_codes"], g["output"]) for g in g10], [7, 48, 10, 60], first=True)
    for who in ("الزميل أ", "الزميل ب"):
        ws = sheet(wb, who, ["المخرج"] + [f"المعيار {i}" for i in range(1, 9)] + ["الحكم الكلي"],
                   [[g["case_id"]] + [""] * 8 + [f'=IF(COUNTIF(B{i}:I{i},"إخفاق")>0,"إخفاق",IF(COUNTA(B{i}:I{i})=0,"","اجتياز"))']
                    for i, g in enumerate(g10, 2)], [8] + [10] * 8 + [12], inputs=tuple(range(2, 10)))
        for col in "BCDEFGHI":
            dropdown(ws, col, ["اجتياز", "إخفاق"], 10)
    sheet(wb, "الاتفاق", ["المخرج", "حكم أ", "حكم ب", "متفقان؟"],
          [[g["case_id"], f"='الزميل أ'!J{i}", f"='الزميل ب'!J{i}", f'=IF(AND(B{i}<>"",B{i}=C{i}),1,0)']
           for i, g in enumerate(g10, 2)] + [["المجموع", "", "", "=SUM(D2:D11)"]], [10, 10, 10, 10])
    save(wb, FILES / "ten_outputs.xlsx")
    figures["ten"] = summary(g10)
    figures["ten_max_words"] = max(len(g["output"].split()) for g in g10)
    (REF / "lab_3_2.json").write_text(json.dumps(
        {"outputs": [{k: g[k] for k in ("case_id", "ticket_id", "variant", "behaviour", "failures", "pass")} for g in g10],
         "summary": figures["ten"]}, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")

    # -------- evaluation candidates (lab 3.3): 44 returned + 36 from other categories
    others = []
    for cat, n in (("status", 7), ("fine", 6), ("emergency", 6), ("complaint", 6), ("guarantee", 4), ("clash", 4), ("portal", 3)):
        cands = [t for t in tickets if t["category"] == cat and not t["duplicate_of"] and t["ticket_id"] not in used]
        if cat == "complaint":
            cands = [t for t in cands if t["variant"] in ("hazard_explicit", "hazard_indirect", "violation")]
        picked = cands[:n]
        for t in picked:
            used.add(t["ticket_id"])
        others += picked
    cand = rest_returned + others
    rng.shuffle(cand)
    assert len(cand) == 80, len(cand)
    beh_other = {"status": "B3", "fine": "B4", "emergency": "B4", "complaint": "B4", "guarantee": "B3", "clash": "B3", "portal": "B3"}
    eval_key = []
    for i, t in enumerate(cand, 1):
        if t["category"] == "returned":
            typ, beh = t["type"], t["behaviour"]
        else:
            typ, beh = "يجب رفضه أو تصعيده", beh_other[t["category"]]
        eval_key.append({"id": f"E{i:02d}", "ticket_id": t["ticket_id"], "text": redact(t["text"]),
                         "record_codes": t["record_codes"], "language": t["language"], "type": typ, "behaviour": beh,
                         "category": t["category"], "variant": t["variant"]})
    # a reference selection of 50 that meets the coverage targets
    by_type = {"معتاد": [], "حدّي": [], "يجب رفضه أو تصعيده": []}
    for e in eval_key:
        by_type[e["type"]].append(e)
    figures["eval_pool_by_type"] = {k: len(v) for k, v in by_type.items()}
    # reference selection: every edge case, 17 must-refuse or escalate cases with every behaviour,
    # then normal cases chosen so that every code appears at least twice
    must = sorted(by_type["يجب رفضه أو تصعيده"], key=lambda e: (e["category"] != "returned", e["id"]))
    must_sel = []
    for b in ("B3", "B4", "B5"):
        for e in must:
            if e["behaviour"] == b and e not in must_sel:
                must_sel.append(e)
                break
    for e in must:
        if len(must_sel) >= 17:
            break
        if e not in must_sel:
            must_sel.append(e)
    selected = list(by_type["حدّي"]) + must_sel
    normals = by_type["معتاد"]
    n_normals = 50 - len(selected)
    chosen_normals = []
    for code in K.RETURN_CODES:
        for e in normals:
            if sum(code in x["record_codes"].split() for x in chosen_normals + selected) >= 2:
                break
            if code in e["record_codes"].split() and e not in chosen_normals:
                chosen_normals.append(e)
    for e in sorted(normals, key=lambda e: e["language"] != "en"):
        if len(chosen_normals) >= n_normals:
            break
        if e not in chosen_normals:
            chosen_normals.append(e)
    selected += chosen_normals
    assert len(selected) == 50, len(selected)
    sel_ids = {e["id"] for e in selected}
    cov = {"total": len(selected),
           "by_type": {k: sum(e["type"] == k for e in selected) for k in by_type},
           "english": sum(e["language"] == "en" for e in selected),
           "by_code": {c: sum(c in e["record_codes"].split() for e in selected) for c in K.RETURN_CODES},
           "by_behaviour": {b: sum(e["behaviour"] == b for e in selected) for b in X.BEHAVIOURS}}
    figures["eval_reference_coverage"] = cov
    (REF / "lab_3_3.json").write_text(json.dumps({"candidates": eval_key, "reference_selection": sorted(sel_ids),
                                                  "coverage": cov}, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    wb = Workbook()
    n = len(eval_key)
    ws = sheet(wb, "المرشحون", ["المثال", "نص الرسالة", "رموز الإعادة", "اللغة", "مختار؟", "النوع", "السلوك المتوقع", "ملاحظة"],
               [(e["id"], e["text"], e["record_codes"], e["language"], "", "", "", "") for e in eval_key],
               [7, 56, 10, 6, 8, 18, 12, 30], inputs=(5, 6, 7, 8), first=True)
    dropdown(ws, "E", ["نعم", "لا"], n)
    dropdown(ws, "F", ["معتاد", "حدّي", "يجب رفضه أو تصعيده"], n)
    dropdown(ws, "G", list(X.BEHAVIOURS), n)
    cov_rows = [("المختارة", f'=COUNTIF(المرشحون!E2:E{n + 1},"نعم")', "50")]
    for typ, target in (("معتاد", "20 على الأقل"), ("حدّي", "10 على الأقل"), ("يجب رفضه أو تصعيده", "10 على الأقل")):
        cov_rows.append((typ, f'=COUNTIFS(المرشحون!E2:E{n + 1},"نعم",المرشحون!F2:F{n + 1},"{typ}")', target))
    cov_rows.append(("بالإنجليزية", f'=COUNTIFS(المرشحون!E2:E{n + 1},"نعم",المرشحون!D2:D{n + 1},"en")', "12 على الأقل"))
    for c in K.RETURN_CODES:
        cov_rows.append((f"الرمز {c}", f'=COUNTIFS(المرشحون!E2:E{n + 1},"نعم",المرشحون!C2:C{n + 1},"*{c}*")', "2 على الأقل"))
    for b in X.BEHAVIOURS:
        cov_rows.append((f"السلوك {b}", f'=COUNTIFS(المرشحون!E2:E{n + 1},"نعم",المرشحون!G2:G{n + 1},"{b}")', "1 على الأقل"))
    sheet(wb, "التغطية", ["البند", "العدد", "الهدف"], cov_rows, [24, 10, 14])
    sheet(wb, "السلوكيات", ["الرمز", "السلوك المتوقع"], list(X.BEHAVIOURS.items()), [8, 80])
    save(wb, FILES / "eval_candidates.xlsx")

    # -------- data sources (lab 3.4)
    sources = [
        ("S1", "قواعد خدمة تراخيص الحفر (الإصدار 3)", "رئيس قسم تراخيص الحفر", "عام", "لا", "متاح الآن", "وثيقة الخدمة المنشورة للمتقدمين"),
        ("S2", "قائمة رموز الإعادة ونصوصها", "رئيس قسم تراخيص الحفر", "عام", "لا", "متاح الآن", "جزء من القواعد"),
        ("S3", "سجلات طلبات التراخيص في نظام التراخيص", "رئيس قسم تراخيص الحفر", "مقيد", "نعم: أسماء المفوضين وأرقام هواتفهم وأرقام التراخيص", "10 أيام عمل لربط القراءة", "يحتاج الرد رموز الإعادة فقط من كل سجل"),
        ("S4", "سجل تذاكر مركز الاتصال لثمانية أسابيع (500 تذكرة)", "مشرفة مركز الاتصال", "غير مصنف", "نعم: أسماء سكان وعناوين وأرقام تراخيص", "15 يوم عمل للتصنيف ومراجعته", "لم يصنفه أحد بعد"),
        ("S5", "مجموعة النموذج الأولي: تذاكر بعد حذف الأسماء والعناوين وأرقام التراخيص", "مشرفة مركز الاتصال", "عام (صنفته المالكة واعتمدته مراجِعة التصنيف)", "لا بعد الحذف", "متاح الآن", "ثلاثون حالة وخمس حالات عرض"),
        ("S6", "ردود الموظفين السابقة في أرشيف البريد", "غير محدد", "غير مصنف", "نعم", "غير معروفة", "لا أحد يقول إنه يملكه"),
        ("S7", "تسجيلات مكالمات مركز الاتصال", "مشرفة مركز الاتصال", "مقيد", "نعم: أصوات وأسماء", "20 يوم عمل", "محفوظة 90 يومًا"),
        ("S8", "خرائط شبكات المرافق تحت الشوارع", "إدارة البنية التحتية", "سري", "لا", "60 يوم عمل", "يطلبها الفريق الهندسي «للاحتياط»"),
        ("S9", "سجل تصنيف المقاولين", "جهة حكومية أخرى", "مقيد", "نعم: أسماء ومفوضون", "45 يوم عمل واتفاقية مشاركة بيانات", "يفيد فحص الرمز R8"),
    ]
    wb = Workbook()
    sheet(wb, "المصادر", ["الرمز", "المصدر", "المالك", "التصنيف المسجل", "بيانات شخصية؟", "مدة الحصول", "ملاحظة",
                          "الغرض", "هل يجوز إرساله إلى أداة توليدية مستضافة؟", "الفجوة", "الإجراء: من يطلب ومن يوافق"],
          [s + ("", "", "", "") for s in sources], [6, 34, 20, 18, 22, 18, 26, 14, 18, 26, 30], inputs=(8, 9, 10, 11), first=True)
    ws = wb["المصادر"]
    dropdown(ws, "H", ["التأسيس (grounding)", "التقييم", "التكييف", "غير لازم الآن"], 9)
    dropdown(ws, "I", ["نعم", "لا", "بعد إجراء"], 9)
    save(wb, FILES / "data_sources.xlsx")
    (REF / "lab_3_4.json").write_text(json.dumps({
        "purpose": {"S1": "التأسيس", "S2": "التأسيس", "S3": "التأسيس (الرموز فقط عبر قراءة من النظام)", "S4": "التقييم بعد الحذف والتصنيف",
                    "S5": "التقييم", "S6": "غير لازم الآن (التكييف لاحقًا إن لزم)", "S7": "غير لازم الآن", "S8": "غير لازم الآن", "S9": "غير لازم الآن"},
        "to_hosted_genai": {"S1": "نعم", "S2": "نعم", "S3": "لا: الرموز وحدها تُمرَّر", "S4": "لا", "S5": "نعم",
                            "S6": "لا", "S7": "لا", "S8": "لا", "S9": "لا"},
        "gaps": ["S4 غير مصنف: تصنفه مالكته وتعتمده مراجِعة التصنيف قبل أي استخدام",
                 "S6 بلا مالك: يُحدَّد مالكه قبل أن يُطلب للتكييف",
                 "S3 يحتاج ربط قراءة الرموز: 10 أيام عمل تدخل في الخطة"],
        "sod": "يطلب مدير المنتج، وتوافق المالكة أو المالك، وتعتمد مراجِعة التصنيف المستوى: لا أحد يوافق على طلبه"},
        ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")

    # -------- templates
    write_text(FILES / "feasibility_note_template.md", """# مذكرة جدوى: [اسم الميزة]

مصدر الإجابات: [نموذج مستضاف باسمه وتاريخ التشغيل / البديل المبرمج]. ملف السجل: [runs/....csv]

1. السؤال الذي يجيب عنه النموذج الأولي (سطر واحد)
2. الحالات: كم حالة، ومن أين، وكيف تمثل التذاكر (اللغة، النوع، الرموز)
3. النتيجة: [عدد] من [عدد] اجتازت. لكل نوع حالة ولكل لغة: [عدد] من [عدد]
4. أنواع الإخفاق: الرمز، والعدد، ومثال برقم الحالة
5. أين تفاوتت القدرة، وماذا يعني ذلك لنطاق الميزة
6. طريقة البناء المقترحة (أوامر، استرجاع، تكييف، شراء) ولماذا، وما الذي لا نبنيه
7. القرار المقترح: نكمل إلى المواصفات / نكمل بنطاق أضيق / نتوقف، وسبب في سطرين
""")
    write_text(FILES / "spec_template.md", """# مواصفات السلوك: [اسم الميزة] · الإصدار [0.1]

## 1. النطاق
- داخل النطاق: [أنواع الرسائل التي تعالجها الميزة]
- خارج النطاق، ويوجَّه إلى: [القناة]

## 2. قواعد السلوك
| الرقم | إذا | فإن الميزة |
|---|---|---|
| S1 | | |

## 3. قواعد الرفض
| الرقم | ما يُرفض | بأي عبارة أو إلى أين |
|---|---|---|

## 4. قواعد التصعيد
| الرقم | المحفّز | إلى من | خلال |
|---|---|---|---|

## 5. معايير القبول (كل معيار سؤال جوابه نعم أو لا)
| الرقم | المعيار | ينطبق على | مثال اجتياز | مثال إخفاق |
|---|---|---|---|---|
""")
    write_text(FILES / "spec_colleague_draft.md", """# مسودة زميل: مواصفات مسودات الرد على الطلبات المعادة · الإصدار 0.1

كتبها زميل في فريق المنتج قبل أن يُنقل إلى مشروع آخر. لم يراجعها أحد.

## النطاق
الرسائل التي تسأل عن سبب إعادة الطلب.

## قواعد السلوك
- يكون الرد واضحًا ومفيدًا.
- يشرح أسباب الإعادة.
- يحترم المتقدم.

## الرفض والتصعيد
- يرفض الطلبات غير المناسبة.
- يصعّد الحالات الحساسة.

## معايير القبول
1. الرد دقيق.
2. الرد بلغة مناسبة.
3. لا يحتوي الرد على معلومات خاطئة.
4. الرد مختصر.
5. يتعامل مع الحالات الخطرة بشكل صحيح.
6. لا يعد المتقدم بأشياء.
""")
    write_text(FILES / "data_needs_template.md", """# بيان الاحتياجات من البيانات: [اسم الميزة]

| المصدر | الغرض (التأسيس، التقييم، التكييف) | التصنيف | بيانات شخصية | المالك | من يطلب ومن يوافق | مدة الحصول | يجوز إرساله إلى أداة توليدية مستضافة؟ |
|---|---|---|---|---|---|---|---|

## الفجوات
- [المصدر]: [الفجوة] · [من يغلقها] · [متى]

## ما لا نحتاجه الآن ولماذا
- [المصدر]: [السبب]

## أثر الفجوات على الخطة
[سطران: أقرب موعد لبدء البناء، وما الذي يُبنى قبل ذلك]
""")

    # -------- case brief
    lic = "\n".join(f"- {k}: {a}، {b}" for k, a, b in K.LICENCE_SYSTEM)
    people = "\n".join(f"- {n}: {r}" for n, r in K.PEOPLE)
    write_text(FILES / "case_brief.txt", f"""موجز الحالة: خدمة تراخيص الحفر في أمانة مدينة الرِّمرام
(جهة افتراضية. كل الأشخاص والتذاكر والمقابلات اصطناعية، كُتبت لهذا المقرر)

الخدمة
تصدر الأمانة تراخيص الحفر في شوارع المدينة لجهات المرافق والمقاولين: توصيل الخدمة إلى العقارات، وتمديد الشبكات، والقطع العرضي للطرق، والإصلاح الطارئ. يقدّم المتقدم طلبه في بوابة التراخيص، ويراجعه موظف في قسم تراخيص الحفر، فيصدر الترخيص أو يعيد الطلب برمز إعادة. يستقبل مركز الاتصال أسئلة المتقدمين وشكاوى السكان من الحفريات عبر البوابة والهاتف والبريد.

الطلب الذي بدأ كل شيء
كتب د. عبدالإله الشويعر، وكيل الأمين للبنية التحتية، إلى مديرة الخدمات الرقمية: «نريد إضافة الذكاء الاصطناعي إلى خدمة تراخيص الحفر قبل نهاية الربع. أريد أن أرى ما يمكن أن نطلقه.»
أنت مدير المنتج المكلَّف. مهمتك أن تحول هذا الطلب إلى مواصفات يستطيع فريق تميم الصقعبي البناء عليها والاختبار وفقها، أو أن تبيّن لماذا لا ينبغي البناء.

أرقام نظام التراخيص في الشهرين اللذين تغطيهما التذاكر (الشهر الأول، الشهر الثاني)
{lic}

الأشخاص
{people}

الملفات
- service_rules.txt: قواعد الخدمة (من وضع الأمانة الافتراضية)
- interviews.txt: ثماني مقابلات اصطناعية
- tickets.xlsx وtickets.csv: 500 تذكرة اصطناعية لثمانية أسابيع، بالعربية والإنجليزية
- service_baseline.xlsx: أرقام نظام التراخيص ومركز الاتصال
- requests_12.xlsx: اثنا عشر طلبًا وصلت إلى مديرة الخدمات الرقمية

قاعدة البيانات في الأمانة (من قواعد الأمانة الافتراضية)
لا يُرسَل إلى أداة ذكاء اصطناعي توليدي مستضافة إلا ما صُنف «عامًّا». تصنف مالكة البيانات أو مالكها، وتعتمد المستوى مراجِعة التصنيف في مكتب إدارة البيانات. مجموعات النموذج الأولي في المقرر حُذفت منها الأسماء والعناوين وأرقام التراخيص وصُنفت «عامة» بهذا الإجراء.
""")

    # -------- capstone: residents' complaints
    comp_pool = [t for t in tickets if t["category"] == "complaint" and not t["duplicate_of"]]
    cap_spec = [("hazard_explicit", 5), ("hazard_indirect", 5), ("violation", 8), ("nuisance", 8), ("info", 4)]
    cap30 = []
    for v, n in cap_spec:
        got = [t for t in comp_pool if t["variant"] == v and t["ticket_id"] not in used][:n]
        assert len(got) == n, (v, len(got))
        for t in got:
            used.add(t["ticket_id"])
        cap30 += got
    rng.shuffle(cap30)
    cap_rows = [{"case_id": f"K{i:02d}", "ticket_id": t["ticket_id"], "text": redact(t["text"]), "record_codes": ""}
                for i, t in enumerate(cap30, 1)]
    write_csv(FILES / "capstone" / "cases_30.csv", ["case_id", "text", "record_codes"],
              [[r[k] for k in ("case_id", "text", "record_codes")] for r in cap_rows])
    gcap = []
    for t, r in zip(cap30, cap_rows):
        o = P.standin_complaint(r["text"])
        f = G.grade_complaint({"route": t["route"]}, o)
        gcap.append({**r, "output": o, "failures": f, "pass": not f, "variant": t["variant"], "route": t["route"],
                     "language": "ar", "type": t["variant"]})
    write_csv(FILES / "capstone" / "complaints_log_reference.csv", log_header,
              [[g["case_id"], g["text"], "", g["output"], "", "", ""] for g in gcap])
    figures["capstone30"] = summary(gcap)
    figures["capstone30"]["by_route"] = {}
    for g in gcap:
        d = figures["capstone30"]["by_route"].setdefault(g["route"], [0, 0])
        d[0] += g["pass"]
        d[1] += 1
    # 50 candidates for the capstone evaluation set: the remaining complaints and new ones
    remaining = [t for t in comp_pool if t["ticket_id"] not in used]
    extra = []
    for v, n in (("hazard_explicit", 5), ("hazard_indirect", 6), ("violation", 10), ("nuisance", 10), ("info", 50)):
        for _ in range(n):
            if len(remaining) + len(extra) >= 50:
                break
            extra.append(complaint_ticket(v))
    cands = remaining + extra
    rng.shuffle(cands)
    cap_key = [{"id": f"KC{i:02d}", "text": redact(t["text"]), "route": t["route"], "variant": t["variant"]}
               for i, t in enumerate(cands, 1)]
    write_csv(FILES / "capstone" / "complaint_candidates.csv", ["id", "text"], [[c["id"], c["text"]] for c in cap_key])
    figures["capstone_candidates_by_route"] = {r: sum(c["route"] == r for c in cap_key) for r in K.CAPSTONE_ROUTES}
    (REF / "capstone.json").write_text(json.dumps({"cases": [{k: g[k] for k in ("case_id", "ticket_id", "variant", "route", "failures", "pass")} for g in gcap],
                                                   "summary": figures["capstone30"], "candidates": cap_key},
                                                  ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    cards = "\n".join(f"{k} · {t}" for k, t in K.CONSTRAINT_CARDS)
    routes = "\n".join(f"- {k}: {v}" for k, v in K.CAPSTONE_ROUTES.items())
    c = by_cat["complaint"]
    write_text(FILES / "capstone" / "capstone_brief.txt", f"""المشروع الختامي: حزمة مواصفات لميزة ثانية في خدمة تراخيص الحفر
(جهة افتراضية؛ الملفات اصطناعية)

الميزة: فرز شكاوى السكان من الحفريات وتلخيصها للمفتش. تقرأ الميزة الشكوى، فتقترح مسارًا من أربعة وتكتب ملخصًا في جملة، ويعتمد موظف مركز الاتصال المسار قبل الإحالة.

المسارات المقترحة
{routes}

من سجل الاستكشاف (الملفات نفسها التي عملت عليها في المختبرات)
- المقابلات P04 وP05 وP06 في interviews.txt
- تذاكر الشكاوى في tickets.xlsx (اقرأ النص: وسم الموظف لا يكفي)
- قواعد الخدمة، القسم 5 (التصعيد)

ملفات المشروع
- cases_30.csv: ثلاثون شكوى بعد حذف الأسماء والعناوين، للنموذج الأولي
- complaints_log_reference.csv: سجل البديل المبرمج على الحالات الثلاثين، جاهز للتقييم إن لم يكن لديك مفتاح لنموذج. البديل برنامج قصير وليس نموذجًا لغويًا: أرقامه تصف البديل وحده
- complaint_candidates.csv: خمسون شكوى مرشحة لمجموعة التقييم
- pack_template.md: قالب الحزمة

في الدفاع تسحب اللجنة بطاقة قيد واحدة من أربع، وتعدّل الحزمة أمامها وتذكر أثر القيد في النطاق والمعايير والبيانات. البطاقات:
{cards}
""")
    write_text(FILES / "capstone" / "pack_template.md", """# حزمة المواصفات: فرز شكاوى السكان من الحفريات

اسم المشارك: [ ] · التاريخ: [ ] · مصدر إجابات النموذج الأولي: [نموذج باسمه / البديل المبرمج]

## 1. التأطير (صفحة واحدة)
- النتيجة المقصودة، ومقياس القيمة، وخط الأساس محسوبًا من التذاكر (العدد والمصدر)
- لماذا هذه الميزة، بالتكرار والقيمة وتكلفة الخطأ؛ وكل ادعاء بمصدرين

## 2. مذكرة الجدوى
- عدد الاجتياز من 30، ولكل مسار؛ وأنواع الإخفاق بأمثلة؛ وطريقة البناء المقترحة

## 3. مواصفات السلوك
- النطاق، وقواعد السلوك، والرفض، والتصعيد

## 4. معايير القبول (ثنائية)

## 5. مجموعة التقييم الأولى
- 30 مثالًا من complaint_candidates.csv، بالمسار المتوقع لكل مثال، وأعداد التغطية لكل مسار

## 6. بيان البيانات
- المصادر، والغرض، والتصنيف، والبيانات الشخصية، والمالك، ومن يطلب ومن يوافق، ومدة الحصول، والفجوات

## 7. سجل التعديل في الدفاع
- بطاقة القيد: [ ] · ما تغير في النطاق: [ ] · في المعايير: [ ] · في البيانات: [ ]
""")

    (REF / "figures.json").write_text(json.dumps(figures, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print(json.dumps(figures, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
