# CAN 重現性診斷

本輪已定位原 A/A 不一致的根因，並完成五組限定範圍驗證。不能據此把上一版候選 CAN gate 改成 PASS。

## 已重現的根因

Honda `CarInterface.init()` 在離線回放中仍執行 ECU 初始化查詢。`disable_ecu()` 的十次重試使用真實時鐘截止時間，但 replay 以最快速度供給已記錄 CAN。兩次原始 A/A 初始化分別消耗 2,902 與 2,970 包 CAN（146,407 與 149,890 個 frame），耗時約 1.029 與 1.010 秒。它們開始正常控制時的輸入狀態根本不同。

這解釋為何不能將原先 130 則無法對齊、1 個 CONTROL_ON 差異，或候選大量未對齊 CAN，當成可忽略誤差。原結果仍為不可信／未通過。

## 最小離線修正

使用僅在 `REPLAY=1` 可啟動的 post-initialization fixture，明確假設硬體初始化已完成。它不消耗 CAN、不對實車傳送資料，也不更動 production `CarInterface`。之後仍跑原生 planner、controlsd、card、Honda parser/controller。各程序分段串接；感測器輸入固定，planner 輸出供 controlsd、carControl 供 card。

這是固定輸入、固定已初始化狀態的測試，不驗證真實 ECU 握手，也不是含車輛動態回饋的閉迴路測試。

## 五組結果

| 組別 | 每側 planner 訊息 | 每側 sendcan 訊息 | 控制／CAN 差異 |
|---|---:|---:|---:|
| 直線 | 1200 | 5985 | 0 |
| 跟車 | 1199 | 5984 | 0 |
| 停止 | 1201 | 5985 | 0 |
| 直線重複執行 | 1200 | 5985 | 0 |
| 連續兩段、保留跨段狀態 | 2400 | 11985 | 0 |

全部 carState、carParams、carOutput、carControl、controlsState、longitudinalPlan、sendcan 逐服務、依原順序比較。CAN address、bus、bytes、frame 排序、訊息時間與數量完全相同；未排序 CAN 來消除差異。

僅排除兩個已證明來源的運算耗時欄位：

- `longitudinalPlan.solverExecutionTime`：planner 直接發布 MPC `solve_time`。
- `carState.cumLagMs`：card 發布 `-Ratekeeper.remaining * 1000`。

沒有加數值容差，沒有排除 CONTROL_ON、BRAKE_REQUEST、shouldStop、FCW、加速度、solver 狀態或時間戳。不同服務的全域交錯順序不作輸出語意比較；同一服務順序與時間保留。

八項比較器測試通過：一致資料、兩個耗時欄位可排除；極小 target 改變、shouldStop、時間、CAN byte、CAN 排序及缺訊息均會失敗。JSON 非有限數值讀取直接失敗。

## Gate 範圍

`INITIALIZED_SCOPED_AA = PASS`。已驗證的五組不是完整路線覆蓋，不能宣稱 `RELEASE_GRADE_FULL_ROUTE_CAN = PASS`。真實初始化／全程序並行 feedback、完整路線與最終候選 A/B 仍須另驗。先前 candidate FAIL 不變。

## 補充全量 planner 重現性

獨立H1／H2執行中的baseline共237618 frame，model時間、vEgoCluster、設定速度、e2e、MPC、final target、shouldStop、FCW、solver、cap、source等核心欄位逐項完全一致。這是全量planner投影證據，不是全量CAN程序證據。
