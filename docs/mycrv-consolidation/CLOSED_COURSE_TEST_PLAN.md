# 可控場地逐項驗證表

狀態：PASS_INTEGRATED_SOFTWARE_GATES；封閉場地軟體候選已通過，GitHub 發布尚待授權。DEVICE_DEPLOYMENT = NOT RUN。
目前整合程式 SHA：`9469a5ce68ed4a5636c77151491d37e42235d296`。taper、overtake、memory 與 restart 修正均已合併；同一提交已通過五组原生 gate、140 個功能／profile 情境、六個實際 controlsd 組合情境、675 個保護檔案一致性及八個實驗開關預設 OFF 檢查。restart 獨立14e68d6的 OFF／ON 各42段與因果稽核已通過。最終整合全 OFF 42段已 PASS_IDENTITY，與80e1901的控制及CAN輸出零差異。四組exact-commit開關清單與工具hash見 V33_PROFILE_DELIVERY.json；GitHub發布尚未完成。

## 共通操作與紀錄

1. 先用全部控制實驗 OFF 的同版本建立參考。每次只啟用一個功能，該功能完成後才測 profile 組合。提醒功能與控制實驗分開記錄。
2. 每次記錄 exact SHA、profile、全部開關值、personality、日期、場地、路面／坡度條件、輪胎與載重變化。bookmark 註明測試編號。
3. 記錄介入前後的 vEgo/vCruise/aEgo/aTarget、leadOne/Two、stop/FCW、pitch freshness、lateral state、feature active/reason/enter/exit。若缺日誌，該次結果不得當作功能通過。
4. 不在公共車流中刻意製造障礙、急切入或突然煞車。危險情境先使用既有 synthetic／plant 測試；實車取樣只在能自行接管與停止的可控條件執行。
5. 任一非預期加速、既有煞車需求削弱、意外變道、creep、rollback、停止位置超出事先可接受範圍，立即由駕駛接管／取消控制，安全停車後關閉功能。行進間不操作 shell。
6. 停車後 UI 單獨 OFF；需要全面停用時使用 ALL_OFF。完整版本回退用部署時保存的 backup manifest 和獨立 manage.py；回退建置失敗不得宣稱成功或繼續測試。

## PROFILE_A_STOP

先個別測 early_stop、taper、restart，再測三者組合。保留足夠可停止區域，不使用未量測的假 stop-line coordinate。

| 編號 | 驗證內容 | 接受條件／立即中止 |
| --- | --- | --- |
| A1 | 提前減速 ON/OFF，同一路徑的模型減速場景 | ON 僅新增負加速度，bias不超過0.15m/s²；既有FCW/stop/braking仍有效。正向加速或移除停止意圖立即中止 |
| A2 | 非停車減速：緩彎、坡頂、rolling traffic取樣 | 記錄誤減速次數、持續時間、bias與jerk；若頻繁干擾正常駕駛則關閉，保留事件重新分析 |
| A3 | taper平地，再於已知坡度測試 | 分別量測停止距離、末段jerk與穩定hold；creep、rollback、overrun即中止。不能僅憑乘坐舒適宣稱通過 |
| A4 | 前車10cm微動／短暫目標失效 | 不允許RELEASE_ALLOWED；任何自動跟進即中止 |
| A5 | 同可靠前車持續移動，三種personality | 必須先通過共同位移／持續性與安全gate，才有不同額外等待；stop intent、FCW、driver brake或新更近lead均須阻擋 |
| A6 | A組合 | early-stop suspect不得被restart或positive recovery抵銷；有相反狀態衝突即中止 |
| A7 | 起步位移量測波動 | 保存連續 dRel、vRel、pending 與 release 時刻。新版以 0.4–0.55 秒時間窗估計距離趨勢，仍要求共同位移／持續性；只有正 vRel 但距離未前移不得釋放。若反覆 pending、無法釋放，記錄效果 FAIL，不手動放寬 gate |
| A8 | taper 退出／坡度資料失效 | 已新增的負加速度應平順回到基準；新的較強基準煞車立即優先。OFF、駕駛接管與控制權失效須立即交還基準，不為舒適度延長實驗權限 |

