# AGENTS.md — read me before writing any code

You are helping build **SafeReturn** at a one-day hackathon (AI Healthcare Hack NYC,
deadline 3:30 PM). This file is the contract between the big picture and every
line of code. If a change conflicts with this file, the change is wrong.

## What we are building (big picture)

A post-discharge medication follow-up **voice agent**:

- Calls a patient after hospital discharge (Twilio Programmable Voice).
- Walks their *specific* discharge med list: pickup check → new meds →
  **stopped meds** (the danger) → symptom screen → close.
- Classifies each patient reply as `yes / no / unclear / clinical_question`.
- Escalates via Twilio SMS: **AMBER** (friction, e.g. prescription not picked up)
  to a coordinator; **RED** (danger, e.g. taking a stopped anticoagulant alongside
  its replacement, or a symptom flag) to the on-call nurse, immediately.
- Shows a triage dashboard: patients with GREEN / AMBER / RED status + escalation log.

Judging rubric we optimize for: Technical Implementation, Idea Uniqueness,
Team Explanation, UI/UX (each 1–5). Twilio usage is required for sponsor prizes.

## Non-negotiable invariants (never violate, never "improve away")

1. **The agent NEVER gives medical advice.** Any clinical question or ambiguous
   medical statement from the patient gets the scripted deflection in
   `state_machine.py` (`DEFLECTION_SCRIPT`) plus a RED escalation. Do not add
   features that answer medical questions, suggest doses, or reassure about symptoms.
2. **The state machine decides; the LLM interprets.** The model's only job is
   mapping an utterance to an intent + tiny structured payload. Flow control,
   escalation logic, and what gets said next live in `state_machine.py`. Never
   let free-form model output be spoken directly to the patient without a template.
3. **Every question must be answerable by DTMF keypad** (1 = yes, 2 = no).
   Voice understanding is a layer on top, never a dependency.
4. **Graceful degradation everywhere.** No model API key → regex classifier.
   No Twilio creds → escalations print to log. No phone → text simulator.
   The demo must survive any single dependency failing.
5. **The agent always identifies itself as an AI assistant** calling on behalf
   of the practice. It never impersonates a human or a relative.
6. **Escalations are idempotent.** One AMBER/RED event per (patient, trigger)
   per call. No SMS spam.
7. **No real PHI, ever.** Fictional patients only (`app/data/patients.json`).
   Don't log anything you wouldn't put on a slide.

## Engineering rules for this hackathon

- **Ship the smallest demoable increment.** Follow the phases in README.md
  (P0 text simulator → P1 structured call → P2 LLM → P3 polish). Never start
  P(n+1) while P(n) is broken.
- **Boring tech, one process.** FastAPI, in-memory store, JSON file data.
  No database, no queue, no Docker, no auth. These are named in the pitch as
  production work, not built today.
- **Small modules, clear seams.** Twilio plumbing (`main.py`), conversation
  logic (`state_machine.py`), model calls (`llm.py`), notifications
  (`escalation.py`) stay separate so three people + agents can work in parallel
  without merge hell.
- **Test in the terminal first.** `scripts/test_conversation.py` runs the whole
  conversation without a phone. If a change can't be verified there or with a
  curl to the webhook, reconsider it.
- **Latency budget for voice:** classification must return in < 1.5 s or we fall
  back to reprompting with DTMF. Prefer small/fast models (see docs/ARCHITECTURE.md).
- **Git discipline (lightweight):** small commits, imperative messages
  ("add stopped-med trap"), push often, `main` always runs. Branches only for
  risky experiments (ConversationRelay). If it doesn't demo, revert fast.
- **Time boxes are real.** If a task exceeds its box in docs/DEMO.md's schedule,
  cut scope, don't extend time.

## Where things live / who owns what

| Area | File(s) | Owner |
|---|---|---|
| Twilio voice + webhooks | `app/main.py` | A |
| Conversation + escalation rules | `app/state_machine.py`, `docs/STATE_MACHINE.md` | B |
| Model adapter | `app/llm.py` | B |
| SMS + dashboard + Devpost | `app/escalation.py`, `dashboard/` | C |

## Definition of done (for the day)

- Margaret's call completes green end-to-end on a real phone.
- Harold's call hits the stopped-med trap → RED SMS arrives on a physical phone
  within seconds → dashboard flips red.
- A clinical question mid-call triggers the deflection + RED escalation.
- Backup video of one clean run exists.
- Devpost page filled: what/why, how we used Twilio, roles, demo link.
