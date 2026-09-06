---
status: canonical
owner: runtime
last_verified: 2026-08-28
canonical_for:
  - physical limit evidence
  - versioned physical safety envelope
related:
  - docs/contracts/fast-arm-joint-limit-config.md
  - docs/contracts/robot-profile-runtime-viewer-profile.md
  - docs/architecture/research-execution-roadmap.md
---

# Physical safety envelope契約

## 目的

この契約は、physical outputの前に参照するlimit evidenceを、実機資料・実測・software
projectionのsourceと一緒にtypedで保持する。これは「実機は安全」という一般証明ではなく、
後続のlimit resolution、collision、trajectory、operator gateがbounded envelopeと未証明領域を
区別するための入力契約である。

## Evidence status

各sourceとlimitは次のいずれかを持つ。

| status | 意味 | safety gateでの扱い |
|---|---|---|
| `authoritative` | manufacturer / lab / measured等の明示されたphysical evidence | provenanceが完全な場合だけ候補値として参照 |
| `provisional` | software設定または未確定の暫定値 | physical authorityとは扱わない |
| `unknown` | sourceまたは値を確認できない | allowへfallbackしない |
| `unavailable` | 必要なsourceが現在取得できない | allowへfallbackしない |
| `conflict` | source間で一致しない | resolutionを停止する |
| `invalid` | schema、値、provenanceが不正 | resolutionを停止する |

`authoritative`にはsource kind、source ID、revision、evidence reference、unit、space、frameが
必要である。値がないsourceを、`[-pi, pi]`、zero、現在のnominal設定などで補完しない。

## Source boundary

`fast_arm_core`の`joint_limits.toml`、Robot Profile、MuJoCo `jnt_range`、controller settingは、
現在のsoftware projectionとして記録できるが、physical evidenceそのものではない。これらを
authorityへ自動昇格する処理は持たない。manufacturer document、lab document、または実測値は、
evidence referenceとrevisionが揃い、callerが明示的にphysical authorityとして提示した場合だけ
`authoritative`となる。

## Value shape and provenance

`PhysicalLimit`はbuilt-in `str`型のconcreteなname（`joint` / `motor` / `actuator` identity）、quantity（`position` /
`velocity` / `acceleration`）、lower / upper、unit、space（`joint` / `motor` / `actuator`）、frame、
status、source provenance、conversion provenanceを保持する。`unknown` / `unavailable`は値を`None`
としてreasonを保持し、placeholderのnameで代用しない。conflict / invalidを既知のbounded rangeへ
変換しない。同一identity（name、quantity、space）の重複は拒否する。

同一spaceの値にもidentity conversionを記録する。gear、sign、offset等が不明な場合は推測せず、
conversion provenanceに`None`を保持する。space間のdeterministic projectionとmodel parityはP2が
所有する。

## Serialization and ownership

`PhysicalSafetyEnvelope`はschema version、envelope identity、robot / model identity、limit list、
optional source summaryを持つ。JSONはsorted key、compact separator、UTF-8 without BOMで決定的に
serializeし、未知field、BOM、非finite値、JSON booleanを含む型違いの数値、欠落provenance、反転rangeをstrictに拒否する。

このcontractのpure validation / serializationはruntime safety packageが所有する。MuJoCo、viewer、
hardware、serial、OSC、network outputはこのcontractの責務ではない。MuJoCoはphysical stateのsource
of truthであり、viewerにlimitまたはcollision判定の第二SoTを追加しない。
