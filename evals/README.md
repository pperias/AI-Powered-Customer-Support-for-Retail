# Product evals

The evals run labeled conversations through the real agent (`handle_message`) and score them two ways.

| Layer | What it checks | How |
| --- | --- | --- |
| Turn checks (code) | Intent on every message, routing, item selection, handoffs, refund replies held for review, access to own orders only, safety | Exact checks listed per turn in `cases.py` |
| LLM judge | Quality of troubleshooting answers against an expert reference: good / partial / bad | `judge.py`, graded on the whole conversation plus the facts from the store's systems |
| Judge calibration | Whether the judge agrees with people | `data/troubleshooting_reference.csv` has a `human_label` per row |

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

`JUDGE_PROMPT` in `judge.py` is the single source of truth; paste the same text into the Arize playground. After any change, run `--calibrate-judge` and keep agreement at 80% or more. When the judge and a person disagree on a new kind of answer, add that example to the calibration CSV with the human label before changing the prompt. The `human_label` values were set by the team; please review them.

## Results (2026-11-17)

- 20/20 conversations pass with the LLM; 17/17 offline.
- Judge (gpt-6-luna) agrees with human labels on 7/7.
- The judge found a real gap: headphones used generic steps (cables, outlets, factory reset) instead of charge, Bluetooth and pairing mode. Fixed in `data/troubleshooting_steps.json`.
