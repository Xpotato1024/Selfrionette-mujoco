---
status: canonical
owner: architecture
last_verified: 2026-07-31
canonical_for:
  - repository-local agent Skill governance
related:
  - AGENTS.md
  - docs/operations/codex-workflow.md
  - docs/operations/validation.md
  - docs/operations/git-pr-workflow.md
  - docs/operations/japanese-doc-writing-guardrails.md
  - docs/architecture/documentation-sot-policy.md
  - research/README.md
---

# repository-local Skill governance

この文書は、`Selfrionette-mujoco`のrepository-local Codex Skillに関するlifecycle、
evidence、autonomy boundary、validationの正本である。現在のtaskを完了することを
Skill改善より優先し、Skill systemは既存の編集、Git、GitHub、external service、
production、hardware権限を拡張しない。

## 責務の分離

| 媒体 | 所有する知識 |
|---|---|
| `AGENTS.md` | 常に適用する短い規則とSkill systemへのrouting |
| `.agents/skill-system.toml` | repository opt-in、threshold、autonomy boundary |
| `.agents/skills/` | 条件付きで再利用する1 job単位のworkflow |
| `.agents/skill-candidates/` | 反復性、再構成コスト、失敗防止価値のevidence |
| `.agents/skill-evals/` | trigger、route boundary、代表dry-runの評価条件 |
| `scripts/` | 決定的で壊れやすい処理。新設・重大変更は別のapproval boundary |
| `references/` | 詳細で比較的安定した参照情報 |
| test / CI / validator | 機械的に強制できる不変条件 |
| Issue / PR / state / research log / RAG | 現在状態、provenance、実験結果などの変動情報 |

Skill本文へcurrent Issue、branch、commit SHA、日付、local absolute pathを固定しない。
canonical documentationの詳細をSkillへ大量複製せず、正本へrouteする。

validatorが検査するSKILL.md frontmatter subsetは、先頭と末尾の`---` delimiter、および
重複しない単純scalarの`name: value`と`description: value`の2 keyだけである。list、nested
mapping、任意のYAML tagは扱わない。`agents/openai.yaml`もYAML全仕様としてparseせず、
`policy.allow_implicit_invocation`のboolean宣言だけを検査する。

## Opt-inとscope

repositoryが`.agents/skill-system.toml`を持ち、`enabled = true`の場合だけ、この
governanceのcandidate記録やrepository-local Skillの作成・更新を許可する。設定の
schemaはvalidatorが検査できる最小構造に限定する。

自動作成・更新の対象は、repository内の`.agents/skills/**`に閉じたinstruction-only
Skillだけである。dependency、MCP、credentials、production、hardware、serial、OSC、
外部mutationを追加・実行しない。user-global Skill、`~/.codex/`、`~/.agents/`は変更禁止。
executable scriptの新設・重大変更、implicit invocationのrepository-wide強制、外部
side effectを持つSkillは、明示承認または専用Issueなしに行わない。

incidentally発生したSkill差分は、product変更と混在させず、可能なら独立commitまたは
follow-upへ分離する。stacked PR、hotfix、merge conflict中、並行branchで同じcandidateや
Skillを更新している場合は、Skill作成を止め、candidate記録または最終報告だけに留める。

## Candidate Reviewの発火条件

次のstrong signalを1件以上、またはcomplexity signalを2件以上、persisted evidenceから
観測した場合だけCandidate Reviewを行う。単にtaskが長い、難しい、fileが多いだけでは
発火しない。

Strong signal:

- 同一または構造的に同等なworkflowを2回以上確認した。
- 同種のreview指摘またはuser修正を複数回確認した。
- 既存Skillの未発火、誤発火、手順不足、stale reference、過剰作業を確認した。
- 同じscript、validator、template、checklist、reportを繰り返し再生成した。

Complexity signal:

- 7段階以上の順序依存手順がある。
- 6回以上のtool、shell、Git、GitHub操作を順序どおりに要する。
- 3個以上のdocument、code、Issue、PR、external sourceからworkflowを再構成する。
- 順序誤りがrollback、CI再実行、merge conflict、PR retarget、review差戻しにつながる。
- 再利用可能なinputs、outputs、Definition of Doneが明確である。

Evidenceはrepositoryのcandidate store、Git、Issue、PR、review履歴、task artifact、
またはuserが反復を明示した事実から取得する。cross-session recurrenceを推測しない。
レビュー履歴が存在しない場合は、存在しないことを証拠として明記し、reviewを捏造しない。

## Scoringと判断

候補は次の5軸を各0〜2点で採点し、`total`は合計値と一致させる。

| 軸 | 2点の条件 |
|---|---|
| `recurrence` | 複数の独立した実例で反復を確認できる |
| `reconstruction_cost` | 正本と状態を毎回再構成するコストが高い |
| `error_prevention` | 手戻り、権限逸脱、state破損を明確に防ぐ |
| `stability` | input、output、順序、責務が安定している |
| `verifiability` | 成否をtest、validator、stateで客観的に確認できる |

判定の目安は、0〜4点を`none`、5〜6点を`record`または`update`、7〜8点を
`create-draft`または既存Skillの`update`、9〜10点をvalidation後の`promote`検討とする。
thresholdは`.agents/skill-system.toml`で固定する。scoreは安全、permission、Issue scope、
repository policyを上書きしない。

