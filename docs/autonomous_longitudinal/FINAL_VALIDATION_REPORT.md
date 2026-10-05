# 凍結後最終驗證

研究 SHA：`899421a2e0fb795187df4982072239043ed91ff9`。最佳部分假說 H1-R20，沒有 production 接線。研究狀態為 **NEEDS_NEW_REAL_WORLD_DATA**，不是 READY_FOR_ROAD_A_B_TEST。

| Gate | 結果 | 證據與限制 |
|---|---|---|
| TRAIN | 部分有效，整體未通過 | BAD04／05改善；BAD03未解決 |
| VALIDATION | 部分有效，整體未通過 | R20有428 frame實質作用；H2有控制權時無獨立改善 |
| HOLDOUT | 未通過有效性驗證 | 81833 frame完全未觸發，不能證明新功能效果 |
| SAFETY | 未完成release-grade證明 | 已掃planner無關鍵訊號遺失；未完成最終候選完整CAN A/B與物理閉迴路 |
| CAN_REPRODUCIBILITY | 限定A/A通過 | 五組含跨段CAN完全一致；全路線全程序範圍仍未完成 |
| FULL_REPLAY | 原生planner執行完成；整體未通過 | 每候選237618 frame；不是完整車輛／CAN候選驗證 |

41件標註全部有效、文字選填；本輪沒有要求重新標註。41件加6件歷史事件窗均齊全、對齊。R20的 BAD02、STOP01、lead holdout、歷史005／010／011／014／020 的 planner target 未改變；event_041亦未改變，但已屬TRAIN。這不是把主觀分類當根因，也不是聲稱 CAN BRAKE_REQUEST 已完成候選驗證。

原生 baseline 來源與固定公開 SHA的檔案 SHA256均為 `b0770e16bc10c2096c0efa49ae474cf8b0fc37922fe988fc9a3049621d854899`。獨立H1/H2兩次回放共237618個baseline frame，model timestamp、速度、e2e、MPC、final target、stop、FCW、solver、cap與source逐項完全一致。

新增工具測試：比較器8項、H1新增14項加原76項、H2隔離測試6項均通過；兩個公開通用runner smoke各838 frame執行成功。在上述凍結SHA重跑原生build通過、Honda／縱向317項通過、panda Honda safety 315項通過／255項平台設定跳過。各exit code均為0。這些程式測試不能抵銷效果／holdout不足，也沒有把未執行的候選完整CAN gate標成PASS。

沒有合併 H1+H2，沒有降低FCW、hardBrake、panda safety、actuator限制或tFollow。沒有改 stop comfort、taper或HOLD。沒有 release tag、沒有comma連線／Params寫入／部署。

原V3.3.1結果仍是RESEARCH_ONLY／不可部署：27 frame stop-window recovery、BAD03無改善、舊A/A130未對齊及1個CONTROL_ON差異、舊full CAN gate不可信、holdout未通過；新fixture修復不追溯改寫舊結果。
