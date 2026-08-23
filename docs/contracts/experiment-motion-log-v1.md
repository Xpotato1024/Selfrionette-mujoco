---
status: canonical
owner: evaluation
last_verified: 2026-07-17
canonical_for:
  - experiment motion log v1
related:
  - docs/evaluation/world-tool-frame-comparison-design.md
  - docs/contracts/endpoint-metadata-vocabulary.md
  - docs/contracts/continuous-endpoint-velocity-input.md
  - docs/archive/drafts/r7-e-p10-measured-axis-progress-semantics.md
  - docs/archive/drafts/r7-e-followup-p12-control-frame-resolution-metadata.md
  - docs/reports/implementation/r7-e-followup-p14-runtime-diagnostic-boundary.md
  - docs/contracts/evaluation-manifest-readiness.md
---

# experiment motion log v1契約

## scopeとownership

これはpilot design limited world/tool pilot用の、独立して再構築可能なrecord-streamの
canonical contractである。現在のversion discriminantは
`experiment-motion-log/v1`である。evaluation artifact schemaであり、payload-v0や
別のtransport payloadではない。schema moduleはpureなrecord、serialization、validationだけを所有し、
runner、participant workflow、questionnaire、analysis、dashboard、viewer、hardware、filesystem lifecycleを
追加しない。current runtime recorderはこのcontractを利用するconsumerであり、schema moduleの責務ではない。

全recordは`schema_version`、`record_kind`、`experiment_id`、`session_id`、
`participant_id`、`configuration_id`を持つ。trial recordはさらに`trial_id`を持つ。
participant identityはpseudonymousであり、このcontractはdirect participant
identifierを保存しない。

## record modelとlifecycle

streamは次の4種類のimmutable typed recordを含む。

1. `configuration`はsoftware revision、initial state、targetとtiming、input source、
   speed/deadzone/max-delta、comparison-critical parameterをfreezeする。
2. `trial_start`はprotocol identityとorderingをfreezeする。対象はblock、task family、
   targetとdirection、practice/recorded flag、condition、task/direction order、
   `repetition_index`、`attempt_index`、nullableな`retry_of_trial_id`である。
3. `motion_sample`はrequested/resolved/predicted/measuredというtruth levelを
   collapseせず、1 stepを記録する。
4. `trial_outcome`はちょうど1つのtrialをcloseし、primary outcome、
   completion/failure classification、optional subjective-response linkを記録する。

必須stream orderは、参照前のconfiguration、sample前のtrial start、zeroから連続する
sample index、最後に1つのoutcomeである。trial内のruntime timestampはfiniteかつ
non-decreasingである。configuration IDとtrial IDはuniqueであり、全trialをcloseしなければ
ならない。

retryはnew trialとして保持する。attempt zeroにはretry linkがない。後続attemptは、
完了済みの以前のtechnical-invalid trialへlinkし、`attempt_index`をちょうど1増やす。
experiment、session、participant、configuration、block、task family、target、
practice status、condition/order、task/direction order、target direction、
`repetition_index`はoriginalと完全に一致しなければならない。異なるのはtrial ID、
retry link、attempt index、timestampだけである。

## field、unit、frame、nullability

全timestampはproducer clock domainにおけるsecondである。source timestampとruntime
timestampは分離したままにする。position/delta/tolerance valueはmetre、velocityは
metre/second、qposはradian、orientationはWXYZ quaternion、ordering/index valueは
zero-based non-negative integerである。

configuration fieldはexperiment manifestが所有する。pre-runのcanonical sourceは
`evaluation-manifest/v1`であり、#405の`EvaluationManifest`がbytes、requested identity、resolved
readiness、freeze identityを確定する。この文書はそのmanifestを参照するrecord schemaであり、#405は
log recordの生成、stream lifecycle、trial close、outcome計算を実装しない。

current runtime projectionは`ConfigurationRecord.configuration_id`へ
`EvaluationReadiness.freeze_record.identity`、すなわちmanifest bytesとresolved identity bytesを束ねた
`frozen_digest`をそのまま使用する。同じfrozen conditionから別configuration identityを生成せず、
別のmanifest ID fieldまたはsecond SoTを追加しない。

- `software_revision`、`configuration_id`、experiment/session/participant ID。
- finiteな`initial_qpos_rad`、measured MuJoCo-world
  `initial_measured_tip_position_m`、absolute norm tolerance `1e-12`以内の
  finite unit-norm `initial_tool_orientation_wxyz`。
- MuJoCo-worldの`target_world_position_m`、`target_tolerance_m`、
  `dwell_interval_s`、`timeout_s`。
