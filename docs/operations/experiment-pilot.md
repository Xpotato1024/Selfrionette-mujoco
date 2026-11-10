---
status: canonical
owner: operations
last_verified: 2026-11-10
canonical_for:
  - S/Gと画面力表示の4条件自己pilotの準備・試行対応・再解析手順
related:
  - docs/contracts/finite-trial-runtime.md
  - docs/contracts/selfrionette-device-input.md
  - docs/architecture/research-execution-roadmap.md
  - docs/operations/unified-cli.md
---

# 4条件の自己pilotを準備・記録・集計する

`xpotato-sim experiment`は、S-rate / G-rate × 画面力表示ON / OFFの条件と順序を準備し、Workbenchで保存した試行を対応付けて再解析する入口である。条件準備だけでは入力装置へ接続せず、試行も開始しない。**準備 → Workbenchで各条件を実行 → 保存試行を対応付け → 集計**の順で進める。

研究範囲は[研究実行ロードマップ](../architecture/research-execution-roadmap.md)に従う。追加の力覚提示デバイス開発は凍結している。画面の力表示は比較対象として残す。押圧再現と強弱判断のどちらを使うか、主指標、成功閾値、反復数、待機・練習・休止規則は未確定であり、このCLIは採択しない。

## 1. 実行前に揃えるもの

準備済みのPython環境と対応するproduction Viewer buildを使う。環境準備は[root README](../../README.md)、Deviceの校正・接続設定は[Device入力契約](../contracts/selfrionette-device-input.md)を参照する。

| 入力 | 内容 |
|---|---|
| Gamepad条件JSON | Workbenchからexportした`workbench-condition/v1`。providerは`gamepad/v1`、Mappingは`viewer_keyboard_gamepad_mapping/v1` |
| Selfrionette条件JSON | 同じモデル・ばね・Task・予算を使うexport。providerは`selfrionette-device/v1`、Mappingは`normalized_endpoint_velocity/v1`。実物から確認した個体・校正・指軸対応を使用 |
| Device接続設定 | 既存bridge executable、port、校正profileの絶対path。条件JSONとは別の個人用file |
| 手順メモ | 課題、目標、基準提示、待機、練習、休止、回答方法、未確定事項を記した版 |
| 実行revision | 条件準備とWorkbenchへ同じ値を渡す。未commit変更をclean HEADと偽らない |

同梱の[比較条件例](../../profiles/experiments/simulation-comparison/README.md)は、Gamepadの速度係数が0.1 m/s、Selfrionetteが0.02 m/sであり、そのまま同一速度の比較にはならない。`prepare --speed-m-s`で共通係数を明示する。Selfrionetteの同梱identityは合成fixtureで、実物の校正・識別値として使えない。

prepareはモデル、scene、Task、Evaluation、制御周期、左右対応、有限予算、command Mapping、表示縮尺等の共通条件を照合する。S側はworld座標に限定し、各出力軸の重みの絶対値和が1以下であることを要求する。重みや校正値を自動修正しない。G/Sの単軸速度係数を指定値に揃え、Sの速度norm上限をその√3倍にする。Gの変位上限がこの範囲を切り詰める場合は拒否する。同じ係数でも、装置固有の前処理・入力応答まで等しいと証明したことにはならない。

## 2. 条件と試行順を準備する

以下はWindows PowerShellの例。repository rootで実行する。先に、上記の実物条件を`%LOCALAPPDATA%/Xpotato-Sim/pilot-source/`へ`gamepad.json`、`selfrionette.json`、`device-connections.json`、`protocol.md`として保存する。氏名を含まないIDを使い、出力先はまだ存在しないdirectoryを指定する。

