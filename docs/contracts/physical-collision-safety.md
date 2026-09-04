---
status: canonical
owner: runtime
last_verified: 2026-09-05
canonical_for:
  - self-interference collision policy
  - environment clearance policy
related:
  - docs/contracts/physical-limit-resolution.md
  - docs/architecture/research-execution-roadmap.md
  - docs/operations/hardware-safety.md
---

# Physical collision safety契約

## 目的とscope

`runtime/safety/collision_policy.py`は、MuJoCo geometryのexplicit inventory、pair policy、
clearance evidenceをpureなtyped resultへ変換する。self-interference、structural proximity、
environment collision、task-object contactを区別し、configurationと有限のbounded trajectoryを
physical output前に検査できる境界を提供する。これはmesh非接触やsoftware fixtureだけで実機安全を
証明する機能ではない。

## Geometry roleとpair classification

各geomは`robot`、`tool`、`environment`、`task_object`、`unknown`のexplicit roleを持つ。
`unknown` role、missing geom/body name、robot geometry欠落は`invalid`であり、環境やself pairへ
黙って分類しない。同じbodyへ複数の異なるroleを割り当てるrole集合の重複も`invalid`とする。
pairは二つの異なる具体的geom nameから決まり、wildcardは使わない。少なくとも一方が
`robot`または`tool` roleであるpairは、bodyが同じでもinventoryへ含める。同一bodyの異なるgeomは
`structural_proximity`として分類し、explicit exclusionがない限りproviderのclearance evidenceを
要求する。

| pair | classification |
|---|---|
| robot/tool roleを含むpair（別body） | `self_interference` |
| robot/tool roleを含むpair（同一body） | `structural_proximity` |
| robot/tool role / environment | `environment_collision` |
| robot/tool role / task_object | `task_object_contact` |
| 明示されたstructural proximity exclusion | `structural_proximity` |

task-object contactはself-interferenceへ変換しない。R7-H #413のcontact identityは、同じ
explicit pair boundaryへ後続接続できる。

`read_mujoco_contact_observations(model, data, inventory)`は同じtyped inventoryを受け取り、
pairのroleを参照して`task_object_contact`だけに`contact=True`を設定する。それ以外の
`self_interference`、`structural_proximity`、`environment_collision`は`contact=False`のまま
MuJoCoのsigned distanceを保持するため、負のdistanceはそれぞれのpenetration reasonへ到達する。
inventory外のpair、unknown role、missing geom、malformed distanceはadapterでfail-closedに停止し、
`invalid_collision_observation`へ変換してclearへ昇格させない。`mj_id2name`、model/dataのcount、
`__index__`、geom/contact配列・field accessorから発生する通常の`Exception`（`RuntimeError`を
含む）は、inventoryや観測を部分生成せず、明示的なadapter境界でtyped `ValueError`へ正規化する。
これによりadapter異常が正常な`CLEAR`へ到達する経路を持たない。一方、`SystemExit`、
`KeyboardInterrupt`、`GeneratorExit`その他の`BaseException`はプロセス制御として捕捉しない。
MuJoCoの`ngeom`、`ncon`、geom/body/contact indexは、暗黙の`int`変換を行わず、
`operator.index`を満たす整数like scalarとして検証した後にだけ使用する。Python / NumPyの
`bool`、fractional値、string、その他の非整数値、負値、範囲外indexは変換前に拒否し、
malformedなcountを空の観測へ縮約しない。したがって、malformedな`ncon`が全structural
exclusionの正常`CLEAR`へ混入することはない。正常なNumPy integral scalarと`__index__`実装は
受理する。

## Clearance semantics

