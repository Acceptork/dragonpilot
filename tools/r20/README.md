# V3.3.2 R20 實驗版

此版本用於收集 CR-V 直線自由巡航的實際反應資料，不是 production release，也不是 SAFE_FOR_ROAD 或實車效果已通過的宣稱。

基準：`3f705e3b520c50fff2c76d64187feaff49476f74`。研究來源：`899421a2e0fb795187df4982072239043ed91ff9`。

僅整合既有有界 selector recovery，加上 e2e/MPC ≤0.20 的相對分歧 veto。所有既有有效／新鮮資料、駕駛踏板、停止、FCW、hardBrake、lead、memory、曲率、未來曲率、加速度及 ramp 限制保留。近期彎道明確排除，沒有 CURVE_EXIT_RECOVERY。

BAD03、lead-memory UNKNOWN、無前車綠燈 HOLD 均未修正。沒有更動 turn-cap 公式、停止調校、taper、tFollow、panda 或 Honda actuator limits。

R20 進入／離開會產生 `R20_RECOVERY` 的 ENTER／EXIT 事件標記，作用期間記錄 SAMPLE。控制執行緒只複製必要訊號並放入容量32的佇列；背景執行緒處理 CAN 解碼及記錄。滿載時丟棄記錄並累計 dropped_samples，不阻塞控制，也不建立檔案。

CAN 欄位是有獨立時間戳的最近已送出命令，不假稱一定由同一模型 frame 造成；超過0.2秒或缺值時標 command_valid=false、值為null。既有完整 `rlog.sendcan` 保留，可回家後精確對時。停止與FCW不因記錄成功或失敗而改變。

使用 `tools/r20/extract_events.py <本機rlog...> --output <本機jsonl>` 匯出事件。記錄含模型時間、兩種車速、設定速度差、e2e／MPC／原selector／R20／final target、aEgo、兩lead、stop／FCW、曲率／turn cap／pitch、踏板、進出原因、veto及有時效標記的GAS／ACCEL／BRAKE_REQUEST。

原本experimental設定不預設重設。UI僅將軟體頁版本顯示改成「V3.3.2 R20 實驗版」，不更改通訊版本號。