```powershell
$pilotSource = Join-Path $env:LOCALAPPDATA 'Xpotato-Sim/pilot-source'
$pilotPlan = Join-Path $env:LOCALAPPDATA 'Xpotato-Sim/pilots/P001/S001'
$pilotResults = Join-Path $env:LOCALAPPDATA 'Xpotato-Sim/results/P001/S001'
$pilotTemp = Join-Path $env:TEMP 'xpotato-sim-pilot'
New-Item -ItemType Directory -Force -Path $pilotResults, $pilotTemp | Out-Null
$pilotRevision = Read-Host '実行sourceのrevision（未commit変更があればそのidentityも含める）'
$pilotSpeed = [double](Read-Host '予備確認で選んだ共通速度係数 [m/s]')
$pilotRepetitions = [int](Read-Host '4条件を実施する反復数 [1..100]')
$pilotOrderRow = [int](Read-Host '順序の開始行 [0..3]')
$pilotProtocol = Join-Path $pilotSource 'protocol.md'
uv run xpotato-sim experiment prepare `
  --gamepad-condition (Join-Path $pilotSource 'gamepad.json') `
  --selfrionette-condition (Join-Path $pilotSource 'selfrionette.json') `
  --output $pilotPlan --participant-id P001 --session-id S001 `
  --repetitions $pilotRepetitions --order-row $pilotOrderRow `
  --speed-m-s $pilotSpeed --software-revision $pilotRevision `
  --protocol-note $pilotProtocol
```

`--protocol-note`は空でない記述を保存する。指定先の文書を読み込んだり、hashで固定したりはしないため、メモ自体の版も保管する。人数・反復数・速度に研究上の推奨値は設けていない。

出力は`g_off.json`、`s_off.json`、`g_on.json`、`s_on.json`と、最後に公開する`session.json`である。`session.json`に条件fileのSHA-256、意味条件、匿名ID、実行revision、予定slotが保存される。準備途中のfileだけが残り、`session.json`がない場合は準備未完了である。再準備では新しい出力先を使う。

| 開始行 | その反復内の順序 |
|---|---|
| 0 | G/OFF → S/OFF → S/ON → G/ON |
| 1 | S/OFF → G/ON → G/OFF → S/ON |
| 2 | G/ON → S/ON → S/OFF → G/OFF |
| 3 | S/ON → G/OFF → G/ON → S/OFF |

反復ごとに次の行へ進む。4行全体で位置と直前条件を釣り合わせる設計であり、一人が1行だけ実施して順序効果を相殺できたとは扱わない。予定の確認は次のとおり。

```powershell
$pilotSessionFile = Join-Path $pilotPlan 'session.json'
$pilotSession = Get-Content -Raw $pilotSessionFile | ConvertFrom-Json
$pilotSession.trials | Format-Table slot, repetition, order_row, condition_id
```

### 合成入力だけで準備する場合

同梱条件を使うソフトウェア確認では`--software-fixture`を必ず指定する。次の0.02 m/s、1反復、開始行0はコマンド確認の例で、実操作者の採択条件ではない。

```powershell
$softwarePlan = Join-Path $env:TEMP 'xpotato-sim-software-pilot-01'
uv run xpotato-sim experiment prepare `
  --gamepad-condition profiles/experiments/simulation-comparison/gamepad-no-force-cue.json `
  --selfrionette-condition profiles/experiments/simulation-comparison/selfrionette-fixture-no-force-cue.json `
  --output $softwarePlan --participant-id software_fixture --session-id software_01 `
  --repetitions 1 --order-row 0 --speed-m-s 0.02 `
  --software-revision software-validation-only `
  --protocol-note '合成入力の確認専用。研究条件と実機受入は未確定。' --software-fixture
```

`usage`はこの場合`software_validation`、通常は`operator_pilot`となる。既知のfixture identityをoperator用へ持ち込むことは拒否するが、任意に書いた別identityの実在性を認定する機能ではない。`readiness.hardware_verified`と`research_protocol_frozen`は常にfalse、追加力覚提示装置は`frozen`である。これらを手書きで認定済みに変更すると読込みを拒否する。

## 3. Workbenchで予定slotを実行する

前節の実操作者用sessionで、最初のslotの条件を選んで起動する。実際の入力装置を接続・操作できる状態で行う。Device設定を指定しても起動時にはserial接続やtareを自動実行しない。

