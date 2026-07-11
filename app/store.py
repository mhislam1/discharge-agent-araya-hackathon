"""In-memory session store. Deliberately trivial (AGENTS.md: boring tech).
Keyed by patient_id — fine for a demo with two patients and one call at a time."""
import time

SEVERITY = {"gray": 0, "in_call": 1, "green": 2, "amber": 3, "red": 4}

_sessions: dict[str, dict] = {}
_seq = 0  # monotonic call order; wall clock can jump backwards under WSL2


def new_session(patient_id: str, patient: dict) -> dict:
    global _seq
    _seq += 1
    s = {
        "seq": _seq,
        "patient_id": patient_id,
        "patient": patient,
        "state": "GREET",
        "symptom_idx": 0,
        "unclear_streak": 0,
        "status": "in_call",           # gray | in_call | green | amber | red
        "transcript": [],              # [{"who": "agent"|"patient", "text": ...}]
        "escalations": [],             # [{"level", "trigger", "message", "ts"}]
        "fired_triggers": set(),       # idempotency (invariant #6)
        "done": False,
        "started": time.time(),
    }
    _sessions[patient_id] = s
    return s


def get_session(patient_id: str) -> dict | None:
    return _sessions.get(patient_id)


def raise_status(session: dict, status: str) -> None:
    """Status only ever escalates in severity; red > amber > green."""
    if SEVERITY[status] > SEVERITY[session["status"]]:
        session["status"] = status


def snapshot() -> list[dict]:
    """JSON-safe view for the dashboard."""
    out = []
    for pid, s in _sessions.items():
        out.append({
            "patient_id": pid,
            "name": s["patient"]["full_name"],
            "status": s["status"],
            "state": s["state"],
            "escalations": s["escalations"],
            "transcript": s["transcript"][-8:],
        })
    return out
