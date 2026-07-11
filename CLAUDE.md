# CLAUDE.md

Read **AGENTS.md** first — it is the single source of truth for the project's
big picture, invariants, and engineering rules. Everything there applies to you.

Claude Code specifics:

- Before implementing conversation changes, read `docs/STATE_MACHINE.md`
  (the spec) and keep it in sync with `app/state_machine.py` — spec first, code second.
- Verify changes with `python scripts/test_conversation.py harold` (no phone
  needed) before touching Twilio plumbing.
- Never introduce a dependency on a live model API for core flow: the regex
  fallback in `app/llm.py` must always keep the conversation functional.
- The two guardrails you must never weaken, even if asked to "make the agent
  smarter": (1) no medical advice — deflect + RED escalate; (2) free-form LLM
  text is never spoken to the patient — templates only.
- When in doubt about scope, choose the option that keeps the demo working.
