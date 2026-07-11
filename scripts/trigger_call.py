#!/usr/bin/env python
"""Trigger an outbound call to a demo patient.
Usage: python scripts/trigger_call.py harold
Needs: TWILIO_* creds and PUBLIC_BASE_URL in .env, server running, ngrok up.
Reminder: on a trial account the patient phone number must be VERIFIED."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config  # noqa: E402


def main():
    pid = sys.argv[1] if len(sys.argv) > 1 else "harold"
    patients = config.load_patients()
    if pid not in patients:
        sys.exit(f"unknown patient {pid!r}; options: {list(patients)}")
    if not (config.TWILIO_ACCOUNT_SID and config.TWILIO_AUTH_TOKEN
            and config.TWILIO_FROM_NUMBER and config.PUBLIC_BASE_URL):
        sys.exit("Missing TWILIO_* creds or PUBLIC_BASE_URL in .env")

    from twilio.rest import Client
    client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)
    call = client.calls.create(
        to=patients[pid]["phone"],
        from_=config.TWILIO_FROM_NUMBER,
        url=f"{config.PUBLIC_BASE_URL}/voice/start?pid={pid}")
    print(f"Calling {patients[pid]['full_name']} at {patients[pid]['phone']} "
          f"— call SID {call.sid}")


if __name__ == "__main__":
    main()
