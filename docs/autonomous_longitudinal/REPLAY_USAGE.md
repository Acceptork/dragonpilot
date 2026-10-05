# 離線重現方式

本研究沒有 production 接線、沒有版本升級、沒有車端部署。H1/H2 是研究 wrapper，禁止把研究 branch 的名稱當成可上路版本。

使用既有原生 build 與同一依賴環境，從公開 baseline commit `cf42fa536c8aeac153d3855129deac5591eee1eb` 匯出 `selfdrive/controls/lib/longitudinal_planner.py` 成本機 `baseline_planner.py`。記錄來源 SHA 與檔案雜湊。

設定以下環境變數後執行 `tools/honda_like_research/autonomous/replay_h1_hypothesis.py` 或 `replay_h2_hypothesis.py`：

- `OPENPILOT_RESEARCH_TREE`：研究 checkout 的絕對路徑。
- `RECOVERY_BASELINE_SOURCE`：匯出的 baseline planner。
- `RECOVERY_INPUT_ROOT`：私有 route 資料夾的父目錄；每個 route 下面為各 segment 的 `rlog.zst`。
- `RECOVERY_EVENT_MANIFEST`：私有 JSON，含 events 陣列與 id／route／t。無事件時可用空陣列。
- `RECOVERY_REPLAY_OUTPUT`：新的本機結果目錄。
- `AUTONOMOUS_SAVE_TRAJECTORY=1`：選填，保存全部模型軌跡以利診斷。

H1 同時輸出 baseline 與三個門檻的原生結果。H2 只改當前曲率上限公式，沒有 H1。兩個 runner 都保留 recorded Params，連續 segment 保留狀態；缺段或模型時間不連續時重置並標 warmup。資料缺段不補造。

原生 planner/MPC 回放不是物理車輛模擬；輸出 target 的改變不能直接換算實車追速秒數或停車公尺數。

程序 A/A 另使用 `card_replay_fixture.py` 與 staged process replay。此 fixture 必須由離線 harness 設定 MODE、OUT，且只允許 `REPLAY=1`。使用 `replay_identity.py A.jsonl B.jsonl` 比較完整逐服務 payload。參見 CAN 報告的限定範圍，不能拿 fixture 假設取代真實 ECU 初始化測試。

原始 CAN、影片、完整 Params、route 身分、時間軸與駕駛個別標註留在本機；GitHub 僅發布研究程式、測試與整理後報告。
