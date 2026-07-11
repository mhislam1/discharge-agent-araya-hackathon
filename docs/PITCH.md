# Pitch narrative & judge Q&A

## Rubric mapping (each criterion scored 1–5)

- **Technical implementation** — "The LLM interprets; the state machine decides."
  DTMF fallback on every question, provider-swappable open model (one env var),
  idempotent escalations, graceful degradation at every layer. Production-shaped.
- **Idea uniqueness** — Not a reminder app: a discharge-window safety net that
  catches the stopped-med / duplicate-therapy error class, automating a workflow
  that is already mandated and reimbursed (Medicare TCM) but unstaffable.
- **Team explanation** — The economics story in one sentence (see README).
- **UI/UX** — Voice designed for elderly users: slow, one question at a time,
  keypad fallback, transparent "I'm an automated assistant." Nurse dashboard:
  triage at a glance.

## Anticipated judge questions — agreed answers

- **"Isn't this an IVR with an LLM?"** The value is (1) grounding in the
  patient's specific discharge med list, (2) detecting a dangerous error class
  (stopped meds, duplicate therapy), (3) closing the loop to a human in seconds.
  IVRs read menus; this catches Harold double-anticoagulated.
- **"How do you know he actually took/stopped it?"** We don't — it's self-report
  plus escalation, and we say so. Self-report with a closed loop still beats the
  status quo (nobody asks at all between visits).
- **"HIPAA?"** Named production work: BAA-covered infra (Twilio signs BAAs),
  consent captured at discharge, PHI-free logging. Today: fictional patients only.
- **"Why an open model?"** The task is intent classification, not medical
  reasoning — a small health-tuned open model (MedGemma/Gemma) is fast, cheap,
  swappable, and self-hostable, which matters for PHI in production.
- **"What if the patient is confused / hard of hearing?"** Reprompt with keypad;
  after repeated failures the agent exits gracefully and escalates AMBER so a
  human calls — confusion is itself a signal worth surfacing.
- **"Business model / long-term?"** Per-episode fee to clinics far below the TCM
  reimbursement they capture, plus readmission-penalty avoidance for hospital
  partners. Long-term: the discharge episode is the wedge of a full personal
  medical secretary — we started where it saves lives and gets paid first.

## Devpost submission checklist (required fields)

- [ ] Project name + one-line description
- [ ] What we built and why (problem)
- [ ] Tools & technologies — including explicitly **how we used Twilio**
      (Voice, Gather, Messaging, ConversationRelay if shipped) and Lovable
- [ ] Team member names and roles
- [ ] Link to live demo / video