## Status、action、lifecycle

候補の`status`と判断の`proposed_action`は別軸で記録する。

- status: `observed`、`candidate`、`draft`、`active`、`deprecated`、`rejected`
- action: `none`、`record`、`update`、`create-draft`、`promote`、`merge`、`disable`、
  `deprecate`、`approval-required`

`merge`はSkill同士の責務統合を意味し、Git / PR mergeを意味しない。lifecycleは
`observed`な事実をevidenceとして確認し、`candidate`を採点し、thresholdに応じてdraftを
作成する。draftはexplicit-onlyで構造、trigger、代表task、side-effect boundaryを検証し、
検証済みで安定している場合だけactive化を検討する。stale、重複、obsoleteなSkillは
`update`、`merge`、`disable`、`deprecate`または`rejected`を選び、理由と残存riskを残す。

## Invocation policy

新規Skillは原則としてexplicit-only draftで開始する。各Skillの
`agents/openai.yaml`に`policy.allow_implicit_invocation: false`を設定し、trigger eval、
代表task、required input、failure path、side-effect boundaryが検証されるまでimplicit
invocationを許可しない。検証後もimplicit化は別判断であり、repository-wideに強制しない。

## Candidate schema

候補は`.agents/skill-candidates/<candidate-key>.toml`に1候補1ファイルで保存する。必須
fieldは`schema_version`、`candidate_key`、`status`、`scope`、`summary`、
`observable_evidence`、`related_overlapping_skills`、`approval_boundary`、
`unresolved_risks`、および`[score]`内の5軸と`total`である。`candidate_key`はfilenameと一致し、
repository内で重複させない。Issue番号、PR番号、SHA、日付は`observable_evidence`に限って
記録し、Skill本文の恒常手順には移さない。時間、token、コストの削減量は根拠なく記録しない。

## Eval schema

各Skillに`.agents/skill-evals/<skill-name>.toml`を対応させる。必須fieldは
`schema_version`、`skill_name`、`invocation_policy`、`side_effect_boundary`、
`positive_triggers`（3件以上）、`negative_triggers`（2件以上）、`route_boundaries`、
`required_inputs`、`expected_major_steps`、`expected_outputs`、`forbidden_actions`、
`representative_dry_run`、`false_positive_risk`、`false_negative_risk`、
`stale_reference_risk`である。triggerは日本語promptを中心とし、negativeには非対象または
別Skillへのroute例を含める。

## Skill authoring contract

1 Skill = 1 jobとする。SKILL.mdはfrontmatterの`name`と`description`、trigger、exclusion、
required inputs、input acquisition、ordered workflow、permitted variation、outputs、
Definition of Done、failure handling、retry、stop / escalation condition、side-effect
boundaryを明示する。frontmatterはvalidatorが検査する小さなsubsetだけを使用し、YAML全仕様を
独自実装しない。placeholder、empty description、secretらしき値、mojibake、BOMは禁止する。

## Validationとpromotion

validatorはconfig、candidate / eval TOML、duplicate key、score total、status / action、
Skill frontmatter、directory/name、lowercase-hyphenated name、duplicate Skill、参照path、
implicit policy、placeholder、transient state、secretらしき値、UTF-8、BOM、mojibakeを検査する。
trigger evaluationではpositive 3件以上・negative 2件以上とroute boundaryを確認し、代表dry-run
ではSkillをexplicitに読み、成果物、DoD、失敗時の停止条件を照合する。

変更層、contract、failure mode、side effectに対するvalidation選択は
[`validation.md`](validation.md)を正本とし、全taskへfull suiteを機械適用しない。testsの削除、
skip、弱体化、未実行項目の成功扱い、simulation smokeのhardware validationへの読み替えはしない。
docsのlink、encoding、Japanese guardrail、Git diff、base / branch / head / PR metadataも
必要範囲で検証する。

promotion前にrequired inputの取得可能性、expected output、failure path、false positive / negative、
stale riskを再確認する。実行できないvalidationはNot Run Reason、代替証拠、残存riskとして報告する。

## 既存workflowへのroute

- Codex全体の入口とtask固有deltaは[`codex-workflow.md`](codex-workflow.md)へrouteする。
- 変更層とfailure modeの検証選択は[`validation.md`](validation.md)へrouteする。
- Git、PR、head一致、long-form bodyのtransport / structure gateは[`git-pr-workflow.md`](git-pr-workflow.md)へrouteする。
- 日本語、UTF-8、BOM、mojibake、PR bodyの安全規則は[`japanese-doc-writing-guardrails.md`](japanese-doc-writing-guardrails.md)へrouteする。
- 文書の配置、canonical role、Source of Truthは[`../architecture/documentation-sot-policy.md`](../architecture/documentation-sot-policy.md)へrouteする。
- research logとexperiment evidenceの要否は[`../../research/README.md`](../../research/README.md)へrouteする。

## Git / PR境界

Skill関連変更も通常のbranch、actual diff、commit、push、Draft PR gateに従う。merge、Ready化、
Issue close、branch削除、release、deploy、外部mutationは、既存workflowと明示承認なしに行わない。
Skill候補だけの変更は可能なら独立commitにし、product変更と混在した場合はdiffと最終報告で分離を明示する。
