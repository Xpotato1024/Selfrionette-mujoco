---
status: canonical
owner: runtime
last_verified: 2026-08-30
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

## Upstream aggregate integrity

P5 boundaryはP2〜P4のtyped aggregateを盲目的に信頼しない。P2では各boundのstatus、source
identity、parity record、rangeの対応を検証し、resolved statusはboundedな`rad` parityと一致する
場合だけ受け入れる。P3ではpair evaluationから導出されるaggregate status / reasonと入力結果を
照合する。P4ではdiagnostic codeのstatus prefix、aggregate status / reason、dynamic bound
evidenceを照合する。いずれかの不整合、重複identity、diagnostic欠落は該当componentの
`invalid`へ写像し、他componentのclear evidenceで上書きしない。

さらにP5は、immutable constructorを迂回したprovider corruptionも防御境界で再検証する。
resultのschema・robot identity・bounds・conversion relation、boundのjoint / source / parity
identity、有限かつ順序付きのrange、parityのstatus・unit・reason整合性を確認し、空集合や
重複identityが`all()`によって`allow`へ到達することを許さない。conversion relationもsource
space、joint / source / relation / unit identity、有限なnon-zero gear ratio、`sign`、offset、
relation identityの重複を検証する。malformedなsource / evaluation provenanceは安全に読み取れる
文字列だけをreasonへ渡し、例外を上位へ漏らさず`invalid`へ閉じる。この再検証はP2のresolutionや
unit conversionを再実行せず、欠落したauthorityを補完しない。

P4のconfiguration / trajectory resultも同じ防御境界で、status・reason、diagnosticsのtuple/memberと
有限値・optional identity、source identity、trajectoryのsample count、bound evidence status tupleを
再検証する。空のtrajectory provenanceや壊れたdiagnosticは`dynamic:dynamic_result_inconsistent`へ閉じ、
`authoritative`や`all()`の評価で`allow`へ進めない。P2 parityは、完全比較可能なall-`match`のrange差だけを
mismatchとし、`match`と`unknown` / `unavailable`の未解決値はそれぞれP2の`unknown` / `unavailable`
優先順位を維持する。`sample_count == 2` のtrajectoryは有限差分accelerationを生成できないため、
`unavailable_acceleration` diagnosticを必須とし、これを欠くFEASIBLE aggregateは`invalid`へ閉じる。

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
