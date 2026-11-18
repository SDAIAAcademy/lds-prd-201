# /// script
# requires-python = ">=3.11"
# ///
"""Every figure the slides, notes and solutions quote, computed from the committed files.

    uv run labs/_tools/figures.py

Reads labs/files/tickets.csv, the trainer's key in labs/solutions/reference/, and reruns the
prototype's scripted stand-in on the committed case files, graded by labs/solutions/grader.py.
Standard library only. The figures of the stand-in describe the stand-in, never a language model.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import statistics
import sys
from pathlib import Path

LABS = Path(__file__).resolve().parents[1]
REF = LABS / "solutions" / "reference"
sys.path.insert(0, str(LABS / "solutions"))
import grader as G  # noqa: E402


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


P = _load("run_prototype", LABS / "prototype" / "run_prototype.py")


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def tally(rows, key):
    out = {}
    for r in rows:
        d = out.setdefault(r[key], [0, 0])
        d[0] += r["pass"]
        d[1] += 1
    return out


def compute() -> dict:
    tickets = read_csv(LABS / "files" / "tickets.csv")
    key = json.loads((REF / "tickets_key.json").read_text(encoding="utf-8"))
    kh = key["header"]
    k = {row[0]: dict(zip(kh, row)) for row in key["rows"]}
    f = {"tickets": len(tickets)}
    cats = {}
    for t in tickets:
        cats.setdefault(k[t["ticket_id"]]["category"], []).append(t)
    f["by_category"] = {c: {"count": len(rs),
                            "median_minutes": statistics.median(int(r["handling_minutes"]) for r in rs),
                            "total_minutes": sum(int(r["handling_minutes"]) for r in rs),
                            "reopen_pct": round(100 * sum(r["reopened"] == "نعم" for r in rs) / len(rs))}
                        for c, rs in cats.items()}
    f["total_minutes"] = sum(int(t["handling_minutes"]) for t in tickets)
    f["english_total"] = sum(t["language"] == "en" for t in tickets)
    f["duplicates"] = sum(bool(k[t["ticket_id"]]["duplicate_of"]) for t in tickets)
    status_tag = [t for t in tickets if t["agent_tag"] == "حالة طلب"]
    f["status_tag_total"] = len(status_tag)
    f["status_tag_first20_returned"] = sum(k[t["ticket_id"]]["category"] == "returned" for t in status_tag[:20])
    f["returned_tagged_status"] = sum(k[t["ticket_id"]]["category"] == "returned" for t in status_tag)
    f["complaints_tagged_other"] = sum(k[t["ticket_id"]]["category"] == "complaint" and t["agent_tag"] == "أخرى" for t in tickets)
    f["returned_share_of_minutes_pct"] = round(100 * f["by_category"]["returned"]["total_minutes"] / f["total_minutes"])

    # the stand-in on the 30 cases, graded against the key
    rules = (LABS / "files" / "service_rules.txt").read_text(encoding="utf-8")
    codes = P.load_codes(rules)
    lab23 = json.loads((REF / "lab_2_3.json").read_text(encoding="utf-8"))
    meta = {c["case_id"]: c for c in lab23["cases"]}
    graded = []
    for c in read_csv(LABS / "prototype" / "cases_30.csv"):
        m = meta[c["case_id"]]
        t = k[m["ticket_id"]]
        full = next(x for x in tickets if x["ticket_id"] == m["ticket_id"])
        exp_lang = P.language_of(full["text"])
        out = P.standin_reply(c["text"], c["record_codes"].split(), codes)
        esc = {"must_hazard_indirect": "inspection", "must_hazard_explicit": "inspection",
               "must_emergency": "emergency", "must_officer": "supervisor"}.get(t["variant"], "")
        fails = G.grade_reply({"expected_lang": exp_lang, "codes": c["record_codes"].split(), "behaviour": t["behaviour"],
                               "variant": t["variant"], "escalate_to": esc}, out)
        graded.append({"pass": not fails, "language": full["language"], "type": t["type"], "failures": fails})
    f["proto30"] = {"n": len(graded), "pass": sum(g["pass"] for g in graded),
                    "by_language": tally(graded, "language"), "by_type": tally(graded, "type")}
    prim = {}
    for g in graded:
        if g["failures"]:
            prim[g["failures"][0]] = prim.get(g["failures"][0], 0) + 1
    f["proto30"]["primary_failures"] = prim

    # the capstone stand-in
    cap = json.loads((REF / "capstone.json").read_text(encoding="utf-8"))
    cmeta = {c["case_id"]: c for c in cap["cases"]}
    cg = []
    for c in read_csv(LABS / "files" / "capstone" / "cases_30.csv"):
        out = P.standin_complaint(c["text"])
        fails = G.grade_complaint({"route": cmeta[c["case_id"]]["route"]}, out)
        cg.append({"pass": not fails, "route": cmeta[c["case_id"]]["route"]})
    f["capstone30"] = {"n": len(cg), "pass": sum(g["pass"] for g in cg), "by_route": tally(cg, "route")}
    return f


def main():
    f = compute()
    print(json.dumps(f, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
