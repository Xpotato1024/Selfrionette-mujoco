---
status: canonical
owner: evaluation
last_verified: 2026-08-20
canonical_for:
  - world/tool control-frame comparison design
related:
  - docs/contracts/continuous-endpoint-velocity-input.md
  - docs/contracts/endpoint-metadata-vocabulary.md
  - docs/archive/drafts/r7-e-followup-p12-control-frame-resolution-metadata.md
  - docs/reports/implementation/r7-e-p9-jacobian-mobility-diagnostics.md
  - docs/archive/drafts/r7-e-p10-measured-axis-progress-semantics.md
  - docs/contracts/evaluation-manifest-readiness.md
---

# world/tool control-frame比較design

## 目的と研究質問

この文書は最小の再現可能な評価とversioned logging contractを定義する。
runtime、input mapping、logging schema、experiment runner、statistical implementationのownershipは持たず、
current implementation boundaryを参照する。

本designはlimited exploratory pilot designである。研究質問は次のとおりである。

> 事前検証済みの単一reset poseと、選択したworld-axis / initial-tool-axis target familyにおいて、
> `world` controlと`tool` controlのmeasured task performanceにどのような差が観測されるか。

control-frame x task-family patternはdescriptiveかつexploratoryに扱う。各task familyは単一tool orientationで異なる
physical directionを使うため、task familyはphysical direction、Jacobian mobility、workspace geometryと交絡する。
このpilotからcausal frame-task alignment effectを特定できない。いずれのframeも普遍的に優れているとは仮定・主張しない。

pilotではfeasibility、event rate、metric stability、target selectionを確認する。confirmatory comparisonには、同じphysical
directionを複数tool orientationとcrossし、task alignmentをdirectionおよびpose-dependent mobilityから分離する後続design
revisionが必要である。

本研究は、共通定義の下でoperator intent、resolved motion、policy prediction、measured motion、task performance、system
limitation、subjective workloadを記録する共通基盤が、input deviceとmapping methodの比較に必要だという立場を支える。

## truth hierarchy

次のevidence classを区別する。

1. **requested**: `requested_control_frame`と`requested_endpoint_velocity`を含むoperator intent
2. **resolved**: `resolved_control_frame`と`resolved_world_endpoint_velocity_m_s`を含むruntime frame resolution
3. **predicted**: `endpoint_delta_achieved_m`とcandidate qposを含むmotion-policy result
4. **measured**: `actual_tip_delta_m`とmeasured tip poseを含むMuJoCo `tip` siteのworld-frame outcome
5. **status**: accepted/scaled/held policy state、rejected command/application、stale input、unavailable evidence

performance conclusionにはmeasured MuJoCo outcomeを使う。requested、resolved、predicted valueはdiagnostic evidenceであり、
actual movementの代替にしない。`current_tip_position_m`はprovenance-dependent compatibility anchorであり、自動的に
measured fieldとはならない。

## 最小task set

predeclared target setは、単一のvalidated initial qposとtool orientationから開始する4つのfree-space point-acquisition
targetで構成する。

- **world-aligned family**: 選択した1本のMuJoCo world axisの正負方向へ同距離のtargetを置く
- **tool-aligned family**: initial tool orientationの選択軸の正負方向へ同距離のtargetを置き、trial初期化時に1回だけ
  MuJoCo world coordinateへtransformする

選択するworld axisとtool axisはinitial poseでnon-collinearかつ、後述のreadiness checkを通過しなければならない。
pilot target manifestにはexact initial qpos、initial tip pose、initial tool orientation、axis vector、distance、target
coordinate、tolerance、timeoutを記録する。axisはvalidated workspaceから選び、data collection開始後にいずれかの
conditionを有利にする変更を行わない。

各trialは同じreset qposとtool orientationから開始する。targetはtrial全体を通してMuJoCo world coordinate上で固定し、
trial開始後のtool rotationには追従しない。successはmeasured MuJoCo `tip` siteがtimeout前にtarget tolerance内へ入り、
predeclared dwell intervalの間そこへ留まることとする。hold、rejection、stale input、unavailable measurementはsuccessではない。