distanceのunitはgeom surface間のmeterである。`distance < 0`はpenetration、
`0 <= distance <= clearance_m + near_collision_margin_m`はnear-collision、
それより大きい値はclearとなる。task-object pairの明示contact observationだけは距離thresholdより
先に評価し、有限かつnon-negativeなdistanceであればthresholdを超えても`contact`となる。
負のdistanceは既存のpenetration規則を優先してcollisionとし、distance欠落は`unknown`、
contact observation欠落は`unavailable`であり、clearへfallbackしない。task-object以外のpairに
contact flagを付けた観測、またはcontact flagにdistanceがない観測は
`invalid_collision_observation`としてfail closedにする。`CollisionEvaluation`は`near_collision_margin_m`も保持し、
near evidenceの上限を同じthresholdから検証する。`collision` evidenceは負のdistance、
`pair_clear` evidenceは`clearance_m + near_collision_margin_m`を超えるdistanceを必須とする。
負のdistanceによる`collision`のreasonはpair kindごとに固定し、
`self_interference`は`self_interference_penetration`、同一bodyの`structural_proximity`は
`structural_proximity_penetration`、`environment_collision`は`environment_penetration`、
`task_object_contact`は`task_object_penetration`とする。same-body structural pairを
task-objectのpenetration reasonへ読み替えず、kindと`COLLISION` statusを保持する。
`contact` evidenceはnon-negative distanceとcanonicalな`task_object_contact` reasonを必須とし、
負のdistanceはcollisionとして扱う。provider由来の非-excluded evaluationは`clear`だけでなく、
`collision`、`near_collision`、`contact`などのnon-clear statusでもtyped provenanceを必須とする。
providerが観測したdistance欠落による`unknown`もtyped provenanceを必須とする一方、観測自体が
存在しない`unavailable`はprovenanceなしで表現できる。provider evidenceを伴う`invalid`も
provenanceを失ってはならない。`invalid`でprovenanceを省略できるのは、provider観測が存在せず
内部validatorが生成するcanonicalなinternal reason code allowlistに含まれるfail-closed reason
だけであり、allowlist外のunknown / unrecognized reasonはprovenanceなしでは拒否する。reason
messageの部分一致やheuristicでinternal扱いへ昇格させない。`unknown` kindはどのstatusでも
evidenceを構成できない。

## Exclusion provenance

collision exclusionは具体的な`pair_id`、理由、evidence referenceを持つsingle-pair declaration
だけを許可する。異なるbodyの`self_interference` pairは、evidence referenceがあっても除外できない。
explicit exclusionは実際に同一bodyで`structural_proximity`へ分類されるpairだけを許可する。
`*|*`等のglobal ignore、environment collisionの除外、根拠なしのstructural exclusionは拒否する。
`unknown`等のplaceholder pair/source/provenanceは拒否する。
exclusionの存在は全geomのcollision filterを変更せず、そのpairだけを
`explicit_structural_exclusion`として追跡可能にする。clear evaluationのpairとevidence referenceは
contextへbindされたpolicy exclusionと一致しなければならず、callerが直接作ったarbitrary exclusion
をclearへ昇格させない。`CollisionContext`のpolicy fingerprintに含める全exclusionは、同じ
contextのinventory fingerprintから導出した`expected_pair_ids`集合に含まれ、かつ導出kindが
`structural_proximity`でなければならない。したがってinventory外のpairや異なるbodyの
`self_interference` pairをfingerprintへ直接注入して保持・無視することもできない。
宣言済みexclusion pairのaggregate evaluationも、必ず`CLEAR`、
`explicit_structural_exclusion`、`STRUCTURAL_PROXIMITY`、宣言済みprovenance、
`distance=None`の完全一致でなければならず、collision、near-collision、contact、unknown、
unavailable、invalid、`pair_clear`を同じpairへ結合しない。

## Configuration / trajectory result

`CollisionContext`はfrozenなtyped bindingであり、robot/model、policy ID/revision、inventory
ID/revision、non-emptyかつuniqueな具体的`expected_pair_ids`を保持する。さらにinventoryの
geom name/body/role/source identity tupleと、policyのID/clearance threshold/exclusion pair・
evidence identity tupleをcanonical fingerprintとして保持する。`expected_pair_ids`はそのinventory
fingerprintから導出したpair集合と順序まで一致しなければならず、factoryとconfiguration evaluatorは
callerのrevision文字列だけを信頼しない。identityは空値やplaceholderの`"unknown"`を許可しない。
`CollisionContext`のconstructor自体も、少なくとも一つの`robot` geometry、bodyごとのdisjointな
role集合、inventory fingerprintから導出したcanonical pair集合を要求する。したがってdirect context
constructionでも、role overlap、unknown role、robot geometry欠落、pairの削除・追加は受理しない。
また、inventory外または非structuralなpolicy fingerprint exclusionも受理しない。
factoryはtyped context、またはcontextを組み立てる明示的なidentity値を要求し、暗黙の`"unknown"`
へfallbackしない。inventory role、body、source identity、policy threshold、exclusion内容が変わった
stale contextは`invalid`として停止する。

