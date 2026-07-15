---
status: canonical
owner: architecture
last_verified: 2026-07-15
canonical_for:
  - Robot Profile contract and registry
  - Robot Runtime Plugin contract and registry
  - Viewer Robot Profile contract and registry
related:
  - docs/architecture/runtime-composition.md
  - docs/contracts/transport-payload.md
  - docs/contracts/fast-arm-joint-limit-config.md
---

# Robot Profile / Runtime Plugin / Viewer Profile契約

## Ownershipの分離

`RobotProfile`はimmutableかつversionedなdeclarationである。robot identity、
MuJoCo asset reference、canonical joint order、qpos/qvel dimension、initial keyframe、
endpoint reference、joint-limit configuration reference、coordinate/unit contract、
viewer-profile reference、capabilityを所有する。executable factory、module name、
class name、import pathは含まない。

`RobotRuntimePlugin`はruntime compositionだけが使用するtyped behavioral boundaryである。
pluginは選択したmodelをvalidateし、既存のrobot-specific IK、FK、motion policy、
qpos feasibility guard、endpoint accessorを構築する。fast_arm pluginは既存algorithmと
P23 TOML guardを再利用し、複製しない。

`ViewerRobotProfile`はbrowser-side rendering declarationである。model URL、
named startup keyframe、debug fixture URL、VFS asset、visual style、joint order、
qpos dimension、model compatibility versionを所有する。IK、FK、planning、
qpos generation、target generation、安全性は一切所有しない。現在のrendererは
MuJoCo compiled mesh geometryを消費し、独立したmesh-fallback routeを持たない。
したがってP24ではOption Bを選択し、未使用のfallback mappingを宣言しない。
profile-owned VFS asset mappingをmodel-loading boundaryとして維持する。
将来fallback routeを追加するには、別Issue、明示的なdiagnostic、cleanup behavior、
profile-driven testが必要である。

architecture test向けのcontract sentinelとして、ここでは`selects Option B`を固定し、
`does not declare an unused fallback mapping`を保証する。

## Registry解決

```text
RuntimeConfig.robot_profile_id
  -> Robot Profile registry
  -> Robot Runtime Plugin registry
  -> registry-set and profile/plugin consistency validation
  -> model load with explicit keyframe
  -> profile/model/joint/dimension validation
  -> IK/FK/motion/guard composition

viewer robotProfileId
  -> Viewer Robot Profile registry
  -> asset/style/model composition
  -> payload metadata compatibility check
  -> qpos render only when compatible
```

PythonとTypeScriptのregistryはdeterministicなknown-ID mappingである。
duplicate registrationとunknown IDは明示的にfailし、registered IDはdiscoverableである。
configuration stringをarbitrary dynamic importへ渡してはならない。robot追加には、
declarativeなRobot Profileが一つ必要である。runtime behaviorをsupportする場合は
runtime plugin registrationが一つ、browser renderingをsupportする場合は
viewer profile registrationが一つ必要である。

すべてのproduction Robot Profile / Robot Runtime Plugin pairには、`tests/`配下に
明示的なtest-only conformance caseも必要である。このcaseはproduction registry entry、
runtime composition dependency、public APIではない。

`resolve_robot_runtime()`は共通production boundaryである。一方のregistryだけにあるID、
requested/registered/plugin identity mismatch、profile/model contract version mismatch、
異なるdeclarative contract、canonical registered profile objectにbindされていないpluginを
rejectする。object identityに加えてsemantic comparisonも必須である。

## Productionとgenericの選択

production fast_arm entry pointは`RuntimeConfig(robot_profile_id="fast_arm")`を
明示的に構築するか、callerにそのIDの指定を要求する。解決済みprofile/plugin pairを通して、
model、`home` keyframe、endpoint reference、現在のIK/FK behavior、motion policy、
P23 qpos guardを解決する。IDのないproduction config、unknown ID、incompatible modelを
与えた場合はstartupをfailする。

`RuntimePipeline`、`build_mujoco_pipeline()`、`build_replay_mujoco_pipeline()`は
genericのままとする。model pathまたはjoint nameからprofileを推論せず、profileがない場合に
fast_armを選択せず、明示的なmodel pathを要求する。callerはgeneric keyframe、guard、
state metadataをinjectしてよい。したがって最小のnon-fast_arm MJCFは、fast_arm validationや
configurationなしでloadとstepができる。

generic profile contractではjoint countを`nq`または`nv`と同一視しない。ball jointと
free jointは、joint nameが一つでもqpos/qvel dimensionが正当に`4/3`、`7/6`となる。
fast_arm pluginはstartup validationで、四つのcanonical joint、`nq=4`、`nv=4`、
exact joint orderを別途enforceする。

## fast_armのjoint、frame、startup契約

fast_armのcanonical joint orderとqpos indexは次のとおりである。

| qpos index | joint name |
|---:|---|
| 0 | `sholder_joint_1` |
| 1 | `sholder_joint_2` |
| 2 | `sholder_joint_3` |
| 3 | `elbow_joint` |

