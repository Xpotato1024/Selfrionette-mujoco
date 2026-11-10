---
status: historical
owner: runtime
last_verified: 2026-11-10
canonical_for: []
related:
  - docs/operations/experiment-pilot.md
  - docs/contracts/finite-trial-runtime.md
  - docs/contracts/object-scene-contact-diagnostic.md
  - profiles/experiments/simulation-comparison/README.md
  - tests/runtime/test_trial_analysis.py
  - tests/plugins/tasks/contact_observation_task/test_contact_observation.py
---

# 実験準備の保存・解析統合と60秒ソフトウェア検証

## 対象と証拠の範囲

2026-11-10に、4条件の準備、実MuJoCoによる有限試行、sessionへの対応付け、保存検査、CSV・PNG出力を確認した。
別に、60秒の中立入力、5秒押込後の55秒中立保持、60秒を上限とする持続過入力を確認した。
すべて合成入力と合成単調clockを使うsoftware fixtureであり、参加者・実Gamepad・実Device・serial・物理出力は使用していない。
実時間の入力遅延、RTF、実機性能、操作者の押圧再現成績を測定した結果ではない。
現在の実行手順は[自己pilotの操作手順](../operations/experiment-pilot.md)、保存契約は
[有限試行の正本](../contracts/finite-trial-runtime.md)を参照する。

### ソースと実行環境

baseは`d3e667b461ff0d795c03afb9bbe43fc7c68201da`（PR #639のmerge後）で、
実行時は`codex/experiment-readiness-20261110`の未commit working diffを含む。
差分にはstrict reader、pilot session・export・CLI、既存信号の保存、観測期間の丸め修正を含む。
base単体やclean commitでの実行と扱わない。

| 項目 | 記録値 |
|---|---|
| OS / Python | Linux x86_64 / Python 3.12.14 |
| 数値・描画依存 | MuJoCo 3.9.0、NumPy 2.4.6、Matplotlib 3.11.0 |
| 環境準備 | `uv sync --locked`で用意したrepositoryの`.venv` |
| `uv.lock` SHA-256 | `440e17b22b34bea614d45c05baaf7f1268bd51880c887b8c502f3551ba1bf6a2` |
| 4条件・中立60秒の`software_revision` | `software-fixture-experiment-readiness-d3e667b-plus-uncommitted-20261110` |
| 5秒押込・55秒中立の`software_revision` | `software-fixture-contact-hold-working-readiness-20261110` |
| 持続過入力の`software_revision` | `software-fixture-working-readiness` |
| 4条件・中立60秒harness SHA-256 | `890de627fae5bdc93e37da74f34a1ad9b748c2562d176282d4ad87aea32d87f8` |
| 5秒押込・55秒中立harness SHA-256 | `992990b99d241129bed47be4ef04c480a61a432a1f3d2a2b1fcbace543996d85` |
| 修正後Task実装 SHA-256 | `d3fd4a6559581cfa3e65c752cc487b6f9667367105155796186e5e3c319159ad` |
| 修正後source manifest SHA-256 | `686b48f1164bfdf5447b42a87e522776124f92f94a4ed0b29bf343e813b1289b` |

修正後のharnessは全`src/**/*.py`と利用する2件のtest helper、合計316ファイルのSHA-256を開始・終了時に保存した。
4条件・中立60秒の再実行と5秒押込・55秒中立は同一manifestで、実行中のsource変更は0件だった。
このmanifestによる固定確認は修正後の2実行に対するものであり、それ以前の持続過入力へ遡及しない。
一時harness・生成結果をrepositoryへ追加せず、このnoteに条件・identity・観測を残す。

## 共通モデル・時刻・入力条件

`tasks/research-spring`、`single_original/v1`、`compression_spring`、対象`cube`、手先`arm`を使った。
物理出力は`disabled`、Viewerは`headless`、Taskは`contact_observation_task/v1`、期間は60秒である。
ばねのworld軸は−Y、剛性100 N/m、減衰2 N s/m、初期変位・速度0、設定範囲0〜0.05 m。
設定範囲はMuJoCoのsoft制約であり、変位を50 mm以下へ切り詰めるhard limitとは扱わない。

