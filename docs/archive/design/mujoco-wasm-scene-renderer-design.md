# MuJoCo WASM Scene Renderer 設計

> Status: historical design record. The executable PoC was promoted to
> `apps/mujoco-viewer` by #185 and retired by #385; the dated history below is
> retained to explain that promotion and the rendering-only boundary.

## 1. 背景

`#174` では、既存の `apps/mujoco-viewer` 上で `fast_arm` の STL mesh を手で合わせ続ける方針が限界に達した。`#176` で MuJoCo native viewer により `assets/mujoco/fast_arm/scene.xml` の素直な表示姿勢が確認でき、`#178` で official `@mujoco/mujoco` WASM PoC が isolated app として成立することも確認できた。

この issue の目的は、production 実装を始めることではない。Python native MuJoCo backend / IK / FK / runtime を source of truth として維持したまま、browser 側の MuJoCo WASM scene renderer をどの位置づけで扱うかを決めることである。

ここでの結論は「browser MuJoCo を canonical runtime に昇格させる」ではない。あくまで「browser 用の visual renderer candidate として評価する」である。

## 2. 既存調査結果

### `#176` で確認できたこと

以下のqpos値は#176時点のhistorical evidenceである。current startup policyは
`docs/operations/r7-e-p22-neutral-initial-pose.md`を参照する。

- `assets/mujoco/fast_arm/scene.xml` は MuJoCo native viewer で正常に表示できた
- `home` keyframe は自然な下垂姿勢だった
- body / joint / site の接続は破綻していなかった
- default `qpos0` は `[0.0, -1.5707963267948966, 0.0, 0.0]`
- keyframe `home` は `[0.0, 0.0, 0.0, 0.0]`

### `#178` で確認できたこと

- official `@mujoco/mujoco` WASM PoC は isolated app として成立した
- browser 上で model / data / keyframe / `mjvScene.geoms` を扱えることが分かった
- MuJoCo geom transform は `Matrix4.fromArray()` ではなく `Matrix4.set(...)` で組み立てる必要があった
- coarse gray mass からは改善でき、link 構造が読めるところまで到達した
- ただし production viewer 置換には未達で、PoC-only 判定が妥当だった

### `#174` の扱い

- 既存 Three.js viewer の fast_arm mesh 手修正方針は close 済み
- STL local transform / quaternion basis を手で詰め続ける方針は、再現コストと保守コストに対して成果が弱かった
- 今後は MuJoCo scene API / WASM PoC の知見を使って viewer 方針を再設計する

### 現行実装から読めること

- `apps/mujoco-viewer/src/runtime/viewerSceneController.ts` は rendering-only の viewer scene controller であり、payload scene / DoF ring / fast arm mesh scene を同期している
- `apps/mujoco-viewer/src/types/transportPayload.ts` には `qpos` / `qvel` / `bodies` / `sites` / `target_position_m` が既にある
- `scripts/run_replay_mujoco_dry_run.py` は deterministic replay を NDJSON として出す入口である
- `scripts/run_replay_mujoco_websocket_publisher.py` は local/dev の WebSocket publisher 入口である
- つまり、browser には既に payload viewer の経路があり、WASM scene viewer は別の表示経路として考えるのが自然である

## 3. 基本方針

### 3.1 Python native MuJoCo remains source of truth

以下は Python native MuJoCo 側に残す。

- model load
- `qpos` / `qvel`
- IK / FK
- target command evaluation
- desired endpoint
- body / site pose generation
- target-tip error
- runtime dry-run
- websocket publisher
- metrics / evaluation

### 3.2 Browser WASM is visual renderer candidate only

browser 側の MuJoCo WASM は、当面は表示 fidelity の候補として扱う。

やってよいこと:

- `scene.xml` を browser で読む
- `home` keyframe / visual scene を browser で確認する
- `mjvScene.geoms` 由来の geom を描画する
- native viewer に近い visual rendering を目指す
- production viewer 候補として評価する

やってはいけないこと:

- browser WASM を runtime source of truth にする
- browser WASM 側で `qpos` を勝手に再計算する
- browser WASM 側の IK / FK を評価正とする
- Python backend と browser WASM の `qpos` が diverge する状態を許す

### 3.3 重要な前提

browser scene viewer が `qpos` を利用する場合でも、それは canonical state を作るためではなく、Python backend が出した状態を受け取って表示するためである。browser 側で state を補完・再推定し始めた時点で、source of truth がずれる。

## 4. Source of Truth 境界

この issue では境界を次のように固定する。

### Python native 側

- `mujoco_backend` が model / data を持つ
- `runtime` が composition root として `mujoco_backend` / `motion` / `kinematics` / `transport` を結線する
- `transport` が `MuJoCoState` を payload にする
- `qpos` / `qvel` / body pose / site pose / target-tip error は backend 側で確定する
- WebSocket publisher は payload delivery だけを担う

### Browser payload viewer 側

- `apps/mujoco-viewer` は rendering-only
- payload の body / site / target / error / metadata を観測する
- `qpos` は payload に含まれていても、scene の canonical source にはしない
- browser での smoke / debug / telemetry を担う

