---
status: canonical
owner: architecture
last_verified: 2026-06-12
canonical_for:
  - hardware safety
related:
  - docs/operations/validation.md
---

# Hardware Safety

Do not perform these operations unless explicitly scoped:

- open a serial port
- send OSC
- move hardware
- change receiver behavior that assumes real hardware
- implement fixed-cycle mode
- perform hardware validation

A future hardware-validation PR must add a pre-checklist, safe dry-run steps,
OSC compatibility checks, rollback steps, and stop steps before real hardware is
used.
