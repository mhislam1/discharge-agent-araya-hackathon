#!/usr/bin/env python
"""Speak the Twilio ConversationRelay WebSocket protocol against our local
server — no phone, no Twilio needed. Requires the server running (uvicorn).

Usage:
    python scripts/test_relay.py harold

Try answering: "yes" / "no" / "well the pharmacy didn't have it" /
"should I take ibuprofen with this?" / "1" / "2"
"""
import asyncio
import json
import sys

import websockets

URL = "ws://localhost:8000/relay"


async def main():
    pid = sys.argv[1] if len(sys.argv) > 1 else "harold"

    async with websockets.connect(f"{URL}?pid={pid}") as ws:
        await ws.send(json.dumps({
            "type": "setup",
            "sessionId": "test",
            "callSid": "CAtest",
            "customParameters": {"pid": pid},
        }))
        print(f"\n=== SafeReturn relay simulator · patient: {pid} ===\n")

        stdin_done = False
        while True:
            try:
                raw = await ws.recv()
            except websockets.exceptions.ConnectionClosed:
                print("--- connection closed ---")
                break

            msg = json.loads(raw)
            if msg.get("type") == "text":
                print(f"AGENT: {msg.get('token', '')}")
            elif msg.get("type") == "end":
                print("--- call ended ---")
                break
            else:
                continue

            if stdin_done:
                continue  # keep draining server messages until end/close

            try:
                line = (await asyncio.to_thread(input, f"{pid.upper()}> ")).strip()
            except EOFError:
                stdin_done = True
                continue

            if line in ("1", "2"):
                await ws.send(json.dumps({"type": "dtmf", "digit": line}))
            else:
                await ws.send(json.dumps({
                    "type": "prompt",
                    "voicePrompt": line,
                    "lang": "en-US",
                    "last": True,
                }))


if __name__ == "__main__":
    asyncio.run(main())
