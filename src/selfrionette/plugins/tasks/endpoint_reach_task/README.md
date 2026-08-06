# endpoint_reach_task Task Plugin

## 意味とresponsibility

`endpoint_reach_task/v1`はmeasured Robot endpointを固定targetへ到達させるTask lifecycleを表す。
Taskはterminal classificationを所有し、metric集計は所有しない。

canonical declaration: [`TASK_PLUGIN`](plugin.py)

## composition role

`endpoint_pose/v1`、`reset_initial_state/v1`、`robot.tool_endpoint` roleを要求し、
`endpoint_reach_terminal_classification/v1`と`endpoint_reach_measured_trajectory/v1`をcanonical
evidenceとして宣言する。

## parameters

なし。target、tolerance、dwell、timeout、initial stateは上位evaluation manifestが唯一のcondition
ownerである。#407 / #408が同じfrozen manifestへbindしたevidenceを渡す。

## lifecycleとside effect

initial stateは`ready`で、runnerが提供するcanonical evidenceから`running`、`success`、`failure`、
`technical_invalid`を分類する。Robot command、MuJoCo step、artifact出力は行わない。

## compatibilityとcomposition

MuJoCo backendとmeter単位のRobot endpoint roleへ依存する。fast_arm固有ID、site、joint、solverは参照しない。

## constraintsとnon-goals

- constraint: missing / unavailable / invalid evidenceをsuccessへ変換しない
- non-goal: contact、force、grasp、metric aggregation、JSON / CSV export

## tests / validation

- [Task plugin test](../../../../../tests/plugins/tasks/test_endpoint_reach_task.py)

## canonical architecture / contract

- [evaluation design](../../../../../docs/evaluation/world-tool-frame-comparison-design.md)
- [experiment plugin composition](../../../../../docs/contracts/experiment-plugin-composition.md)
