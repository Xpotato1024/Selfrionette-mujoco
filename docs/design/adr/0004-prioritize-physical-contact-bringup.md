---
status: historical
owner: research
last_verified: 2026-08-27
canonical_for: []
related:
  - docs/architecture/research-execution-roadmap.md
  - docs/contracts/runtime-input-source-registry.md
  - docs/operations/hardware-safety.md
  - https://github.com/Xpotato1024/Selfrionette-mujoco/issues/501
---

# ADR 0004: 実機接触bring-upを研究実行の最優先にする

## Status

Accepted

## Context

R7-G完了により、versioned manifest / readiness、production six-axis composition、world / tool MuJoCo execution、`experiment-motion-log/v1`、measured evaluation artifact、deterministic software-only E2Eまでが成立した。

また、Input Source Pluginとしてlive `selfrionette/v1`とviewer bridge `viewer/v1`が既にproduction化され、gamepad入力も`viewer_gamepad` subtypeとしてruntimeへ到達できる。

一方、既存roadmapは概ね次の順序を想定していた。

```text
R7-H full software-only contact
  -> R7-J physical feasibility
  -> R7-K persistent runtime / physical output
  -> R7-I participant pilot
```

この順序では、virtual reaction-force、viewer / E2E completion、service / containerなどの価値ある基盤作業が、研究上より重要な「Selfrionette / gamepadで実機を操作し、接触タスクを成立させる」milestoneより前にhard dependencyとして並ぶ。

研究目的はsoftware基盤の完成自体ではなく、接触を含む遠隔操作においてSelfrionette系入力の写像方式・入力補助処理が操作性能へ与える影響を評価することである。そのため、operational physical feasibilityを早期に確認しないままsoftware-only completenessを積み上げることは、研究上の主要riskを後ろへ送る。

## Decision

R7-G完了後のcritical pathを、**contact-coreとphysical safetyを並行して進め、minimal physical output gateを経てfree-space physical bring-up、その後にphysical contactへ進む構成**へ変更する。

具体的には次を採用する。

1. R7-H contact-coreは`#411 -> #412 -> #413 -> #415`とする。
2. #414 virtual reaction-forceは#413から分岐する後続trackとし、#415のhard dependencyにしない。
3. R7-J physical safety coreはR7-H全完了を待たず、R7-Gで成立したRobot / model / feasibility境界から並行開始する。
4. R7-Kはpersistent service / containerより、foreground・manual-gatedなminimal physical output gateを先に成立させる。
5. physical bring-upは`gamepad free-space -> Selfrionette free-space -> physical contact`の順に進める。
6. R7-I participant studyはoperational physical contact feasibilityとformal data logging readinessの後に行う。
7. Gamepadはbring-up / control baselineとし、研究の主比較を入力装置間比較へ変更しない。
8. 実機作動は専用Issueと明示許可を必須とし、このdecisionだけでhardware権限を拡張しない。

currentな詳細dependencyとmilestone gateは`docs/architecture/research-execution-roadmap.md`を正とする。

## Considered alternatives

### 既存roadmapをそのまま順番に完了する

R7-Hのvirtual reaction-force、logging / viewer、full E2Eをすべて完了し、その後R7-J、R7-Kへ進む案。

software-only completenessは高いが、実機で操作できるか、physical safety gateを設計できるか、接触時に実際の問題が何かという研究riskの検証が遅れるため採用しない。

### R7-K persistent runtimeを先に完成する

service / container / restart / long-duration operationを先に整備してから実機へ接続する案。

運用資産としては有用だが、最初のmanual physical bring-upに不要なscopeが多く、研究milestoneを遅らせるため採用しない。

### participant pilotを先に実施する

R7-G free-space基盤だけでparticipant studyへ進む案。

現在の研究優先順位は接触を含む実機遠隔操作の成立確認であり、操作pathとcontact taskが未成立のままstudy designを固めると実験条件を再設計する可能性が高いため採用しない。

## Consequences

### Positive

- 実機操作・接触という研究上の主要riskを早期に検証できる。
- contact task側の問題とphysical output側の問題を、free-space bring-upを挟んで切り分けられる。
- Selfrionetteとgamepadで同じRobot / Mapping semantics / safety / output pathを共有しやすい。
- virtual reaction-forceやpersistent runtimeを、実際に必要な条件が分かった後で設計できる。
- participant studyのtask / logging / exclusion ruleをoperational evidenceに基づいて決められる。

### Negative / trade-off

- R7-Hはfull completion前にphysical trackが並行するため、単純なRound直列管理ではなくdependency graphを確認する必要がある。
- 初回physical smokeとformal research data collectionを明確に分離しなければならない。
- R7-J safety coreのacceptance boundaryを早めに具体化する必要がある。
- R7-Kをminimal gateとpersistent operationへ段階化するため、既存parent Issueの記述をreconcileする必要がある。

## Safety consequence

研究優先度がphysical operationへ移ることは、serial、OSC、network transmission、robot actuationを通常taskで許可することを意味しない。

actual hardware taskでは`docs/operations/hardware-safety.md`、repository permission boundary、専用Issueのoperator gate / stop / rollback / physical clearanceを満たすことを必須とする。
