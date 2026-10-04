公開彙總版。完整逐事件分析、時間同步、人工分類與私有證據保留於本機；本檔不含可識別行車元資料。

# Honda 行為參考（公開彙總）

採儀表速度 deficit、1 秒中位數、120 秒 block 與保留事件區域，排除已確認測試／主動操作附近樣本。
36 個觀測 cell，4 個符合至少 20 TRAIN 秒、至少 2 TRAIN blocks。支持格都接近設定速度；deficit≥5 km/h 無支持格。
因此可描述穩態巡航，不能據此學出可信的積極追速幅度。只有一條 Honda 路線，非獨立跨路線驗證。

跟車按 speed/dRel/vRel 分格。前車消失有 10 個可連續觀察 2 秒的候選，但尚未做同 deficit／曲率的配對因果比較。
沒有可識別的 Honda lead-movement→ego-movement 起步 envelope。pitch 僅作條件分布，不冒充已識別坡度補償。
HONDA_REFERENCE_USABLE = PARTIAL_DESCRIPTIVE。