`CollisionCheckResult`はpairごとの`CollisionEvaluation`とaggregate statusを返す。same-bodyの
`structural_proximity` pairも`expected_pair_ids`とevaluation coverageから削除されない。explicit
exclusionがないsame-body pairはprovider evidenceが欠けると`unavailable`となり、暗黙のclearへ
fallbackしない。statusは
`clear`、`near_collision`、`collision`、`contact`、`unknown`、`unavailable`、`invalid`である。
constructorは空、duplicate、subset、extraのevaluation coverageを拒否し、aggregate status/reason
は一つのcanonical derivationと完全一致しなければならない。明示structural exclusionも一つの
evaluationとしてexpected pair coverageへ含める。`clear`はexpected inventoryを完全に覆う、
各pairのvalid clear evidenceだけで成立し、unknown・unavailable・invalidや欠落をclearへ変換しない。
constructorとpublicな`.clear` accessはnested evaluation/resultを再導出・再検証し、constructor bypassや
`object.__setattr__`によるkind、status、distance、provenanceの改変をclearとして残さない。
この再検証を補強するため、ownerは`GeometryIdentity`、`GeometryInventory`、`CollisionPair`、
`CollisionExclusion`、`CollisionPolicy`、`CollisionObservation`、`CollisionContext`、
`CollisionEvaluation`、`CollisionCheckResult`、`BoundedCollisionTrajectoryResult`の正規化semantic
snapshotを、nested objectのidentityとともにobject identityへexternal weakref sealとして登録する。
public fieldとprivate fingerprintを一緒に書き換えてもsealは更新されず、同じ値のnested objectへの差し替え、
subclass、`object.__new__`で作った未登録DTOもclear/accessorを通過しない。constructorとpublic validator、
inventory/policy accessor、aggregate/trajectory accessorは同じdeep validatorを通る。これは新しいphysical
authorityを生成する仕組みではなく、constructor後のbypassを検出するowner-local integrity boundaryである。
malformedなcontextは既存sealから復元できる場合だけtyped `invalid`へ閉じ、復元も明示identityもできない場合は
`CollisionContractViolation`で停止する。空inventoryもclearへ推測せず、identity不足としてfail-closedに停止する。
aggregateはinvalid、collision、near-collision、contact、unavailable、unknownの順でfail-closedに
優先する。

invalid、stale、inventory / policy binding mismatch、unexpected observationなどの内部fail-closed
経路は、`expected_pair_ids`の全pairに`INVALID` evaluationを構成し、aggregateのcanonical derivationと
一致させる。すべてのpairがstructural exclusionとして宣言されていても、invalid経路でsyntheticな
`CLEAR` evaluationを混在させない。一方、正常なcomplete evaluationでは、宣言済みexclusionを
`CLEAR + explicit_structural_exclusion`として保持し、valid-pathのexclusion provenanceを消去しない。

`BoundedCollisionTrajectoryResult`は空でない`sample_results`、それと同じ順序・長さのfrozenな
`sample_indices`（factoryでは`(0, ..., n - 1)`）を保持する。全sampleは同一のCollisionContext
bindingを共有し、trajectoryは最初のnon-clear sampleで停止する。aggregate statusと
`failed_sample_index`はそのfirst non-clearから導出し、non-clear列にsynthetic `clear`を許可しない。

MuJoCo inventory / contact projectionはadapter helperとして利用できるが、viewerに第二の
collision判定を追加しない。serial、OSC、robot output、hardware validationはこのcontractの
scope外である。