- canonical input `source_kind`、manifest `target_id`、
  `local_endpoint_speed_m_s`、`deadzone`、`local_endpoint_max_delta_m`、
  sorted scalar `comparison_parameters`。

configurationの`source_kind`は全sampleで期待するsource identityであり、v1に別の
`input_source_id` synonymはない。configurationの`target_id`は、world
target/tolerance/timing fieldをfreezeするmanifest identityである。すべての
`trial_start.target_id`はこれと一致しなければならない。

motion fieldはcanonical hierarchyと正確なproducer vocabularyを維持する。

| 事実レベル | field | owner / nullability |
|---|---|---|
| requested operator intent | `source_kind`、`source_timestamp_s`、`source_active`、`axis_values`、`zero_input`、`stale_reason`、`requested_control_frame`、`local_endpoint_velocity_m_s` | input-owned。lifecycle fieldは常にpresent、stale reasonはoptional |
| resolved runtime motion | `resolved_control_frame`、`control_frame_resolution_status`、`control_frame_resolution_reason`、`resolved_world_endpoint_velocity_m_s` | frame resolution。unresolved時はworld fieldがnullable |
| policy request/prediction | `endpoint_delta_requested_m`、`endpoint_delta_achieved_m`、`candidate_qpos_rad` | motion policy。validなresolved policy request/candidateがない場合はnullable |
| measured MuJoCo outcome | `qpos_before_rad`、`qpos_after_rad`、measured tip before/after、`actual_tip_delta_m`、measured-progress metric | MuJoCo/post-step diagnostic。measured tip 3 fieldはすべてpresentまたはすべてnull |
| policy state | `motion_status`、`motion_rejection_reason` | motion policy。statusは`accepted`、`scaled`、`held`だけ |
| target state | `target_rejected`、`target_rejection_reason` | target acceptance/application。motion statusとは独立 |
| measured progress | `endpoint_progress_status`、`endpoint_progress_*`、`measurement_unavailable_reason` | post-step evaluation。motionとsource lifecycleから独立 |

`endpoint_delta_achieved_m`はpolicy predictionであり、measured movementではない。
`actual_tip_delta_m`とmeasured tip positionはMuJoCo evidenceである。before/after qposは
同じnon-empty finite structureを持たなければならない。candidate qposがavailableなら、
そのstructureと一致しなければならない。

## missing valueとstate semantics

missing evidenceはJSON `null`であり、fabricated zeroにはしない。3つのmeasured tip
fieldはall-or-noneである。absentの場合は
`endpoint_progress_measurement_available=false`とし、
`measurement_unavailable_reason`を必須とする。complete measured evidenceがある場合、
availability flagをtrueにする。

tool-frame resolution failureでは、
`control_frame_resolution_status=tool_orientation_unavailable`、必須の
`control_frame_resolution_reason`、nullのresolved frame、resolved world velocity、
policy-requested world deltaを持つ。tool-local velocityをworld motionとして
serializeしてはならない。

control-frame resolution tupleはclosedである。`world_passthrough`と
`invalid_control_frame_defaulted`にはworld requestと、
`local_endpoint_velocity_m_s`に`1e-12`以内で等しいresolved `mujoco_world`
velocityが必要である。`tool_orientation_resolved`にはtool requestとresolved world
velocityが必要である。`tool_orientation_unavailable`にはtool request、nullのresolved
frame/world velocity/requested delta、rejection reasonを伴うheld motion、pre-step qposと
等しいcandidateおよびpost-step qpos、zero policy-achieved deltaが必要である。
measurementが存在する場合はzero measured tip deltaも必要である。

独立したaxisは`motion_status`へoverloadしない。target rejectionには
`target_rejected`と`target_rejection_reason`を使う。active nonzero、active zero、
inactive non-stale、stale inputは、`source_active`、`axis_values`、導出と整合する
`zero_input`、`stale_reason`から再構築する。measurement unavailabilityには、measured progress
`measurement_unavailable`、そのreason、null metricを使う。measured zeroを許可するのは、
before/after measurementがzeroを生成した場合だけである。operator起因の
timeout/hold/rejection/staleは、`failure_attribution=operator`を伴う`failed` outcomeとして
保持する。infrastructureまたはmissing-evidenceによるinvalidityは、
`failure_attribution=technical`を伴う`technical_invalid`として保持する。

Input Source取得前など、source timestampまたはbefore/after stateをownerが生成できなかったtechnical-invalid
trialでは、必須sample fieldを推測せずzero-sample trialとしてoutcomeをcloseしてよい。生成済みの完全なstepだけを
sampleとして残し、partial stepへfake timestamp、qpos、measurement、zero motionを追加しない。

