---
status: draft
owner: runtime
last_updated: 2026-07-14
related:
  - docs/architecture/runtime-composition.md
  - docs/operations/r7-e-p25-live-viewer-pacing-backlog.md
  - docs/operations/hardware-safety.md
related_issues:
  - "#324"
  - "#341"
  - "#380"
---

# Provisional Persistent Task Runtime and Robot Output Round

## Status

This document records a provisional future-round direction so that cleanup and
near-term implementation do not erase the intended handoff.

It is not a formal Round allocation, implementation specification, permission to
access hardware, or permission to send OSC. The Round identifier, issue set,
interfaces, deployment target, and physical acceptance procedure remain to be
reviewed and assigned after cleanup.

## Decision

R7-E follow-up work established a production viewer path with bounded live
transport, render-cadence coalescing, and wall-clock pacing. The next operational
milestone is larger than the current workspace-policy Issue alone.

The future Round should treat the following as one staged system objective:

> Operate sustained manipulation tasks through an explicitly managed runtime
> session, with safe process lifecycle, workspace-aware continuous motion,
> service/container operation, OSC output boundaries, and a separately gated
> physical robot path.

Before formalizing that Round, perform behavior-preserving cleanup inventory and
remove or isolate only assets proven unnecessary. Cleanup must not delete code,
contracts, fixtures, or adapters that may be required by the future runtime,
service, OSC dry-run, or physical safety boundary.

## Why this is a new Round

The remaining work crosses several responsibilities:

- motion feasibility and workspace policy;
- long-duration directional task behavior;
- task/session start, pause, resume, stop, and completion;
- process supervision, daemon/service behavior, and graceful shutdown;
- container configuration, health checks, logs, and restart policy;
- OSC output schema, rate, stale-command behavior, and stop semantics;
- physical robot operator gates and emergency-stop-compatible procedures.

These concerns should not be appended to R7-E as isolated fixes. They require a
new objective, staged dependencies, explicit safety boundaries, and completion
evidence that distinguishes software-only validation from physical operation.

## Provisional work packages

The following packages describe intended responsibility boundaries. They are not
yet assigned Issue numbers and may be split or reordered during formal planning.

### 1. Requirements and safety boundary

- define the runtime, task, service, OSC, and physical-operation boundaries;
- identify configuration ownership and source-of-truth rules;
- define operator permissions and prohibited side effects for each stage;
- define stop, rollback, stale-input, disconnect, and failure semantics;
- define the evidence required before enabling the next stage.

### 2. Task and session lifecycle

- run-until-stop and finite-task modes;
- task/session identity and start time;
- start, pause, resume, stop, complete, abort, and failure states;
- idempotent commands and bounded shutdown;
- periodic bounded health summaries;
- explicit behavior when the controlling viewer disconnects or becomes stale.

### 3. Process, service, and container lifecycle

- foreground CLI remains a supported development path;
- supervised daemon/service mode;
- container image and configuration injection without embedded credentials;
- readiness, liveness, restart, and graceful termination contracts;
- bounded log retention and diagnostic export;
- no implicit hardware access during service startup.

### 4. Workspace-aware sustained motion

- local incremental directional motion over long tasks;
- workspace, joint-limit, singularity, acceleration, and numerical-feasibility
  handling;
- explicit hold, reject, recover, and operator-visible reason semantics;
- repeated direction changes and boundary approach/recovery;
- soak tests that measure stability, memory, pacing, command age, and recovery;
- separation between command feasibility and physical output enablement.

### 5. OSC output boundary and dry-run

- versioned OSC command schema and endpoint configuration;
- dry-run/recording sink before network transmission;
- bounded output rate and latest-command policy;
- stale input, disconnect, shutdown, and explicit stop-command semantics;
- no assumption that OSC transmission implies robot acceptance or movement;
- network side effects only in a dedicated Issue with explicit permission.

### 6. Physical robot gate

- dedicated hardware Issue and operator procedure;
- explicit target host/port/device and verified command mapping;
- physical clearance, emergency stop, stop command, and rollback procedure;
- bounded initial command and staged motion envelope;
- expected/observed output recording;
- no unattended enablement or implicit startup actuation.

### 7. Completion and operational audit

- software-only acceptance separated from hardware acceptance;
- long-duration session and reconnect evidence;
- service/container lifecycle evidence;
- OSC dry-run and network-enabled evidence separated;
- physical operator gate evidence;
- canonical operations documentation and remaining-risk handoff.

## Provisional dependency order

```text
R7-E P26 cleanup inventory
  -> behavior-preserving cleanup issues justified by the inventory
  -> formal new-Round requirements and safety design
  -> task/session lifecycle
  -> service/container lifecycle
  -> workspace-aware sustained motion
  -> OSC dry-run boundary
  -> explicitly permitted OSC transmission
  -> physical robot operator gate
  -> completion audit
```

The exact order between service/container work and sustained-motion work may be
revised after the requirements Issue. Physical output must remain after the
software-only and dry-run gates.

## Relationship to Issue #341

Issue #341 currently captures workspace-aware viewer endpoint motion. Its core
problem remains valid, but the implementation and acceptance criteria should be
reviewed in the context of the new Round.

Until that Round is formalized:

- keep #341 open as evidence and a requirements source;
- do not treat #341 alone as acceptance for sustained task operation;
- do not expand #341 into daemon, container, OSC, or hardware work;
- decide later whether #341 becomes a bounded child Issue, is rewritten, or is
  superseded by a more complete workspace/sustained-motion Issue.

## Cleanup guardrail

The cleanup inventory preceding this Round must classify candidates using at
least the following outcomes:

- keep as production architecture;
- keep as test fixture or validation asset;
- integrate into the production path;
- isolate as legacy/reference-only;
- deprecate with a documented replacement;
- remove in a dedicated behavior-preserving Issue;
- defer because the future Round may depend on it.

A file or API must not be removed solely because it is not used by the current
viewer smoke path. Search imports, tests, docs, scripts, fixtures, public exports,
legacy references, and plausible future-Round ownership before recommending
removal.

## Exit criteria for formal Round creation

The provisional direction may be converted into a formal Round only after:

- cleanup inventory identifies the production and compatibility surface;
- the intended deployment environment is selected;
- task/session state and process ownership are defined;
- OSC schema and stop/stale behavior are designed without transmitting data;
- workspace and sustained-motion acceptance scenarios are defined;
- hardware safety requirements and operator responsibilities are reviewed;
- the work is split into independently reviewable Issues with explicit gates;
- Round numbering and parent/roadmap allocation are recorded in the repository
  numbering source of truth.

## Explicit non-goals of this proposal

- implementing daemon, service, or container behavior;
- modifying motion policy or workspace limits;
- sending OSC packets;
- opening serial ports;
- uploading firmware;
- actuating a robot;
- choosing a final deployment platform;
- assigning final Round or Issue numbers;
- authorizing destructive cleanup.
