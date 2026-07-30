# runtime

## 責務

唯一のcomposition root。複数層を結線してよい唯一の場所であり、内部責務を次へ分ける。

| owner | 責務 |
|---|---|
| `composition/` | config、Robot Profile / Plugin / Bundle、typed provider assembly、pipeline builder |
| `execution/` | pipeline lifecycle、input step loop、timing / pacing |
| `control/` | input selection/state、endpoint target、viewer control ingress、step diagnostics |
| `safety/` | stale input policy、qpos feasibility |
| `experiment/` | versioned experiment contract、registry、readiness composition |
| `evaluation/` | FK / endpoint evaluation、progress、manifest / freeze readiness |
| `runners/` | 既存のdry-run、live / offline smoke、WebSocket publisher entry point |

将来#406以降のexperiment lifecycle / runnerは`experiment/`が所有する。
`runners/`は既存のoperational smoke / runnerだけを所有する。新しいframeworkや先行runnerは追加しない。

## 入力

config、選択されたInput Source / Control Mapping / command semantics route /
Robot Bundle、MuJoCo backend、transport。

## 出力

実行ループと結線済み pipeline。

## 依存してよい層

すべての層。

## 依存してはいけない層

なし。ただし各層が runtime に依存してはいけない。

## 禁止事項

層の中身の責務を runtime に吸収しない。runtime は結線と lifecycle 管理に限定する。

runtime package rootは`RuntimeConfig`とRobot catalog resolver 5件だけをlazy exportする。
各contract、control、safety、evaluation、runner APIは上表のcanonical ownerからimportする。

## canonical routing

- [runtime composition](../../../docs/architecture/runtime-composition.md)
- [dependency boundary](../../../docs/architecture/dependency-boundaries.md)
- [plugin system](../plugins/README.md)
- [unified CLI](../../../docs/operations/unified-cli.md)
