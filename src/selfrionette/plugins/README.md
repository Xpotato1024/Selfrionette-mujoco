# plugin system

## 目的

このdirectoryは、Robot、Environment、Mapping、Task、Evaluation、Input Sourceの6軸を
独立に選択し、`runtime/`でcompositionするfirst-party pluginの入口である。
現在の診断・運用runtimeは主にRobot、Input Source、Mappingを使用する。6軸すべてを扱う
generic experiment compositionとはreadinessが異なるため、未実装のaxisをproduction-readyとは扱わない。

## identityとdiscovery

pluginのidentityはversion付きlogical identityであり、package名やPython class名を正本にしない。
Robot、Input Source、Mappingは各axis直下のpublic direct-child packageだけを対象に、固定
`plugin.py` entry pointからbounded discoveryする。具体plugin、identity、parameterのcurrent値は
各packageのdeclarationとcatalogを正とし、このREADMEではregistryを複製しない。

- [共通bounded discovery](bounded_discovery.py)
- [logical identity contract](../../../docs/contracts/experiment-plugin-composition.md)

## axis ownership

- [Robot](robots/README.md): production catalog、Bundle、Profile、Runtime Plugin、resource declaration
- [Input Source](input_sources/README.md): acquisition、sample、health、reader lifecycle
- [Mapping](mappings/README.md): sampleからcontrol intent / command semantics declarationへの変換
- [Environment](environments/README.md): generic contractのみ
- [Task](tasks/README.md): generic contractのみ
- [Evaluation](evaluations/README.md): generic contractのみ

Environment、Task、Evaluationにはproduction concrete plugin、catalog、runner / UIがまだない。
planned featureをcurrent behaviorとして補完しない。

## architectureとcontract

- [dependency boundary](../../../docs/architecture/dependency-boundaries.md)
- [runtime composition](../../../docs/architecture/runtime-composition.md)
- [experiment plugin composition](../../../docs/contracts/experiment-plugin-composition.md)
- [code / plugin documentation policy](../../../docs/architecture/code-documentation-policy.md)

## 追加時の入口

追加する責務のaxis READMEを読み、axis直下のpackage、固定entry point、plugin-local README、
関連testを同じ変更に含める。generic runtimeや別axisへ具体ID、fallback、暗黙登録を追加しない。
