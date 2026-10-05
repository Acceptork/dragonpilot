# 無前車綠燈與前車起步

BAD01 的不起步不能全歸因於模型。本輪確認 no-lead HOLD 是獨立限制：`AutoRestart` 的可靠前車條件不成立時，狀態維持 HOLD，planner 再將 shouldStop 做 OR 並把 target 壓到不大於零。

| 時窗 | frame | 模型 shouldStop=false | planner shouldStop=true | endpoint 中位數 |
|---|---:|---:|---:|---:|
| 轉綠前最後約 2 秒 | 39 | 0 | 39 | 0.84 m/s |
| 轉綠後、駕駛介入前 | 37 | 31 | 37 | 12.80 m/s |

綠燈後 e2e 中位數約 0.343 m/s²，MPC 約 1.799，最終 target=0，記錄的 actuator acceleration 約 -2.003。全段無前車，restart 原因為 `common_safety_gate`。綠燈後模型並非一直要求停止，但最後仍有停止意圖回跳，不能把所有 frame 當成穩定 go。

另建立不修改控制的 shadow 審查：資料有效且 fresh、無前車／踏板／FCW／hardBrake、靜止、模型解除停止、e2e>0.1、endpoint>2，持續 1 秒。在開發集找到一段 1.45 秒 episode，正是此案例。這是診斷假說，未把持續時間調到剛好通過案例，也未產生解除煞車命令。

一個正例不足以驗證紅燈／遮擋／停止線附近的錯誤放行率。因此沒有新增無前車自動起步控制，沒有改 HOLD、terminal taper 或假造交通燈 detector。H4 的狀態機限制已確認，安全修正仍需獨立的紅燈保持與綠燈 go 資料。前車起步仍使用前車運動證據，與此問題分開。
