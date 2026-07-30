# Task Plugin

## 責務

Task axisはgeneric experiment composition上の目的と条件を表す。

## 置けるもの / 置けないもの

- 置けるもの: 将来のproduction task declarationとtask固有parameter
- 置けないもの: source acquisition、Robot command実行、Evaluation metric implementation

## contractとI/O

- required contract: [experiment plugin composition](../../../../docs/contracts/experiment-plugin-composition.md)
- input: generic compositionのversion付きselection
- output: task identityとcomposition role

## lifecycleとside effect

現在はgeneric contractとtest fixtureだけであり、production task lifecycleやside effectはない。

## catalog / discovery / registration

production concrete plugin、axis catalog、runner / UIは未実装である。

## shared private owner

なし。

## concrete pluginの追加

最初のproduction pluginでは、parameter owner、start / completion / failure semantics、
bounded discovery、catalog、runner結線、README、validationを同時に定義する。

## canonical document

- [runtime composition](../../../../docs/architecture/runtime-composition.md)
- [experiment plugin composition](../../../../docs/contracts/experiment-plugin-composition.md)
