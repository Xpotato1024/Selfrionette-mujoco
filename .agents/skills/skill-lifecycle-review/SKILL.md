---
name: skill-lifecycle-review
description: repository-local Skill候補の知識分類、evidence確認、5軸scoring、lifecycle判断を行う。反復workflowの候補レビュー、draft作成、promotion検討、既存Skillのupdate・merge・disable・deprecateを判断するときに使用する。
---

# Skill lifecycle review

## Triggerとexclusion

反復性、再構成コスト、失敗防止価値をevidence付きで判定する必要があるときに使用する。
単にtaskが長い、難しい、fileが多いだけでは使用しない。read-only taskではSkill関連fileを
変更せず、重要な候補を報告だけに留める。Git / PR merge、Issue close、branch削除、external
mutation、credentials、production、hardwareは対象外であり、既存canonical workflowへrouteする。

## Required inputsと取得方法

- repository opt-inとthreshold: `.agents/skill-system.toml`をUTF-8で読む。
- 常時規則と責務: `AGENTS.md`、`docs/operations/agent-skill-governance.md`を読む。
- persisted evidence: 対象Issue / PR、Git履歴、review履歴、task artifactを現在状態として取得する。
- 既存の候補・Skill・eval: `.agents/skill-candidates/`、`.agents/skills/`、`.agents/skill-evals/`を列挙する。

取得できないevidenceは推測で補わず、Not Run Reasonと残存riskにする。

## Ordered workflow

1. opt-in、task scope、read-onlyかどうか、既存権限境界を確認する。
2. 知識を、AGENTS規則、Skill workflow、script、reference、変動state、test / validator、不安定な単発作業に分類する。
3. 同型workflowの独立したevidenceを2件以上確認し、Issue番号、PR番号、SHA、日付はevidence欄だけに残す。
4. recurrence、reconstruction cost、error prevention、stability、verifiabilityを各0〜2点で採点し、totalを再計算する。
5. 既存Skillのtrigger、scope、output、evalとoverlapを照合し、新設より最小update・route・deprecateを優先する。
6. `status`と`proposed_action`を分離して、record、draft、promote、update、merge、disable、deprecate、approval-requiredのいずれかを選ぶ。
7. approval boundary、unresolved risks、必要なvalidation、invocation policyをcandidateへ記録する。

`merge`はSkill同士の責務統合を意味し、Git / PR mergeではない。GitやGitHubの状態を変更する判断はこのSkillの出力に含めず、既存workflowへrouteする。

## Permitted variation

evidence源の組合せ、scoreの内訳、既存Skillとの関係はtaskに応じて変えてよい。ただし、
cross-session recurrenceの推測、根拠のない時間・token・cost削減量、current stateのSkill本文への固定は許可しない。

## OutputsとDefinition of Done

出力は、分類、evidence一覧、5軸scoreとtotal、overlap、status / action、approval boundary、
validation、残存riskを含む短いレビュー結果とする。write taskでopt-inとscopeが許す場合だけ、
`.agents/skill-candidates/<candidate-key>.toml`を1候補1fileで追加または更新する。

完了条件は、schema validatorが通り、candidate keyの重複がなく、score totalが合計と一致し、
actionがstatusと整合し、Skill本文がcurrent Issue / branch / SHA / date / local pathを固定していないことである。

## Failure、retry、stop / escalation

TOML parse、encoding、evidence取得、overlap判定、threshold判定のいずれかに失敗したら、
候補をdraftやactiveとして報告しない。再試行は同じcurrent sourceを一度再取得して比較するまでとし、
差分・並行更新・権限不明・既存SoT矛盾があれば停止してユーザーへescalateする。

## Side-effect boundary

通常はread-onlyである。許可されるwriteはopt-in済みrepository内のcandidate recordだけで、
repository外、user-global Skill、executable script、dependency、MCP、GitHub、production、
hardware、external serviceへ副作用を出さない。Skill作成・更新は別途Issue scopeとvalidationを満たす場合に限る。