```powershell
$pilotFirst = $pilotSession.trials[0].condition_id
$pilotFirstFile = Join-Path $pilotPlan $pilotSession.conditions.$pilotFirst.file
uv run xpotato-sim workbench --condition $pilotFirstFile `
  --device-config (Join-Path $pilotSource 'device-connections.json') `
  --temporary-root $pilotTemp --result-root $pilotResults `
  --software-revision $pilotRevision --open-browser
```

1. 開いた操作ページで操作権を取得し、モードを**実験**へ切り替える。初期のデモモードは記録を保存しない。
2. slotの条件JSONを確認し、「検証・準備」を実行する。S条件では個体確認・接続、無荷重tare、使用姿勢neutral、profile適用をそれぞれ確認する。
3. sceneの準備完了後に「操作画面へ」を選び、「開始」する。各試行の新しい中立入力から進む。
4. 終了または「停止を要求」の後、保存完了とtrial IDを確認する。次節のattachで、そのIDを現在slotへ対応付ける。
5. 次slotのJSONをimportし、実験モードのまま検証・準備をやり直す。条件は実行中に変更しない。S条件の再準備では表示されたDevice準備を再確認する。

CLIは予定を自動実行せず、次slotへの自動切替や回答取得を行わない。Taskの観測時間満了や`task_success`だけで、押圧再現・強弱判断の成功とは判定しない。予定条件を途中で編集したtrialはattachの意味条件照合を通らないため、条件変更が必要なら理由を記録して別sessionを準備する。

operator用のattachはproduction Viewerとlive入力来歴を要求し、headless・dev表示・合成入力を実操作者結果へ混ぜない。analyzeでも予定slotの意味条件・revision・来歴を再照合し、linkを別条件のslotへ書き換えた記録を受理しない。この検査は機器校正、操作性、正式な研究Task成立の認定ではない。

## 4. 保存したtrialをslotへ対応付ける

保存完了したtrial directoryを指定する。元trialのfileは変更せず、session側の`records/slot-NNN-attempt-NNN.json`へ対応を追加する。**同じsessionへのattachは一つずつ実行する。** 複数processからの同時attachを調停するlockは提供しない。

```powershell
$pilotSlot = [int](Read-Host '実行したslot番号')
$pilotTrialId = Read-Host '保存完了したtrial ID'
uv run xpotato-sim experiment attach --session $pilotSessionFile `
  --slot $pilotSlot --trial-directory (Join-Path $pilotResults $pilotTrialId)
```

記録が完了していれば、`operator_abort`、timeout、`technical_invalid`等も対応付けられる。成功試行だけを残さない。保存が不完全で照合できないtrialはattachできないが、元directoryを保持してanalyzeの不完全一覧へ残す。

同じslotを再試行する場合は、前のattemptの対応付け後に`--attempt 2 --retry-reason '再試行した理由'`を追加する。attemptは連番とし、前の結果は上書きしない。同じtrialを別slotや別attemptへ重複登録できない。再試行を新しい参加者として数えない。

`--response <回答JSON>`で推定値、自信、提示・回答区間等を任意のJSON objectとして添付できる。上限は8 KiBで、項目の単位・尺度・正解・採点法はCLIが決めない。回答方法を手順メモへ定義し、回答の欠落と0を区別する。添付した回答はanalysis JSONへ保持されるが、自動採点・主観尺度集約は行わない。

## 5. 全試行を検査・集計する

Workbenchが保存を終え、attachが完了してから実行する。出力は新しいdirectoryだけを受け付ける。

```powershell
$pilotAnalysis = Join-Path $env:LOCALAPPDATA 'Xpotato-Sim/analysis/P001/S001-01'
uv run xpotato-sim experiment analyze --result-root $pilotResults `
  --session $pilotSessionFile --output $pilotAnalysis
