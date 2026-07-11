#!/usr/bin/env python
"""Run the whole conversation in the terminal — no phone, no Twilio, no model
API needed (regex classifier by default). This is P0 and the fastest dev loop.

Usage:
    python scripts/test_conversation.py harold
    python scripts/test_conversation.py margaret

Try answering: "yes" / "no" / "well the pharmacy didn't have it" /
"should I take ibuprofen with this?" / "1" / "2"
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config, llm, state_machine, store  # noqa: E402

COLORS = {"green": "\033[92m", "amber": "\033[93m", "red": "\033[91m",
          "in_call": "\033[96m", "gray": "\033[90m"}
RESET = "\033[0m"


def main():
    pid = sys.argv[1] if len(sys.argv) > 1 else "harold"
    patients = config.load_patients()
    if pid not in patients:
        sys.exit(f"unknown patient {pid!r}; options: {list(patients)}")
    session = store.new_session(pid, patients[pid])

    print(f"\n=== SafeReturn text simulator · patient: {pid} · "
          f"classifier: {config.LLM_PROVIDER} ===\n")
    say = state_machine.prompt_for(session)
    while True:
        print(f"AGENT: {say}")
        if session["done"]:
            break
        raw = input(f"{pid.upper()}> ").strip()
        if raw in ("1", "2"):
            intent, utter = {"1": "yes", "2": "no"}[raw], f"[pressed {raw}]"
        else:
            r = llm.classify(raw, state_machine.prompt_for(session))
            intent, utter = r["intent"], raw
            print(f"       (classified: {intent})")
        say = state_machine.advance(session, intent, utter)

    c = COLORS.get(session["status"], "")
    print(f"\n--- call ended · status: {c}{session['status'].upper()}{RESET} ---")
    for e in session["escalations"]:
        print(f"  {COLORS.get(e['level'], '')}{e['level'].upper()}{RESET}: {e['message']}")


if __name__ == "__main__":
    main()
