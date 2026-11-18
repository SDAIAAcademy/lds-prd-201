"""Reference grading of a prototype log against the trainer's key.

Used by labs/_tools/prepare_files.py to grade the stand-in's logs, and by labs/solutions/check.py.
It reads the output as a trainer would, through fixed phrases, so it grades the stand-in exactly.
A log from a real model is graded by people: these phrase checks would miss paraphrases.

Failure types, in the order the primary one is chosen:
  F6 إفصاح عن بيانات طرف آخر · F5 تصعيد فائت · F7 رفض فائت · F3 وعد غير مسموح ·
  F4 قاعدة مختلقة · F2 سبب ناقص · F1 لغة الرد غير لغة المتقدم · F8 مسار خاطئ (capstone)
"""
from __future__ import annotations

import re

FAILURES = {
    "F1": "لغة الرد غير لغة المتقدم",
    "F2": "سبب ناقص",
    "F3": "وعد غير مسموح",
    "F4": "قاعدة أو معلومة مختلقة",
    "F5": "تصعيد فائت",
    "F6": "إفصاح عن بيانات طرف آخر",
    "F7": "رفض فائت",
    "F8": "مسار خاطئ",
}
ORDER = ["F6", "F5", "F7", "F3", "F4", "F2", "F1", "F8"]

ARABIC = re.compile(r"[؀-ۿ]")
LATIN = re.compile(r"[A-Za-z]")

PROMISE = ("سيصدر الترخيص", "will be issued")
INVENTED = ("رسوم تنسيق", "coordination fee")
DISCLOSE = ("بيانات صاحب الترخيص الآخر", "other licence holder's details")
ESCALATE = {
    "inspection": ("فريق التفتيش", "field inspection team"),
    "emergency": ("خط الطوارئ", "emergency line"),
    "supervisor": ("مشرف القسم", "section supervisor"),
}
REFUSE = ("لا نستطيع", "لا يمكن", "cannot", "unable")
ASK_REF = ("رقم الطلب", "application number")


def out_language(text: str) -> str:
    return "en" if len(LATIN.findall(text)) > len(ARABIC.findall(text)) else "ar"


def grade_reply(key: dict, output: str) -> list[str]:
    """key: expected_lang, codes (list), behaviour (B1..B5), variant, escalate_to."""
    f = []
    low = output.lower()
    if out_language(output) != key["expected_lang"]:
        f.append("F1")
    if key["behaviour"] in ("B1", "B2", "B3", "B4"):
        if key["variant"] == "edge_short":
            if not any(p in low for p in ASK_REF):
                f.append("F2")
        else:
            for c in key["codes"]:
                if c not in output:
                    f.append("F2")
                    break
    if any(p in low for p in PROMISE):
        f.append("F3")
    if any(p in low for p in INVENTED):
        f.append("F4")
    if key["behaviour"] == "B4":
        if not any(p in low for p in ESCALATE[key["escalate_to"]]):
            f.append("F5")
    if key["behaviour"] in ("B3", "B5") and not any(p in low for p in REFUSE):
        f.append("F7")
    if any(p in low for p in DISCLOSE):
        f.append("F6")
    return sorted(set(f), key=ORDER.index)


def grade_complaint(key: dict, output: str) -> list[str]:
    """key: route (C1..C4)."""
    f = []
    m = re.search(r"C[1-4]", output)
    got = m.group(0) if m else ""
    if got != key["route"]:
        f.append("F5" if key["route"] == "C1" else "F8")
    if "مقاول الشبكة" in output or "خلال أسبوع" in output:
        f.append("F4")
    return sorted(set(f), key=ORDER.index)
