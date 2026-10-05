# 假說帳本


## H0

- **HYPOTHESIS_ID**：H0
- **OBSERVATION**：A/A 的 CAN 無法對齊。
- **POSSIBLE_CAUSE**：真實時鐘 ECU 查詢在高速 replay 中消耗不同輸入。
- **SUPPORTING_EVIDENCE**：兩次消耗2902／2970包；固定 post-init 後五組完全一致。
- **COUNTER_EVIDENCE**：fixture 不驗證真實 ECU 握手或全路線並行程序。
- **PROPOSED_CHANGE**：僅離線明確初始狀態。
- **EXPECTED_OUTPUT_CHANGE**：相同輸入應得到逐欄位相同控制／CAN。
- **SAFETY_RISK**：若偷略 production 初始化會不安全；本次不改 production。
- **TEST_METHOD**：完整payload比對、跨段與重複執行、突變測試。
- **RESULT**：限定 A/A 修復成立；全範圍 CAN gate 不宣稱通過。

## H1

- **HYPOTHESIS_ID**：H1
- **OBSERVATION**：BAD04／05 MPC 明顯較高、final target 偏小。
- **POSSIBLE_CAUSE**：min(e2e,MPC) 過度保守。
- **SUPPORTING_EVIDENCE**：R20保留+0.178／+0.408平均增量。
- **COUNTER_EVIDENCE**：BAD03完全不變；holdout沒有新作用。
- **PROPOSED_CHANGE**：只對高度相對分歧增加原V3.3.1 eligibility。
- **EXPECTED_OUTPUT_CHANGE**：保留合法直線增量、擋掉不相似的減速前兆。
- **SAFETY_RISK**：分歧比例不是停止語意，可能漏擋或錯擋。
- **TEST_METHOD**：三門檻原生全資料、反例挖掘、凍結後holdout。
- **RESULT**：R20保留研究；不可部署。

## H2

- **HYPOTHESIS_ID**：H2
- **OBSERVATION**：BAD03合成上限中位數0。
- **POSSIBLE_CAUSE**：turn-cap公式、真實曲率與釋放平滑共同限制。
- **SUPPORTING_EVIDENCE**：原公式逐frame吻合；不同曲率來源有可量測差異。
- **COUNTER_EVIDENCE**：兩種當前負荷均高於當時總額度；清晰退出僅最後0.424秒。
- **PROPOSED_CHANGE**：單獨替換為VehicleModel推導曲率，保持額度。
- **EXPECTED_OUTPUT_CHANGE**：若公式過保守應在獨立出彎樣本改善。
- **SAFETY_RISK**：彎中放出更多正加速度，改變入彎行為。
- **TEST_METHOD**：原生全資料與active Top50。
- **RESULT**：BAD03僅+0.052，VALIDATION有效控制無變化；淘汰。

## H3

- **HYPOTHESIS_ID**：H3
- **OBSERVATION**：UNKNOWN限制正target；GOOD06連續約10.6秒。
- **POSSIBLE_CAUSE**：失去可靠前車後缺少解除證據。
- **SUPPORTING_EVIDENCE**：控制鏈可量化正target被壓成0；原事件總約63.95秒。
- **COUNTER_EVIDENCE**：無lead不代表無障礙；缺可靠物體identity。
- **PROPOSED_CHANGE**：本輪只建立episode，不加timeout。
- **EXPECTED_OUTPUT_CHANGE**：若可靠離開可解除，但應保留dropout安全。
- **SAFETY_RISK**：誤把漏偵測當前車離開會削弱制動。
- **TEST_METHOD**：幾何、相對速度、radar ID與重現檢查。
- **RESULT**：不能可靠區分B/C；需新資料。

## H4

- **HYPOTHESIS_ID**：H4
- **OBSERVATION**：無前車綠燈後模型已常解除停止，planner仍HOLD。
- **POSSIBLE_CAUSE**：可靠lead是現有restart解除必要條件。
- **SUPPORTING_EVIDENCE**：31/37 frame模型解除、37/37 planner仍停止；原程式分支吻合。
- **COUNTER_EVIDENCE**：模型停止意圖會回跳；只有一個獨立正例。
- **PROPOSED_CHANGE**：僅model-go持續時間shadow審查。
- **EXPECTED_OUTPUT_CHANGE**：有穩定go但HOLD不放行應可被獨立識別。
- **SAFETY_RISK**：錯誤go可能導致紅燈放行。
- **TEST_METHOD**：已核對燈號的BAD01與全開發集shadow。
- **RESULT**：診斷成立，未修改HOLD；需紅燈保持負例。

## H5

- **HYPOTHESIS_ID**：H5
- **OBSERVATION**：小正target時實際仍掉速。
- **POSSIBLE_CAUSE**：坡度、動力延遲、命令幅度與plant反應。
- **SUPPORTING_EVIDENCE**：上坡篩選22 frame：target中位0.156、實際aEgo -0.397。
- **COUNTER_EVIDENCE**：約1.1秒且有時間相關性，非穩態辨識。
- **PROPOSED_CHANGE**：不新增全域gas或坡度固定補償。
- **EXPECTED_OUTPUT_CHANGE**：充分分層後才能判斷控制不足還是物理遲滯。
- **SAFETY_RISK**：以短樣本加油可能造成過衝。
- **TEST_METHOD**：pitch／target／actuator／aEgo分層。
- **RESULT**：現資料不足以擬合可靠response envelope。

## H6

- **HYPOTHESIS_ID**：H6
- **OBSERVATION**：前段功能可能被後段clip／memory蓋掉。
- **POSSIBLE_CAUSE**：selector→clip→stop→restart→ramp→personality→overtake→memory的順序。
- **SUPPORTING_EVIDENCE**：開發集personality/overtake final改變0；restart與memory主要降低target。
- **COUNTER_EVIDENCE**：低觸發不代表所有場景功能無用；taper在controller另一路。
- **PROPOSED_CHANGE**：本輪不重排，保留逐stage before/after。
- **EXPECTED_OUTPUT_CHANGE**：辨識真正影響final的控制量。
- **SAFETY_RISK**：重排安全interlock可能反轉停止意圖。
- **TEST_METHOD**：原生trace與作用秒數稽核。
- **RESULT**：確認順序限制；不把UI ON當成有效。
