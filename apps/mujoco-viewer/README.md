# mujoco-viewer

## endpoint表示の境界

input overlayは、既存のpayload-v0 endpoint metadataを型付きのrequested、resolved、
predicted、measured groupとしてparseする。欠落または不正な値はzeroへ変換せず、
unavailableのまま扱う。held、rejected、stale、resolution-unavailable、
measurement-unavailableは互いに独立した状態である。このoverlayはread-only consumerであり、
schemaを定義せず、FKまたはIKを実行しない。

`apps/mujoco-viewer` は MuJoCo WASM scene renderer を rendering-only でホストする。

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
uv run python scripts/export_wasm_qpos_fixture.py --preset sweep_x --steps 30
```

既定の出力先はSelfrionette adapter packageの
`src/selfrionette/plugins/robots/fast_arm/adapter/resources/fixtures/fast_arm_sweep_x_qpos.json`である。
contractは`schema_version: 1`、model `assets/mujoco/fast_arm/scene.xml`、
preset `sweep_x`、`qpos_length: 4`、30 framesである。修復済みcurrent pathの内容は
SHA-256 `4925D77535A67ED0E4EB68BDCC0B66C262D2D11AE5E1F7DCA99C3AE5E38D312A`
である。viewer testはtracked fileをparseし、schema、source、model path、preset、
frame count、連続するframe index、単調増加するsimulation time、qpos dimension、
finiteなqpos value、有意なsweep progressionを検証する。

採用しなかったPR #392の再生成候補は、SHA-256
`A30FD0A303506C7807BA2E687411FACDF28BA2BC2AE9AC8F909B9C59997FEE36`
だった。joint positionの直接適用によって古いMuJoCo velocity stateが残り、
BADQACC recoveryとtime rollbackが発生したため採用しなかった。現在のnative simulatorは
position command時にvelocityをclearし、`sweep_x`はframeごとのdesired endpointを供給する。
exporterはproduct-owned fixtureをatomicに置換する前にsequence全体を検証する。

Viteは`publicDir`や旧`assets/` physical directoryを使わず、core/adapterのpackage source bindingから
development serverとproduction buildへ同じstable URLでresource bytesを公開する。manual copyは不要であり、
build outputの`mujoco/fast_arm/`はdeterministicなgenerated artifactである。

## 参照用の検証コマンド

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
