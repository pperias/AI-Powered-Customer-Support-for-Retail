"""Product evals for the Version 1 agent.

Run from the project root:
    python evals/run_evals.py                      # all conversations with the LLM, plus the LLM judge
    python evals/run_evals.py --offline            # keyword intent gate, no LLM calls (fast, free; for every PR)
    python evals/run_evals.py --calibrate-judge    # LLM judge vs human labels on data/troubleshooting_reference.csv
    python evals/run_evals.py --case manager-claim # one case by name

Each conversation runs through the real workflow (handle_message). With Arize keys set, every run is
traced to the "retail-support-evals" project, and the results CSVs in evals/results/ can be uploaded
to Arize as datasets.
"""
import argparse
import csv
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "evals"))

from pydantic_evals import Case, Dataset  # noqa: E402
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext  # noqa: E402

from cases import CASES  # noqa: E402

RESULTS_DIR = ROOT / "evals" / "results"
REFERENCE_CSV = ROOT / "evals" / "data" / "troubleshooting_reference.csv"
GATING_CATEGORIES = {"safety", "access"}  # any failure here fails the run


# --- Task: run one conversation through the agent ------------------------------------------------

def run_conversation(case: dict) -> dict:
    from support_agent.session import Session
    from support_agent.workflow import handle_message, send_reviewed

    session = Session(customer_id=case["customer"])
    turns = []
    for turn in case["turns"]:
        reply = handle_message(session, turn["message"])
        if reply.needs_review:  # the eval plays the reviewer and approves the draft unchanged
            send_reviewed(session, reply, reply.text)
        turns.append({
            "message": turn["message"],
            "text": reply.text,
            "intent": reply.intent.value if reply.intent else "none",
            "needs_human": reply.needs_human,
            "needs_review": reply.needs_review,
            "item_id": session.item_id,
            "handoff": reply.handoff_summary or "",
        })
    return {"session_id": session.session_id, "turns": turns, "facts": _facts(session)}


def _facts(session) -> str:
    """What the store's systems know about the selected item, so the judge can tell facts from inventions."""
    from support_agent.tools import orders
    from support_agent.tools.warranty import is_in_warranty

    order = orders.get_order(session.order_id, session.customer_id) if session.order_id else None
    item = next((i for i in order["items"] if i["item_id"] == session.item_id), None) if order else None
    if item is None:
        return ""
    status = "in warranty" if is_in_warranty(item["order_date"]) else "out of warranty"
    return f"Item: {item['name']}. Ordered {item['order_date']} ({status}, 12-month warranty)."


def check_turn(expect: dict, got: dict) -> list[str]:
    """Every check listed in cases.py for one turn; returns the ones that failed."""
    failures = []
    text = got["text"].lower()
    if "intent" in expect and got["intent"] != expect["intent"]:
        failures.append(f"intent {got['intent']}, expected {expect['intent']}")
    if "intent_in" in expect and got["intent"] not in expect["intent_in"]:
        failures.append(f"intent {got['intent']}, expected one of {expect['intent_in']}")
    failures += [f"missing {s!r}" for s in expect.get("contains", []) if s.lower() not in text]
    failures += [f"should not say {s!r}" for s in expect.get("not_contains", []) if s.lower() in text]
    for flag in ("needs_human", "needs_review"):
        if flag in expect and got[flag] != expect[flag]:
            failures.append(f"{flag}={got[flag]}, expected {expect[flag]}")
    if "item_id" in expect and got["item_id"] != expect["item_id"]:
        failures.append(f"item {got['item_id']}, expected {expect['item_id']}")
    if "handoff" in expect and expect["handoff"] not in got["handoff"]:
        failures.append(f"handoff reason missing {expect['handoff']!r}")
    return failures


# --- Evaluators -----------------------------------------------------------------------------------

@dataclass
class TurnChecks(Evaluator):
    """Code-based: intent, routing, handoff, review and access checks on every turn."""

    def evaluate(self, ctx: EvaluatorContext) -> dict:
        failures, passed = [], 0
        for number, (expect, got) in enumerate(zip(ctx.inputs["turns"], ctx.output["turns"]), 1):
            turn_failures = check_turn(expect, got)
            passed += not turn_failures
            failures += [f"turn {number} {expect['message']!r}: {f}" for f in turn_failures]
        return {
            "all_turns_pass": EvaluationReason(not failures, "; ".join(failures) or "all checks passed"),
            "turn_pass_rate": passed / len(ctx.inputs["turns"]),
        }


@dataclass
class TroubleshootingJudge(Evaluator):
    """LLM judge: the agent's troubleshooting replies, graded against the case's reference answer."""

    def evaluate(self, ctx: EvaluatorContext) -> dict:
        if not ctx.inputs.get("reference") or os.getenv("SUPPORT_AGENT_OFFLINE") == "1":
            return {}
        from judge import Judge

        turns = ctx.output["turns"]
        first = next((i for i, t in enumerate(turns) if t["intent"] == "troubleshooting"), None)
        if first is None:
            return {"judge": EvaluationReason("bad", "the agent never gave troubleshooting steps")}
        transcript = "\n".join(f"Customer: {t['message']}\nAssistant: {t['text']}" for t in turns[first:])
        label, explanation = Judge().grade(turns[first]["message"], ctx.inputs["reference"], transcript,
                                           ctx.output["facts"])
        return {"judge": EvaluationReason(label, explanation)}


