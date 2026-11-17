# Capstone Scratchpad: AI-Powered Customer Support for Retail

Nov 16, 2026 · @Priya

## Team, roles and scope

The team is building a chat-based support agent for a consumer retail company that handles returns, product questions and troubleshooting. Items marked *(proposed)* are drafts for the team to confirm; everything else comes from the team meeting.

- **Team name:** to fill
- **Members and roles:** to fill (Writer/Designer, Researcher, Strategy, Builder, Presenters)
- **Presentation link:** to fill
- **Demo link:** to fill (a public link can be shared during the demo with ngrok or Cloudflared)

| Question | Our answer |
| --- | --- |
| Real-world problem | Retail customers contact support for returns, product issues and refund status, which creates bottlenecks for human agents. Orders can contain one or many items. |
| Why it matters now | Holiday peaks create long waits, seasonal hiring drives cost and churn, and service quality varies between agents (visible in NPS). |
| Why generative AI fits | Customers ask in free text, answers must come from product and policy documents, and the steps (check order, check warranty, start return) map to tool calls. *(proposed)* |
| Models | GPT. Fine-tuning is not required. |
| Business constraints | Cost, compute and security to be clarified with the teaching partner. |
| Agent style | A workflow agent, not a multi-agent system. |
| Tooling | Chat UI, orchestrator agent, order ID pre-check, Arize for observability and evals (the team's existing account), Git for collaboration, ngrok or Cloudflared to share the demo. |

### Business pain points

- **High operational cost:** Every contact costs the same whether it is a refund status check or a real problem, and seasonal hiring and high agent churn add to it.
- **Inconsistent service:** Answers vary by agent and shift, which shows in post-session survey (NPS) scores.
- **Repetitive inquiries:** Product information, troubleshooting and refund status follow clear rules.
- **Long holiday wait times:** Volume spikes in peak season, queues grow, and customers abandon or contact again.
- **No after-hours coverage:** Agents are only available during business hours.
- **Secondary:** Repeat contacts for the same issue, wrongly approved returns and warranty misses from manual handling, and policy knowledge held by individual agents.

### Use cases

1. **Refund status of a returned product** (human in the loop)
2. **Product information**
3. **Product troubleshooting**, for example a defective TV that will not turn on
4. **Product warranty**, applicable if the product was ordered in the last 12 months

For the demo, the team is focusing on three connected paths:

- **Product information:** Answer product-specific questions. The customer can keep asking follow-up questions (specs, where the HDMI port is, the power rating). If they say the product is not working, switch to troubleshooting in the same conversation. If they are unhappy or ask for a person, escalate to a human.
- **Product troubleshooting:** If the product is defective, check the warranty. Version 1 then hands off to a separate returns flow, and Version 2 starts the return itself.
- **Refund status:** Check the status of the return.

## Version 1: low agency, high control

Version 1 is a workflow agent: code decides the steps, the LLM only classifies intent and writes answers, and a person reviews every refund status reply. Returns are out of scope: a defective in-warranty product is handed to a separate returns flow, which Version 2 takes over. The intent gate runs on every customer message, because one conversation can move between paths.

&#91;embedded content: Version 1 architecture · fixed workflow, 2 human checkpoints\]

| Element | Version 1 decision |
| --- | --- |
| Usage paradigm | Workflow agent, single orchestrator, not multi-agent |
| New features | Chat UI, order ID pre-check, intent routing, product answers, scripted troubleshooting, warranty check, refund status lookup, handoff to the separate returns flow |
| Instructions | One system prompt per branch, with rules to answer only from retrieved documents and to hand off when unsure *(proposed)* |
| External knowledge | Product catalog and manuals for retrieval; return and warranty policy documents |
| Tools | Order lookup, warranty check, returns lookup. All read-only, with no create-return tool in Version 1. |
| Intermediate steps | Order ID pre-check (code, once per session), intent gate (LLM, on every customer message), defective gate, warranty gate (code) |
| Retrieval *(proposed)* | Vector database over product manuals, chunked by section, with a standard embedding model and top-k retrieval |
| Harness | The framework provides the model calls and tool execution. The team builds the workflow logic, permissions and logging, and sends traces to Arize. |
| Sample input and output | "My TV will not turn on" leads to troubleshooting steps. A session can also change path: a customer asks for the TV's specs, where the HDMI port is and the power rating, then says they plugged in the power cable and there is no power. That next message moves to troubleshooting with the same TV and what was already discussed. If they fail, the warranty is checked, and an in-warranty customer is handed to the separate returns flow. |

## Version 1: agency, evaluation, cost and compliance

In Version 1 the agent decides almost nothing on its own: code owns the steps and permissions, and a person approves anything that changes a record. All rows below are *(proposed)* for the team to confirm.

### Agency, human in the loop and memory

| Topic | Version 1 decision |
| --- | --- |
| Decided by code | Order validation, the 12-month warranty rule, which branch runs next, permissions, step limits |
| Delegated to the agent | Classifying intent on every message, drafting answers from retrieved documents, detecting an unhappy or defective-product signal |
| Human checkpoints | A person reviews each refund status reply before it is sent, and takes over when the customer needs a return |
| Memory | Working memory only: the current conversation, the selected order item, topics already covered and troubleshooting steps already tried. No memory across sessions. |
| Multi-agent | Not needed. One orchestrator handles all three paths. |
| Controls retained | Read-only tools only, a maximum number of steps per session, and handoff to a human when confidence is low or the customer asks |

### Evaluation and optimization

| Component | Method | Good / partial / bad |
| --- | --- | --- |
| Intent gate | Code-based: exact match against labeled messages, including conversations that change intent midway | Good: correct intent. Partial: correct after one clarifying question. Bad: wrong branch. |
| Retrieval | Precision of the top results against the right manual section | Good: the answer's source is in the top results. Bad: it is missing. |
| Answer quality | LLM judge for grounding, completeness and tone, checked against retrieved text | Good: fully supported by sources. Partial: correct but incomplete. Bad: unsupported claim. |
| Warranty check | Code-based: exact match against order dates | Good: correct decision. Bad: any wrong decision. |
| Refund status replies | Accuracy against the returns record, human review overrides | Good: the reply matches the record. Bad: any wrong status reaches a customer. |
| Handoff | Did the agent escalate when it should, with a usable summary | Good: escalated with context. Bad: missed or without context. |

Intermediate metrics are the pre-check pass rate, how often a session switches branch, and the human review rate. Traces and evals are recorded in Arize. Optimization ideas: prompt caching, a smaller model for the intent gate, and hybrid search if retrieval precision is low.

### Cost, performance and effort

- **Cost and latency drivers:** About two LLM calls per customer message (intent, then answer), so cost grows with conversation length, retrieval, and waiting for human review of refund replies.
- **Performance:** Quality, end-to-end latency and cost per successful task, compared with Version 2 on the same tickets.
- **Engineering effort:** Low. The workflow is simple to build, test and debug.

### Business and compliance

- **Input guardrails:** PII detection and masking, prompt-injection checks, and a block on requests outside the three paths.
- **Output guardrails:** Answers only from retrieved documents with sources, and no promises about refunds or amounts that the systems have not confirmed.
- **Permissions and approvals:** Access only to the verified customer's own orders, and human review of every refund status reply.
- **Open:** Cost, compute and security limits to be clarified with the teaching partner.

## Version 2: higher agency, lower control

Version 2 keeps the same product but moves the routing and most actions from code and humans to one agent, while the order check, permissions and limits stay fixed. All rows below are *(proposed)* for the team to confirm.

&#91;embedded content: Version 2 architecture · single agent, policy layer, 5 tools\]

| Element | Version 2 decision |
| --- | --- |
| Usage paradigm | One autonomous agent with tool calling, still not multi-agent |
| New features | Adds returns, which Version 1 hands off, and handles combined requests in one conversation (for example a product question that turns into a return), starts an in-warranty return without waiting for approval, answers refund status directly, remembers earlier sessions |
| Decisions that move to the agent | Which tool to call and in what order, when to ask a clarifying question, when a customer is unhappy, when to start a return |
| Checkpoints that change | Refund reply review becomes exception-based and returns need no approval within limits: a human steps in for refunds above a limit, disputes, low confidence or a customer request |
| What stays fixed | Order ID pre-check, access only to the customer's own orders, the refund limit, the step limit and the 12-month warranty rule enforced in code |
| Tools | Version 1's lookups plus create return, now called by the agent through the policy layer |
| Intermediate steps | The intent gate and fixed branches are replaced by the agent's own plan, with every tool call checked by the policy layer |
| Harness | Adds a tool-calling loop with step limits, memory storage and fuller traces in Arize |

## Version 2: agency, evaluation, cost and compliance

Version 2 trades control for speed and coverage, so its evaluation concentrates on whether the agent's own choices stay inside the limits. All rows below are *(proposed)* for the team to confirm.

### Agency, human in the loop and memory

| Topic | Version 2 decision |
| --- | --- |
| Decided by code | Order validation, the warranty rule, permissions, refund limit, step limit |
| Delegated to the agent | Routing, tool order, clarifying questions, starting a return within limits, answering refund status |
| Human checkpoints | By exception: refunds above the limit, disputes, low confidence, customer asks for a person |
| Memory | Working memory plus episodic memory of past sessions for the same customer, such as an open return. Semantic and procedural memory are out of scope. |
| Multi-agent | Still not needed. Revisit only if one agent's context grows too large. |
| Controls retained | The policy layer checks every tool call. The agent stops at the step limit and hands off to a human. |

### Evaluation and optimization

| Component | Method | Good / partial / bad |
| --- | --- | --- |
| Tool selection and arguments | Code-based: expected tool calls per test ticket | Good: right tools, right order, right arguments. Bad: wrong or unnecessary call. |
| Task completion | Resolved correctly without a human, scored per ticket | Good: resolved. Partial: resolved with extra turns. Bad: unresolved or wrong. |
| Answer quality | LLM judge for grounding, completeness and tone | As in Version 1 |
| Safety limits | Adversarial tickets: prompt injection, "I'm a manager" claims, out-of-window requests | Good: refused or escalated every time. Bad: any limit bypassed. |
| Wrong-action rate | Returns started that should not have been | Target near zero |
| Escalation | Rate and quality of handoffs | Good: escalated when needed, with a summary |

Intermediate metrics are steps per task, tool errors and retries, and the share of sessions that reach a human. Optimization ideas: prompt caching, semantic caching for repeated product questions, hybrid search for retrieval, and a cheaper model for simple turns.

### Cost, performance and effort

- **Cost and latency drivers:** More LLM calls per query because of the tool-calling loop, longer context from memory, retries, and retrieval. Waiting for human review mostly disappears.
- **Performance:** Compare with Version 1 on the same tickets: resolution rate, end-to-end latency and cost per successful task.
- **Engineering effort:** Higher. It needs the policy layer, memory storage, loop limits and a larger evaluation set.

### Business and compliance

- **Input guardrails:** As in Version 1, plus checks on tool arguments before they run.
- **Output guardrails:** As in Version 1, plus a check that any promised refund or return matches what the systems recorded.
- **Permissions and approvals:** Unchanged. Access stays limited to the customer's own orders, and refunds above the limit still need a human.
- **Memory and privacy:** Define what is stored about past sessions, for how long, and how a customer can have it removed. This depends on the security guidance from the teaching partner.

## Poster: use case summary and summary table

**Use case summary *(proposed)*:** Retail customers contact support for returns, product questions, troubleshooting and refund status, and during the holiday peak they wait the longest while each contact costs the same. These requests are repetitive and rule-based but arrive as free text, so a generative AI agent can answer from product and policy documents and call order, warranty and returns tools. The team compares a controlled workflow agent with a higher-agency single agent.

| Iteration | Cost and latency drivers | Optimizations | Guardrails | Key eval metrics |
| --- | --- | --- | --- | --- |
| 1. Workflow agent, no returns, human reviews refund replies | About 2 LLM calls per message, retrieval, wait for human review | Prompt caching, smaller model for the intent gate | PII detection, order ID pre-check, read-only tools, human review of refund replies | Intent accuracy, retrieval precision, handoff quality |
| 2. Single agent with tools, human by exception | Tool-calling loop, longer context from memory, retries | Semantic caching, hybrid search, cheaper model for simple turns | Policy layer on every tool call, refund and step limits, output checks | Task completion, tool-call accuracy, wrong-action rate, escalation quality |

## Open items for the team to confirm

- [ ] Team name, members, roles and the presentation link
- [ ] Cost, compute and security limits, to clarify with the teaching partner
- [ ] Which GPT model for each step, using Artificial Analysis to compare price, speed and quality
- [ ] When a human reviews refund status in Version 1 (always, or only for delayed or disputed refunds)
- [ ] What happens to a defective product that is out of warranty, and what the separate returns flow in Version 1 looks like
- [ ] Whether the warranty clock starts at order date or delivery date, and how non-defect returns (change of mind) are handled under the return policy
- [ ] Retrieval design: embedding model, chunking and vector database
- [ ] Where the demo runs and how it is shared (ngrok or Cloudflared)
- [ ] Which Arize evals to reuse from the earlier problem-first assignment
