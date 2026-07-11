# Conversation state machine — spec (source of truth)

Keep this file and `app/state_machine.py` in sync. Spec first, code second.

## Intents (output of `llm.classify`, or DTMF mapping)

- `yes` (DTMF 1) · `no` (DTMF 2) · `unclear` (anything else) ·
  `clinical_question` (patient asks for medical advice/reassurance)

## Global rules (apply in every state)

- `clinical_question` ⇒ speak `DEFLECTION_SCRIPT`, fire **RED** escalation
  `advice_requested`, then repeat the current question.
- `unclear` twice in a row ⇒ reprompt with explicit DTMF instructions
  ("press 1 for yes, 2 for no"). Third failure ⇒ **AMBER** `unreachable_midcall`,
  polite goodbye, end call.
- No answer to the call at all ⇒ (production: retry later) demo: **AMBER** `no_answer`.
- Escalations are deduplicated per (patient, trigger) per call.

## States

| # | State | Prompt (template, personalized from patients.json) | yes | no |
|---|---|---|---|---|
| 1 | GREET | "Hi, is this {name}? This is the automated care assistant calling on behalf of {practice} after your recent hospital stay. This will take about two minutes. Is now an okay time?" | → 2 | polite goodbye; **AMBER** `declined_checkin`; END |
| 2 | PICKUP | "You were prescribed a new medication, {new_med.name}. Were you able to pick it up from the pharmacy?" | → 3 | **AMBER** `rx_not_picked_up` ("coordinator will help"); → 3 |
| 3 | NEW_MEDS | "Have you been taking {new_med.name} {new_med.schedule_phrase}?" | → 4 | **AMBER** `nonadherent_new_med`; → 4 |
| 4 | STOPPED | "One more important check. The hospital **stopped** your previous medication, {stopped_med.name} — you should not be taking it anymore. Are you **still taking it**, even now and then?" (asked in the affirmative — "no longer taking it?" is a negation trap) | yes ⇒ **RED** `taking_stopped_med` (e.g. duplicate anticoagulation); speak SAFE_HOLD script; → 5 | no ⇒ → 5 |
| 5 | SYMPTOMS | Per patient `symptom_checks[]`, asked one at a time: e.g. "Have you noticed any unusual bruising or bleeding?" | any yes ⇒ **RED** `symptom_flag`; next check | next check; after last → 6 |
| 6 | CLOSE | Green: "That all sounds good, {name}. Your care team can see this update…" / If escalated: "…your nurse will be in touch shortly. Please don't change anything until you hear from them." | END | END |

## Fixed scripts (spoken verbatim — never LLM-generated)

- `DEFLECTION_SCRIPT`: "That's an important question for your nurse, and I want
  you to get the right answer — I'm flagging it right now so they call you back.
  I'm an automated assistant and can't give medical advice."
- `SAFE_HOLD` (after RED in state 4): "Thank you for telling me. I'm letting
  your nurse know right now — someone will call you back shortly. Please don't
  change anything until you hear from them."
- Reprompts escalate in verbosity: 1st unclear answer → `REPROMPT_SOFT`
  ("Sorry — was that a yes or a no?", question NOT repeated); 2nd → `REPROMPT_DTMF`
  (keypad instructions + full question); 3rd → graceful exit + AMBER
  `unreachable_midcall`. Keeps the agent from lecturing after every stumble.

## Escalation payloads (SMS)

- AMBER → `COORDINATOR_PHONE`:
  `"[SafeReturn] {name}: {trigger}. Details: {note}. Callback suggested."`
- RED → `NURSE_PHONE`:
  `"[SafeReturn] RED {name}: {trigger_detail}. Callback requested NOW."`
  e.g. `"RED Harold K.: reports taking BOTH warfarin (stopped 7/8) and Eliquis — duplicate anticoagulation risk."`

## Session status

`gray` (not called) → `in_call` → `green` | `amber` | `red` (highest severity
reached wins; red > amber > green). Dashboard reads this.

## Demo patients

- **margaret** — everything yes ⇒ pure green path.
- **harold** — answers "yes / still taking it" in STOPPED ⇒ the RED demo moment.

## Intents

`yes | no | unclear | question | clinical_question` — `question` is a
non-clinical patient question (logistics, dates, records): acknowledged with a
template, AMBER `patient_question` so the callback answers it. When the model
is unsure between `question` and `clinical_question` it must pick
`clinical_question` (fail toward the stronger escalation).
