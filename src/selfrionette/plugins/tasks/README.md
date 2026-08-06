# Task Plugin

## 責務

Task axisはgeneric experiment composition上の目的と条件を表す。

## 置けるもの / 置けないもの

- 置けるもの: production task declaration、task state、terminal classification、task固有parameter
- 置けないもの: source acquisition、Robot command実行、Evaluation metric implementation

## contractとI/O

- required contract: [experiment plugin composition](../../../../docs/contracts/experiment-plugin-composition.md)
- input: generic compositionのversion付きselection
- output: task identity、required capability / role、canonical task evidence、terminal classification

## lifecycleとside effect

`endpoint_reach_task/v1`はendpoint reachのstateとclosed terminal classificationを所有する。
runner execution、target parameter、metric導出、artifact出力は所有せず、external side effectはない。

## catalog / discovery / registration

`discovery.py`はpublic direct-child packageの`plugin.py::TASK_PLUGIN`だけをbounded discoveryし、
`catalog.py`がlogical identity順のproduction registryへ投影する。private package、test fixture、arbitrary
dynamic importは対象外である。production runner / UIは未実装である。

## shared private owner

現在はなし。

## concrete pluginの追加

axis直下へself-contained packageを追加し、`plugin.py::TASK_PLUGIN`、plugin-local README、focused
testsを同じ変更に含める。package basenameとlogical identityを一致させ、catalogやgeneric runtimeへ
concrete ID / importを追加しない。

## current concrete plugins

- [`endpoint_reach_task/v1`](endpoint_reach_task/README.md): endpoint pose / initial stateと`robot.tool_endpoint`を要求し、terminal classificationとmeasured trajectory evidenceを宣言するR7-G task

## canonical document

- [runtime composition](../../../../docs/architecture/runtime-composition.md)
- [experiment plugin composition](../../../../docs/contracts/experiment-plugin-composition.md)
