---
status: canonical
owner: runtime
last_verified: 2026-08-28
canonical_for:
  - R7-H contact task / object manifest
  - contact scene contract
related:
  - docs/contracts/experiment-plugin-composition.md
  - docs/architecture/research-execution-roadmap.md
  - https://github.com/Xpotato1024/Selfrionette-mujoco/issues/411
---

# R7-H contact task / object manifest

`selfrionette.runtime.contact.manifest` は、接触taskを再現するための
versioned manifestとscene contractのcanonical ownerである。manifestのencode、decode、digestは
pureであり、MuJoCo model load、scene spawn、physics step、viewer描画、hardware outputを開始しない。

## identityと構成

`ContactTaskManifest`は次のidentityを必須入力とする。

- Robot Bundle、Environment、Task、Evaluation Plugin群の`PluginSelection`
- manifest schema / contract version
- software revision identity
- scene identity
- object、reset、target、MuJoCo setting、presentation identity

Task / Evaluatorはfast_armのjoint名、geom名、site名、solver classを参照しない。互換性とsemantic
roleはversioned identity、`SemanticRoleRequirement`、required capabilityで表し、unknown、version
mismatch、missing capability、role mismatchを後段のdefaultやzeroで補わない。

## objectとreset

`ContactCubeObject`は`box` shapeのpose（MuJoCo world frame、m、`wxyz`）、size（m）、mass（kg）、
material / RGBA、3成分friction、body / geom name、enable conditionを保持する。sizeとmassは正、
sliding frictionは正、その他frictionは非負でなければならない。非有限値、未定義shape、空identityは拒否する。

`ContactResetState`はrobot qpos / qvel、actuator、object pose、simulation time、warm-start stateを
保持する。qpos / qvelのdimensionは一致し、reset simulation timeは`0`に固定する。#412はこの値を
MuJoCo dataへ適用し、contact、velocity、actuator、simulation time、warm-startのtrial間leakageを防ぐ。

## targetとMuJoCo設定

`ContactTarget`はtarget face、object-frame normal、world-frame approach direction、penetration band
（m）を保持する。normalとdirectionはunit vector、bandは非負で下限以下に上限を置く。

`MuJoCoSettingsIdentity`はtimestep、integrator、solver、iterations、line-search / noslip iterationsを
固定する。presentation identity（camera / visual feedback）はphysical scene identityと別に保持し、
viewerへ判定責務を移さない。

## canonical serialization

`encode_contact_manifest()`はUTF-8、`ensure_ascii=False`、`allow_nan=False`、sorted keys、compact
separatorsでcanonical bytesを生成する。`decode_contact_manifest()`はrootとnested objectのunknown /
missing / duplicate field、malformed JSON、non-finite JSON constant、型不一致をfail-closedで拒否する。
同一semantic contentは入力mappingの挿入順に依存せず同一bytesになり、`contact_manifest_digest()`は
canonical bytesの`sha256:<64 lowercase hex>`を返す。

このmanifestはsoftware-only readinessの入力であり、serialization成功だけではscene readiness、contact
measurement、task outcome、experiment evidence、hardware safetyを意味しない。
