# 自動反例搜尋

四個離線候選各完成 237,618 個可用 frame 的原生回放。全資料包含指定日期 185,276 frame、較早輔助資料 3,038、歷史安全資料 49,304；不含缺失記錄。先掃 TRAIN／VALIDATION，凍結 H1-R20 後才檢查其 HOLDOUT。被淘汰 H2 未拿 holdout 反覆調參。

每版各取最大正增量、負 target 減弱、停止正向增量、近 lead 正向增量、cut-in 代理正向增量、彎道正向增量、solver 異常與最長新增作用的 Top 50；不足 50 即保留實際筆數，不湊數。同時保留全訊號及有 OP 控制權兩套分類。

Top 50 是極端 frame，不是假稱 50 件獨立事件；最長作用另外以時間連續 episode 排序。cut-in 代理使用 lead 新出現／距離跳近與近距離條件，不聲稱可靠物體身分。變化摘要以 1e-6 m/s² 區分實質變動；CAN A/A 比較仍是零容差，沒有用這個門檻遮掩控制差異。

## H1

R10／R15／R20 開發集均未出現 lost FCW、lost shouldStop、新 solver failure、非有限 target、負 target 減弱、停止／近 lead／cut-in 代理／高曲率正向增量，或 baseline -0.2 門檻制動起始被候選延後。

R20 最大新增約 0.49706，發生在有控制權、無踏板、無 lead／stop 標記的視窗；其原生 policy 仍受 fresh／valid、完整路徑、未來曲率、memory、加速度與 ramp 約束。這是通過已定義訊號檢查，不代表畫面所有危險都被辨識。event_041 原 27 frame 誤觸已消失，該事件屬 TRAIN，不能再當 holdout 證據。

## H2

若不區分控制權，會得到 VALIDATION 21 個停止正向增量、TRAIN 189 個負 target 減弱等數字。核對後這些不是具有 OP 控制權的退化，部分來自 Honda OEM／手動／踏板輸入。報告不把它們誇大成實車控制問題。

真正有控制權的 TRAIN：225 個實質變更、其中 216 個仍有曲率標記，最大新增 0.35；有控制權的 VALIDATION：0 個實質變更。沒有看到 active stop、close lead、cut-in 或負 target 減弱，但作用在彎中、缺少獨立出彎效果仍足以淘汰。

## 保留集

H1-R20 HOLDOUT 81,833 frame 全部沒有新作用，故 Top 50 清單為空。不能將「沒有測到功能作用」包裝成有效性 PASS。完整 41 件＋6 件歷史窗資料均對齊且齊全；個別結果留在本機 FULL_EVENT_VALIDATION 檔。

本機原始極端清單為 `ab_development_top50.private.json`、`h2_development_top50.private.json`、`ab_holdout_top50.private.json`。GitHub 不上傳 route 身分與精確時間軸。
