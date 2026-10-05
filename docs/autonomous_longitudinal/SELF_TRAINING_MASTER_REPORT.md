# 自主診斷與迭代結果

**狀態：NEEDS_NEW_REAL_WORLD_DATA。車端完全未修改。**

本輪完成2輪最小控制假說比較，建立4個離線候選、淘汰3個，保留H1-R20作部分研究結果。固定研究SHA：`899421a2e0fb795187df4982072239043ed91ff9`。它仍未達可實車A/B標準，沒有candidate release tag。

最重要成果是定位 replay A/A 的初始化問題：原本真實時鐘ECU查詢消耗不同數量CAN。相同離線已初始化狀態下，五組原生程序A/A包含跨段驗證，控制訊號與CAN完全一致，只排除兩項運算耗時。另兩次全資料baseline planner共237618 frame核心輸出逐項一致。這不等於全路線候選CAN gate已完成。

## 控制結果

| 問題 | 結果 |
|---|---|
| 直線追速 | 部分改善：BAD04 0.141→0.318；BAD05 0.090→0.498 m/s²。R20移除event_041原27 frame recovery |
| 出彎 | 未解決。保留版BAD03不變；獨立公式替代只有小幅改善且未證明EXIT_CLEAR效益，已淘汰 |
| 前車離開 | 未解決。UNKNOWN延遲已量化，缺可靠object identity，不能安全加timeout |
| 無前車綠燈 | 限制已定位，但未修改。模型31/37 frame解除停止，HOLD仍未放行 |
| 入彎／紅燈停止／跟車 | 最佳部分版保留集planner未改變；未完成候選完整CAN安全證明 |

目前前三大限制是：e2e/MPC selector 的保守限制、曲率上限與真正出彎時點不一致的證據問題、lead-memory UNKNOWN缺乏可靠解除依據。no-lead HOLD是另一個已確認獨立問題。

TRAIN／VALIDATION只有部分直線效果；HOLDOUT 81833 frame完全無新作用，不能宣稱通過。SAFETY與FULL_REPLAY都沒有達到release-grade。採用實際控制權分類，未把OEM／手動狀態下的影子target差異誤報成實車退化。

## 為何停止繼續調參

R20門檻能分開已知正例與event_041，但不是停止辨識器。BAD03清晰低曲率條件只在介入前約0.424秒出現，不足證明應如何更早解除。前車缺可靠identity；上坡有效小正target樣本約1.1秒；停止位置沒有camera-to-bumper／停止線真值。繼續只針對這些事件調門檻會增加過度擬合。

## 下次資料怎麼收集

沿用已知穩定 `my-crv-experimental`／`3f705e3b520c50fff2c76d64187feaff49476f74`。本輪沒有重新SSH驗證車端，只確認未對其操作。**八個experimental開關先維持目前全部ON，不啟用本輪研究程式，也不在行駛中改設定。** 初次收集固定設定有助於比對，暫不要求ON/OFF混跑。

| 場景 | 建議數量 | 怎麼收集 |
|---|---:|---|
| 清楚直線追速 | 每種安全速度差5／10／20 km/h各3次 | 在合法設定速度與正常交通下自然累積；20不足就不湊數，不刻意減速阻礙交通 |
| 單彎後長直線 | 3次 | 保留入彎、彎中、拉直到自然恢復；不為等系統而延遲必要介入 |
| 連續彎／短直線接下一彎 | 3次 | 作反例，正常駕駛，不故意要求加速 |
| 前車正常轉出／換道離開 | 各3次自然機會 | 記下同一前車何時離開；同步收集短暫遮擋後重現，不製造危險cut-in |
| 無前車紅燈轉綠 | 3次自然機會 | 保留轉綠前至少10秒與轉綠後；照正常安全駕駛接管，不為測試阻塞車流 |
| 有前車起步 | 3次 | 與無前車綠燈分組，不用同一解除假說 |
| 穩定緩坡與近水平路段 | 各3次 | 以相近合法速度、固定設定，保留target、實際加速度與pitch；不做油門階躍或危險坡道測試 |

另需正常紅燈持續保持的負例至少3段；不要刻意晚煞測試。停止線幾何若要研究，先在停妥且安全位置量測camera-to-bumper並記錄可見參考，否則僅評估相對時序，不報精準公尺。

新一日／新route至少保留一組直線、出彎、lead與stop完全不調參，作真正新holdout。完整rlog、road／wide影片、當時Params與版本需同步保存；簡短記下介入原因即可，既有41件不用重標。

## 報告索引

- HYPOTHESIS_LEDGER.md：H0～H6證據與反證。
- ITERATION_HISTORY.md：所有候選、淘汰與工具失敗。
- COUNTEREXAMPLE_REPORT.md：Top50與控制權分類。
- CAN_REPRODUCIBILITY_REPORT.md：A/A根因、fixture與範圍。
- FREE_CRUISE_REPORT.md、CURVE_EXIT_REPORT.md：逐項效果。
- LEAD_MEMORY_REPORT.md、RESTART_REPORT.md：未解決限制。
- FINAL_VALIDATION_REPORT.md：凍結後gate。

研究分支：`my-crv-autonomous-longitudinal-research-20261005`。發布結果與最終report commit另存PUBLICATION_STATUS.json；未force push穩定分支。**COMMA_DEPLOYED = NO。上車仍需未來另行授權。**