measurementが存在する場合、`actual_tip_delta_m`はafter minus beforeにEuclidean
tolerance `1e-12`以内で等しく、unavailable reasonを許可しない。absentの場合、
全measured fieldとmeasurement-dependent measured-progress metricをnullにする。

`success_within_timeout=true`には、`completion_status=success`、failure attribution
なし、同じtrialのcomplete measurementを持つprimary sampleが必要である。primary sampleは
設定timeout以前に発生しなければならない。そのmeasured tip-to-target distanceは
`final_measured_endpoint_error_m`と`1e-12`以内で一致し、かつ
`target_tolerance_m`以内でなければならない。primary sampleまでのordered sampleは、
少なくとも`dwell_interval_s`の連続したinside-tolerance measured intervalを
提供しなければならない。outsideまたはunavailable sampleはdwellをresetする。
これがdeterministicなpilot design dwell-proof policyである。

successはwhole-trial resultである。held、target-rejected、stale、
measurement-unavailable、unresolvedのsampleが1つでもあってはならない。
`primary_outcome_sample_index`はfinal motion sampleでなければならず、dwellはそのfinal
sampleまで連続してinside toleranceを維持しなければならない。以前のsampleをfinal
evidenceの代わりにしてはならない。

outcome classificationはclosedである。successは`success` / `none` / null reason、
operator failureは`failed` / `operator` / required reason、technical invalidは
`technical_invalid` / `technical` / required reasonである。他の組み合わせはvalidではない。

全outcomeで、`primary_outcome_sample_index`と`final_measured_endpoint_error_m`は、
両方nullまたは両方presentである。presentの場合、indexはfinal motion sampleを参照し、
そのsampleはcomplete measured evidenceを持ち、保存したerrorはmeasured tipから
configuration targetまでのdistanceに`1e-12`以内で等しくなければならない。
これはoperator failureとtechnical invalidityへ同様に適用する。
measurement-unavailable technical invalidでは両fieldをnullにする。defensibleなfinal
measurementを保持していないoperator failureでも両fieldをnullにしてよいが、operator
classificationとrequired reasonはmissingnessから推論せず、明示したままにする。

## trajectory reconstructionとanalog fixture compatibility

trial start/endはstart runtime timestampとoutcome runtime timestampである。primary
endpoint-error outcomeはoutcomeへ保存し、そのsource sampleへlinkする。timeout内の
successは明示し、validateする。sample内のordered measured tip positionから
MuJoCo-world trajectoryを再構築する。各position/deltaをtask directionと直交する方向へ
projectionすることでoff-axis driftを導出する。condition/order、repetition、
attempt、retry、practice status、failure attributionは、prespecified exclusion ruleと
retry ruleを支える。

recorded analog mappingはcontinuous endpoint velocity contractを使ってnormalized analog fixture intentを生成し、
これらの正確なrequested fieldを通じてlogへ記録してよい。mapping layerはv1へraw analog
mapping fieldを追加せず、このschemaを暗黙に変更してはならない。

## serializationとcompatibility

`record_to_json_value()`は通常のJSON object、array、string、boolean、finite number、
nullだけを返す。`encode_jsonl()`はUTF-8 text semantics、sorted key、NaN/Infinityなし、
末尾newlineありで、1 lineに1つのcompact objectを出力する。`decode_jsonl()`はblank
lineとnon-object recordをrejectする。supported streamのserialize-parse-serializeは
byte-deterministicである。

parseはstrictである。正確なversionと4つのrecord kindのいずれかを必須とし、unknown
field、record kind、versionをrejectする。したがってadditiveなfuture fieldには、
新しいsupported schema versionまたは明示的なreader updateが必要である。v1 readerは
forward compatibilityを推測しない。既存v1 fieldは意味を維持し、incompatibleな変更には
new versionが必要である。

record constructorは正確なJSON booleanと正確なfinite JSON numberを必須とし、
booleans-as-numbersとnumeric stringをrejectする。全enumをruntimeで確認する。
`comparison_parameters`がacceptするのはstring、integer、finite float、boolean、
nullのscalar valueだけであり、nested array/objectはrejectする。

`validate_record_stream()`はcross-record context equality、uniqueness、retry
protocol identity、sample ordering、timestamp、lifecycle closure、pilot design success evidenceを
所有する。どちらのhelperもI/Oを実行せず、inputをmutateしない。

current runtime recorderは、runnerの既存loopが生成時点で保持したinput、frame resolution、motion policy、
MuJoCo before/after measurement、Task terminal evidenceだけをv1へprojectionする。loggingのためにMapping、
motion policy、MuJoCo step、Task classificationを再実行または推定しない。trial IDは明示されたprotocol
contextとfrozen configurationから決定的に導出し、wall-clock time、random UUID、process identityを使わない。

