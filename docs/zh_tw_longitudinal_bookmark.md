# 縱向事件書籤：現有功能與保留範圍

本文件對應 `my-crv-zh-tw-complete` 的原始 `bookmarkButton`／`userBookmark` 流程。這個分支沒有新增車控訊號、錄影程序或資料上傳程式。

## 操作與資料流

行車畫面點一下以顯示側欄，再按旗標。`selfdrive/ui/layouts/main.py` 發送 `bookmarkButton`；`selfdrive/ui/feedback/feedbackd.py` 收到後發送 `userBookmark`；`system/loggerd/loggerd.cc` 為**當前**記錄 segment 設定 `user.preserve=1`。旗標不是事故分類，也不會判斷當下的駕駛意圖。它僅標記記錄所在路段。

## 實際保留範圍

- `loggerd` 的正式 segment 長度為 60 秒；書籤標記當前 segment。
- 磁碟清理器對最近 **5 個**帶有保留標記的 segment，各自納入該 segment 與**之前 2 個** segment。這項邏輯能涵蓋一般情況下書籤前 15 秒。
- 沒有標記**下一個** segment。若按旗標時距離當前 segment 結束少於 10 秒，所要求的「事件後 10 秒」可能落入未保留的下一段。書籤也不會精確裁出事件前 15 秒／後 10 秒的影片或 CSV。
- 清理器在低磁碟空間時優先刪除未保留資料，但保留集合不是永久保證；所有候選資料都可能在空間極端不足時被刪除。書籤也不能補救先前已遺失的片段。
- 原有 `loggerd` 同時把書籤路線加入 `AthenadRecentlyViewedRoutes`，供 uploader 優先處理。使用此功能前應知悉該原有上傳行為；本分支不會額外上傳私人路線或影片。

因此，現有旗標適合快速標記與優先保存附近路段，但**尚不滿足可保證事件前 15 秒、後 10 秒的本機事件剪輯**。若將來需要精確區間，須另做有容量限制的非阻塞錄製設計與測試，且明確決定是否允許原有的路線上傳機制。

## OVERTAKE_PREACCEL 訊號限制

此基準分支找不到 `OVERTAKE_PREACCEL` 的狀態欄位或生產者，因此 HUD 不顯示「超車預加速」、「等待駕駛確認變道」、「前車限制加速」、「變道完成，恢復巡航」。只有定義並驗證後端狀態語意後，才能以真實訊號驅動這些文字；不能由方向燈或油門數值猜測。
