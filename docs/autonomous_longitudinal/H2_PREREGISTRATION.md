# H2 獨立最小實驗

只比較原 turn-cap 公式與 controlsState 中 VehicleModel 推導的當前曲率。保持相同 1.7～3.2 總加速度額度、原 selector、MPC、stop、memory 與上限變化率。沒有 H1 recovery。

這是原程式 FIXME 所提示的公式替代假說，並不把 cap 設大。當 carState／controlsState／modelV2 無效或超過 0.2 秒，或曲率非有限值，沿用原公式。候選只在離線 wrapper 使用，不進 production。

TRAIN 比較 BAD03 是否真的較早／較強恢復，並搜尋所有 TRAIN／VALIDATION 彎道與停止反例。假如只在仍有高側向負荷時提高速度、或在模型要求制動時減弱制動，即淘汰。不得以效果數字取代安全 gate。

不能因為此公式在某事件有效就預設 VehicleModel 為幾何真值。需要檢查模型路徑、實際側向動態與未知偏差。
