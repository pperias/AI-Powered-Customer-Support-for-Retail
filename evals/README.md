# Product evals

The evals run labeled conversations through the real agent (`handle_message`) and score them two ways.

| Layer | What it checks | How |
| --- | --- | --- |
| Turn checks (code) | Intent on every message, routing, item selection, handoffs, refund replies held for review, access to own orders only, safety | Exact checks listed per turn in `cases.py` |
| LLM judge | Quality of troubleshooting answers against an expert reference: good / partial / bad | `judge.py`, graded on the whole conversation plus the facts from the store's systems |
| Judge calibration | Whether the judge agrees with people | `data/troubleshooting_reference.csv` has a `human_label` per row |

## Online evals in Arize

The same idea runs on live traces in Arize with a rules-based judge (`ONLINE_JUDGE_PROMPT`), calibrated on `data/online_judge_calibration.csv`. Its 15 labels were proposed by Claude at Priya's request (2026-11-17) to get the Arize setup running; the team should relabel them and recalibrate. Setup steps are in `docs/arize-online-evals.md`.

## Run

```bash
python evals/run_evals.py --offline           # no LLM calls; run on every pull request
python evals/run_evals.py                     # with the LLM intent gate and the judge
python evals/run_evals.py --case manager-claim
python evals/run_evals.py --calibrate-judge
python evals/run_evals.py --verbose           # also print the full pydantic-evals report
```

The run exits with an error if any **safety** or **access** case fails. Results are saved as CSV in `evals/results/` (not committed). With Arize keys set, every eval conversation is traced to the Arize project `retail-support-evals`; the `session_id` column links a result to its trace. The CSVs can be uploaded to Arize as datasets.

## Add a case

Add a conversation to `CASES` in `cases.py`. Each turn has the customer's message and the checks that must hold for the reply (`intent`, `contains`, `needs_human`, `item_id`, ...; the list is at the top of the file). Add a `reference` to have the judge grade the troubleshooting answer. Mark cases that only the LLM intent gate can pass with `"needs_llm": True`.

## Change the judge

`JUDGE_PROMPT` in `judge.py` is the single source of truth; paste the same text into the Arize playground. After any change, run `--calibrate-judge` and keep agreement at 80% or more. When the judge and a person disagree on a new kind of answer, add that example to the calibration CSV with the human label before changing the prompt. The first 7 `human_label` values were proposed by Claude and must be replaced by the team's own labels. The other 30 rows are unlabeled on purpose: label them yourselves (good, partial or bad) without asking an LLM, otherwise the calibration only checks the judge against another model. Calibration passes at 80% agreement or more and only if every answer labeled bad is caught.

## Results (2026-11-18, with Sid's RAG and the item-switching fix)

`python evals/run_evals.py --repeat 3`: 30 conversations, each run 3 times (90 runs, 258 turns). Metrics are saved to `evals/results/metrics-llm-<timestamp>.json`.

| Metric | Result |
| --- | --- |
| Conversations passing | 90/90; no flaky cases |
| Intent accuracy (75 checked turns) | 100% |
| Safety and access | 12/12 |
| Product questions (RAG) | 27/27, including both "not in the manual" questions (no invented answers) |
| Troubleshooting judge | 6/6 good |
| Turn latency | p50 0.86 s, p95 2.28 s, max 4.82 s |
| LLM calls per turn | 1.17 chat calls, plus embeddings for product questions |
| Cost (gpt-4o-mini + text-embedding-3-small) | about $0.00035 per conversation, $0.00012 per turn (judge excluded; prices in `metrics.py`) |
| Reference judge calibration | 7/7, 2/2 bad caught (labels: 6 proposed by Claude, 1 by Priya) |
| Online judge calibration | 14/15, 5/5 bad caught (labels proposed by Claude); the one disagreement changes between runs, so the judge is not fully deterministic |

Before the item-switching fix: 81/84. "Where do I plug in a soundbar?" about the TV switched the chat to the soundbar, because any keyword of another item counted as a switch. The intent gate now reports which item the customer needs help with (`help_with`), and the chat switches only when that is a different item. The longer intent prompt raised tokens per conversation from about 1,450 to 1,980.

Earlier finding: the judge found that headphones used generic troubleshooting steps; fixed in `data/troubleshooting_steps.json`.
