# 起步提醒候選（整合驗證中）

本地分支：`my-crv-departure-alerts-experimental`。
目前 HEAD：`bf60a309aaa1daf71ef5c0f341515dfea4152a33`；4 秒狀態機 commit：`167c72787f65d1c4b5146d3216e2ad165d3754cf`。
功能 commit：`b83c9720fd442f60dd904109313b6787657854aa`；後續 `4aa5ffa` 修正原生唯讀訊息測試資料，`1898032` 加入實際畫面／聲音優先權測試。

## 2026-10-03：駕駛無動作 4 秒門檻

既有候選判定保留。兩種提醒都從候選首次確認時刻等待至少 4.0 秒；不是從前車初動或模型初次變化開始計時。每個觀察 frame 必須繼續滿足相同候選，才累積等待時間。

駕駛補油、車速超過 0.2 m/s、相對確認時速度上升至少 0.1 m/s、離開 D、offroad、資料失效／時間中斷、模型 shouldStop、hazard、更近障礙、前車再停／關聯不連續、關閉相應提醒開關，均取消 pending。取消後保守鎖定至本車至少 0.8 m/s 持續 2 秒重新準備，避免短暫資料恢復再次倒數。這些車速門檻是實驗提醒判定，仍需實車確認噪聲與漏報。

狀態提供 WAITING_FOR_DRIVER_RESPONSE／CANCELLED／ALERTED；日誌記錄轉移、confirmed_at、資料有效性、駕駛動作和障礙資訊。提示事件另外記錄實際 driver_wait_seconds。保留 20 秒 cooldown、同次停車一次、原有警告優先權及控制隔離。

新增兩種候選各 11 種取消測試、兩種完整四秒與單次提醒測試；ACC=false 原生 reader 測試延長覆蓋等待期。另加入兩種提醒 × 9 種模型兩幀之間失效測試及禁止用重複模型累積證據的測試。提醒狀態機／接線 62 項通過；目前 SHA 的完整 UI suite 為 209 passed、2 skipped。

bf60a30 修正模型沒有更新時仍須立即取消 pending 的邊界，並保留 offroad／freshness 中斷前的同次停車鎖定，防止重新武裝。沒有改動既有候選門檻或控制輸出。

## 功能

- 「前車起步提醒」：本車接近靜止、D 檔、同一可靠前車先持續停止，之後位移至少 0.7 m、持續前移至少 0.8 秒確認，再等待駕駛連續 4 秒無動作才提示「前車已起步」。10 cm 微動、資料中斷、換目標、較近障礙與駕駛已補油會抑制提醒。
- 「號誌通行提醒」：無前車、先有至少 3 秒模型停止軌跡，再有至少 1.5 秒持續前進軌跡確認，等待駕駛連續 4 秒無動作且場景仍成立才提示「前方可能已可通行」。沒有紅綠燈語意辨識，不使用「綠燈」文案。
- 兩個繁中 UI 開關獨立，設定 default 為 ON；它們不是自動跟車起步或任何控制實驗開關。
- 同一次停止只提示一次，冷卻 20 秒；需本車實際持續移動後才能重新準備下一次提醒。資料丟失不會重新武裝已提醒的同次停止。

## 與控制的隔離

判定依 onroad、D 檔、車速、gasPressed、model／radar freshness 與連續觀察。沒有讀取 longActive 作 gate。原生測試使用 enabled=false、active=false、longActive=false 的訊息仍可觸發。

adapter 只寫入短期 UI 提示參數 `dp_departure_alert_cue`，不發布 planner、carControl、CAN 或 RESUME，也不解除煞車。參數在 manager 啟動時清除，訊息三秒失效；離線／關閉開關時不顯示。兩種 UI renderer 與 soundd 都保留既有警告優先權，不排隊延遲播放過時提醒。

## 已驗證與未完成

- bf60a30 原生建置、控制單元、Honda／longitudinal／MPC、panda Honda safety、UI 五項 gate 全部通過，詳見 `v33_results/departure/` 的 exact-SHA ledger。
- 已合併到本地 experimental `b2e26db22d92fa4195156e49fe879bfcd41074ce`，該 SHA 五項 gate 也全部通過；其中 UI 209 passed、2 skipped。涵蓋原生 reader 不可變性、ACC 未啟用、UI 文案／時效／開關、兩種 renderer 與聲音優先權。
- 今天 20,604 個對齊樣本使用修正後匯出資料重掃：20,561 fresh、1,949 靜止 D 檔未踩油門、1,428 lead anchor frame、83 model slow-armed frame，沒有進入 pending 或提醒。這不證明實際提醒效果良好；需逐停止 episode 診斷及實車 UI／音量確認。先前模型 endpoint 全空白的掃描已另存為 INVALID_MISSING_ENDPOINT，不能用作驗證。
- 尚未 push、尚未完成 b2e26db 的整合後 all-OFF 控制 identity／完整回放 gate；更早 e4d0889 的 42/42 identity PASS 不代替目前 SHA。
- 實車需要確認停車時可聽見提示、畫面易辨識、塞車不重複提示及兩開關可即時關閉。若有錯誤提醒或重複提醒，立即關閉相應提醒開關；任何控制介入均不屬本功能允許行為。

本輪未連線或修改 comma，未部署，未重啟。

## 原生提醒與 profile 補驗

最終本地 b2e26db 的四組 profile、各單一開關、全開及全關，合計 140 個原生 planner 情境通過輸出／旗標隔離與安全約束檢查。情境中的危險訊號按每 frame 實際輸入判斷（braking case 前 2 秒尚無 lead），不以場景名稱誤套整段 veto；首次過廣 assertion 的失敗紀錄保留。

提醒接線已使用今天 35 段按 monotonic timestamp 排序的原始 native readers 執行，共 41,120 model frames，41,105 all-valid；2,861 lead anchor、150 model slow-armed frames，沒有 pending／提示。僅寫入 UI cue key，未發布控制訊息。log timestamp 代替 receive time，因此此掃描不能驗證 soundd 排程或實際聲音。結果在 v33_results/departure/today_native_results.json，先前未排序掃描保留，不能用作效果結論。
