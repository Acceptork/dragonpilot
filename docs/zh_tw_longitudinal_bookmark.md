# 縱向事件書籤：跨段保留範圍

本文件對應 `bookmarkButton`／`userBookmark` 流程及 v3.1 RC 的跨段保留修改。沒有新增車控訊號、錄影程序或資料上傳程式。

## 操作與資料流

行車畫面點一下以顯示側欄，再按旗標。`selfdrive/ui/layouts/main.py` 發送 `bookmarkButton`；`selfdrive/ui/feedback/feedbackd.py` 收到後發送 `userBookmark`；`system/loggerd/loggerd.cc` 為當前記錄 segment 設定 `user.preserve=1`，並對接下來 10 秒內新開啟的 segment 設 `user.preserve_followup=1`。旗標不是事故分類，也不判斷駕駛意圖。

## 實際保留範圍

- `loggerd` 正式 segment 長度為 60 秒；書籤標記當前 segment。
- 磁碟清理器對最近 **5 個**主要書籤，各自保留當前 segment、之前 **2 個** segment，以及後續 10 秒內切入且帶有 followup 標記的 segment。followup 不消耗主要書籤名額。
- 因此保留的完整原始 segment 涵蓋一般情況下事件前 15 秒與後 10 秒。它不會精確裁出 25 秒影片或 CSV，也不會額外複製影像。
- 清理器在低磁碟空間時優先刪除未保留資料，但保留不是永久備份保證；極端空間不足時仍可能刪除。書籤不能補救已遺失的片段。
- 原有 `loggerd` 仍將書籤路線加入 `AthenadRecentlyViewedRoutes`，供既有 uploader 優先處理；新增的 followup 不額外加入。使用前請知悉既有上傳行為。

若需要精準的事件前 15 秒、後 10 秒剪輯，須另做有容量限制的離線裁切，並明確決定是否允許原有路線上傳機制。

## OVERTAKE_PREACCEL 訊號限制

目前沒有經生產驗證的 `OVERTAKE_PREACCEL` 狀態或加速度輸出，因此 HUD 不會虛構「超車預加速」已啟用。只有後端狀態與舊前車路徑清空條件都被驗證後，才能用真實訊號驅動相關文字；不能只由方向燈或油門數值推測。