Taper 的預設 plant 掃描仍有四個下坡 overrun case，不能稱為全通過。初始實驗限平坦場地，再依實際制動增益、延遲與坡度安排下一階段；此軟體 gate 不批准下坡測試。四個失敗 case 與原始十個失敗的分類見 [PLANT_FAILURE_ANALYSIS.md](v33_results/taper/PLANT_FAILURE_ANALYSIS.md)，不以舒適度改善抵銷停止距離失敗。

## PROFILE_B_LCA

「此車型無可靠盲點資料，變換車道前請自行確認後方安全。」

| 編號 | 驗證內容 | 接受條件／立即中止 |
| --- | --- | --- |
| B1 | 方向燈單獨、torque單獨、打燈前held torque | 不得產生fresh confirm或開始協助變道 |
| B2 | 打燈後新的同方向torque | 只消耗一次確認token，仍保留road edge、timeout、cancel、fade與車輛限制 |
| B3 | latActive=false→true且一直held torque | 恢復後仍需重新torque onset；不得自動承接舊確認 |
| B4 | 分別取樣0/1/3/5/10/20km/h | 記錄helper intent與實際latActive/steering command；物理能力不允許時不得強制steering。沒有輔助不等於helper失敗 |
| B5 | 取消方向燈、反向燈、disengage、timeout、完成 | token失效，held torque不得再次觸發；任何重複協助即中止 |

blindspot true/false/missing一致性已列軟體測試，不在道路上以真實鄰車製造危險來驗證。road-edge阻擋同樣先以synthetic驗證，實車不刻意逼近邊界。

## PROFILE_C_PERFORMANCE

| 編號 | 驗證內容 | 接受條件／立即中止 |
| --- | --- | --- |
| C1 | no-lead free-cruise恢復，三種personality | 相同條件下正加速度建立可區分；有lead/stop/negative model時不能為人格弱化煞車 |
| C2 | 新鮮坡度資料、e2e小幅正值而MPC允許較高值 | ramp blend新增量不超過0.1m/s²；必須保存trigger与before/after |
| C3 | closing lead或負model accel | ramp不得介入；出現覆蓋負model或忽略lead即中止 |
| C4 | 接近設定速度與超速事件 | 檢查OVERSHOOT_EVENT與前後資料，記錄peak/持續時間；本輪不以修改PID或safety壓掉問題 |

今天gas027/032多數負e2e樣本不自動符合C2；先判讀，不全域加floor。

## PROFILE_D_OVERTAKE

只在無公共車流干擾的可控測試條件驗證；駕駛自行确认後方與相鄰路徑。

| 編號 | 驗證內容 | 接受條件／立即中止 |
| --- | --- | --- |
| D1 | 方向燈單獨、held torque、longActive=false | 不得產生Stage1 preaccel |
| D2 | fresh同方向torque＋confirmed lane-change intent | Stage1額外preference最多0.05m/s²且受既有MPC/雙lead/FCW/stop/hardBrake/total cap約束；沒有餘量時允許零效果 |
| D3 | 現有lead仍約束ego path | 不能解除lead constraint換取效果；任何危險煞車削弱即中止 |
| D4 | Stage2 | provider未驗證，必須BLOCKED；不能以方向燈、blindspot=false或無CAN資料推定path clear |

Stage 1 效果需另行判讀：若兩個 lead 的既有安全距離或 MPC 上限正在限制，零額外加速度是正確 veto；若 fresh torque、confirmed intent、雙 lead 安全距離及 MPC 正向餘量都成立，卻持續無 active，列效果 FAIL 並保留 reason。獨立 `278e190` 已用左右方向共 14 個原生 MPC 情境驗證這個區別，包括本車 85 km/h、設定 124、前車 150 m 且相對速度 -1 m/s 的正向餘量案例。這些數值是合成測試輸入，不是要求駕駛在場地重現的速度或安全距離標準。前車較慢不能單憑相對速度一項永久拒絕 Stage 1，也不能因此解除雙 lead 或 MPC 約束。