filesystem ownerはruntime recorderである。保存前にtyped streamのvalidation、encode、decode、decoded streamの
再validation、再encode一致を確認し、UTF-8 without BOM bytesへ固定する。同じdirectoryのtemporary fileへ書き、
strict read-backが一致した場合だけatomic replaceし、replace後もtarget bytesをread-backする。partial / RUNNING
trial、invalid retry chain、encodingまたはwrite failureではfinal artifactをcommitせず、既存artifactを保持する。

## evaluation-artifact/v1へのhandoff

`experiment-motion-log/v1`は実行時のtruth-levelを保持する入力ログであり、metric resultやcondition summaryの正本ではない。
`runtime/evaluation/artifact.py`は、strict stream validationを通過したv1 bytesと入力`EvaluationReadiness`を受け、
configurationの`initial_measured_tip_position_m`とordered `MotionSampleRecord`のmeasured endpoint factsから
Task-owned trajectory evidence equivalentを再構成する。requested、predicted、またはzeroの値をmeasured trajectoryへ昇格させない。

`TrialOutcomeRecord`とvalidated lifecycleからterminal classificationを再構成し、既存endpoint reach evidence codecと
producer provenanceをそのまま検証する。source logのconfiguration ID、software revision、target、condition、freeze / manifest
identityはreadinessとexact matchで照合し、別manifestや別revisionへ黙って適用しない。technical-invalid、missing、unavailableの
evidenceはsuccess、trajectory、completion time、zero値へ補完せず、既存Evaluation Pluginのdeclared policyに従う。
artifact側のterminal elapsedとtrajectory sample elapsedは`TrialStartRecord.runtime_timestamp_s`を基準に
non-negativeなtrial-relative timeへrebaseする。complete measured sampleが残る場合でも、terminalが
`technical_invalid`ならTask-owned trajectory evidenceも`invalid`とし、4 evaluatorのdeclared policyへ渡す。
configurationの`comparison_parameters`はreadinessがfreezeするcadence、camera、seed、fixture、input source、
normalized range、presentation、feedback、condition/order、manifest/resolved identityを含む15-fieldのcanonical
projectionと完全一致しなければならない。

生成される`evaluation-artifact/v1`はschema/version、source log identity / SHA-256、software revision、configuration / freeze
identity、trial、condition/requested control frame、ordered evaluator identity、各metricのstatus/value/unit/frame/provenance/reason、
およびdescriptive condition summaryを持つ。JSONはsorted compact UTF-8、finite number、unknown field拒否、decode / round-tripを
必須とし、保存はsame-directory temporary file、read-back、atomic replaceの順で行う。これはsoftware-only evaluation artifactであり、
pilot、inferential statistics、superiority、#409 full E2Eの証拠を作らない。
cooperative writer間のoverwrite raceはtargetと同じdirectoryのpersistent sidecar
(`.<target-name>.lock`, creation permission `0600`)をkernel advisory lockで直列化する。sidecarの存在とcontentはinertなoperational
lock stateであり、PID / JSON owner metadataを読まず、stale lockの回収やsidecarのunlinkを行わない。
Windowsでは`msvcrt.locking`、POSIXでは`fcntl.flock`をnon-blockingで使い、process-local path lockも併用する。
lock取得から既存bytes確認、replace、rollback、kernel handle closeまでを同じcritical sectionとして扱う。
handleは正常終了・失敗・process crashでkernelに解放され、sidecar自体は次回writerのために残る。

1つのprotocol identityとrepetition内でattempt indexはuniqueであり、initial attemptは
ちょうど1つである。各trialが持てるdirect retry childは最大1つである。retryは直前の
completed technical-invalid attemptを参照し、1本のlinearな`0 -> 1 -> 2 ...` chainを
作る。sibling retryとduplicate attemptはinvalidである。

さらに、各sample request frameをtrial control conditionへbindし、source/target identityを
configurationへbindする。最初のsample qpos/tipはconfiguration initial qpos/tipと
一致しなければならない。隣接するqpos boundaryと、両方がavailableな場合のmeasured
tip boundaryはcontinuousでなければならない。vector identity、trajectory、
measured-delta、target-error、velocity、dwellの全比較は、記載されたunitにおける
Euclidean absolute tolerance `1e-12`を使用する。

input numeric consistencyはsequenceとしてvalidateする。`axis_values` normは最大1であり、
`local_endpoint_velocity_m_s == configuration.local_endpoint_speed_m_s * axis_values`
がそのtolerance内で成立しなければならない。したがって、設定speedがzeroでaxisが
nonzeroの場合もvalidなままであり、`zero_input`を変更せずにzero requested velocityを
生成する。
