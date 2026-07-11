"""FastAPI app — Twilio Voice webhooks (structured <Gather> mode, P1),
call trigger, dashboard API.

Endpoints:
  POST /voice/start?pid=harold     Twilio fetches first TwiML here
  POST /voice/input?pid=harold     Gather posts Digits/SpeechResult here
  POST /call/{pid}                 trigger an outbound call (or curl it)
  GET  /api/status                 dashboard JSON
  GET  /dashboard                  serves dashboard/index.html
"""
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response

from . import config, llm, state_machine, store

app = FastAPI(title="SafeReturn")
PATIENTS = config.load_patients()
DASH = Path(__file__).resolve().parent.parent / "dashboard" / "index.html"

DTMF_INTENT = {"1": "yes", "2": "no"}
GATHER_HINT = " You can also press 1 for yes, or 2 for no."


def _twiml(inner: str) -> Response:
    return Response(
        content=f'<?xml version="1.0" encoding="UTF-8"?><Response>{inner}</Response>',
        media_type="application/xml")


def _gather(say: str, pid: str) -> str:
    action = f"{config.PUBLIC_BASE_URL}/voice/input?pid={pid}"
    return (f'<Gather input="dtmf speech" numDigits="1" speechTimeout="auto" '
            f'action="{action}" method="POST">'
            f'<Say voice="Polly.Joanna">{say}</Say></Gather>'
            f'<Redirect method="POST">{action}</Redirect>')  # no input => reprompt


@app.post("/voice/start")
async def voice_start(pid: str):
    patient = PATIENTS.get(pid)
    if not patient:
        return _twiml('<Say>Unknown patient. Goodbye.</Say><Hangup/>')
    session = store.new_session(pid, patient)
    first = state_machine.prompt_for(session)
    session["transcript"].append({"who": "agent", "text": first})
    return _twiml(_gather(first + GATHER_HINT, pid))


@app.post("/voice/input")
async def voice_input(pid: str, request: Request):
    session = store.get_session(pid)
    if not session or session["done"]:
        return _twiml("<Say>Goodbye.</Say><Hangup/>")
    form = await request.form()
    digits = (form.get("Digits") or "").strip()
    speech = (form.get("SpeechResult") or "").strip()

    if digits in DTMF_INTENT:                      # keypad always wins (invariant #3)
        intent, utterance = DTMF_INTENT[digits], f"[pressed {digits}]"
    elif speech:
        ctx = state_machine.prompt_for(session)
        result = llm.classify(speech, ctx)
        intent, utterance = result["intent"], speech
    else:
        intent, utterance = "unclear", "[silence]"

    say = state_machine.advance(session, intent, utterance)
    if session["done"]:
        return _twiml(f'<Say voice="Polly.Joanna">{say}</Say><Hangup/>')
    return _twiml(_gather(say, pid))


@app.post("/call/{pid}")
async def trigger_call(pid: str):
    """Kick off the outbound call. Requires Twilio creds + PUBLIC_BASE_URL."""
    patient = PATIENTS.get(pid)
    if not patient:
        return JSONResponse({"error": "unknown patient"}, status_code=404)
    if not (config.TWILIO_ACCOUNT_SID and config.PUBLIC_BASE_URL):
        return JSONResponse(
            {"error": "Twilio creds / PUBLIC_BASE_URL missing — "
                      "use scripts/test_conversation.py meanwhile"},
            status_code=400)
    from twilio.rest import Client
    client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)
    call = client.calls.create(
        to=patient["phone"], from_=config.TWILIO_FROM_NUMBER,
        url=f"{config.PUBLIC_BASE_URL}/voice/start?pid={pid}")
    return {"queued": call.sid, "to": patient["phone"]}


@app.get("/api/status")
async def status():
    known = [{"patient_id": k, "name": v["full_name"], "status": "gray",
              "state": "-", "escalations": [], "transcript": []}
             for k, v in PATIENTS.items() if not store.get_session(k)]
    return known + store.snapshot()


@app.get("/dashboard")
async def dashboard():
    return FileResponse(DASH)