controlは1/60 s、native physicsは1/600 sで1 control tickあたり10 substep。
`implicitfast` / `Newton` / 50 iterations / tolerance `1e-10`を使い、
joint speed上限10 rad/s、tracking error上限0.75 radを維持した。
input age上限0.2 s、入力待機5秒、準備30秒、wall予算360秒も維持した。
wall clock自体が合成値なので、記録されたwall経過時間を実処理時間やRTFの根拠にしない。

最初に新しい中立sampleを与え、開始gateを通した後も毎tick新しいsequence・timestampのsampleを供給した。
Gは`tests/runtime/test_trial_runner.py::message`、Sは
`tests/runtime/test_device_force_integration.py::device_message`の既存fixtureを使う。
Sのroleは`left`、sessionは2147、sequenceは`81 + tick`、source ageは2 ms。
個体ID・校正record・operator等は同梱fixtureの合成identityである。

## 4条件の準備からCSV・PNGまで

入力元は`profiles/experiments/simulation-comparison/`の
`gamepad-no-force-cue.json`と`selfrionette-fixture-no-force-cue.json`。
コピーの`max_ticks`を360へ変更し、`experiment prepare`へ
`--software-fixture --speed-m-s .02 --repetitions 1 --order-row 0`を明示した。
participant IDには`fixture-only`、session IDには`integration-20261110`を使った。
凍結済みの4 slotは`g_off → s_off → s_on → g_on`の順で各1回実行した。

Gの`gamepad_speed_m_s`は0.02 m/s、Sの`speed_m_s`は0.02 m/s、
準備後のSの`max_speed_m_s`は`√3 × 0.02 = 0.034641016151377546` m/sだった。
Gは全360 tickでaxes `(0.8, 0, 0, 0)`、Sはcommand・normalized
`(0, -0.8, 0, 0, 0, 0, 0)`、第2channelのみactiveとした。
Gのdeadzone 0.1等は残しており、同じgainをG/Sの入力伝達特性や軌道の同一性とは扱わない。

CLIはprepare 1回、attach 4回、4条件のanalyze 1回、中立60秒のanalyze 1回、計7回すべてexit code 0。
4条件exportは`verified_count=4`、`invalid_or_incomplete_count=0`、
`participant_count=0`、`software_fixture_id_count=1`、`session_linkage_complete=true`だった。
不足trial、未対応trial、未実行slotはいずれも0件。試行表CSV、時系列CSV 4件、PNG 4件を作成した。
session、condition、trial、terminal hashの対応を検査してから集計している。

| 条件 | tick数 / 論理秒 | 最大ばね変位（m） | 全記録接触点の最大力ノルム（N） | 終了理由 |
|---|---|---|---|---|
| G / OFF | 360 / 6.0 | 0.02340776359991507 | 2.3731495542787115 | `simulation_budget` |
| G / ON | 360 / 6.0 | 0.02340776359991507 | 2.3731495542787115 | `simulation_budget` |
| S / OFF | 360 / 6.0 | 0.025190303931670186 | 2.5534804666318487 | `simulation_budget` |
| S / ON | 360 / 6.0 | 0.025190303931670186 | 2.5534804666318487 | `simulation_budget` |

6秒で打ち切る条件に対しTask期間は60秒のままであり、Taskは4件とも
`failure / aborted / execution_budget_exhausted`として残る。CLIの成功と研究課題の成功を混同しない。
exportの力誤差計算には、ソフトウェア計算確認としてばね対象`cube`、目標1 N、window `[0.05, 6)`秒を指定した。
canonical tick時刻で357 sampleが選択された。この目標・windowは研究の押圧課題や成功閾値を採用したものではない。
対象量`kq`は接触力や指先入力力と区別する。

### 提示ON/OFFの独立性

各入力方式内で360 tickの保存列を比較した。除外したのは試行ごとのtrial・epoch・condition identityと
`force_presentation_v1`だけで、qpos/qvel、入力identity、geometry、dynamics、Task、その他の保存信号を丸めていない。
そのcanonical byte列はG・SともON/OFFで完全一致した。GとSの相互一致は判定していない。

| 比較 | 共通byte数 | 共通SHA-256 |
|---|---|---|
| GのON/OFF | 1,761,614 | `42864392d0f6a7ecbfdbfe0fb3c7c8a6f1b45584afbd0f37489b0d9e4af48526` |
| SのON/OFF | 1,757,352 | `7b6df14e42ee71859e80f8422907a2e46359cf7e6c78ac294009404d9ae2afab` |

## 中立60秒と期間境界の修正

