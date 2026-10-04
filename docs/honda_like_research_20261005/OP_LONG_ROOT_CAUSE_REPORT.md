公開彙總版。完整逐事件分析、時間同步、人工分類與私有證據保留於本機；本檔不含可識別行車元資料。

# 縱向控制直接限制（公開彙總）

確認的機制包括：blended 的 min(e2e,MPC) 選擇較低 e2e；轉向加速度上限及解除斜率；lead_memory UNKNOWN 將正 target 歸零；無可靠前車時 restart HOLD 持續維持 shouldStop。
上述判讀交叉比對原始功能日誌、planner 回放與實際控制輸出，不只來自駕駛描述。

嚴格巡航診斷子集排除 lead、stop、負 e2e、預測末端減速、throttle veto、高曲率、測試模式與 warmup，儀表速度落差至少 5 km/h。其中 1398 個影格、50 段、69.90 秒為 MPC 希望加速但 e2e 更低。
控制需求差積分不是實際速度損失；沒有可靠 vehicle plant，不能量化實際恢復時間改善。

出彎案例並非全部 e2e 遲緩：有案例在駕駛介入前已隨轉向上限解除而增加 target。
前車離開案例存在 memory UNKNOWN 長期限制。無前車起步案例模型曾解除 stop，但 restart interlock 仍維持 HOLD。
直接取消 HOLD 可能放過停止期間的模型 flicker，未當作安全修復。
停止舒適度與位置分開；缺少相機到車頭及停止線標定，沒有虛構公尺數。歷史紅燈不足停止案例仍未被本候選修復。
