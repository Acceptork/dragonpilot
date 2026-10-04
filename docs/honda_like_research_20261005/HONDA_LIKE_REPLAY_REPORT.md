公開彙總版。完整逐事件分析、時間同步、人工分類與私有證據保留於本機；本檔不含可識別行車元資料。

# 原生回放結果（公開彙總）

本次日期範圍 planner/MPC 185276 影格；重大歷史安全 route 49,304 影格，另有舊資料 3,038 影格。全部 candidate target 變更為 0。
41 件分類事件及六件重大安全事件均有回放窗。
518 次踏板介入：509 次中心有 native frame，500 次有完整 −10/+5 秒窗；其餘初始化／缺口不得當成已通過。
另有 20120 個 active、無踩踏、所選事件窗外的影格，變更為 0。

原生 plannerd/controlsd/card 執行 55 個區段，涵蓋 47 件事件，產生 sendcan。它使用未改動 production 路徑；research proposal 在獨立 planner harness 執行，未冒充完整 candidate process/CAN A/B gate。
主要 active route 的 current native 對 recorded plan P95 誤差約 0.00817 m/s²，最大約 0.10427；有 ramp 持續條件差異。不能事後放寬容差宣稱完美重現。
無 closed-loop vehicle plant；沒有把原 aEgo 當 candidate 實測回應。