joint orderのsource of truthは`assets/mujoco/fast_arm/arm.xml`とresolved
`RobotProfile`である。runtimeはjoint nameを推論または並べ替えない。
`sholder_joint_2`のMuJoCo `ref=-90`に対するsolver adapterは、
`mujoco_qpos1 = solver_q1 - pi/2`、`solver_q1 = mujoco_qpos1 + pi/2`を維持する。
legacyのdifferential shoulder mappingをproduction qpos mappingとして暗黙適用しない。

solver local frameは`base_link`をrootとする。physical endpointのsource of truthは
MuJoCo world / scene frameの`tip` siteであり、viewer表示またはsolver-local FKではない。
world commandからsolver-local targetへの変換はrobot-specific runtime/plugin boundaryが所有する。

fast_armのactive initial qpos sourceは、`assets/mujoco/fast_arm/arm.xml`のnamed
`home` keyframeだけである。selected `home` qposは
`(0, -0.5235987755982989, 0, -1.0471975511965976)`、すなわち
`(0, -pi/6, 0, -pi/3)`である。Python loader/resetとbrowser WASMのpre-payload
startupは同じXML keyframeを読み、runtime first state/payloadも同じqposを運ぶ。
`ViewerInputSource`とinitial target markerは、そのposeのMuJoCo
`tip = (0.240000, -0.245951, 0.284308) m`へrebaseする。

collision geomがdisabledでcollision checkを利用できない状態では、このstartup poseを
collision-freeの物理証拠とは扱わない。joint range内であること、startup continuity、
first-input continuityと、physical collision feasibilityは別のacceptance boundaryである。

## Backend/viewer整合性とpayload v0

Runtimeは既存のopen payload-v0 `metadata` mapへ`robot_profile_id`、
`model_contract_version`、`robot_joint_names`、`robot_qpos_dimension`を追加する。
envelopeとpayload versionは変更しない。viewerはrenderer construction前にprofileを解決し、
qpos適用前にloaded modelのdimension/joint orderと四つすべてのbackend compatibility keyを
確認する。profile-aware production viewerでは、`robot_profile_id`、
`model_contract_version`、`robot_joint_names`、`robot_qpos_dimension`が
解決済みViewer Robot Profileと完全一致しなければならない。compatibility metadataが
missing、unknown、malformed、mismatchedの場合は明示的なinvalid diagnosticを生成し、
qposを適用しない。このviewerではprofile-free legacy payloadまたはgeneric payloadから
暗黙にfast_armへfallbackしない。このadditive metadata boundaryは、rendererにtransport
policyを所有させることなく、将来session manifestまたはhello messageへ移せる。

四つのcompatibility keyはreservedかつauthoritativeである。production compositionでは
general state metadataと分離し、state、replay frame、input intent、motion command、
input-source metadataの後に最後に適用する（overwrite-protection Option A）。したがって
spoofed valueは、qpos-rejection pathを含めて解決済みprofile valueに置換される。
authoritative profile metadataを持たないgeneric pipelineはこれらのkeyを追加せず、通常の
metadata behaviorを維持する。fieldはopen payload-v0 metadata mapへのadditive fieldのままだが、
P24 production compositionではprofile-aware viewer compatibilityのため四つすべてを
authoritativeかつmandatoryとする。

## P23 integrationとcleanup handoff

`QposFeasibilityGuard`と`QposFeasibilityResult.accepted`はgeneric pipelineの
safety boundaryであり続ける。fast_arm pluginはprofile-owned TOML referenceから既存の
`FastArmJointLimitGuard`を構築する。exact-boundary acceptance、whole-candidate hold、
current-qpos preservation、target lifecycle suppression、viewer rebase suppressionは変更しない。

Planar compatibility FK/IK implementationとpublic exportは、generic testをtest-only doubleへ
移し、offline smokeをresolved plugin ownershipへ移した後、#389でretireした。
robot-specific production IK/FK、motion、endpoint、home/seed、feasibility behaviorは、
選択した`RobotRuntimePlugin`を通して解決する。明示的なno-op/stub helperは分離された
negative controlとして残し、production fallbackにはしない。executableな
`experiments/mujoco-wasm-viewer-poc`は、promote済みrendererと有用なfixture assertionを
product viewerで検証した後、#385でretireした。canonical qpos fixtureは現在
`apps/mujoco-viewer/public/fixtures/fast_arm_sweep_x_qpos.json`が所有する。

fixtureはproduct-owned debug/validation assetであり、startupまたはruntime state sourceではない。
PR #392では、current `main`とcleanup branchの両方でstale-velocity
BADQACC/time-rollbackを再現した後、native generation pathを修正した。修正済みexporterは
complete sequenceをvalidateし、invalid output時には既存fileをatomicに保持する。
payload schema、Viewer Profile compatibility boundary、browser rendering-only ownershipは
変更しない。現在のgenerated fixtureはproduct testでvalidateされ、SHA-256は
`4925D77535A67ED0E4EB68BDCC0B66C262D2D11AE5E1F7DCA99C3AE5E38D312A`である。