### Browser WASM scene viewer 側

- `@mujoco/mujoco` を使って model / scene を読む
- visual scene の fidelity を確認する
- native viewer に近い geometry / material / camera の見え方を評価する
- ただし Python backend の state を上書きしない

### 境界の禁止事項

- browser 側が state source になって Python 側を追い越すこと
- browser 側で再計算した `qpos` を canonical とみなすこと
- payload viewer と WASM viewer のどちらかが別の arm pose source of truth を持つこと

## 5. Viewer architecture options

### Option A: Existing WebSocket payload viewer を維持

内容:

- 現行 `apps/mujoco-viewer` を継続
- payload の bodies / sites / target / tip / error / rings を描画
- fast_arm STL mesh fidelity は future
- 中間発表では debug / telemetry viewer と割り切る

評価:

- 安定性: 高い
- 実装量: 少ない
- visual fidelity: 低〜中
- research demo suitability: 中
- risk: 低

### Option B: WASM scene viewer を別 viewer として併設

内容:

- `experiments/mujoco-wasm-viewer-poc` 系統を viewer app として整備する
- Python backend / websocket viewer とは別経路にする
- native visual parity 確認用 / demo visual 用に使う

評価:

- source of truth 二重化リスク: 中
- asset loading: 中
- `qpos` synchronization: 中〜高
- local development: 中
- CI / Vite / WASM delivery: 中〜高

### Option C: Existing viewer に WASM scene renderer mode を追加

内容:

- `apps/mujoco-viewer` に display mode を追加する
- `payload mode` と `wasm scene mode` を切り替える
- `@mujoco/mujoco` を production dependency に昇格する

評価:

- dependency risk: 高い
- UI complexity: 高い
- build complexity: 高い
- WASM delivery: 高い
- future maintainability: 中〜低

### Option D: 現行 Three.js mesh 手実装を継続

内容:

- `#174` の方向を継続
- `fastArmMeshes.ts` の transform / quaternion / local frame を手で詰める

評価:

- native viewer parity の難しさ: 高い
- transform 再現コスト: 高い
- maintenance risk: 高い

### 比較結論

Option D は原則非推奨とする。`#174` で繰り返し修正しても自然な表示に到達しなかったためである。

## 6. 推奨 architecture

現時点の推奨は次の三段階である。

### 短期

Option A を維持し、browser viewer は telemetry / target-tip debug viewer として使う。native MuJoCo viewer と WASM PoC を ground truth / visual parity 調査として参照する。

### 中期

Option B として WASM scene viewer を別 viewer として整備する。まずは `scene.xml + home keyframe` の visual parity を高める。production viewer にはまだ統合しない。

### 長期

Option C として existing viewer に WASM scene renderer mode を統合するか判断する。ただし production dependency 昇格条件を満たすまで実施しない。

### 推奨の理由

- Python native MuJoCo を source of truth として固定できる
- 現行 payload viewer の debug 価値を落とさない
- WASM PoC の知見を isolated に育てられる
- 早期に production viewer として結論を出し過ぎない

## 7. WebSocket payload viewer と WASM scene viewer の棲み分け

### Payload viewer

- runtime payload の監視
- frame / target / tip / error / body / site / metadata の確認
- websocket transport の検証
- lightweight browser smoke
- evaluation / debug に向く

### WASM scene viewer

- MuJoCo visual scene fidelity の確認
- mesh / geom / material / camera の確認
- native viewer parity の検証
- demo visual candidate
- production 採用には同期設計が必要

### 実務上の使い分け

- payload viewer は「状態が正しく流れているか」を見る
- WASM scene viewer は「MuJoCo の見え方が十分近いか」を見る
- 両者を同じ viewer に無理に押し込む必要はない

### qpos synchronization problem

WASM scene viewer を production に使う場合の最大リスクは `qpos` synchronization である。

- Python backend が `qpos` source of truth
- browser WASM も model / data を持つなら `qpos` を受け取る必要がある
- 現在の payload には `qpos` があるが、scene viewer でどう消費するかは別途設計が必要
- `qpos` を schema に正式追加し直すか、visual-only payload として扱うかを決める必要がある
- `qpos` なしで `mjvScene.geoms` を再現できるかは不明
- body/site pose payload と MuJoCo WASM model pose が二重化しないことを保証する必要がある

この issue では schema 変更はしない。qpos synchronization は次 issue の論点として切り出す。

## 8. Production dependency 昇格条件

`@mujoco/mujoco` は現時点では PoC-only とし、production dependency に上げるには少なくとも次を満たす必要がある。

- Windows local dev で安定して `npm ci` / build / dev server が通る
- Vite dev / build の両方で WASM `locateFile` が安定する
- `scene.xml` と STL assets が安定して読める
- native viewer と比較して視覚的に十分近い
- payload / qpos synchronization 方針が明確
- CI で壊れない
- dependency size / load time が許容範囲
- fallback がある
- production viewer に入れる価値が明確

追加で、次の条件も実務上は必要である。

- browser 側の state 管理が複雑化しすぎない
- `apps/mujoco-viewer` の rendering-only 境界を破らない
- 既存の payload viewer を壊さない
- experiments から production へ移すだけの再現性がある