control conditionは`requested_control_frame=world`と`requested_control_frame=tool`である。各conditionのControl Mapping Pluginは
explicitなversioned comparison family identityとmapping semantics identityを持ち、family identityだけを一致させた
unrelated strategyの組合せは許可しない。両conditionは同じinput
source、physicalまたはnormalized input range、speed/gain、deadzone、maximum per-step delta、update cadence、target
distance/tolerance/timeout、initial condition、visual feedback、camera、safety ruleを使う。変更するのはrequested
control frameだけである。

contact、grasping、collision task、device comparison、task definition中のtool orientation変更は本designのscope外である。

## 記録するrepetitionとretry

participantごと、control-frame conditionごとに、4 targetすべてへ同数のrecorded repetitionを割り当てる。本pilot designでは
repetition countを決めない。data collection前のprotocol revisionで宣言するか、versioned pilot manifestでconfiguration
として固定する。同じcountを両conditionへ適用する。practice trialはrecorded repetitionに数えない。

recorded repetition orderはbalanceするか、両conditionで同じ規則を使うrecorded deterministic seedから生成する。
outcome dataを見る前にpilot stopping rule、manifest-freeze condition、recorded repetition countを固定する。
participant countとeffect sizeは本pilot designでは指定しない。

operator-caused timeout、hold、rejection、stale inputはfailed recorded trialとして保持し、retryしない。predeclared
technical-invalid ruleを満たすtrialだけを、predeclared per-repetition limitまでretryできる。original invalid recordは
datasetに残し、retryには新しいtrial identifierを付けてoriginalへlinkする。retry limitを使い切った場合、そのrepetitionは
attemptを暗黙に追加せずtechnically invalidのままにする。

## outcome

単一primary outcomeはbinary measured task resultである**success within timeout**とする。failed trialへ架空のcompletion
timeを与えず、unavailable measurementを明示できる。

単一objective secondary outcomeは**off-axis drift**とする。initial measured tip positionとtargetを結ぶ直線から、
measured `tip` trajectoryが離れたperpendicular distanceの最大値をmeterで報告する。requested、resolved、predicted
motionから計算しない。

completion timeとfinal measured endpoint errorはdescriptionとdiagnostic review用にlogするが、追加primary
outcomeではない。結果を見た後に新しいpreregistered design revisionなしでprimaryへ昇格しない。

## subjective evidence

各condition blockの後で、同じscaleとwordingを使ってworkload、ease of control、predictabilityを収集する。frame
preferenceは両condition完了後だけ収集する。responseをsession、participant、block identifierへlinkする。

workload instrumentとしてNASA-TLXを使ってよいが、subjective evidenceはsupplementaryである。measured task outcomeの
代替、universal frame superiorityの証明、sole conclusion basisにはできない。

## study sequenceとbalancing

比較はwithin-subjectで行う。participantにはequivalent instructionと、各frameで同数のpractice trialを与える。
practiceは同じtask familyを使うがpracticeとしてmarkし、primary analysisから除外する。

participantを可能な限り均等に`world-first`と`tool-first`へ割り当てる。各condition内ではstarting task familyをbalanceし、
positive/negative target directionをalternateまたはcounterbalanceする。両conditionで同じorder schedule ruleを使う。
outcome後にimbalanceを補正せず、assigned scheduleを記録する。

participantごとのsequenceは、standardized briefing、first-condition practice、first-condition recorded block、rest、
second-condition practice、second-condition recorded block、preferenceの順とする。predeclared rest ruleと同じmaximum
block durationでfatigueを制限する。

## confoundの扱い

