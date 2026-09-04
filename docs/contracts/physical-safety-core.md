---
status: canonical
owner: runtime
last_verified: 2026-09-04
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

## Upstream guaranteeとP5 defense

P2、P3、P4のconstructorと公開validatorが、それぞれのcanonical data、inventory、policy、
identity、evidence、status、aggregateを生成・検証する。P5はその保証を置き換えず、公開validator
とtyped DTO invariantをdecision直前に再利用して、constructor bypass、部分的な削除、contextや
policyのidentity tamper、malformed provenanceを防御する。P5はP2のrange / conversion formula、
P3のcollision evaluator、P4のdynamic evaluatorを複製せず、欠落したbound、pair、source、evidence、
authorityを作成・補完しない。

したがってP5の`allow`は、全componentのcanonical aggregateが完全で、かつ必要なphysical
authority evidenceが明示された場合だけ成立する。completeなprovisional resultは`hold`へ写像し、
`UNAVAILABLE/unavailable_qvel`、`UNAVAILABLE/unavailable_acceleration`など正規の未取得証拠は
`unavailable`へ保持する。P5は新しいphysical authorityや実機測定値を生成しない。

P5自身にも公開canonical validatorを持つ。`validate_safety_input`はcandidate identityとtop-level
provenanceを検証し、`validate_safety_reason`と`validate_safety_decision`はconstructorと同じ
binding fingerprintを使ってreason、component assessment、action、aggregate provenanceを再検証する。
通常の`SafetyDecision`は`limit`、`collision`、`dynamic`の3 assessmentを必須とし、actionとreasonは
このcanonical順序からのみ受け付け、最高優先度assessmentからのみ導出できる。入力エラー用の`input:invalid_safety_input`だけが空assessmentを
許容する。`allowed`は呼出し時にもvalidatorを通るため、constructor後のaction、reason、nested assessment
改変は`False`となる。

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
重複なくsorted tupleへ束ねる。個別`SafetyComponentAssessment`はcomponent別のcanonical
reason/action mappingと完全一致しなければならず、unknown reasonや`unavailable`理由の
自己申告`allow`を構成できない。canonicalなallow reasonは空でないconcrete provenanceを
必須とする。

## Upstream aggregate integrity

P5 boundaryはP2〜P4のtyped aggregateを盲目的に信頼しない。P2では各boundのstatus、source
identity、parity record、rangeの対応を検証し、resolved statusはboundedな`rad` parityと一致する
場合だけ受け入れる。P3ではpair evaluationから導出されるaggregate status / reasonと入力結果を
照合し、typed `CollisionContext`のrobot / model / policy / inventory identityとexpected pair coverageも
保持する。P4では公開validatorを呼び出し、diagnostic codeのstatus prefix、aggregate status / reason、
dynamic bound、availability、source、velocity evidenceを照合する。いずれかの不整合、重複identity、diagnostic欠落は該当componentの
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

`evaluate_bounded_safety_samples`の戻り値も`validate_bounded_safety_sampling_result`で再検証する。
decisionsは空でないtupleで、`first_non_allow_index`は実際の最初のnon-allowと完全一致しなければならない。
non-allowが存在する場合、sequenceはそのdecisionで停止し、後続のtrailing decisionを許可しない。
aggregateのaction、reason、provenanceは、そのindexのdecision（全件allowの場合は最後のdecision）からcanonicalに
導出され、`(ALLOW, REJECT)`を`first_non_allow_index = 0`やaggregate `ALLOW`として保持することはできない。
`action`と`allowed`は改変時にfail-closedとなる。これらはP5のcomposition contractであり、upstream checkerの
formulaやphysical authorityを追加するものではない。

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
