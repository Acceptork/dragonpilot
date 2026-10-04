公開彙總版。完整逐事件分析、時間同步、人工分類與私有證據保留於本機；本檔不含可識別行車元資料。

# 41 件駕駛事件分析（公開彙總）

41/41 分類有效；文字選填。未分類 0、無輸入 0、僅分類無文字 26。
已完成分類彙總：加速太慢 8、晚煞／不足 1、正常 23、主動操作 3、刻意測試 3、無法判斷 3。
原候選與駕駛意圖分開保存，沒有把主觀描述當程式根因。

每件本機分析均包含 DRIVER_INTENT、SYSTEM_STATE、MODEL_INTENT、MPC_INTENT、FINAL_PLAN、HONDA_COMMAND、VEHICLE_RESPONSE、DRIVER_INTERVENTION。
41 件都重新對齊 road/wide 曝光索引；無前車起步案例另逐格核對。其餘影像判讀是既有抽樣，未冒充逐幀審查。
速度落差採 vEgoCluster。Honda OEM 命令使用實際接收 CAN，OP 使用 sendcan，並未把 OP planner 當 Honda 韌體。
日誌範圍有 162 個可用 telemetry 區段，128 個已知缺段仍未補回；相機影片不能替代缺失訊號。
