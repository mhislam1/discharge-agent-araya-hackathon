"""The conversation state machine. Source of truth spec: docs/STATE_MACHINE.md.

Invariants enforced here (AGENTS.md):
  #1 no medical advice — clinical_question => DEFLECTION + RED, repeat question
  #2 the state machine decides; templates only are spoken
  #6 idempotent escalations
"""
import time

from . import escalation, store

# ---- fixed scripts (spoken verbatim; never LLM-generated) ----
DEFLECTION_SCRIPT = (
    "That's an important question for your nurse, and I want you to get the "
    "right answer. I'm flagging it right now so they call you back. "
    "I'm an automated assistant and can't give medical advice."
)
SAFE_HOLD = (
    "Thank you for telling me — that's exactly the kind of thing we check. "
    "I'm letting your nurse know right now, and someone will call you back "
    "shortly. Please don't change anything until you hear from them."
)
REPROMPT_DTMF = "Sorry, I didn't catch that. Press 1 for yes, or 2 for no."


def _p(session):  # patient record shortcut
    return session["patient"]


# ---- prompts (templates, personalized) ----
def prompt_for(session: dict) -> str:
    p, st = _p(session), session["state"]
    if st == "GREET":
        return (f"Hi, is this {p['name']}? This is the automated care assistant "
                f"calling on behalf of {p['practice']} after your recent hospital "
                f"stay. This will take about two minutes. Is now an okay time?")
    if st == "PICKUP":
        return (f"You were prescribed a new medication, {p['new_med']['name']}. "
                f"Were you able to pick it up from the pharmacy?")
    if st == "NEW_MEDS":
        return (f"Have you been taking {p['new_med']['name']} "
                f"{p['new_med']['schedule_phrase']}?")
    if st == "STOPPED":
        return (f"One more important check. The hospital stopped your previous "
                f"medication, {p['stopped_med']['name']}. Just to confirm — "
                f"you are no longer taking it?")
    if st == "SYMPTOMS":
        return p["symptom_checks"][session["symptom_idx"]]
    if st == "CLOSE":
        if session["status"] in ("amber", "red"):
            return (f"Thank you, {p['name']}. Your care team has been notified and "
                    f"will be in touch shortly. Take care.")
        return (f"That all sounds good, {p['name']}. Your care team can see this "
                f"update. Thanks for your time, and take care.")
    return "Goodbye."


# ---- escalation helper (idempotent) ----
def _escalate(session: dict, level: str, trigger: str, detail: str) -> None:
    key = (session["patient_id"], trigger)
    if key in session["fired_triggers"]:
        return
    session["fired_triggers"].add(key)
    msg = escalation.send(level, _p(session), trigger, detail)
    session["escalations"].append(
        {"level": level, "trigger": trigger, "message": msg, "ts": time.time()})
    store.raise_status(session, level)


# ---- the transition function ----
def advance(session: dict, intent: str, utterance: str = "") -> str:
    """Consume one classified patient answer; return the next thing to SAY.
    Sets session['done'] when the call should end."""
    session["transcript"].append({"who": "patient", "text": utterance or intent})
    say = _advance(session, intent, utterance)
    session["transcript"].append({"who": "agent", "text": say})
    return say


def _advance(session: dict, intent: str, utterance: str) -> str:
    p, st = _p(session), session["state"]

    # global rule: clinical questions (invariant #1)
    if intent == "clinical_question":
        _escalate(session, "red", "advice_requested",
                  f"asked for medical advice mid-call: \"{utterance[:80]}\"")
        return DEFLECTION_SCRIPT + " Now, back to my question. " + prompt_for(session)

    # global rule: unclear answers
    if intent == "unclear":
        session["unclear_streak"] += 1
        if session["unclear_streak"] >= 3:
            _escalate(session, "amber", "unreachable_midcall",
                      "could not complete check-in; repeated unclear answers")
            session["done"] = True
            return ("I'm having trouble hearing you, so I'll have someone from "
                    "your care team call you directly. Take care.")
        return REPROMPT_DTMF + " " + prompt_for(session)
    session["unclear_streak"] = 0

    say_first = ""  # optional interjection before next prompt

    if st == "GREET":
        if intent == "no":
            _escalate(session, "amber", "declined_checkin",
                      "declined the check-in call")
            session["done"] = True
            return "No problem, we'll try you another time. Take care."
        session["state"] = "PICKUP"

    elif st == "PICKUP":
        if intent == "no":
            _escalate(session, "amber", "rx_not_picked_up",
                      f"has NOT picked up {p['new_med']['name']}")
            say_first = ("Okay — a care coordinator will reach out to help "
                         "with the pharmacy. ")
        session["state"] = "NEW_MEDS"

    elif st == "NEW_MEDS":
        if intent == "no":
            _escalate(session, "amber", "nonadherent_new_med",
                      f"not taking {p['new_med']['name']} as prescribed")
            say_first = "Understood — I'll note that for your care team. "
        session["state"] = "STOPPED"

    elif st == "STOPPED":
        # NOTE: question is "you are NO LONGER taking it?"
        # yes => safely stopped; no => STILL taking it => RED
        if intent == "no":
            _escalate(session, "red", "taking_stopped_med",
                      f"reports taking BOTH {p['stopped_med']['name']} (stopped "
                      f"{p['discharged']}) and {p['new_med']['name']} — "
                      f"{p['stopped_med']['risk_note']}")
            say_first = SAFE_HOLD + " Just a couple more quick questions. "
        session["state"] = "SYMPTOMS"
        session["symptom_idx"] = 0

    elif st == "SYMPTOMS":
        if intent == "yes":
            _escalate(session, "red", f"symptom_flag_{session['symptom_idx']}",
                      f"symptom flag: \"{p['symptom_checks'][session['symptom_idx']]}\" -> YES")
        session["symptom_idx"] += 1
        if session["symptom_idx"] >= len(p["symptom_checks"]):
            session["state"] = "CLOSE"

    if session["state"] == "CLOSE":
        session["done"] = True
        if session["status"] == "in_call":
            session["status"] = "green"
        return say_first + prompt_for(session)

    return say_first + prompt_for(session)
