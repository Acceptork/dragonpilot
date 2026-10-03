# 可控場地 profile 預設組合

本工具只調整已安裝版本的實驗開關；不下載、部署、重啟、改 branch 或修改 safety。所有控制實驗安裝預設 OFF。

先在停車狀態查看：`python3 tools/mycrv_experimental/profiles.py PROFILE_A_STOP`。沒有 `--apply` 不會更改任何開關。
日後實車套用須在 /data/openpilot 使用該裝置 Python／PYTHONPATH，明確提供 `--apply --sha <已驗證完整 commit>`。
立刻關閉所有控制實驗的停車後命令：`python3 tools/mycrv_experimental/profiles.py ALL_OFF --apply --sha <目前完整 commit>`。
行駛中若有異常，先由駕駛接管／取消控制並安全停車；不要操作 shell。

| Profile | 唯一啟用的控制實驗 | 初次測試重點／立即中止 |
| --- | --- | --- |
| PROFILE_A_STOP | 提前減速、平順停車、自動跟車起步 | 封閉平地、先各功能單獨 ON；任何 creep、rollback、停止距離增加、微動跟車立即接管 |
| PROFILE_B_LCA | 低速變換車道 | 各速度先確認 latActive／Honda 能力；held torque、未確認、自動重複變道或道路邊緣介入即停止 |
| PROFILE_C_PERFORMANCE | 匝道追速、巡航回復性格 | 先低風險直線且無 closing lead；模型負加速度被覆蓋、煞車需求被削弱、overshoot 立即停止 |
| PROFILE_D_OVERTAKE | 低速變換車道、超車預加速 | 僅 Stage 1；Stage 2 缺可靠 path-exit provider 維持 BLOCKED。方向燈單獨加速、無 torque 確認或 lead 約束失守即停止 |

每次套用先清除上一組全部控制實驗，再啟用選定組合。儲存或 offroad 狀態檢查失敗會嘗試全部 OFF 並回報錯誤。
提醒開關與控制實驗完全分離，profile 不更改起步提醒設定。前車記憶未包含四組預設，可在 UI 單獨測試。
軟體測試不等於實車效果驗證；各功能 CLOSED_COURSE_REQUIRED。完整版本回退使用正式交付的 pinned backup 工具；此 profile 命令不是版本回退。
