"""Provider-agnostic intent classifier (see docs/ARCHITECTURE.md).

Contract:
    classify(utterance, question_context) -> {"intent": "...", "note": "..."}
intent ∈ {yes, no, unclear, clinical_question}

Rules (AGENTS.md #2, #4):
- The model ONLY classifies. Its text is never spoken to the patient.
- Any failure (timeout, bad JSON, no key) => regex fallback => at worst "unclear",
  which the state machine handles with a DTMF reprompt. A model can never break a call.
"""
import json
import re

import httpx

from . import config

SYSTEM_PROMPT = (
    "You classify a patient's short spoken reply during a medication check-in "
    "call. Given the QUESTION asked and the patient's REPLY, output ONLY a JSON "
    "object: {\"intent\": \"yes\"|\"no\"|\"unclear\"|\"clinical_question\", "
    "\"note\": \"<=12 words of useful detail or empty\"}. "
    "Use clinical_question if the patient asks for medical advice, dosing "
    "guidance, drug-interaction info, or reassurance about symptoms. "
    "Mind negation: for 'you are no longer taking it?', 'right, I stopped' = yes; "
    "'I still take it' = no. No prose, JSON only."
)

_YES = re.compile(r"\b(yes|yeah|yep|yup|correct|right|sure|i (did|have|do)|"
                  r"that's right|stopped|of course|okay|ok|fine)\b", re.I)
_NO = re.compile(r"\b(no|nope|nah|not yet|haven'?t|didn'?t|don'?t|never|"
                 r"still tak|keep tak|kept tak)\b", re.I)
_CLINICAL = re.compile(r"\b(should i|can i take|is it (safe|ok(ay)?)|what if i|"
                       r"interact|double dose|instead of|how (much|many)|"
                       r"ibuprofen|aspirin|advil|tylenol)\b.*\?|"
                       r"\b(should i|can i)\b", re.I)


def _regex_classify(utterance: str) -> dict:
    u = utterance.strip()
    if _CLINICAL.search(u):
        return {"intent": "clinical_question", "note": ""}
    no, yes = bool(_NO.search(u)), bool(_YES.search(u))
    if no and not yes:
        return {"intent": "no", "note": ""}
    # negation-heavy replies like "no, I stopped" mean yes-to-'no longer taking';
    # the LLM handles these better — regex stays conservative:
    if yes and not no:
        return {"intent": "yes", "note": ""}
    return {"intent": "unclear", "note": ""}


def _parse(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    obj = json.loads(m.group(0)) if m else {}
    intent = obj.get("intent", "unclear")
    if intent not in ("yes", "no", "unclear", "clinical_question"):
        intent = "unclear"
    return {"intent": intent, "note": str(obj.get("note", ""))[:120]}


def _user_msg(utterance: str, question_context: str) -> str:
    return f"QUESTION: {question_context}\nREPLY: {utterance}"


def _via_ollama(utterance, ctx) -> dict:
    r = httpx.post(f"{config.OLLAMA_URL}/api/chat", timeout=config.LLM_TIMEOUT_S,
                   json={"model": config.OLLAMA_MODEL, "stream": False,
                         "format": "json",
                         "messages": [
                             {"role": "system", "content": SYSTEM_PROMPT},
                             {"role": "user", "content": _user_msg(utterance, ctx)}]})
    r.raise_for_status()
    return _parse(r.json()["message"]["content"])


def _via_groq(utterance, ctx) -> dict:
    r = httpx.post("https://api.groq.com/openai/v1/chat/completions",
                   timeout=config.LLM_TIMEOUT_S,
                   headers={"Authorization": f"Bearer {config.GROQ_API_KEY}"},
                   json={"model": config.GROQ_MODEL, "temperature": 0,
                         "response_format": {"type": "json_object"},
                         "messages": [
                             {"role": "system", "content": SYSTEM_PROMPT},
                             {"role": "user", "content": _user_msg(utterance, ctx)}]})
    r.raise_for_status()
    return _parse(r.json()["choices"][0]["message"]["content"])


def _via_gemini(utterance, ctx) -> dict:
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{config.GEMINI_MODEL}:generateContent?key={config.GEMINI_API_KEY}")
    r = httpx.post(url, timeout=config.LLM_TIMEOUT_S, json={
        "contents": [{"parts": [{"text": SYSTEM_PROMPT + "\n\n" +
                                 _user_msg(utterance, ctx)}]}]})
    r.raise_for_status()
    return _parse(r.json()["candidates"][0]["content"]["parts"][0]["text"])


_PROVIDERS = {"ollama": _via_ollama, "groq": _via_groq, "gemini_api": _via_gemini}


def classify(utterance: str, question_context: str) -> dict:
    """Never raises. Model failure degrades to regex (invariant #4)."""
    fn = _PROVIDERS.get(config.LLM_PROVIDER)
    if fn:
        try:
            return fn(utterance, question_context)
        except Exception as e:  # timeout, bad JSON, network — all equivalent here
            print(f"[llm] {config.LLM_PROVIDER} failed ({e!r}); regex fallback")
    return _regex_classify(utterance)
