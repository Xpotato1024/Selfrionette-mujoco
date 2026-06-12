# Motiveのデータを受信し関節角へ変換して、OSCで投げるプログラム

# Brief
1. Motive上でrigidbodyと定義された上腕(ID: 1)と前腕(ID: 2)のデータを受信する
2. 前腕と上腕のrigidbodyの姿勢(角度)から、高速マニピュレータの関節角を計算
    - いわゆるIKを解いているわけではないので注意
3. 関節角データをOSCで送信する（Address: "/armR", data: {float, float, float, float}）

# Contents
- mocap2joint.py
  - 実行コード
- NatNetClient.py
  - 公式のNatNetSDKのサンプルコードの改変
  - UDPでMotiveと通信するクラス
- arm_communicator.py
  - OSCを使って
- geometry.py
  - デバッグ用のutils

# Environment
- OS : Windows 11 Pro
- Python 3.11.3

# Setup
## 必要パッケージのインストール  
```bash
$ pip install -U pip
$ pip install numpy scipy
$ pip install matplotlib
$ pip install pyquaternion
$ pip install python-osc
```

# Run
- Motiveを起動しているPC上で実行する
  - 実行後、デバッグ用のMatplotlibのGUIが表示される
```bash
$ python get_mocap.py
```
- Local PCとServerのIPを指定することも可能
  - コマンドライン引数で`[Local IP] [Server IP]`の順に渡す  
  - 例 : `python get_mocap.py 192.168.11.32 192.168.11.234` 