| Confound | Treatment |
|---|---|
| learningとcondition order | equivalent practiceとworld-first/tool-first balancingで制御し、orderをlogしてanalysisに含める |
| taskとdirection order | balanced scheduleで制御し、exact orderをlogする |
| fatigue | 同じrest / block-duration ruleで制御し、block/orderをanalysisに含める |
| initial qposとtool orientation | trial前に同じvalidated valueへresetし、achieved valueをlogする。failed resetはreason付きで除外する |
| target directionとdistance | 4-target manifestで固定・記録するが、このpilotではtask familyから分離しない。この交絡が解釈を制限する |
| workspaceとmobility limitation | limited-pilot workspace gateで除外し、mobility evidenceとselected axisをconfiguration identityとしてlogする |
| stale input、hold、rejection、unavailable measurement | status/reasonとしてlogする。predeclared technical-invalid ruleに該当しない限りprimary outcome failureとして残す |
| cameraとvisual feedback | 同じcamera pose、overlay、target appearance、feedback latency/settingsで制御し、configuration identityをlogする |

## readiness gate

R7-G-P1 / #405は、data collection前にmanifestのschema、canonical bytes、requested / resolved
identity、plugin capability / role / evidence、neutral initial-state、world/tool shared invariantsを
software-onlyで検証するpre-run gateを追加する。このgateは`compose_experiment()`を呼ぶが、model load、
physics step、fixture playback、measured reachability、task outcome、metric妥当性を実行・証明しない。
manifestのsoftware revisionはactual startup `SoftwareExecutionIdentity`とexact matchし、Robot Bundleの
versioned canonical initial-state contract（identity、keyframe、qpos、tip、orientation、frame、unit、quaternion order）とも
一致しなければならない。
したがって#405の`READY`は「runnerへ渡せる静的configuration identityがfreezeされた」ことだけを意味し、
下記のmeasured MuJoCo reachability / progress条件の成立を意味しない。

## current software-only runner

#406のcurrent runnerは`build_r7_g_free_space_manifest_pair()`からproduction pair readinessを構築し、
world/toolの各conditionを同じinput、gain、deadzone、cadence、target、initial state、tolerance、dwell、timeoutで
有限実行する。差分はmanifestで許可されたrequested / condition-specific control frameだけである。

trial開始時はselected Environmentを明示resetし、selected Robot / MuJoCoをcanonical keyframeへresetする。
reset後のactual qposとmeasured tool orientationがfrozen manifestに一致しない場合はTask開始前にfail closedとする。
一致後にMuJoCoの`endpoint_pose/v1` providerから取得したmeasured endpointをelapsed `0.0`でTaskへ渡す。
manifest initial tipはreadiness referenceであり、measurementとして挿入しない。各step後もMuJoCo measurementと
runtime motion status/reasonをTaskへ渡し、TaskTransitionのterminal classification / evidenceを利用する。

manifestへ固定するsoftware revisionとstartup側が独立に取得するactual `SoftwareExecutionIdentity`は別入力とし、
exact matchしない実行はreadinessで拒否する。

simulation timeはmanifest cadenceで進み、`ceil(timeout / cadence)`をstep上限とする。wall-clock sleep、daemon、
viewer、hardwareを実行条件にしない。

#407のcurrent integrationは、同じexecution loopからowner-generated input / resolution / policy / MuJoCo
before-after / Task terminal factsをimmutable traceとして受け、既存`experiment-motion-log/v1`へprojectionする。
configuration identityはconditionごとの`FreezeRecord.identity`へbindし、trial protocol identityはcallerが
明示する。complete streamはstrict round-trip validationとsame-directory atomic write / read-backを通過した場合だけ
保存する。#408のmetric / evaluation artifactと#409のfull E2E / completion auditは実行しない。

次のcheckがすべてpassするまでdata collectionを開始しない。

1. experiment log contractが後述のlogging contractを満たすversioned schemaを実装・検証している。
2. requested、resolved、predicted、measured fieldをstatus/reason provenance付きで個別識別できる。
3. frozen manifestの全targetが両control conditionでreset poseからreachableであることを、measured MuJoCo `tip`
   outcomeで確認している。
