# schemas

## 責務

層間契約を定義する。`RawInputFrame`、`InputIntent`、`TargetCommand`,
`JointCommand`、`MotionCommand`、`MuJoCoState`, `RenderState` などを置く予定。

## 入力

なし。schemas はどの層にも依存しない。

## 出力

各層が参照する immutable な contract 型。

## 依存してよい層

なし。

## 依存してはいけない層

すべての実装層。

## 禁止事項

処理ロジック、MuJoCo 操作、通信、表示、入力読み取りを持たない。

## 今後 stub を置く予定のファイル名

`input_frame.py`, `input_intent.py`, `target_command.py`, `joint_command.py`,
`motion_command.py`, `mujoco_state.py`, `render_state.py`
