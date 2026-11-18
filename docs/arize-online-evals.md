# Online evals in Arize

An online eval runs an LLM judge inside Arize on live traces, so every troubleshooting reply in the web UI gets a label (good, partial or bad) without anyone running a script. Bad and partial replies are then reviewed and turned into new cases in `evals/cases.py`.

Live chats have no reference answer, so the online judge grades each reply against rules (relevant to the problem, one clear step, safe, no unsupported promises, correct handoff) instead of comparing it with an expert answer. Its prompt is `ONLINE_JUDGE_PROMPT` in `evals/judge.py`.

## What the judge reads

Every customer message creates a `turn` span in the Arize project `retail-support-v1`. The judge's placeholders map to these span attributes:

| Placeholder | Span attribute | Example |
| --- | --- | --- |
| `{input}` | `attributes.input.value` | still nothing |
| `{output}` | `attributes.output.value` | Thanks. Next, Step 2: Check that the power cable... |
| `{facts}` | `attributes.facts` | Item: 55-inch OLED TV. Ordered 2026-06-15 (in warranty, 12-month warranty). Troubleshooting steps given so far: 2. |
| `{recent_conversation}` | `attributes.recent_conversation` | The previous messages, oldest first |

## Before you set it up: calibrate the judge

1. Label every row in `evals/data/online_judge_calibration.csv` (the `human_label` column: good, partial or bad). Label it yourselves; do not ask an LLM.
2. Run `python evals/run_evals.py --calibrate-judge --online`.
3. Continue only if agreement is 80% or more and every reply labeled bad is caught. Otherwise adjust `ONLINE_JUDGE_PROMPT`, rerun, and keep the calibration rows unchanged.

## Set up the task in Arize

Menu names can differ slightly between Arize versions.

1. **Settings > AI Providers > OpenAI**: the integration must test successfully with `gpt-6-luna` (already done).
2. Open the project **retail-support-v1**, then **Evals & Metrics > Evaluators > New evaluator > LLM as a Judge**.
3. Choose a custom template. Paste `ONLINE_JUDGE_PROMPT` from `evals/judge.py`, from "You are grading one reply" to "good, partial or bad."
4. Map the placeholders to the span attributes in the table above.
5. Set the output labels (rails) to `good`, `partial`, `bad`, and turn on explanations.
6. Model: the OpenAI integration with `gpt-6-luna`, the model the calibration used. If you choose another model, run the calibration with `EVAL_JUDGE_MODEL=<model>` first.
7. Filter the spans it runs on: span name is `turn` and `attributes.intent` is `troubleshooting`. Other turns (greetings, refund drafts) are not graded by this judge.
8. Sampling: 100% while testing; lower it later to control cost. Optionally run it on the last few days of traces too (backfill); recent troubleshooting traces are already there.
9. Save. Have a troubleshooting chat in the web UI (`python -m support_agent.ui`). The label and explanation appear on the `turn` spans within a few minutes.

## Use the results

Once a week, filter the `turn` spans to label `bad` or `partial` and read the explanations:

- **The reply really was poor:** copy the conversation into `evals/cases.py` as a new case, fix the app, and rerun `python evals/run_evals.py`.
- **The judge was wrong:** add the example to `evals/data/online_judge_calibration.csv` with your label, then adjust the prompt and recalibrate.

Keep `ONLINE_JUDGE_PROMPT` in `evals/judge.py` as the only copy you edit. When it changes, paste the new version into the Arize evaluator.
