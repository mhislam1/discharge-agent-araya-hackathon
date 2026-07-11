# Architecture

## System

```
                 ┌────────────────────────── laptop (one FastAPI process) ─────────────────────────┐
                 │                                                                                  │
 Patient phone ──► Twilio Voice ──webhook (ngrok)──► app/main.py ──► app/state_machine.py           │
                 │        ▲                              │                    │                     │
                 │        │ TwiML <Say>/<Gather>         │ utterance          │ escalation events   │
                 │        │ (or ConversationRelay WS)    ▼                    ▼                     │
                 │        └───────────────────── app/llm.py            app/escalation.py ──► Twilio SMS ──► nurse phone
                 │                                (intent classify)           │                     │
                 │                                                            ▼                     │
                 │                                        app/store.py ──► GET /api/status ──► dashboard/
                 └──────────────────────────────────────────────────────────────────────────────────┘
```

One process, in-memory state, JSON patient records. Everything else
(DB, auth, HIPAA infra, EHR ingestion, scheduling) is deliberately out of
scope and named in the pitch as production work.

## Voice modes (build in this order)

1. **Structured (P1):** TwiML `<Say>` for prompts + `<Gather input="dtmf speech">`
   for answers. Rock solid; Twilio's built-in speech result is good enough for
   yes/no. This is the guaranteed stage mode.
2. **Free-form (P3, stretch):** Twilio **ConversationRelay** — Twilio hosts
   STT/TTS and streams text to a WebSocket on our server; we return text to speak.
   Exactly the product the Twilio AI Startup Searchlight celebrates. Only attempt
   after P2 is stable; keep it on a branch.

## Model choice (no proprietary assistant API)

The LLM's job here is deliberately small: classify a short utterance into
`yes / no / unclear / clinical_question` (+ optionally extract a detail like
"picking it up Thursday"). That means we don't need a frontier model — we need
**fast + reliable JSON output**, and an open model is a genuine fit, not a compromise.

`app/llm.py` is a provider adapter with a strict priority ladder, selected by env:

| Priority | Provider (`LLM_PROVIDER`) | Model suggestion | Why |
|---|---|---|---|
| 0 | `regex` (always-on fallback) | — | Keyword yes/no matcher. Zero deps, keeps the demo alive if every API dies. |
| 1 | `ollama` (local) | `gemma3:4b` — or **MedGemma-4B-it** pulled from Hugging Face | Google's Gemma line; MedGemma is the health-tuned variant, a great pitch line ("open, health-domain model"). Local = no network risk, but test latency on your laptop first. |
| 2 | `groq` | a small hosted open model (Gemma or Llama instant-class) | OpenAI-compatible API, typically the fastest hosted inference — best latency for live voice. |
| 3 | `gemini_api` | Gemma via Google AI Studio's free tier | Managed fallback if Groq is down and local is slow. |

**Honest guidance:** verify model names/availability on the day — hosted
catalogs change. Decision rule at T+1:40: whichever provider returns a correct
classification in **< 1.5 s p95** from the venue Wi-Fi wins; everything else is
disabled. MedGemma is the nicest *story* ("health-tuned open model"); Groq is
usually the nicest *latency*. Because of invariant #2 (state machine decides,
LLM only classifies), swapping providers is a one-line env change — say that
to the judges, it's a portability/reliability point.

The adapter contract every provider implements:

```
classify(utterance: str, question_context: str) -> {"intent": "yes|no|unclear|clinical_question", "note": str}
```

Prompted for JSON-only output; any parse failure ⇒ intent `unclear` ⇒ the state
machine reprompts with DTMF. A model failure can degrade UX but can never
break the call or cause a wrong escalation.

## Sponsor stack usage (Devpost requires "how you used Twilio")

- **Twilio Programmable Voice** — outbound call + TwiML conversation.
- **Twilio `<Gather>`** — DTMF + speech capture (structured mode).
- **Twilio ConversationRelay** — streaming free-form voice (stretch).
- **Twilio Programmable Messaging** — AMBER/RED escalation SMS.
- **Lovable** — generates the React triage dashboard against `GET /api/status`
  (and optionally a landing page). Lovable renders state only; core logic stays here.
- **Open model (Gemma/MedGemma)** — utterance classification, per the ladder above.

## Known traps

- Twilio **trial accounts can only call verified numbers** — verify all team +
  demo phones immediately.
- ngrok URL changes on restart — keep `PUBLIC_BASE_URL` in `.env`, one place.
- Venue Wi-Fi: rehearse on a phone hotspot too; record a backup video.