最初のG中立試行は、3,600 tickで論理時刻60.0秒へ到達した一方、native時刻が
`59.99999999996167`秒になり、厳密な`native_time >= 60`比較を満たさなかった。
そのため`simulation_budget / failure / execution_budget_exhausted`として保存された。
初回JSONLは23,261,632 byteで、記録破損ではなく期間完了判定の丸め不具合だった。

Taskの期間到達比較だけに`min(1 ns, duration_s × 10⁻⁹)`の絶対許容差を追加した。
生時刻は書き換えず、時刻逆行・scene不一致・先行する明示STOPの優先を維持した。
2 ns不足・1 tick不足を完了扱いしないこと、極短期間が時刻0で完了しないことも直接回帰で確認した。
修正前の再現testは失敗し、修正後はTask・ばね・strict readerの関連67 testsが通過した。

再実行はG / OFF、`max_ticks=3600`、全tick中立で、3,600 tick・入力3,601 sampleを保存した。
論理時刻60.0秒、生native時刻`59.99999999996167`秒のまま
`task_success / success / completed`、理由`observation window completed; not contact success`となった。
JSONLは**23,261,700 byte**。strict readerで全artifact chainを検査し、CSV・PNGのexportも
`verified_count=1`、`invalid_or_incomplete_count=0`で完了した。
無接触でばね変位0の観測期間完了であり、押圧再現・抵抗判断の課題成功ではない。

## 5秒押込後の55秒中立保持

中立のみの完走では接触後の保持を確認できないため、準備済みS / OFF条件から`max_ticks=3600`だけを変更した。
gain 0.02 m/s、上限`√3 × 0.02` m/sを維持し、第1〜300 tickは新規の−0.8 Y入力、
第301〜3,600 tickは新規の中立入力を与えた。中立は入力を停止する意味ではなく、更新済みのゼロcommandである。
MuJoCo stateや目標位置を直接書き換えていない。

| 観測項目 | 結果 |
|---|---|
| 終了 | 3,600 tick、論理60.0秒、`task_success / success / completed`、`error=null` |
| 生native時刻 | `59.99999999996167`秒 |
| 入力・欠測 | 3,601 sample、欠測0 |
| 最大ばね変位 | 0.014690677017517726 m |
| 最終記録tickのばね変位 | 0.013684203700997072 m |
| 全記録接触点の最大力ノルム | 1.4840193435924163 N |
| 対象接触を記録したtick数 | 3,378 |
| 最終記録tickの接触力ノルム | 1.3684203700997064 N |
| JSONL容量 | 29,132,135 byte |

strict readerで保存の整合性を確認し、最終tickにも対象接触が残った。
この1本の合成軌道で接触後の中立保持と記録が成立した証拠であり、操作者による全軌道の安定性や操作性を保証しない。

## 持続過入力の停止も保存

別のsoftware stressでは、`tasks/research-spring`の既存S fixtureを使い、
gain 0.02 m/s・上限0.05 m/s・`max_ticks=3600`を設定した。
開始中立の後、毎tick新規のcommand・normalized `(0, -0.8, 0, 0, 0, 0, 0)`を入力した。
4条件prepare後のS上限とは異なるため、同一条件の追加反復には数えない。

2,255 tickをcommitした後、論理時刻`37.583333333333336`秒で
`technical_invalid`、`ValueError:dynamic joint speed budget exceeded`により停止した。
Taskの保存分類は`failure / aborted`、reasonは`technical_invalid`である。
JSONLは**17,991,438 byte**、最大ばね変位は**0.05694070978255461 m**、
全記録接触点の最大力ノルムは**40.852277464486356 N**だった。
入力は2,257 sampleで、最後の停止へ至った入力も含む。strict readerで原artifact chainを検証できた。

この失敗を集計から削除せず、観測期間完了や操作者の課題失敗へ読み替えない。
50 mmのsoft制約超過をそのまま記録しており、hard limitの成立や無制限の連続押込安定性を主張しない。
停止を回避するためのjoint speed・tracking error・接触・ばね閾値の緩和は行っていない。

### 60秒系記録のidentity

