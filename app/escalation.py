"""AMBER/RED escalations via Twilio SMS.
No Twilio creds configured => print to log instead (invariant #4)."""
from . import config

_client = None
if config.TWILIO_ACCOUNT_SID and config.TWILIO_AUTH_TOKEN:
    try:
        from twilio.rest import Client
        _client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)
    except Exception as e:
        print(f"[escalation] Twilio client unavailable: {e!r}")


def _compose(level: str, patient: dict, trigger: str, detail: str) -> str:
    if level == "red":
        return f"[SafeReturn] RED {patient['full_name']}: {detail}. Callback requested NOW."
    return f"[SafeReturn] {patient['full_name']}: {trigger}. {detail}. Callback suggested."


def send(level: str, patient: dict, trigger: str, detail: str) -> str:
    """Returns the message text (for the dashboard log) regardless of transport."""
    msg = _compose(level, patient, trigger, detail)
    to = config.NURSE_PHONE if level == "red" else config.COORDINATOR_PHONE
    if _client and to and config.TWILIO_FROM_NUMBER:
        try:
            _client.messages.create(
                body=msg, from_=config.TWILIO_FROM_NUMBER, to=to)
            print(f"[escalation] SMS sent to {to}: {msg}")
        except Exception as e:
            print(f"[escalation] SMS failed ({e!r}) — logged only: {msg}")
    else:
        print(f"[escalation] (no SMS transport) {level.upper()}: {msg}")
    return msg
