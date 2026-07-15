---
status: canonical
owner: architecture
last_verified: 2026-06-12
canonical_for:
  - skeleton-first development
related:
  - docs/architecture/mujoco-skeleton-first-spec.md
  - docs/architecture/documentation-sot-policy.md
---

# 開発方針

Selfrionette-mujocoの初期移行ではskeleton-first developmentを採用した。最初の目的は
simulatorを動かすことではなく、実装開始前に責務のdriftを防ぐことだった。

過去にはinput、motion generation、kinematics、physics、communication、rendering、
documentation ruleを順次追加した結果、責務が重複した。このrepositoryでは構造を先に固定し、
layerごとに実装を追加した。

この手順は初期移行の基準であり、新しいすべてのIssueへ自動適用しない。現在のtask、Issue、
canonical docs、既存実装から、必要な成果が調査、設計、実装、bug fix、validationのどれかを判断する。

## 初期移行で用いた順序

```text
Step 1:
  Build the complete skeleton

Step 2:
  Add stubs to each layer

Step 3:
  Wire the stubs together in runtime

Step 4:
  Implement each stub one by one

Step 5:
  Freeze the parallel work contracts
```

Step 5-0では、control、transport、viewer、input、IK作業のdriftを防ぐparallel work
contractを固定した。このcontract-lockでは、IK、FK、MuJoCo loading、WebSocket server、
device input、Three.js rendering behaviorを追加しない。

## 責務driftのguardrail

新しい実装は既存layerのいずれかに配置する。新しい責務が必要な場合は、先にcanonical
architecture文書を更新し、その後で文書に定義したlayerへ実装する。
