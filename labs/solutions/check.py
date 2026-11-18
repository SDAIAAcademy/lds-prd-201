# /// script
# requires-python = ">=3.11"
# ///
"""Check the reference solutions against the committed case files. Prints PASS or the first difference.

    uv run labs/solutions/check.py

Standard library only. It recomputes every figure with labs/_tools/figures.py, reruns the scripted
stand-in on the committed cases, and checks each lab's reference values.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path

SOL = Path(__file__).resolve().parent
LABS = SOL.parent
REF = SOL / "reference"
FILES = LABS / "files"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def ref(name):
    return json.loads((REF / name).read_text(encoding="utf-8"))


def rows(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


FAILED = []


def check(label, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + label + ("" if ok else f": {detail}"))
    if not ok:
        FAILED.append(label)


def main() -> int:
    figures = load("figures", LABS / "_tools" / "figures.py").compute()
    saved = ref("figures.json")

    # lab 1.1 and 1.2: the twelve requests and the uneven key
    key12 = ref("lab_1_2.json")
    counts = {}
    for v in key12.values():
        counts[v["class"]] = counts.get(v["class"], 0) + 1
    check("1.2 key has 12 rows, 4 generative, 2 predictive, 4 rules, 2 no automation",
          len(key12) == 12 and counts == {"توليدي": 4, "تنبؤي": 2, "قواعد": 4, "دون أتمتة": 2}, counts)

    # lab 1.4: ticket figures
    for c, v in figures["by_category"].items():
        s = saved["by_category"][c]
        check(f"1.4 category {c}: count, median, total minutes, reopen",
              (v["count"], v["median_minutes"], v["total_minutes"], v["reopen_pct"]) ==
              (s["count"], s["median_minutes"], s["total_minutes"], s["reopen_pct"]), (v, s))
    for k in ("tickets", "total_minutes", "english_total", "duplicates", "status_tag_total", "returned_tagged_status", "status_tag_first20_returned",
              "complaints_tagged_other"):
        check(f"1.4 {k} = {figures[k]}", figures[k] == saved[k], (figures[k], saved[k]))

    # lab 2.1: three unsupported claims in the AI synthesis
    synthesis = (FILES / "ai_synthesis.txt").read_text(encoding="utf-8")
    l21 = ref("lab_2_1.json")
    check("2.1 the synthesis holds claims A01 to A10 and the key marks three unsupported",
          all(f"A{i:02d}" in synthesis for i in range(1, 11)) and len(l21["unsupported"]) == 3)

    # lab 2.3: the stand-in's log, rerun and regraded
    p = figures["proto30"]
    s = saved["proto30"]
    check(f"2.3 stand-in passes {p['pass']} of {p['n']}", (p["pass"], p["n"]) == (s["pass"], s["n"]), (p, s))
    check("2.3 by language and by type", p["by_language"] == s["by_language"] and p["by_type"] == s["by_type"], (p, s))
    check("2.3 primary failure types", p["primary_failures"] == s["primary_failures"], (p["primary_failures"], s["primary_failures"]))
    ref_log = rows(LABS / "prototype" / "prototype_log_reference.csv")
    P = load("run_prototype", LABS / "prototype" / "run_prototype.py")
    codes = P.load_codes((FILES / "service_rules.txt").read_text(encoding="utf-8"))
    same = all(P.standin_reply(r["text"], r["record_codes"].split(), codes) == r["output"] for r in ref_log)
    check("2.3 prototype_log_reference.csv is what the stand-in writes today", same)

    # lab 2.2: the reference prompt keeps the rules slot, and the demo set passes in full with the stand-in
    v2 = (REF / "prompt_v2.txt").read_text(encoding="utf-8")
    check("2.2 reference prompt keeps {rules}", "{rules}" in v2)
    d = figures["demo"]
    check(f"2.2 stand-in passes {d['pass']} of {d['n']} demo cases", (d["pass"], d["n"]) == (saved["demo"]["pass"], saved["demo"]["n"]), d)

    # lab 2.4: the graded log handed out for the feasibility note matches the reference grading
    graded = rows(LABS / "prototype" / "prototype_log_graded.csv")
    l23 = {c["case_id"]: c for c in ref("lab_2_3.json")["cases"]}
    agree = all((g["pass_fail"] == "اجتياز") == l23[g["case_id"]]["pass"]
                and g["failure_type"].split() == l23[g["case_id"]]["failures"]
                and g["language"] == l23[g["case_id"]]["language"] and g["case_type"] == l23[g["case_id"]]["type"]
                for g in graded) and len(graded) == 30
    check("2.4 prototype_log_graded.csv matches the reference grading", agree)
    two = [c for c in l23.values() if c["variant"] == "normal_two"]
    check(f"2.4 requests with two codes: {sum(c['pass'] for c in two)} of {len(two)} pass", (sum(c["pass"] for c in two), len(two)) == (0, 6))

    # lab 3.2: ten outputs
    l32 = ref("lab_3_2.json")
    check(f"3.2 ten outputs, {l32['summary']['pass']} pass the reference criteria", len(l32["outputs"]) == 10)

    # lab 3.3: the reference selection meets every coverage target
    l33 = ref("lab_3_3.json")
    cov = l33["coverage"]
    ok = (cov["total"] == 50 and cov["by_type"]["معتاد"] >= 20 and cov["by_type"]["حدّي"] >= 10
          and cov["by_type"]["يجب رفضه أو تصعيده"] >= 10 and cov["english"] >= 12
          and all(v >= 2 for v in cov["by_code"].values()) and all(v >= 1 for v in cov["by_behaviour"].values()))
    check("3.3 reference selection: 50 examples, every target met", ok, cov)
    sel = set(l33["reference_selection"])
    recount = {t: sum(1 for c in l33["candidates"] if c["id"] in sel and c["type"] == t) for t in cov["by_type"]}
    check("3.3 coverage recounted from the candidates", recount == cov["by_type"], (recount, cov["by_type"]))
    cands = l33["candidates"]
    pool = ({t: sum(c["type"] == t for c in cands) for t in cov["by_type"]},
            sum(c["language"] == "en" for c in cands), sum(c["behaviour"] == "B5" for c in cands))
    check("3.3 candidates: 24 normal, 11 edge, 45 must; 23 in English; one B5",
          pool == ({"معتاد": 24, "حدّي": 11, "يجب رفضه أو تصعيده": 45}, 23, 1), pool)

    # lab 3.4: segregation of duties in the reference
    l34 = ref("lab_3_4.json")
    check("3.4 nine sources classified for purpose and hosted use", len(l34["purpose"]) == 9 and len(l34["to_hosted_genai"]) == 9)

    # capstone
    c = figures["capstone30"]
    sc = saved["capstone30"]
    check(f"capstone stand-in passes {c['pass']} of {c['n']}", (c["pass"], c["n"], c["by_route"]) == (sc["pass"], sc["n"], sc["by_route"]), (c, sc))
    check("capstone 50 candidates", len(ref("capstone.json")["candidates"]) == 50)

    print("ALL PASS" if not FAILED else f"{len(FAILED)} FAILED")
    return 0 if not FAILED else 1


if __name__ == "__main__":
    sys.exit(main())
