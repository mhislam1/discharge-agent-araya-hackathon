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
 Twilio Voice ──► FastAPI webhook ──► State Machine (decides everything)
      ▲                                    │
      │  TwiML / ConversationRelay         │ classify utterance
      │                                    ▼
   Patient ◄── TTS prompt            LLM adapter (Gemma / MedGemma / Groq)
                                           │
                                           ▼
                              GREEN log · AMBER/RED ──► Twilio SMS ──► Nurse
                                           │
                                           ▼
                                   Dashboard (Lovable / dashboard/index.html)
```

**Core invariant:** the LLM only *interprets* what the patient said
(yes / no / unclear / clinical_question). The **state machine** owns the flow
and every escalation decision. DTMF keypad input works on every question,
so the demo survives a noisy room and a dead model API.

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
  state_machine.py   The conversation: states, transitions, escalation triggers
  llm.py             Model adapter: regex fallback → Ollama (Gemma/MedGemma) → Groq → Gemini
  escalation.py      Amber/Red SMS via Twilio (logs instead if no creds)
  store.py           In-memory session store (per-call state)
  config.py          Env config
  data/patients.json Margaret (green path) + Harold (red path)
dashboard/index.html Minimal polling triage board (replace with Lovable build if time)
scripts/
  test_conversation.py  Text-mode simulator — develop the conversation with no phone
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
4. **P3 — polish**: Lovable dashboard, ConversationRelay free-form voice (stretch), backup demo video.

If time runs out at any phase boundary, we still have a working demo.
