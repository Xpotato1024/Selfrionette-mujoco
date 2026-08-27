---
status: canonical
owner: research
last_verified: 2026-08-27
canonical_for:
  - R7-G完了後の研究実行優先順位
  - 実機接触成立までのcross-round dependency roadmap
related:
  - docs/design/adr/0004-prioritize-physical-contact-bringup.md
  - docs/contracts/runtime-input-source-registry.md
  - docs/evaluation/world-tool-frame-comparison-design.md
  - docs/operations/hardware-safety.md
  - https://github.com/Xpotato1024/Selfrionette-mujoco/issues/410
  - https://github.com/Xpotato1024/Selfrionette-mujoco/issues/418
  - https://github.com/Xpotato1024/Selfrionette-mujoco/issues/419
  - https://github.com/Xpotato1024/Selfrionette-mujoco/issues/420
---

# 研究実行ロードマップ

## 目的と位置付け

この文書は、R7-G完了後にSelfrionette-mujocoで何を先に成立させるかを定めるcurrentな研究実行順序の正本である。
研究目的そのものや卒業論文の主張を置き換える文書ではなく、既存の研究目的を最短で検証可能な状態へ運ぶためのsoftware / experiment execution roadmapを定める。

現在の最優先milestoneは、**Selfrionetteまたはgamepadから同じversioned Input Source / Mapping / safety boundaryを通してfast_arm実機をmanual-gatedに操作し、対象物への接触・押込み・保持をmeasured evidence付きで実行できる状態**である。

```text
Selfrionette ─┐
              ├─> Input Source -> Mapping -> safety -> physical fast_arm
Gamepad ──────┘                                      |
                                                     v
                                                  contact
                                                     |
                                                     v
                                             measured task outcome
```

Gamepadはbring-upとcontrol baselineに用いる。研究の主比較を入力装置間比較へ変更せず、主比較はSelfrionette系入力を固定した写像方式・入力補助処理の比較とする。

## 現在成立している前提

R7-G / #404までに、versioned manifest / readiness、production six-axis composition、world / tool MuJoCo execution、`experiment-motion-log/v1`、canonical Task evidence reconstruction、production Evaluation Plugin、`evaluation-artifact/v1`、deterministic software-only E2Eが成立した。

入力取得についても、新規device support自体を最優先課題にはしない。

- `selfrionette/v1`はlive production Input Sourceである。
- `viewer/v1`はbrowser keyboard / gamepad bridgeであり、gamepad入力は`viewer_gamepad` subtypeとしてruntimeへ到達する。
- Input Sourceはacquisitionとhealthを所有し、Control Mappingはsampleからcontrol intentへの変換を所有する。

したがって次の主課題は、入力device追加ではなく、**接触task core、authoritative physical safety、minimal physical output gateを接続すること**である。

## 固定する優先順位

### 1. R7-H contact-coreを先に成立させる

R7-H / #410の最初のcritical pathは次とする。

```text
#411 task / object manifest
  -> #412 MuJoCo scene / spawn / reset
  -> #413 measured contact evidence
  -> #415 contact task lifecycle / measured outcome
```

#415はvirtual reaction-force signalを必要条件にしない。接触開始、押込み、保持、success / failure / technical-invalidをmeasured contact evidenceから判定できることをcontact-core completion gateとする。

#414 virtual reaction-force signalは#413から分岐する後続trackとし、最初のphysical contact milestoneのhard blockerにしない。

#416 logging / transport / viewerと#417 full software-only E2EはR7-H全体のtraceabilityとsoftware-only completionには必要だが、最初のmanual physical contact smokeのhard blockerにはしない。ただし、formal pilotまたは研究data collectionを開始する前には、contact trialのlossless logging / provenance / outcome再構成が成立していなければならない。

### 2. R7-J physical safety coreをR7-Hと並行して開始する

R7-J / #419はR7-H全完了を待たない。

R7-Gで成立したRobot Profile / Runtime Plugin、joint-limit configuration、qpos feasibility、MuJoCo modelと、実機のauthoritative資料・観測を入力として、次をphysical safety coreとして先行させる。

- authoritative joint / motor / actuator range
- MuJoCo modelと実機rangeの差分
- self-interference pairとcollision filtering policy
- robot-environment clearance / collision proxy
- velocity / acceleration / numerical feasibility boundary
- configuration / trajectory feasibility
- operator-visible hold / reject / stop / recover reason

contact-specificなself-contact / target-object contact / environment contact分類だけは、R7-H #413のcontact identityを利用できる時点で接続する。

physical safety coreは「安全である」という一般主張ではなく、**physical outputを許可してよいbounded envelopeと停止条件を明示するgate**である。

### 3. R7-Kはminimal physical output gateをpersistent runtimeより先にする

