# Demo script (Version 1)

Conversations to try in the web chat. Each one shows a part of the Version 1 design. Product questions ("what are the specs?") will not work until the RAG part is connected; until then the agent says it could not find the answer in the product documents and offers a person.

## Start the app

```bash
pip install -e ".[ui]"
python -m support_agent.ui   # open http://localhost:8000
```

`OPENAI_API_KEY` must be set (in `.env`). If your shell already has an old `OPENAI_API_KEY`, run `unset OPENAI_API_KEY` first.

The left side is the customer chat. The right side is the support agent console: refund replies waiting for review, the handoff summary, and the agent's working memory.

## Mock data

| Customer | Order | Items |
| --- | --- | --- |
| C100 | A1001 | 55-inch OLED TV (in warranty), Soundbar 200 (out of warranty) |
| C100 | A1002 | Wireless Headphones X (return in progress) |
| C200 | A1003 | 55-inch OLED TV |

Choose the customer in the "Signed in as" dropdown, and click **New chat** between scenarios.

## Scenarios

### 1. Troubleshooting, then warranty, then handoff to returns

Signed in as C100.

```
A1001
1
my TV won't turn on
still nothing
still not working
the light is off, nothing happens
```

Expected: the agent asks which item, then gives troubleshooting steps one at a time. After the third step it says the TV is defective and under warranty, and hands the customer to the returns team. The handoff summary on the right lists the order, the item and the steps tried.

### 2. Troubleshooting that fixes the problem

Signed in as C100.

```
A1001 my soundbar has no sound
it works now
```

Expected: the agent picks the soundbar from the first message and starts step 1 straight away. "It works now" ends troubleshooting.

### 3. Defective but out of warranty

Signed in as C100.

```
A1001
soundbar
no sound
still no sound
still no sound
still no sound
```

Expected: after three steps the agent says the soundbar is outside the 12-month warranty and connects the customer to a person.

### 4. Refund status with human review

Signed in as C100.

```
A1002 where is my refund?
```

Expected: the customer sees "One moment, a member of our team is checking this for you." The draft reply appears in the console on the right. Edit it if you want, then click **Approve and send**, or click **Take over**.

### 5. Escalation

Signed in as C100.

```
A1002
this is ridiculous, I've waited 3 weeks
```

Expected: the agent detects an unhappy customer and hands off with a summary. "I want to talk to a person" also hands off at any point, even before an order ID.

### 6. Out of scope

Signed in as C100.

```
A1002
can you recommend a laptop to buy?
```

Expected: the agent says what it can help with and offers the team for anything else.

### 7. Access to the customer's own orders only

Signed in as C200.

```
A1001
A1003
```

Expected: A1001 belongs to C100, so the agent says it could not find that order on the account. A1003 works.

### 8. Changing the subject mid-conversation

Signed in as C100.

```
A1001
tv
my TV has no power
actually my soundbar has no sound too
```

Expected: the agent switches to the soundbar and starts its troubleshooting steps.

## Known limits

- **One request per message.** "My headphones won't charge and where is my refund" gets troubleshooting only. Handling combined requests is planned for Version 2.
- **Troubleshooting steps are scripted per product, not per symptom** (`data/troubleshooting_steps.json`).
- **Product questions wait for RAG.**
