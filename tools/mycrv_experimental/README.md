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

## 完整版本切換／回退（本輪只建立工具，未在車端執行）

`python3 tools/mycrv_experimental/manage.py deploy my-crv-experimental <完整SHA>` 只顯示計畫。
另加 `--apply` 才會在本機 comma 上要求停車、乾淨工作樹、固定 origin、遠端 exact SHA、AGNOS 相符與受保護檔案不變，保存原 SHA 的本地 branch 及 backup manifest，將所有控制實驗 OFF，再切換與建置。不自行 reboot，也不啟用 profile。

回退使用備份中的獨立工具：`python3 /data/mycrv_branch_backups/<backup>/manage.py rollback /data/mycrv_branch_backups/<backup> --apply`。
回退同樣維持全部控制實驗 OFF；建置失敗會保存失敗資訊。目標建置失敗會嘗試恢復原 SHA 並重建，若恢復也失敗則必須保持停車，不視為回退成功。

測試使用 fake device 與暫存目錄，涵蓋遠端 SHA 不符、非停車、失敗恢復、雙重建置失敗、備份路徑拒絕、所有開關 OFF 及 preview 無裝置存取。這些不是實際裝置部署驗證。切換後需由使用者另行確認執行版本與啟動狀態；本工具完成建置不等於執行中版本已更新。
