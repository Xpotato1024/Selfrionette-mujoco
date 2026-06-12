# Selfrionette MuJoCo Migration Documents

このフォルダには、Selfrionette の MuJoCo + Three.js 新系統へ移行するための初期ドキュメントを格納している。

## ファイル

- `01_development_policy.md`
  - 開発方針。Skeleton-first、MuJoCo SoT、Rapier/PoseStateの扱い、PR運用方針を定義する。

- `02_mujoco_skeleton_first_spec.md`
  - 詳細仕様。ディレクトリ構成、レイヤー責務、型、Protocol、依存方向、import boundary test、既存資産の移植方針を定義する。

- `AGENTS.md`
  - プロジェクト直下に置く AI agent / Codex 向け運用ルール。旧Selfrionetteで発生した責務混在を防ぐための改善版。

## 配置案

```text
Selfrionette/
  AGENTS.md
  docs/
    architecture/
      development-policy.md
      mujoco-skeleton-first-spec.md
```
