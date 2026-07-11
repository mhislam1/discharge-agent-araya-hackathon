# Demo plan & day schedule

## The 3-minute demo (rehearse twice, minimum)

- **Beat 1 (30 s) — the problem.** Dashboard on screen, two patients, both gray.
  Say the one-liner: "Clinics are paid by Medicare to make these calls and can't
  staff them; hospitals are penalized for the readmissions they prevent.
  We automate the call and escalate the judgment."
- **Beat 2 (60 s) — green path.** Trigger Margaret's call; teammate answers on
  speaker; agent walks her meds; dashboard flips GREEN.
- **Beat 3 (75 s) — the moment.** Trigger Harold. He admits he's still taking the
  stopped warfarin alongside the new Eliquis. Agent stays calm, gives no advice,
  says the SAFE_HOLD script — and the RED escalation SMS lands **on a judge's
  phone in their hand** while the dashboard flips red.
  (Ask a judge for their number right before, or hand them the "nurse" phone.)
- **Beat 4 (15 s) — close.** "Notice the agent never told Harold what to do —
  it flagged and escalated. That guardrail isn't a limitation, it's the product.
  This is the wedge of a full personal medical secretary: we built the episode
  where it saves lives and gets reimbursed first."

## Fallback ladder (decide at rehearsal, T+2:00)

1. ConversationRelay free-form voice (only if flawless twice in a row)
2. `<Gather>` speech ("yes/no" spoken answers)
3. `<Gather>` DTMF only ("press 1 for yes") — still a winning demo
4. Backup video of a clean run (record one no matter what)
5. Text simulator on screen (absolute last resort)

## Day schedule (owners: A=Twilio, B=state machine+LLM, C=dashboard/SMS/Devpost)

| Time | Milestone | Notes |
|---|---|---|
| T+0:00–0:20 | Repo cloned, venv, Twilio account + number, **all phones verified**, ngrok up | all |
| T+0:20–1:00 | **P1**: Margaret green path on a real phone via `<Gather>` | A+B (P0 simulator already works out of the box) |
| T+1:00–1:40 | **P2**: LLM classification live (pick provider by latency), Harold red path, deflection guardrail | B (+A) |
| T+1:40–2:00 | Escalation SMS on real phones; dashboard (Lovable or `dashboard/index.html`) | C |
| T+2:00–2:30 | Rehearse ×2, record backup video, pick stage mode from ladder | all |
| T+2:30–3:00 | Devpost page (name, what/why, **how we used Twilio**, roles, demo link), submit early | C + all |

Hard rule: feature freeze at T+2:00. After that, only demo-breaking bugs get fixed.

## Rehearsal checklist

- [ ] Margaret green path end-to-end on speakerphone
- [ ] Harold red path: SMS arrives < 5 s after his answer
- [ ] Ask the agent a clinical question mid-call → deflection + RED
- [ ] Kill the model API key → call still works via DTMF (prove invariant #4)
- [ ] Run once on phone-hotspot internet (venue Wi-Fi insurance)
- [ ] Backup video recorded and uploaded
