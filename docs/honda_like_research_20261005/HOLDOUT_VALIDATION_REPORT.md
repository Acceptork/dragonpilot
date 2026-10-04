公開彙總版。完整逐事件分析、時間同步、人工分類與私有證據保留於本機；本檔不含可識別行車元資料。

# 保留資料驗證

新候選執行前固定 TRAIN 18、VALIDATION 10、HOLDOUT 13；另保留六件歷史安全事件。
事件先前已檢視，故是 tuning-excluded holdout，不是完全盲測。沒有依 holdout 再降低 Honda 支持門檻或重新選參數。
TRAIN、VALIDATION、HOLDOUT 都是零 target 變更；沒有新 planner 退化，也沒有改善。

TRAIN_GATE = FAIL_EFFECTIVENESS
HOLDOUT_GATE = IDENTITY_ONLY_NOT_RELEASE_PASS
SAFETY_GATE = INCOMPLETE_FOR_DEPLOYMENT

零 lost FCW、零 lost shouldStop、零 danger 正向增加、零新增 solver failure、零非有限輸出，僅是 identity candidate 的觀測結果。
完整 candidate CAN A/B 與所有介入完整窗未成立，不能把軟體單元測試 PASS 當成部署 PASS。
