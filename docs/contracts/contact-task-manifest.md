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
sliding frictionは正、その他frictionは非負でなければならない。MuJoCoのcontact parameterである
`contype`、`conaffinity`、`condim`もobject physical identityの一部であり、bitmaskは非負整数、
`condim`はMuJoCoが許す`1`、`3`、`4`、`6`のいずれかでなければならない。非有限値、未定義shape、
空identityは拒否する。

`ContactResetState`はrobot qpos / qvel、`ctrl`（MuJoCo `data.ctrl`へ適用するcontrol input）、
`act`（MuJoCo `data.act`へ適用するactivation state）、object pose、simulation time、warm-start stateを
保持する。qpos / qvelのdimensionは一致し、reset simulation timeは`0`に固定する。旧`actuator`入力は
`ctrl`へ正規化されるsource-compatibility aliasであり、canonical documentには出力しない。#412は宣言された`ctrl`と`act`を
別々のownerへ適用し、contact、velocity、actuation、simulation time、warm-startのtrial間leakageを防ぐ。
`ContactSceneContract.initial_penetration_tolerance_m`は初期接触判定の許容値としてmanifestへbindされ、
contact parameterと同じcanonical identityに含まれる。scene側が別の値を暗黙に補ってreadinessを変えてはならない。

R7-H v1 scene identityは`contact_cube_scene/v1`である。`ContactCubeObject.size_m`はMuJoCo `box`
geomの各軸half-extentとして解釈する。#412の
`ContactSceneComposer`はRobot-owned base MJCFへversioned object body、freejoint、geom、materialを
追加し、viewerへ別のcubeを生成しない。disabled sceneではobjectを追加せず、contact task用sceneとして
誤って扱わない。scene load時はmanifestのEnvironment / Robot / viewer identity、MuJoCo settings、
reset vector dimensionを照合し、`mj_forward`後の初期contactまたはpenetrationをfail-closedで拒否する。

## targetとMuJoCo設定

`ContactTarget`はtarget face、object-frame normal、world-frame approach direction、penetration band
（m）を保持する。normalとdirectionはunit vector、bandは非負で下限以下に上限を置く。

`MuJoCoSettingsIdentity`はtimestep、integrator、solver、iterations、line-search / noslip iterationsを
固定する。presentation identity（camera / visual feedback）はphysical scene identityと別に保持し、
viewerへ判定責務を移さない。

## measured contact evidence

`runtime/contact/evidence.py`は、#412でloadした同一のMuJoCo model/dataから
`mjData.contact`を読み、公式`mj_contactForce`で各contactの6D force / torqueを測定する
backend ownerである。viewer、reaction-force filter、clamp、task outcomeはこの測定を再実装しない。
Robot geom identityはcallerがRobot Bundleのcanonical model resourceから名前またはIDで明示する。
generic extractorはmodel内の未分類geomをrobotと推測せず、identityがmissingならfail-closedにする。

各`ContactRecord`は次を保持する。

- `contact_identity`、geom / body IDとname、target-object / self / environment / other-object分類
- MuJoCo world frameのcontact point（m）、normal、9成分contact frame
- signed distance（m）とnon-negative penetration depth（m）
- contact frameのforce（N） / torque（N m）とworld frameへの変換
- target contactに対する`object_on_tool` / `tool_on_object` force、normal / tangential / resultant

MuJoCo contact frameはrow-majorのnormal、tangent1、tangent2を保持し、force frameのx成分を
normal forceとする。`mj_contactForce`のgeom2 forceを基準にし、target pairのgeom1 / geom2順に
応じて符号を反転する。canonical conventionは`object_on_tool`を正方向、逆向きを
`tool_on_object`とし、両方のworld vectorを記録する。multiple target contactはidentity、geom、
point、distance、normal順に安定ソートしてから`math.fsum`で集約し、world-originのwrenchも
同じ順序で合算する。

`ContactRecord`の公開constructorは、contact frameの3行が有限な正規直交基底であり、第一行が
`normal_world`と一致することを検証する。local force / torqueとworld force / torqueの両方がある場合は、
そのframe変換結果が一致しなければならない。target recordでは`object_on_tool`と`tool_on_object`の
反対符号、normal / tangential / resultantの分解も再計算して検証し、未測定・solver invalidのrecordは
force fieldを保持できない。`ContactEvidence`はtarget recordのstatus、count、normal / tangential /
resultant、force、wrenchをaggregateと照合するため、countだけを変更したartifactや不整合なaggregateを
`measured`として受け付けない。

Evidence statusは次を区別する。

- `no_contact`: target-object contactが存在しないvalid measured state。target force aggregateは
  explicitなzeroである。
- `measured`: 1つ以上のtarget-object contactをMuJoCo APIで測定できたstate。
- `measurement_unavailable`: model/dataまたはsolver constraintが利用できず、forceをzeroへ
  置換できないstate。
- `invalid_contact`: geom/body ID、name、frame、distance、normal、model identityなどが不正なstate。
- `solver_invalid`: `mj_contactForce`失敗またはnon-finite force / torqueのstate。

`no_contact`以外のfailure statusはaggregateやsynthetic forceを保持せず、canonical
`EvidenceStatus.UNAVAILABLE`または`INVALID`へ投影される。target-object contactだけがtarget
measurementへ入り、self-contact、environment contact、別objectは分類済みraw recordとして保持する。
evidenceにはscene / object identity、manifest digest、sample time、simulation time、frame indexを
含め、canonical JSON bytesをdeterministicに生成できる。
extractorは正規表現でdigestの形だけを確認せず、必ず`ContactTaskManifest`を受け取り、
`encode_contact_manifest()`から再計算したdigestと一致することを検証する。manifestがない、または
sceneから受け取ったdigestとcanonical bytesが一致しない場合、validなcontact evidenceを生成しない。

## canonical serialization

`encode_contact_manifest()`はUTF-8、`ensure_ascii=False`、`allow_nan=False`、sorted keys、compact
separatorsでcanonical bytesを生成する。`decode_contact_manifest()`はrootとnested objectのunknown /
missing / duplicate field、malformed JSON、non-finite JSON constant、型不一致をfail-closedで拒否する。
identity名、plugin ID、semantic role、frame、unit、object / material / target / MuJoCo / presentationの
文字列はdecoderで別型から文字列へcoerceしない。contact parameterと初期penetration toleranceも
canonical bytesへ含め、decoderで検証する。
同一semantic contentは入力mappingの挿入順に依存せず同一bytesになり、`contact_manifest_digest()`は
canonical bytesの`sha256:<64 lowercase hex>`を返す。

このmanifestはsoftware-only readinessの入力であり、serialization成功だけではscene readiness、contact
measurement、task outcome、experiment evidence、hardware safetyを意味しない。
