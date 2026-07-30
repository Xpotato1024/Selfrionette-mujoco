# fast_arm Robot Plugin

## 意味とresponsibility

fast_armをSelfrionetteのRobot Bundleとして接続し、Profile、Runtime Plugin、typed provider、
viewer / resource declarationを一つのregistrationへ束ねる。

canonical declaration: [`ROBOT_PLUGIN`](plugin.py)

## composition role

[`adapter/bundle.py`](adapter/bundle.py)がProfileとRuntime PluginからBundleを構成し、
endpoint pose / command、qpos feasibility、initial state、scene roleと
`joint_position_command` execution providerを提供する。

## parameters

concrete Robot Plugin自体に自由形式parameterはない。logical identity、Profile、capability、
resourceのcurrent値は[`plugin.py`](plugin.py)とadapter declarationを正とする。

## lifecycleとside effect

import / discoveryはhardwareへ接続しない。runtime assembly後にpackage resourceからMuJoCo modelを
loadし、simulatorを構築する。serial、OSC、robot hardwareはopenしない。

## compatibilityとcomposition

Profile、Runtime Plugin、Bundle、registration identityとmodel / joint / resource contractを
fail-closedで照合する。viewer declarationはrendering resourceを宣言するだけで、physical state、
FK / IK、safety decisionを所有しない。

## command semantics route

Bundleはtyped `joint_position_command` execution providerを持つ。Mapping由来のendpoint intentは
runtimeのmotion / safety boundaryでjoint positionへ解決され、native endpoint commandとして
backendへ直接渡されない。

## resource contract

physical model / joint-limit definitionを独立`fast_arm_core`が所有し、
`adapter/`がSelfrionette contract、MuJoCo / viewer resource bindingへ投影する。
これはself-containedな巨大packageでもgeneric third-party installerでもない。

## constraintsとnon-goals

- constraint: model、joint order、endpoint site、resource manifestをregistration時とstartup時に検証する
- non-goal: generic runtime、viewer、Input Source / Mappingの責務をrobot packageへ吸収しない

## tests / validation

- [Robot Runtime conformance](../../../../../docs/operations/robot-runtime-plugin-conformance-tests.md)
- [endpoint motion sanity](../../../../../docs/operations/r7-e-p1-fast-arm-endpoint-motion-sanity.md)

## canonical architecture / contract

- [Robot Profile / Runtime / Viewer contract](../../../../../docs/contracts/robot-profile-runtime-viewer-profile.md)
- [asset contract](../../../../../docs/contracts/assets.md)
