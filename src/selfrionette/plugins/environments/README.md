# Environment Plugin

## 責務

Environment axisはgeneric experiment composition上のworld / scene条件を表す。

## 置けるもの / 置けないもの

- 置けるもの: 将来のproduction environment declarationとその固有resource
- 置けないもの: Robot model、Task目標、Evaluation metric、viewer独自physics

## contractとI/O

- required contract: [experiment plugin composition](../../../../docs/contracts/experiment-plugin-composition.md)
- input: generic compositionのversion付きselection
- output: environment identityとcomposition role

## lifecycleとside effect

現在はgeneric contractとtest fixtureだけであり、production lifecycleやexternal side effectはない。

## catalog / discovery / registration

production concrete plugin、axis catalog、runner / UIは未実装である。generic registry testを
production readinessの証拠にしない。

## shared private owner

なし。

## concrete pluginの追加

最初のproduction pluginでは、resource ownership、bounded discovery、catalog、lifecycle、
runtime assembly、README、validationを同じ変更で設計する。planned control planeを先取りしない。

## canonical document

- [runtime composition](../../../../docs/architecture/runtime-composition.md)
- [experiment plugin composition](../../../../docs/contracts/experiment-plugin-composition.md)