| 試行 | trial ID | condition SHA-256 | terminal SHA-256 |
|---|---|---|---|
| 修正後G中立 | `b4f098afedee4b49bbf0623456e2fcef` | `e0a6e0d88d131c0f7b95938f682a35f711764f87a920e4f9a86a13bc88658cbf` | `ef57b1a72d6cecfc83557be9a831717db6b84ef40790b25c105203c256e7f0c8` |
| S 5秒押込・55秒中立 | `c23a65c856f444ef8e6db8e5e10d93fd` | `c941e249e1549b638ef404028680af5d7764583ac923179ae49974318badf602` | `77ecb8f4a2b91baac4b9fa11acce24d7d126ebe25ee0c04cf229cd57ef54a94c` |
| S持続過入力 | `1af55e5d37964e2691344324f36f7b73` | `f39b15cf70f43fd89d02a897d1c13d17e05a35d88a89b9e06993914295489122` | `9187d91ce2e513b81503d0ba8f1611dc971c053f38a6a0d5e14e2f5409815add` |

## 移植可能な有限再現例

repository rootのdev環境で実行する。`MODE`を`neutral`、`hold`、`stress`から選び、
それぞれG中立60秒、S 5秒押込・55秒中立、S持続過入力を構成する。
既存test helperからfresh入力を作り、正式`TrialRunner`へ渡す。
実行ごとに新しい一時保存先・trial ID・provenanceができるため、上表のterminal hashやbyte数そのものの再生成は目的にしない。
sessionの準備・attach・exportの運用は[自己pilot手順](../operations/experiment-pilot.md)を参照する。

```sh
.venv/bin/python - <<'PY'
import json
from math import sqrt
from pathlib import Path
from tempfile import mkdtemp
from tests.runtime.test_trial_runner import Clock, message
from tests.runtime.test_device_force_integration import device_message
from xpotato_sim.runtime.experiment.edited_condition import preset_condition, resolve_condition
from xpotato_sim.runtime.experiment.trial_runner import TrialRunner
from xpotato_sim.runtime.experiment.trial_analysis import load_validated_trial

MODE = "neutral"  # neutral / hold / stress
assert MODE in {"neutral", "hold", "stress"}
provider = "gamepad/v1" if MODE == "neutral" else "selfrionette-device/v1"
document = preset_condition("tasks/research-spring", input_provider=provider)
document["limits"]["max_ticks"] = 3600
mapping = document["configuration"]["mapping"]["parameters"]
if MODE == "neutral":
    mapping["gamepad_speed_m_s"] = .02
else:
    mapping.update(speed_m_s=.02, max_speed_m_s=sqrt(3) * .02 if MODE == "hold" else .05)
profile, limits, _ = resolve_condition(document)
root = Path(mkdtemp(prefix="xpotato-software-"))
clock = Clock()
runner = TrialRunner(result_root=root, software_revision="software-fixture-note-replay", clock=clock)
try:
    ticket = runner.prepare(profile, limits)
    runner.start(ticket, input_provenance={"source": MODE, "participant_data": False,
                                          "hardware_acceptance": False})
    for tick in range(3601):
        clock.sleep(.02 if tick == 0 else profile.dt_s)
        if MODE == "neutral":
            wire = message(tick)
        else:
            raw = device_message("left", tick)
            moving = tick > 0 and (MODE == "stress" or tick <= 300)
            values = [0., -.8 if moving else 0., 0., 0., 0., 0., 0.]
            raw["event"].update(command=values.copy(), normalized=values.copy(),
                                active=[False, moving, False, False, False, False, False])
            wire = json.dumps(raw)
        runner.ingest(ticket, wire, received_at_s=clock())
        runner.advance(ticket)
        if runner.status != "running":
            break
    assert runner.status == "terminal", (runner.status, runner.error)
    verified = load_validated_trial(root / ticket.trial_id)
    result = verified.analysis()
    print(root / ticket.trial_id)
    print(json.dumps({key: result[key] for key in
        ("condition_sha256", "runner_stop_reason", "error", "task_outcome", "metrics")}, indent=2))
finally:
    runner.close()
PY
```

## 解釈と残る受入

保存・対応付け・解析の正常系、提示ON/OFFの物理独立性、60秒の中立および限定した接触保持、
過入力時の停止記録までをsoftwareとして確認した。
`task_success`は保存された観測Taskの分類で、目標力の再現成功やcueの有効性ではない。
研究上の対象force、target、評価window、成功閾値、実Deviceの個体・校正・原点・方向・実操作は、この証拠から決定しない。
正式研究条件と実機受入をfreezeする際も、software fixtureと参加者数を分離し、
failure・abort・technical-invalid・incompleteを隠さず保持する。
