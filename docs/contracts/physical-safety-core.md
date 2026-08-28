---
status: canonical
owner: runtime
last_verified: 2026-08-28
canonical_for:
  - physical safety core decision
  - limit / collision / dynamic composition
  - bounded software safety sampling
related:
  - docs/contracts/physical-safety-envelope.md
  - docs/contracts/physical-limit-resolution.md
  - docs/contracts/physical-collision-safety.md
  - docs/contracts/physical-trajectory-feasibility.md
  - docs/operations/hardware-safety.md
---

# Physical safety core契約

## 目的とownership

`runtime/safety/physical_safety_core.py`は、P2のlimit resolution、P3のcollision policy、
P4のdynamic feasibility resultを一つのcandidate-level decisionへcomposeするpure boundaryで
ある。個別checkerの実装、MuJoCo state、command application、viewer判定、hardware outputは
このmoduleが所有しない。resultはimmutableで、state / commandを書き換えない。

## Closed decision vocabulary

| action | 意味 |
|---|---|
| `allow` | 全componentがclearかつ必要なbound evidenceがauthoritativeであるため、後続layerがcandidateを扱える |
| `hold` | near-collision、task-object contact、またはprovisional boundのため、現在状態を保持する |
| `reject` | limit source mismatchまたはdynamic threshold超過でcandidateを拒否する |
| `stop` | collision / penetrationを検知し、直ちに停止する |
| `unavailable` | unknown / unavailable evidenceのため、安全判定を成立させられない |
| `invalid` | schema、dimension、numerical、またはcomponent resultがinvalidである |

`unknown`、`unavailable`、`invalid`、conflict、missing componentは`allow`へfallbackしない。
既知のcollisionは`stop`を優先し、invalidは常に最優先とする。その他のaction precedenceは
`invalid > stop > unavailable > reject > hold > allow`で固定する。

## Reason / provenance

`SafetyReason`はmachine-readable `reason_code`、owner `component`、operator-visible message、
provenanceを一体で保持する。`reason.identity`（`component:reason_code`）を両表示面で共有し、
limit source name、collision evidence source、dynamic source identity、candidate provenanceを
重複なくsorted tupleへ束ねる。個別`SafetyComponentAssessment`も同じreason contractを持つ。

## Component mapping

P2 `resolved_authoritative`はallow、`resolved_provisional`はhold、mismatchはreject、unknown /
unavailableはunavailable、invalidはinvalidへ写像する。P3 clearはallow、near-collision / contact
はhold、collisionはstop、unknown / unavailableはunavailable、invalidはinvalidへ写像する。
P4 feasibleはauthoritative evidenceが揃った場合だけallow、provisionalはhold、rejectedはreject、
unknown / unavailableはunavailable、invalidはinvalidへ写像する。

## Bounded sampling

`evaluate_bounded_safety_samples`はfinite candidate sequenceを順序通り評価し、最初のnon-allow
decisionで停止する。結果はsample index、candidate identity、component assessments、reason、
provenanceを保持する。これはsoftware fixture / bounded envelope characterizationであり、
mesh全体、full planner、実機安全、physical actuation、manual hardware validationの証明では
ない。

serial、OSC、robot output、deployment、credentials、#509 hardware validationはscope外である。
