公開彙總版。完整逐事件分析、時間同步、人工分類與私有證據保留於本機；本檔不含可識別行車元資料。

# Honda-like 候選設計 — NOT DEPLOYABLE

獨立 RecoveryPolicy 在 selector 前提出 bounded e2e recovery，再經原生 MPC/min/clip/既有保護。沒有全域 aggressive multiplier，沒有在 MPC 最後硬加加速度。
保留 headway、FCW、hardBrake、Honda actuator limits、panda safety、terminal braking 與原使用者設定。

狀態含 FREE_CRUISE、LEAD_FOLLOW、LEAD_CLEAR_RECOVERY、CURVE_APPROACH、CURVE_EXIT_RECOVERY、STOP_APPROACH、STOP_TERMINAL、STANDSTILL、RESTART、OVERTAKE_INTENT、UNKNOWN。
shouldStop 不是紅燈 detector，STOP_APPROACH 的辨識完整性未通過驗證。
只有正向／非減速模型意圖、有效連續資料、無 lead/stop/curve 危險、儀表 deficit≥5 且有 Honda TRAIN 支持時才可提出恢復，並有限幅與限斜率。

實際參考沒有該 deficit 的 supported cell，因此每個 replay 影格均 fallback。這不是更像 Honda 的成功版本。
沒有將 restart/memory 根因直接套成未經驗證的 production 修補；本分支 production source 不變。
