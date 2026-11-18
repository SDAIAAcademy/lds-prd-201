# /// script
# requires-python = ">=3.11"
# ///
"""A prompt-level prototype for the Excavation Licences Service (a fictional case).

Runs one prompt over a file of cases and writes a log with one row per case, ready to grade.

    uv run run_prototype.py --cases demo_5.csv --label demo
    uv run run_prototype.py --cases cases_30.csv --label first30
    uv run run_prototype.py --task complaint --cases ../files/capstone/cases_30.csv --prompt prompt_complaints_starter.txt --label capstone

Where the answers come from
- A hosted model, when three settings are present: LLM_BASE_URL, LLM_MODEL and LLM_API_KEY. The script
  reads them from the environment, or from a file named .env in this folder (one NAME=value per line;
  see .env.example). Any endpoint that speaks the OpenAI chat-completions format works.
- Otherwise the scripted stand-in below. It is not a language model: it is a short program whose
  weaknesses are written in plain sight (see STANDIN WEAKNESSES), so that a log can be graded in class
  without a key. A count from a stand-in log describes the stand-in, never a model.

Nothing is installed and nothing is downloaded. The log goes to runs/<label>.csv and runs/<label>.json.
Answers from a model are cached in runs/cache.json, so running the same prompt on the same case twice
does not spend a second request of a free daily quota.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = HERE / "runs"
PAUSE_SECONDS = 3.5  # free tiers allow about 20 requests a minute

# ------------------------------------------------------------------ settings


def read_settings() -> dict:
    """Environment first; a .env file in this folder fills what the environment leaves empty."""
    found = {}
    env_file = HERE / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            found[name.strip()] = value.strip().strip('"').strip("'")
    keys = ("LLM_BASE_URL", "LLM_MODEL", "LLM_API_KEY")
    return {k: os.environ.get(k) or found.get(k, "") for k in keys}


def model_ready(s: dict) -> bool:
    return all(s.get(k) for k in ("LLM_BASE_URL", "LLM_MODEL", "LLM_API_KEY"))


# ------------------------------------------------------------------ the stand-in

ARABIC = re.compile(r"[؀-ۿ]")
LATIN = re.compile(r"[A-Za-z]")


def language_of(text: str) -> str:
    return "en" if len(LATIN.findall(text)) > len(ARABIC.findall(text)) else "ar"


def load_codes(rules_text: str) -> dict:
    """Code meanings from section 2 of the service rules: lines like 'R2 · meaning · remedy'."""
    codes = {}
    for line in rules_text.splitlines():
        m = re.match(r"\s*-\s*(R\d)\s*·\s*(.+?)\s*·\s*(.+?)\s*\|\s*(.+?)\s*·\s*(.+)$", line)
        if m:
            codes[m.group(1)] = {"ar": (m.group(2), m.group(3)), "en": (m.group(4), m.group(5))}
    return codes


# STANDIN WEAKNESSES (reply task), written on purpose so the log has something to find:
#  1. replies in Arabic to an English message longer than 160 characters
#  2. explains only the first code when a record carries two
#  3. answers a question about time with a date it has no right to give
#  4. adds a coordination fee to code R3 that no rule contains
#  5. escalates only when the message uses an explicit word (danger, leak, emergency, complaint)
#  6. offers another applicant's details when asked for "the other licence"
#  7. never refuses an approval or a waiver request: it just explains the codes

TIME_WORDS = ("متى", "كم يوم", "how long", "when ")
HAZARD_WORDS = ("خطر", "انهار", "danger", "collapse")
EMERGENCY_WORDS = ("تسرب", "انقطاع", "طارئ", "leak", "burst", "emergency")
OFFICER_WORDS = ("شكوى على الموظف", "complaint against")
OTHER_WORDS = ("الترخيص الآخر", "other licence")


def standin_reply(text: str, record_codes: list[str], codes: dict) -> str:
    lang = language_of(text)
    if lang == "en" and len(text) > 160:
        lang = "ar"  # weakness 1
    used = record_codes[:1]  # weakness 2
    low = text.lower()
    parts = []
    if lang == "ar":
        parts.append("مسودة رد للمراجعة:")
        if not used:
            parts.append("أُعيد طلبك لنقص في المستندات. يرجى مراجعة الملاحظات في البوابة.")
        for c in used:
            meaning, remedy = codes[c]["ar"]
            line = f"الرمز {c}: {meaning}. المطلوب: {remedy}"
            if c == "R3":
                line += "، مع سداد رسوم تنسيق قدرها 500 ريال"  # weakness 4
            parts.append(line + ".")
        if any(w in low for w in TIME_WORDS):
            parts.append("سيصدر الترخيص خلال يومي عمل من إعادة التقديم.")  # weakness 3
        if any(w in low for w in OTHER_WORDS):
            parts.append("سنرسل لكم بيانات صاحب الترخيص الآخر للتنسيق المباشر.")  # weakness 6
        if any(w in low for w in HAZARD_WORDS):
            parts.append("أحلنا بلاغ السلامة إلى فريق التفتيش الميداني فورًا.")
        if any(w in low for w in EMERGENCY_WORDS):
            parts.append("للإصلاح الطارئ اتصل بخط الطوارئ، وأبلغنا المهندس المناوب.")
        if any(w in low for w in OFFICER_WORDS):
            parts.append("أحلنا رسالتك إلى مشرف القسم.")
    else:
        parts.append("Draft reply for review:")
        if not used:
            parts.append("Your application was returned because documents are missing. Please check the notes in the portal.")
        for c in used:
            meaning, remedy = codes[c]["en"]
            line = f"Code {c}: {meaning}. Please {remedy}"
            if c == "R3":
                line += ", and pay a coordination fee of 500 riyals"  # weakness 4
            parts.append(line + ".")
        if any(w in low for w in TIME_WORDS):
            parts.append("Your licence will be issued within two working days of resubmission.")  # weakness 3
        if any(w in low for w in OTHER_WORDS):
            parts.append("We will send you the other licence holder's details so you can coordinate directly.")  # weakness 6
        if any(w in low for w in HAZARD_WORDS):
            parts.append("We have referred the safety report to the field inspection team immediately.")
        if any(w in low for w in EMERGENCY_WORDS):
            parts.append("For emergency repairs call the emergency line; we have informed the duty engineer.")
        if any(w in low for w in OFFICER_WORDS):
            parts.append("We have referred your message to the section supervisor.")
    return "\n".join(parts)


# STANDIN WEAKNESSES (complaint task, capstone):
#  1. routes to urgent inspection only when the message uses an explicit hazard word
#  2. any question about time goes to the information route, even when the work is overdue
#  3. answers "who is doing the work" with a contractor and an end date it does not know

def standin_complaint(text: str) -> str:
    if any(w in text for w in ("خطر", "انهار", "سقط", "كابلات مكشوفة")):
        route, summary = "C1", "بلاغ خطر في موقع حفر يحتاج زيارة عاجلة."
    elif any(w in text for w in ("كم مدة", "متى", "من الجهة")):
        route, summary = "C4", "سؤال عن مدة العمل وجهته. الجهة المنفذة مقاول الشبكة، وتنتهي الأعمال خلال أسبوع."
    elif any(w in text for w in ("منتصف الليل", "غبار", "أغلقوا", "تحويلة")):
        route, summary = "C2", "مخالفة لاشتراطات العمل دون خطر قائم."
    else:
        route, summary = "C3", "إزعاج أو تأخر في إغلاق الحفرة."
    return f"المسار: {route}\nالملخص: {summary}"


# ------------------------------------------------------------------ the model


def call_model(s: dict, system: str, user: str) -> str:
    body = json.dumps({
        "model": s["LLM_MODEL"],
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": 0,
    }).encode("utf-8")
    url = s["LLM_BASE_URL"].rstrip("/") + "/chat/completions"
    for attempt in range(3):
        req = urllib.request.Request(url, data=body, headers={
            "Authorization": f"Bearer {s['LLM_API_KEY']}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                data = json.loads(r.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"].strip()
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise SystemExit(f"The endpoint refused the key (HTTP {e.code}). Check LLM_API_KEY, or run with --standin.")
            if e.code in (429, 500, 502, 503) and attempt < 2:
                time.sleep(10 * (attempt + 1))
                continue
            raise SystemExit(f"The endpoint answered HTTP {e.code}. Try again later, or run with --standin.")
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < 2:
                time.sleep(5)
                continue
            raise SystemExit(f"No answer from the endpoint ({e.__class__.__name__}). Check LLM_BASE_URL, or run with --standin.")
    raise SystemExit("No answer from the endpoint.")


# ------------------------------------------------------------------ the run


def read_cases(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Run one prompt over a file of cases and log every result.")
    p.add_argument("--cases", default="cases_30.csv")
    p.add_argument("--prompt", default="prompt_starter.txt")
    p.add_argument("--rules", default="../files/service_rules.txt")
    p.add_argument("--task", choices=["reply", "complaint"], default="reply")
    p.add_argument("--label", default="run")
    p.add_argument("--standin", action="store_true", help="use the scripted stand-in even if a model is configured")
    a = p.parse_args(argv)

    cases_path, prompt_path, rules_path = (HERE / a.cases), (HERE / a.prompt), (HERE / a.rules)
    for f in (cases_path, prompt_path, rules_path):
        if not f.exists():
            print(f"Missing file: {f.name}. Run the script from labs/prototype/ in the course folder.")
            return 2
    if not re.fullmatch(r"[A-Za-z0-9_-]+", a.label):
        print("Use letters, digits, - and _ in --label.")
        return 2

    rules = rules_path.read_text(encoding="utf-8")
    codes = load_codes(rules)
    system = prompt_path.read_text(encoding="utf-8").replace("{rules}", rules)
    cases = read_cases(cases_path)

    s = read_settings()
    use_model = model_ready(s) and not a.standin
    mode = s["LLM_MODEL"] if use_model else "stand-in (scripted, not a language model)"
    print(f"Answers from: {mode}")
    if not use_model and not a.standin:
        print("No model settings found (LLM_BASE_URL, LLM_MODEL, LLM_API_KEY), so the stand-in answers.")
    if not use_model:
        print("The stand-in ignores the prompt: changing the prompt does not change its outputs.")

    RUNS.mkdir(exist_ok=True)
    cache_path = RUNS / "cache.json"
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}

    rows, spent = [], 0
    for c in cases:
        text = c["text"]
        if use_model:
            user = text if a.task == "complaint" else f"{text}\n\nرموز الإعادة المسجلة على الطلب: {c.get('record_codes') or 'لا يوجد'}"
            key = hashlib.sha256(f"{s['LLM_MODEL']}\n{system}\n{user}".encode("utf-8")).hexdigest()
            if key not in cache:
                if spent:
                    time.sleep(PAUSE_SECONDS)
                cache[key] = call_model(s, system, user)
                spent += 1
                cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
            out = cache[key]
        elif a.task == "complaint":
            out = standin_complaint(text)
        else:
            out = standin_reply(text, (c.get("record_codes") or "").split(), codes)
        rows.append({"case_id": c["case_id"], "text": text, "record_codes": c.get("record_codes", ""),
                     "output": out, "pass_fail": "", "failure_type": "", "note": "", "answers_from": mode})
        print(f"{c['case_id']}: done")

    out_csv = RUNS / f"{a.label}.csv"
    with out_csv.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    meta = {"label": a.label, "date": date.today().isoformat(), "answers_from": mode, "task": a.task,
            "cases_file": cases_path.name, "prompt_file": prompt_path.name, "cases": len(rows),
            "new_model_requests": spent}
    (RUNS / f"{a.label}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Log: runs/{out_csv.name} ({len(rows)} rows). Grade every row: pass_fail, failure_type, note.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