## 獨立取樣：記憶、EPS、回正、提醒

- Lead memory：分別0.2/0.3/0.5秒，先shadow再單獨active；距離應隨vRel預測、不freeze；更近新lead立即優先。從未見到的機車記為PERCEPTION_LIMITATION。另依下方 M1–M5 取樣，不能只以「更保守」當效果通過。
- EPS：保存requested/applied torque、EPS torque、safety limiting、curvature與saturation duration。資料不可得要留空，不填0假裝正常。先不修改longitudinal cap。
- 回正：STEERING_RETURN_EVENT保留前後10秒；區分driver countersteer、laneChangeFinishing與一般曲率衰減。本輪不改steering tuning。
- 前車／可能可通行提醒：候選确认後4秒內駕駛自己起步不得出聲；完整4秒無動作且場景每frame仍成立才提示一次。再次停止、資料失效、換目標或障礙取消。ACC关闭也需可運作；不得產生任何控制。


### Lead memory 取樣與退出檢查

舊版 f034a4 的 42 段啟用回放沒有遺失 BRAKE_REQUEST／FCW／shouldStop，也沒有 GAS 增加；但未知狀態最長約 143.4 秒，且實際控制中出現記憶約束退出的命令跳升。原始輸入確認主要反例並非駕駛接管。修正版 e2358e4 新增目標恢復限速，原生測試與新版 OFF／ON 各 42 段回放已通過獨立控制 gate。原跳升反例單次回升由約 1.31 降至 0.10 m/s²，沒有未解釋的新增向上步階；最終整合與物理驗證仍未完成。

| 編號 | 驗證內容 | 接受條件／立即中止 |
| --- | --- | --- |
| M1 | 同一已可靠追蹤前車短暫失去，先 shadow | 記錄 age、預測距離、不確定度及 release reason；未曾可靠出現的物體不得被建立成記憶。不要故意遮擋攝影機 |
| M2 | 記憶期內重新出現、index reassociation、新更近前車 | 新更近前車立即優先；不得凍結舊距離或以舊目標阻擋新目標。任何忽略新障礙立即接管 |
| M3 | 逾時仍 UNKNOWN | 不自動當作 path clear 補油。记录 UNKNOWN 持續时间与抑制程度；若持續妨礙預定操作，停止該次試驗、由駕駛接管，安全停車後單獨 OFF，列效果 FAIL，不能反覆 toggle 嘗試取得加速 |
| M4 | 可靠重獲目標後恢復 | 檢查 release_active/release_reason、aTarget before/after、實際 actuator 命令及 aEgo。目標恢復限制不等於物理 jerk 已證明；若仍有明顯跳升或點頭，立即接管並停用，保存前後至少 10 秒 |
| M5 | 更強煞車、駕駛接管、關閉功能 | 更強基準或記憶煞車不得被恢復限速延遲。駕駛接管與 OFF 應清除恢復歷史；不得持續保留本功能的權限。危險煞車情境先 synthetic，不刻意製造碰撞風險 |

本功能不納入四個 profile 的預設組合，需單獨開啟。實驗 UI「前車短暫記憶」OFF／ALL_OFF 為功能退出方式；完整版本回退仍使用保存的部署 backup manifest。任何取樣缺少 flags、reason、時間或控制命令，結果記 INCONCLUSIVE。
## 每次結果欄位

測試ID／SHA／flags／bookmark／PASS、FAIL或INCONCLUSIVE／reason／資料檔案／是否接管／功能關閉與回退結果。缺乏可重現資料用INCONCLUSIVE，不填PASS。任何FAIL保留原始證據，不覆寫上次結果。




