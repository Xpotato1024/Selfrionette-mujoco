---
status: historical
owner: operations
last_verified: 2026-07-16
canonical_for: []
related:
  - docs/experiment-notes/README.md
---

# R7-A-lite CLI Monitor

Arduino IDE を使わずに loadcell firmware の serial monitor を開くための最小手順。

## Monitor

```powershell
cd D:\Xpotato-apps\Selfrionette-mujoco
.\scripts\monitor_loadcell_serial.ps1 -Port COM5
```

操作キー:
- `p` = pause vectors only
- `r` = resume vectors
- `c` = send calibration
- `q` = quit

pause 中も `status` と `warn` は表示される。`vector` だけ止める。

## Send calibration

```powershell
cd D:\Xpotato-apps\Selfrionette-mujoco
.\scripts\monitor_loadcell_serial.ps1 -Port COM5 -Calibrate
```

## Notes

- `Port` は実際の COM 番号に合わせる
- `-Calibrate` は `c` を送って `status,calibration_end` まで待つ
- `pio device monitor` の代替として使える
