# mujoco-viewer

browser上でMuJoCo WASM sceneを描画し、payload-v0のstateとdiagnostic overlayを表示する
rendering-only applicationである。最初の起動手順は
[backend / viewer startup](../../docs/operations/backend-viewer-startup.md)を参照する。

## responsibilityと境界

input overlayは、既存のpayload-v0 endpoint metadataを型付きのrequested、resolved、
predicted、measured groupとしてparseする。欠落または不正な値はzeroへ変換せず、
unavailableのまま扱う。held、rejected、stale、resolution-unavailable、
measurement-unavailableは互いに独立した状態である。このoverlayはread-only consumerであり、
schemaを定義せず、FKまたはIKを実行しない。

`apps/mujoco-viewer` は MuJoCo WASM scene renderer を rendering-only でホストする。
Input Sourceとしてのbrowser control acquisitionとbackend-side source / Mappingの境界は
[viewer Input Source](../../src/selfrionette/plugins/input_sources/viewer/README.md)から辿る。

## 正本

- [docs/operations/backend-viewer-startup.md](../../docs/operations/backend-viewer-startup.md)
- [docs/operations/r7-c-viewer-fixture-demo-procedure.md](../../docs/operations/r7-c-viewer-fixture-demo-procedure.md)
- [docs/operations/websocket-host-port-contract.md](../../docs/operations/websocket-host-port-contract.md)

## 役割

- browser-side FK / IK / qpos recompute: しない
- MuJoCo model loading: browser-side source of truth ではない
- `/mujoco/fast_arm/fixtures/fast_arm_sweep_x_qpos.json`: package-owned fixtureのstable public URL
- endpoint evaluation overlay: read-only diagnostic
- input overlay: read-only source state plus target rejection / hold metadata

## fixtureのownershipと再生成

canonical fixtureはnative MuJoCo replay pathから生成し、fast_arm Robot Plugin resourceとして所有する。
repository rootから次のコマンドで再生成する。

```powershell
uv run python scripts/viewer/export_wasm_qpos_fixture.py --preset sweep_x --steps 30
```

既定の出力先はSelfrionette adapter packageの
`src/selfrionette/plugins/robots/fast_arm/adapter/resources/fixtures/fast_arm_sweep_x_qpos.json`である。
fixture contractとresource identityは
[fast_arm Robot Plugin README](../../src/selfrionette/plugins/robots/fast_arm/README.md)からcanonical
ownerへ辿る。viewer testはtracked fixtureのschema、model path、frame ordering、qpos dimension、
finite値、progressionを検証する。過去の候補hashや採否理由は`docs/reports/`のevidenceに残し、
このcurrent operation入口には複製しない。

Viteは`publicDir`や旧`assets/` physical directoryを使わず、core/adapterのpackage source bindingから
development serverとproduction buildへ同じstable URLでresource bytesを公開する。manual copyは不要であり、
build outputの`mujoco/fast_arm/`はdeterministicなgenerated artifactである。

## validation

```powershell
cd apps\mujoco-viewer
npm run typecheck
npm test
npm run build
```

リポジトリ root からの差分確認も行う。

```powershell
cd <repository root>
git diff --check
```

## Live ViewerのURL

```powershell
cd apps\mujoco-viewer
npm run dev -- --host 127.0.0.1 --port 5173
```

```text
http://127.0.0.1:5173/apps/mujoco-viewer/?websocketUrl=ws://127.0.0.1:8766
```

`/apps/mujoco-viewer/`だけを開いた場合はdisconnected viewerになる。canonical live
viewer URLは、同じrouteへ`?websocketUrl=ws://127.0.0.1:8766`を付けたものである。
