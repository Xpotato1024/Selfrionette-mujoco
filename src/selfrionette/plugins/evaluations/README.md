# Evaluation Plugin

## 責務

Evaluation axisはgeneric experiment composition上の評価方法とresult contractを表す。

## 置けるもの / 置けないもの

- 置けるもの: 将来のproduction evaluatorとmetric固有parameter
- 置けないもの: Task目標、Robot control、source acquisition、viewer diagnosticだけの表示

## contractとI/O

- required contract: [experiment plugin composition](../../../../docs/contracts/experiment-plugin-composition.md)
- input: generic compositionのversion付きselectionと将来のrun result
- output: evaluation identityとcomposition role

## lifecycleとside effect

現在はgeneric contractとtest fixtureだけであり、production evaluator、result persistence、
external side effectはない。

## catalog / discovery / registration

production concrete plugin、axis catalog、runner / UIは未実装である。

## shared private owner

なし。

## concrete pluginの追加

最初のproduction pluginでは、metric / unit / aggregation owner、failure semantics、bounded discovery、
catalog、runner / manifest結線、README、validationを同時に定義する。

## canonical document

- [evaluation readiness](../../../../docs/contracts/evaluation-manifest-readiness.md)
- [experiment plugin composition](../../../../docs/contracts/experiment-plugin-composition.md)
