"""ConversationRelay WebSocket transport — streaming STT/TTS alternative to <Gather>.
The state machine and classifier are unchanged; this is transport only."""
import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from . import config, llm, state_machine, store

router = APIRouter()
DTMF_INTENT = {"1": "yes", "2": "no"}


@router.websocket("/relay")
async def relay(ws: WebSocket):
    await ws.accept()
    session = None

    async def speak(text: str) -> None:
        await ws.send_text(json.dumps({"type": "text", "token": text, "last": True}))

    async def end() -> None:
        await ws.send_text(json.dumps({"type": "end"}))

    async def respond(say: str) -> bool:
        """Speak the next line; on the final line let TTS finish, then end.
        Returns True when the call is over."""
        await speak(say)
        if session["done"]:
            await asyncio.sleep(min(20.0, max(4.0, len(say.split()) / 2.5)))
            await end()
        return session["done"]

    try:
        while True:
            try:
                # dead air: Gather mode reprompts via <Redirect>; here we time out
                # (budget covers our TTS playing + the patient thinking)
                raw = await asyncio.wait_for(ws.receive_text(), timeout=25.0)
            except asyncio.TimeoutError:
                if not session or session["done"]:
                    continue
                if await respond(state_machine.advance(session, "unclear", "[silence]")):
                    break
                continue
            msg = json.loads(raw)
            t = msg.get("type")
            if t == "setup":
                pid = (msg.get("customParameters") or {}).get("pid") or ws.query_params.get("pid", "")
                patient = config.load_patients().get(pid)
                if not patient:
                    await end()
                    break
                session = store.new_session(pid, patient)
                first = state_machine.prompt_for(session)
                session["transcript"].append({"who": "agent", "text": first})
                await speak(first)
            elif t in ("prompt", "dtmf") and session and not session["done"]:
                if t == "dtmf":
                    digit = str(msg.get("digit", ""))
                    if digit not in DTMF_INTENT:
                        continue
                    intent, utter = DTMF_INTENT[digit], f"[pressed {digit}]"
                else:
                    utter = (msg.get("voicePrompt") or "").strip()
                    if not utter:
                        continue
                    ctx = state_machine.prompt_for(session)
                    result = await asyncio.to_thread(llm.classify, utter, ctx)
                    intent = result["intent"]
                say = state_machine.advance(session, intent, utter)
                if await respond(say):
                    break
            elif t == "interrupt":
                pass  # patient barged in; CR already stopped TTS — nothing to do
            elif t == "error":
                print(f"[relay] error from Twilio: {msg}")
    except WebSocketDisconnect:
        pass
