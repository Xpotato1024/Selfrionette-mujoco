# tests

このdirectoryはproduction contractとarchitecture invariantを検証するtest / fixture / supportの入口である。
test treeをproduction registryやpublic APIのownerにしない。

## ownership

- `architecture/`: dependency、discovery、ownership、documentation governance
- `schemas/`: layer contract型
- `runtime/`: composition、execution、control、safety、evaluation
- `plugins/` / `input_sources/` / `robots/`: axis / concrete plugin behavior
- `integration/`: 複数のproduction boundaryを通すsoftware integration
- `fixtures/` / `support/` / `stubs/`: test-only dataとdouble。production discoveryへ入れない

変更層に対応するfocused testから開始し、必要に応じて
[validation policy](../docs/operations/validation.md)のrepository standardへ広げる。