R7-K / #420では、daemon / service / container / long-duration soakを最初の実機bring-upの前提にしない。

最初に成立させる範囲は次とする。

```text
foreground CLI / explicit operator action
  -> versioned physical command boundary
  -> recording / dry-run sink
  -> stale / disconnect / stop semantics
  -> R7-J safety-core gate
  -> explicitly enabled transmission
  -> bounded physical robot output
```

actual physical actuationはR7-J safety-core acceptance後にのみ行う。service / container、restart policy、unattended operation、long-duration soakはinitial physical contact milestone後の後続scopeとする。

### 4. physical bring-upはfree-spaceから接触へ進める

physical output pathが成立しても、最初から対象物へ接触させない。

順序は次とする。

```text
A. gamepad -> physical fast_arm / free-space
B. Selfrionette -> physical fast_arm / free-space
C. gamepad -> physical contact task
D. Selfrionette -> physical contact task
```

A / Bでは入力経路、control semantics、workspace / collision / stale / stop、operator gateを切り分ける。C / Dで初めてcontact-coreをphysical operationへ接続する。

GamepadとSelfrionetteで可能な限り同じRobot、Environment、Mapping semantics、Task、safety / output pathを共有し、入力device固有差分と実機output差分を混同しない。

### 5. R7-I participant studyはoperational feasibilityの後に行う

R7-I / #418は、少なくとも次がmanual operator smokeで成立した後にstudy designを具体化する。

- gamepad free-space physical operation
- Selfrionette free-space physical operation
- contact-coreを使ったbounded physical contact operation
- technical-invalid / stop / abort / retryの運用境界
- formal data collectionに必要なlogging / provenance

participant studyをphysical bring-upの代替にせず、操作可能性と安全運用を先に確認する。

## Cross-round critical path

```text
R7-G completed
  |
  +--> R7-H contact core: #411 -> #412 -> #413 -> #415
  |
  +--> R7-J physical safety core -----------------------+
                                                        |
                                                        v
                                      R7-K minimal physical output gate
                                                        |
                                                        v
                                      gamepad physical free-space smoke
                                                        |
                                                        v
                                   Selfrionette physical free-space smoke
                                                        |
                                                        v
                                      bounded physical contact smoke
                                                        |
                                                        v
                                      R7-I pilot / participant design
```

並行して進められる非critical track:

```text
#413 -> #414 virtual reaction-force signal
#413 / #414 / #415 -> #416 logging / transport / viewer
#411-#416 -> #417 full R7-H software-only E2E
R7-K persistent service / container / long-duration operation
```

これらは価値があるが、最初のphysical contact milestoneを不要に遅らせない。

## Milestone gate

| Milestone | 必須成立条件 | まだ要求しないもの |
|---|---|---|
| contact-core software gate | #411 / #412 / #413 / #415 | virtual reaction force、participant study |
| physical safety gate | R7-J safety-coreのbounded envelope、stop / reject条件 | universal physical safety claim |
| minimal output gate | foreground / manual gate、dry-run、stale / stop、R7-J gate | daemon、container、unattended runtime |
| physical free-space smoke | gamepadとSelfrionetteのbounded movement、stop / stale / collision gate | object contact、formal experiment |
| physical contact smoke | contact-core + physical safety + minimal output gate | participant study、statistical conclusion |
| formal pilot readiness | contact logging / provenance、protocol freeze、exclusion / retry rule | universal superiority claim |

## Safety / permission boundary

このroadmapがphysical operationを優先することは、hardware accessを通常taskへ自動許可することを意味しない。

実機作動を行うIssueでは、`docs/operations/hardware-safety.md`に従い、少なくとも次を明示する。

- target device / host / port
- command / rate / bounded envelope
- operator gate
- physical clearance
- stop / emergency stop procedure
- rollback / recovery
- expected / observed output

serial open、OSC send、network transmission、physical robot outputは、該当する専用Issueと明示許可がある場合だけ実行する。

## Research claim boundary

この優先順位変更から次を推論しない。

- GamepadがSelfrionetteの主比較対象になったとは言えない。
- physical smokeの成立だけで写像方式の優越は言えない。
- software-only contactの成立だけで実機contact stabilityは言えない。
- bounded physical operationだけでauthoritative physical safety全体を証明したとは言えない。
- operator smokeをparticipant experimentとして扱わない。

formal evaluationでは入力装置、写像、補助、反力条件を同時に増やしすぎず、解釈可能な最小比較を維持する。

## Roadmap更新ルール

この文書はcurrent execution priorityの正本である。Round番号・Issue本文はこの文書と矛盾させない。

優先順位またはdependencyのmaterialな変更を行う場合は、current canonical documentを更新し、判断理由が将来必要な場合は新しいADRとして残す。既存ADRは現在方針に合わせて書き換えない。