```

result rootの直下にあるtrial directoryを全件読む。単一trial directoryも指定できる。再帰探索はせず、1回の上限は1,000 trialである。sessionを指定しても未対応trialを黙って除外せず、次の一覧を出す。

| field | 内容 |
|---|---|
| `missing_linked_trial_ids` | linkがあるが、この解析対象内で検証済みとして確認できないtrial |
| `unlinked_trial_ids` | 保存は整合しているが、このsessionにattachされていないtrial |
| `unattempted_slots` | まだ1件もtrialがattachされていない予定slot |
| `session_linkage_complete` | 上の3一覧が全て空ならtrue、残っていればfalse。session未指定ならnull |

ここでslotの対応完了は課題成功を意味しない。中断や失敗のtrialを対応付けたslotもattempt済みとなる。再試行の採否・除外理由は手順に従い、保存した全attemptから確認する。

| 出力 | 内容 |
|---|---|
| `analysis.json` | 条件・来歴・Task分類・停止理由・指標・回答・不完全一覧。最後に公開する解析完了marker |
| `trials.csv` | 全directoryの一覧。不完全・不正も理由付きで1行残す |
| `series/trial-NNNN.csv` | 保存tickごとのばね変位・速度・復元荷重・減衰荷重・軸荷重。ばね測定がない試行では作らない |
| `figures/trial-NNNN.png` | ばね変位と荷重の時系列。`--no-plots`で省略できる |

整合した記録は`verified`、不完全・不正は`invalid_or_incomplete`となる。`verified`は保存整合性の判定で、Task成功ではない。Task失敗や中断も整合していればverifiedに含む。CLIは不完全・不正または`session_linkage_complete=false`があればexit 1を返す。sessionなしの解析では対応完了判定はnullであり、整合した失敗・中断だけならexit 0になる。集計fileが出ていても件数と理由を確認する。

`analysis.json`はpendingへの書込み、flush/fsync、read-backの一致確認後に排他的に公開する。CSVや図だけで`analysis.json`がない出力は、解析処理が完了していない。

`participant_count`は、検証済みtrialへ結び付いた匿名participant IDの異なり数であり、反復・attempt数ではない。`software_validation`では必ず0とし、合成fixtureのID数は`software_fixture_id_count`に分ける。operator用IDの数も、参加者が実在したことや手続きに適合したことの外部証明ではない。

保存参照、SHA-256、trial/epoch/条件/revision、tickの連続性、時計、状態・物理観測のidentityを照合する。**hash照合は電子署名や外部証明ではなく、全fileを作り替えた記録の真正性を保証しない。** 元データの保全と取得状況の記録は別に必要である。

### ばね復元荷重の誤差を計算する場合

`--spring-object`、`--target-force-n`、`--window-start-s`、`--window-end-s`を全て明示する。対象は保存したばね復元荷重`kq = -restoring_force_n`であり、接触力や指先入力力ではない。選んだ課題でこの量を評価する場合だけ使い、対象object、目標、区間は結果を見る前に手順へ定める。

区間はsimulation秒で開始を含み、終了を含まない。保存されたcontrol commitの最終substep観測からMAE、符号付きbias、目標超過の最大値を計算する。試行が区間終了前に終わった場合や対象sampleが欠けた場合は`unavailable`と理由を残し、0で補わない。

`kq`、`kq + cv`、contact solverの接触力、指先入力のN校正は別量である。接触原力の全接触点peakは対象以外の接触も含む。対象手先・物体別の集計はanalysis JSONの`metrics.target_contacts`を確認する。保存tick間のpeakやsubstep中の最大衝撃、描画が実際に見えた時刻、人体の知覚をこれらの値から推定しない。

## 6. 変更・再開の扱い

sessionやtrialを手書き修正して整合検査を通さず、条件・revision・手順を変える場合は新しいsessionを作る。保存失敗や再試行の元fileを残し、原因と再開点を記録する。計測と課題が成立しているかの判断、主指標の採択、実装変更後の実入力受入はこの手順の外側で行う。ソフトウェア準備の完了を、自己pilotや本実験の実施済み記録に置き換えない。
