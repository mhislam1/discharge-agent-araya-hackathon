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
    "Thank you for telling me. I'm letting your nurse know right now — "
    "someone will call you back shortly. Please don't change anything "
    "until you hear from them."
)
REPROMPT_SOFT = "Sorry — was that a yes or a no?"
REPROMPT_DTMF = "Sorry, I didn't catch that. Press 1 for yes, or 2 for no."


def _p(session):  # patient record shortcut
    return session["patient"]


def _quote(utterance: str) -> str:
    """Patient's own words for the escalation SMS; skip DTMF placeholders."""
    u = utterance.strip()
    if not u or u.startswith("["):
        return ""
    return f' — said: "{u[:60]}"'


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
        # asked in the affirmative on purpose: "you are no longer taking it?"
        # is a negation trap — "no" is ambiguous for patients AND classifiers
        return (f"One more important check. The hospital stopped your previous "
                f"medication, {p['stopped_med']['name']} — you should not be "
                f"taking it anymore. Are you still taking it, even now and then?")
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

    # global rule: non-clinical questions — acknowledge, queue for the callback
    if intent == "question":
        _escalate(session, "amber", "patient_question",
                  f"asked mid-call: \"{utterance[:80]}\" — answer on callback")
        return ("Good question — I can't answer that myself, but your care team "
                "will cover it when they call you back. For now — "
                + prompt_for(session))

    # global rule: unclear answers
    if intent == "unclear":
        session["unclear_streak"] += 1
        if session["unclear_streak"] >= 3:
            _escalate(session, "amber", "unreachable_midcall",
                      "could not complete check-in; repeated unclear answers")
            session["done"] = True
            return ("I'm having trouble hearing you, so I'll have someone from "
                    "your care team call you directly. Take care.")
        # first miss: short nudge (at GREET just repeat the greeting — people
        # answer the phone with "Hello?"); second: full question + keypad help
        if session["unclear_streak"] == 1:
            return prompt_for(session) if st == "GREET" else REPROMPT_SOFT
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
                      f"has NOT picked up {p['new_med']['name']}"
                      f"{_quote(utterance)}")
            say_first = ("Okay — a care coordinator will reach out to help "
                         "with the pharmacy. ")
        session["state"] = "NEW_MEDS"

    elif st == "NEW_MEDS":
        if intent == "no":
            _escalate(session, "amber", "nonadherent_new_med",
                      f"not taking {p['new_med']['name']} as prescribed"
                      f"{_quote(utterance)}")
            say_first = "Understood — I'll note that for your care team. "
        session["state"] = "STOPPED"

    elif st == "STOPPED":
        # question is "Are you STILL taking it?" — yes = danger
        if intent == "yes":
            _escalate(session, "red", "taking_stopped_med",
                      f"reports taking BOTH {p['stopped_med']['name']} (stopped "
                      f"{p['discharged']}) and {p['new_med']['name']} — "
                      f"{p['stopped_med']['risk_note']}")
            n = len(p["symptom_checks"])
            say_first = SAFE_HOLD + (" One last quick question. " if n == 1
                                     else " A few more quick questions. ")
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