## 9. 実装候補の分割

次 issue は次のように分けると切りやすい。

### Issue A: WASM scene viewer PoC hardening

目的:

- `#178` PoC を安定化する
- camera / material / lighting / floor / mesh presentation を native viewer に近づける
- screenshots は commit しない
- production viewer にはまだ統合しない

### Issue B: qpos synchronization design

目的:

- Python backend の `qpos` を browser WASM scene viewer に渡す方式を設計する
- schema 変更の要否を判断する
- payload viewer と WASM scene viewer の source of truth 境界を決める

### Issue C: viewer mode architecture

目的:

- `payload mode`
- `wasm scene mode`
- `hybrid diagnostics mode`

を設計する。

### Issue D: middle presentation visual path

目的:

- 中間発表で使う viewer を決める
- native viewer screenshot / WASM PoC / payload viewer の使い分けを決める

## 10. `#174` から salvage するもの / 破棄するもの

### salvage するもの

- header compact 化の知見
- coordinate convention 調査
- scene status card の情報整理
- visual smoke の acceptance 観点
- fast_arm 表示が難しいという negative result

### 破棄するもの

- STL mesh local transform を手で推定し続ける方針
- quaternion basis を手で詰め続ける方針
- `fastArmMeshes.ts` を production viewer の fidelity 解として扱う方針

### 補足

`#174` の失敗は無駄ではないが、再利用するのは「手修正の継続」ではなく「WASM scene parity を別経路で評価する」という判断材料である。

## 11. 中間発表までの現実的な採用方針

中間発表までに現実的なのは次である。

- 既定の production path は Option A の payload viewer のままにする
- 中間発表の補助資料として native viewer の結果を使う
- WASM PoC は visual parity の参考として使う
- ただし WASM scene viewer を production viewer として約束しない

実務上は、次の順で扱うのが安全である。

1. runtime / payload の正しさを payload viewer で確認する
2. native MuJoCo viewer で scene.xml の ground truth を確認する
3. WASM PoC で browser 表示の可能性を検証する
4. そのうえで Option B か Option C を判断する

この順序を崩して browser 実装を先に production 化すると、`qpos` 同期と asset 表示の両方で責務が曖昧になる。

## 12. リスク

- `@mujoco/mujoco` は experimental / PoC 前提であり、Windows support もまだ安定保証ではない
- WASM 配信は `locateFile` と Vite の dev/build 差分に依存する
- browser 側で MuJoCo scene を直接描画しても、native viewer と同じ camera / lighting / mesh fidelity が自動では得られない
- payload viewer と WASM viewer の責務が混ざると、source of truth が再び曖昧になる
- `qpos` synchronization を曖昧にしたまま production に入れると、表示は似ていても state の意味がずれる
- Option C を早くやり過ぎると、`apps/mujoco-viewer` の UI / build / dependency が重くなる

## 13. Acceptance Criteria

- `docs/design/mujoco-wasm-scene-renderer-design.md` が追加されている
- Python native MuJoCo / IK / FK / runtime が source of truth として明記されている
- browser WASM MuJoCo が visual renderer candidate に限定されている
- WebSocket payload viewer と WASM scene viewer の棲み分けが整理されている
- production dependency 昇格条件が明確である
- `#174` の manual STL fidelity 方針をどう扱うかが明確である
- 次の implementation issue が切れる粒度まで分解されている
- production 実装を含まない
- dependency 追加なし

## 14. 次 issue 案

### 次 issue 案 1

`WASM scene viewer PoC hardening`

- `#178` の PoC を安定化する
- camera / lighting / material / floor / framing を詰める
- production viewer にはまだ入れない

### 次 issue 案 2

`qpos synchronization design`

- browser scene viewer に backend `qpos` をどう渡すかを決める
- schema 変更が必要かを判断する
- divergence を防ぐ条件を定義する

### 次 issue 案 3

`viewer mode architecture`

- payload mode
- wasm scene mode
- hybrid diagnostics mode

を切り分ける。

### 次 issue 案 4

`middle presentation visual path`

- 中間発表で何を表示するかを決める
- native viewer / WASM PoC / payload viewer の役割分担を固定する

### 推奨の分割順

1. qpos synchronization design
2. WASM scene viewer PoC hardening
3. viewer mode architecture
4. middle presentation visual path

qpos を曖昧にしたまま mode 設計に進むと、表示系の責務境界が再び崩れるため、まず同期方針を固めるのがよい。
## 2026-06-19 update

`#185` で `experiments/mujoco-wasm-viewer-poc` の WASM scene renderer を `apps/mujoco-viewer` の product viewer に昇格した。以後の default route は `wasm-scene` であり、旧 Three.js 手実装 renderer は default production path から外れている。
`#186` の follow-up で旧 viewer 専用の renderer / runtime / view model / tests は削除済みで、default product viewer からは参照されない。
> Historical status: the executable PoC described by this design was retired by
> #385 after promotion. Its technical outcome and chronology remain evidence;
> current operation and fixture generation belong to `apps/mujoco-viewer`.