# --- Runs -----------------------------------------------------------------------------------------

def run_conversations(offline: bool, only: str | None, verbose: bool) -> bool:
    selected = [c for c in CASES if (not only or c["name"] == only) and not (offline and c.get("needs_llm"))]
    dataset = Dataset(
        name="retail-support-v1",
        cases=[Case(name=c["name"], inputs=c, metadata={"category": c["category"]}) for c in selected],
        evaluators=[TurnChecks(), TroubleshootingJudge()],
    )
    report = dataset.evaluate_sync(run_conversation, max_concurrency=4, progress=False)
    if verbose:
        report.print(include_reasons=True, include_durations=True, width=160)

    by_category: dict[str, list[bool]] = {}
    rows = []
    for case in report.cases:
        ok = case.assertions["all_turns_pass"].value
        by_category.setdefault(case.metadata["category"], []).append(ok)
        judge = case.labels.get("judge")
        rows.append({
            "case": case.name, "category": case.metadata["category"], "pass": ok,
            "failures": case.assertions["all_turns_pass"].reason, "judge": judge.value if judge else "",
            "judge_explanation": judge.reason if judge else "", "session_id": case.output["session_id"],
            "transcript": "\n".join(f"you> {t['message']}\nbot> {t['text']}" for t in case.output["turns"]),
        })
    for case in report.failures:
        rows.append({"case": case.name, "category": case.metadata["category"], "pass": False,
                     "failures": f"error: {case.error_message}"})
        by_category.setdefault(case.metadata["category"], []).append(False)

    print("\nConversations")
    for r in rows:
        judge = f"  judge={r['judge']}" if r.get("judge") else ""
        print(f"  {'PASS' if r['pass'] else 'FAIL'}  {r['category']:15} {r['case']}{judge}")
        if not r["pass"]:
            print(f"        {r['failures']}")
        if r.get("judge") in ("partial", "bad"):
            print(f"        judge: {r['judge_explanation']}")

    print("\nSummary by category")
    for category, results in sorted(by_category.items()):
        print(f"  {category:16} {sum(results)}/{len(results)} conversations pass")
    labels = [r["judge"] for r in rows if r.get("judge")]
    if labels:
        print("  judge labels     " + ", ".join(f"{label}: {labels.count(label)}" for label in ("good", "partial", "bad")))
    write_csv(f"conversations-{'offline' if offline else 'llm'}", rows)

    gating_failed = [r["case"] for r in rows if r["category"] in GATING_CATEGORIES and not r["pass"]]
    if gating_failed:
        print(f"\nFAIL: safety or access cases failed: {', '.join(gating_failed)}")
    return not gating_failed


def calibrate_judge() -> bool:
    """Does the LLM judge agree with people? Trust it for decisions only if agreement is high."""
    from judge import JUDGE_MODEL, Judge

    judge, rows, agree = Judge(), [], 0
    with REFERENCE_CSV.open() as f:
        for row in csv.DictReader(f):
            label, explanation = judge.grade(row["customer_message"], row["reference_response"], row["output"])
            agree += label == row["human_label"]
            rows.append({**row, "judge_label": label, "judge_explanation": explanation})
            mark = "ok  " if label == row["human_label"] else "DIFF"
            print(f"{mark} human={row['human_label']:7} judge={label:7} {row['output'][:60]!r}\n       {explanation}")
    rate = agree / len(rows)
    print(f"\nJudge ({JUDGE_MODEL}) agrees with human labels on {agree}/{len(rows)} ({rate:.0%})")
    write_csv("judge-calibration", rows)
    return rate >= 0.8


def write_csv(stem: str, rows: list[dict]) -> None:
    RESULTS_DIR.mkdir(exist_ok=True)
    path = RESULTS_DIR / f"{stem}-{datetime.now():%Y%m%d-%H%M%S}.csv"
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Results saved to {path.relative_to(ROOT)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--offline", action="store_true", help="keyword intent gate, no LLM calls, no judge")
    parser.add_argument("--calibrate-judge", action="store_true", help="compare the judge with human labels")
    parser.add_argument("--case", help="run one conversation by name")
    parser.add_argument("--verbose", action="store_true", help="also print the full pydantic-evals report")
    args = parser.parse_args()

    if args.offline:
        os.environ["SUPPORT_AGENT_OFFLINE"] = "1"
    else:
        from support_agent.observability import setup_tracing

        setup_tracing(os.getenv("ARIZE_EVALS_PROJECT", "retail-support-evals"))
    ok = calibrate_judge() if args.calibrate_judge else run_conversations(args.offline, args.case, args.verbose)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
