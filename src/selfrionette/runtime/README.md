# runtime

## 責務

唯一の composition root。複数層を結線してよい唯一の場所。

## 入力

config、選択された input source / interpreter / motion generator /
MuJoCo backend / transport。

## 出力

実行ループと結線済み pipeline。

## 依存してよい層

すべての層。

## 依存してはいけない層

なし。ただし各層が runtime に依存してはいけない。

## 禁止事項

層の中身の責務を runtime に吸収しない。runtime は結線と lifecycle 管理に限定する。

## 今後 stub を置く予定のファイル名

`config.py`, `pipeline.py`, `main_mujoco_server.py`