4. initial/final tip poseとper-sample measured tip motionを利用でき、欠落をzeroではなくexplicit unavailable evidenceにする。
5. world/tool conditionが`requested_control_frame`以外で同一のinput / motion settingを使うことを実証している。
6. selected axisが既知のweak world-X/default-pose mobilityおよびnatural-motion limitationを
   避け、mobility diagnosticとmeasured pilotで両方向のadequate progressを確認している。

本designはuniversal workspace completionを必須にせず、**affected workspace外のlimited exploratory pilot**を採用する。local mobility / natural-motion limitationであり、本designはbounded descriptive questionを扱う。avoidanceが有効
なのは、frozen 4 targetすべてが同じmeasured reachability/progress checkをpassする場合だけである。non-collinearなmatched
axisが一組もpassしなければ、known workspace limitationが解決するまでstudyをblockする。collection中にtargetを暗黙に弱めたり置換したりしない。

## logging contract

experiment log contractはwire/schema representation、versioning、unit、nullability、validationを定義する。少なくとも一つのrecoverable
experiment record streamが次を提供しなければならない。

- model、target-manifest、input/motion setting、camera/feedback setting、schema versionを含むsoftware revisionと
  configuration identity
- session、participant、block、trial、task-family、target、practice/recorded identifier
- original technically invalid trialとbounded retryを保持する`repetition_index`、`attempt_index`、nullable
  `retry_of_trial_id`
- `requested_control_frame`、assigned condition order、task order、target direction
- initial qpos、initial measured tip pose / tool orientation、target world position、tolerance、dwell interval、timeout
- existing `requested_endpoint_velocity`とsource timing/lifecycle evidenceを含むoperator-requested motion
- `resolved_control_frame`、`control_frame_resolution_status`、`resolved_world_endpoint_velocity_m_s`を含むresolved motion
- `endpoint_delta_requested_m`、`endpoint_delta_achieved_m`、candidate qposを含むpolicy-requested / predicted motion。
  これらをmeasuredと呼ばない
- `actual_tip_delta_m`を含む時系列measured MuJoCo `tip` pose/delta、およびqpos before/after
- machine-readable reason付きの`motion_status`、endpoint progress status、application rejection、hold、stale、
  measurement-unavailable state
- trial start/end timing、completion status、success-within-timeout、final measured endpoint error、off-axis drift導出に
  必要なsample
- workload、ease、predictability、preference responseとsession/participant/blockのlink

既存canonical field nameを優先し、experiment recordへ合わせるためだけのsynonymを作らない。既存canonical nameがない場合、
experiment log contractはnew fieldのowner、frame、unit、lifecycle、unavailable-value policyを記録する。missing、held、rejected、stale、
unavailable valueをsuccessful zero motionとしてencodeしない。

## analysis policy

control-frame x task-family patternをwithin-subject exploratory analysisで扱う。effect sizeとuncertaintyを報告するが、
causal frame-task alignment effectとして解釈せず、main effectからuniversal superiorityを推論しない。本designではphysical
direction、Jacobian mobility、workspace geometryをtask familyから分離できない。本designはparticipant countとeffect sizeを
指定しない。pilot dataはfeasibility、event rate、metric stability、variance、target suitability、後続power analysisへの
inputを推定するものであり、confirmatory evidenceではない。

recorded dataを見る前にtechnical-invalid rule、retry limit、stopping rule、manifest-freeze condition、missing-data handlingを
宣言する。practice trialは常に除外する。reset failure、corrupted identifier/order、required measured truth欠落はlogged reasonと
retry linkageを保持してtechnically invalidとして除外できる。operator-caused timeout、hold、rejection、stale inputはretryなしの
primary-outcome failureとして残す。control frame / task family別にすべてのexclusion、retry、missingnessを報告する。
missing measured motionをrequested、resolved、predicted、zero motionで置換しない。

## scope境界

このdesign document自体はruntime ownerではない。current #406 / #407 implementationはsoftware-only experiment
runnerと既存v1へのrecording boundaryを追加したが、input mapping、logging schema、statistical code、viewer behavior、
MuJoCo model、dependency、CI、hardware、serial、Arduino、OSC、robot outputは変更しない。
