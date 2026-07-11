# SafeReturn — the post-discharge medication safety net

An AI voice agent that makes the follow-up calls nurses can't, during the 30 days
after hospital discharge. It calls the patient, walks their **actual** discharge
medication list, catches dangerous errors (like still taking a stopped med), and
escalates anything abnormal to a human via SMS.

**It never gives medical advice. It flags and escalates. That's the product.**

Built at AI Healthcare Hack NYC (Arya Health × Twilio AI Startup Searchlight).

---

## The one-line pitch (memorize it)

> Clinics are paid by Medicare (TCM) to make these calls and can't staff them;
> hospitals are penalized for the readmissions these calls prevent.
> We automate the call — and escalate the judgment to humans.

## How it works

```
 Twilio Voice ──► FastAPI ──────────► State Machine (decides everything)
      ▲          two transports            │
      │          (env-switched):           │ classify utterance
      │           ConversationRelay        ▼
   Patient        websocket (streaming    LLM adapter (regex-first →
      │           STT/TTS, barge-in)      Groq llama-3.3-70b / Ollama / Gemini)
      │           or <Gather> webhooks     │
      ▼                                    ▼
                              GREEN log · AMBER/RED ──► Twilio SMS ──► Nurse
                                           │            (patient's own words
                                           ▼             quoted in the SMS)
                                   Nurse triage dashboard (live transcript)
```

**Core invariant:** the LLM only *interprets* what the patient said
(yes / no / unclear / question / clinical_question). The **state machine** owns
the flow and every escalation decision; nothing the model generates is ever
spoken to the patient. DTMF keypad (1 = yes, 2 = no) works on every question,
so the call survives a noisy room and a dead model API.

**Conversation design that came out of live testing:**
- The stopped-med check is asked in the affirmative ("Are you *still* taking
  it?") — "you are no longer taking it?" is a negation trap for elderly
  patients and classifiers alike.
- Unambiguous replies ("Yes.", "No.") are classified by regex instantly and
  never depend on a model; only nuanced phrasing goes to the LLM.
- Patient questions are acknowledged, never answered: clinical ones get a
  scripted deflection + RED; logistical ones ("when was it canceled?") are
  queued for the human callback + AMBER.
- Reprompts escalate gently: "Sorry — was that a yes or a no?" before any
  keypad instructions.

## Quickstart

```bash
git clone <this-repo> && cd discharge-agent-araya-hackathon
uv pip install -r requirements.txt
# .env already scaffolded at repo root — see docs/GOLIVE.md for what to fill in

# 1. Develop WITHOUT a phone (text simulator — start here):
uv run python scripts/test_conversation.py harold

# 2. Run the server:
uv run uvicorn app.main:app --reload --port 8000

# 3. Expose it and wire Twilio (full checklist: docs/GOLIVE.md):
ngrok http 8000             # put the https URL in .env as PUBLIC_BASE_URL

# 4. Trigger a real call:
uv run python scripts/trigger_call.py margaret
uv run python scripts/trigger_call.py harold   # the red-path demo

# 5. Dashboard:
open http://localhost:8000/dashboard
```

## Repo map

```
app/
  main.py            FastAPI app: Twilio webhooks, call trigger, status API, dashboard
  relay.py           ConversationRelay websocket transport (VOICE_MODE=relay)
  state_machine.py   The conversation: states, transitions, escalation triggers
  llm.py             Intent classifier: regex first, then Groq/Ollama/Gemini
  escalation.py      Amber/Red SMS via Twilio (logs instead if no creds)
  store.py           In-memory session store (per-call state)
  config.py          Env config
  data/patients.json Margaret + Harold (fake numbers — real ones go in .env)
dashboard/index.html Nurse triage board: action queue, live transcript, med lists
scripts/
  test_conversation.py  Text-mode simulator — develop the conversation with no phone
  test_relay.py         Speak the ConversationRelay protocol locally, no phone
  trigger_call.py       Kick off an outbound Twilio call
docs/
  GOLIVE.md          Twilio + Groq wiring checklist — read this to start testing
  ARCHITECTURE.md    System design + model choice rationale
  STATE_MACHINE.md   Full conversation spec (the source of truth)
  DEMO.md            Demo script, fallback ladder, rehearsal checklist
  PITCH.md           Pitch narrative + judge Q&A prep
AGENTS.md            Read this first if you are an AI coding agent (or a human)
CLAUDE.md            Pointer to AGENTS.md for Claude Code
```

## Build phases (ship in this order — each phase is demoable)

1. **P0 — text simulator green path**: full Margaret conversation in the terminal. No phone, no model API (regex classifier).
2. **P1 — real call, structured**: Twilio Voice + `<Gather>` (DTMF + basic speech), Harold red path, escalation SMS fires.
3. **P2 — LLM understanding**: natural-language answers classified by Gemma/MedGemma; DTMF stays as fallback.
4. **P3 — polish**: nurse triage dashboard, ConversationRelay streaming voice — both shipped. Backup demo video.

If time runs out at any phase boundary, we still have a working demo.
