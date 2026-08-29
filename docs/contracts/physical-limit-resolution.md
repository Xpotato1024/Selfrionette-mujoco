---
status: canonical
owner: runtime
last_verified: 2026-08-28
canonical_for:
  - physical limit resolution
  - fast_arm joint motor actuator parity
related:
  - docs/contracts/physical-safety-envelope.md
  - docs/contracts/fast-arm-joint-limit-config.md
  - docs/contracts/robot-profile-runtime-viewer-profile.md
---

# Physical limit resolution契約

## 目的とowner

P1の`PhysicalLimit`を入力として、motor / actuator spaceのrangeを明示したconversion
relationでjoint spaceへ投影し、Robot Profile、joint-limit TOML、MuJoCo `jnt_range`の
software projectionをmachine-readableに照合する。pureなresolutionとread-only providerは
`runtime/safety/limit_resolution.py`が所有し、fast_armの既存TOML parse / qpos guardやMuJoCo
stateを再実装しない。

## Conversion

`JointSpaceConversion`はsource space、joint name、source name、gear ratio、sign、offset、
relation ID、unitを必須とする。projectionは次の一式に限定する。

```text
joint = sign * source / gear_ratio + offset
```

gear ratioはnon-zero、signは`-1`または`1`、すべての数値はfiniteでなければならない。
負のsignではlower / upperを並べ替え、conversion provenanceとrelation IDを結果へ保持する。
`source_name`は入力`PhysicalLimit.name`と、`joint_name`は期待するcanonical joint identityと
必ず一致しなければならない。source identityまたはtarget identityの重複・曖昧なfallbackは拒否する。
limitとrelationの`unit`は完全一致を必須とし、暗黙のdegree / radianなどのunit変換は行わない。
明示的なunit変換relationがない不一致は`unknown`へ移行し、zero、TOML値、identity relationを
暗黙適用しない。
normalizedなjoint boundの単位は`rad`だけである。同じnon-rad unitのsourceが1つだけ、または
複数一致していても`unknown`として扱い、mixed unitは`mismatch`とする。resolverはnon-radの
値を`rad`へ暗黙変換しない。

## Parity and resolution

同一jointのsourceを比較し、次のstatusを返す。

| status | 意味 |
|---|---|
| `resolved_authoritative` | explicit physical authorityと他sourceのrangeが一致 |
| `resolved_provisional` | bounded sourceは一致するがphysical authorityではない |
| `mismatch` | source rangeが不一致、またはconflict |
| `unknown` | mapping / source / bounded valueが不明 |
| `unavailable` | 必要なsourceを取得できない |
| `invalid` | schema、値、conversionが不正 |

unresolved statusではlower / upperを`None`とする。sourceのstatusに
`unknown`、`unavailable`、`conflict`、`invalid`が含まれる場合は、別sourceの値だけで
authoritative resolutionを成立させない。全sourceがsoftware-onlyでも、同じrangeなら
`resolved_provisional`に留める。

`LimitParityRecord`はjoint、source identity（unitを含む）、status、range、unit、reasonを保持する。
同一jointのbounded sourceはunitも一致しなければ`mismatch`となる。
`resolved_authoritative` / `resolved_provisional`の`lower_rad` / `upper_rad`は両方存在し、
parityの全unitが`rad`で、reasonを持たない場合だけ成立する。unresolved statusは両boundを
`None`とし、reasonを必須とする。
`ResolvedJointBound`と`LimitResolutionResult`はtuple / frozen dataclassのread-only valueで、
callerがProfile、TOML、MJCF、model stateを書き換える機能を持たない。

## fast_arm projection

既存`fast_arm_core/resources/config/joint_limits.toml`は`joint_limit_toml`という
`provisional` sourceとして投影する。Robot Profileの明示boundもprovisionalとして扱う。
MuJoCoの`jnt_range`はlimited jointだけを読み、unlimited joint、missing model、inspection
failureは`unknown`とする。現在のfast_arm modelはjoint rangeをphysical authorityとして提供
しないため、既存TOMLの`[-pi, pi]`へ自動統合しない。

## Boundary

この契約はjoint / motor / actuator parityと後続gate向けのnormalized read-only boundsを
扱う。self-collision、environment clearance、velocity / acceleration、singularity、physical
actuation、serial、OSC、viewer側判定はP3以降または専用Issueのownerであり、ここでは実装しない。
