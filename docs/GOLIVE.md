# Go-live checklist — Twilio wiring + Groq (do this in order)

Goal: real phone call end-to-end. ~15 min. One person on the Twilio console,
one on the terminal. Everything degrades gracefully if a step is skipped
(AGENTS.md invariant #4), but the demo wants all of it.

## 1. Fill `.env` (repo root — already scaffolded, gitignored)

| Var | Where to get it |
|---|---|
| `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` | console.twilio.com home → "Account Info" box |
| `TWILIO_FROM_NUMBER` | your Twilio number, E.164 (`+1...`) |
| `NURSE_PHONE` | phone that receives **RED** SMS — hand this one to a judge |
| `COORDINATOR_PHONE` | receives AMBER; same phone is fine |
| `GROQ_API_KEY` | paste the team key; provider + model are pre-filled (`llama-3.1-8b-instant`) |
| `PUBLIC_BASE_URL` | fill in step 3 |

## 2. Real patient phones

Edit `app/data/patients.json`: replace the fake `+1555...` numbers for
`margaret` and `harold` with the actual phones teammates will answer.
**This is the step everyone forgets.**

Trial account? EVERY number involved (patients + nurse + coordinator) must be
verified: console → Phone Numbers → Verified Caller IDs. Trial calls also play
a "trial account" preamble before the agent speaks — upgrading (~$20) removes it.

## 3. Expose the server

```bash
ngrok http 8000
```

Copy the `https://….ngrok-free.app` URL into `PUBLIC_BASE_URL` — **no trailing
slash**. No webhook config needed on the Twilio number: outbound calls pass the
URL directly.

## 4. (Re)start the server — config loads at startup

```bash
uv run uvicorn app.main:app --port 8000
```

Dashboard: http://localhost:8000/dashboard (put this on the projector).

## 5. Smoke tests, cheapest first

```bash
# a) No phone: Groq classification in the terminal.
#    Answer naturally: "yeah I picked it up", "no, I stopped it",
#    "should I take ibuprofen with this?"  (expect: yes / yes / clinical_question)
uv run python scripts/test_conversation.py harold

# b) Webhook without a phone (server must be up):
curl -s -X POST 'localhost:8000/voice/start?pid=harold'

# c) The real thing:
uv run python scripts/trigger_call.py margaret   # green path
uv run python scripts/trigger_call.py harold     # red path — RED SMS lands on NURSE_PHONE
```

Pass criteria (= rehearsal checklist in DEMO.md):

- [ ] Margaret green end-to-end on speakerphone; dashboard card flips CLEARED
- [ ] Harold red path: SMS on the nurse phone < 5 s; action queue shows the card
- [ ] Clinical question mid-call ("should I take ibuprofen?") → deflection + RED
- [ ] Pull `GROQ_API_KEY` from `.env`, restart, repeat a call → still works via
      regex/DTMF (invariant #4 — put the key back after)
- [ ] Backup video recorded

## Gotchas

- Edited `.env`? Restart the server — values load once, at import.
- Agent doesn't speak / call loops: `PUBLIC_BASE_URL` wrong or has a trailing
  slash, or ngrok restarted and the URL changed.
- SMS silent: number not verified (trial), or `NURSE_PHONE` missing — check the
  server log for `[escalation] SMS failed`.
- Fresh board for the demo = just restart the server (sessions are in-memory).
- Speech misheard in a noisy room: press **1 = yes, 2 = no** — keypad always wins.
