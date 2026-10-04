公開彙總版。完整逐事件分析、時間同步、人工分類與私有證據保留於本機；本檔不含可識別行車元資料。

# 八功能實際效果（公開彙總）

只計原始日誌中 OP 系統控制、非程式測試模式。日誌降頻，秒數為 sample-and-hold 估計，不能当作精確 actuator duration。

|功能|active 筆數|改值筆數|觀測 episode|改值秒數估計|
|---|---|---|---|---|
|early_stop|25|25|3|9.315|
|taper|46|46|1|1.502|
|restart|173|164|5|82.042|
|lca|186|0|0|0.000|
|personality|0|0|0|0.000|
|ramp|3|3|2|0.519|
|overtake|2|2|1|0.351|
|lead_memory|1|136|25|66.453|

early_stop/taper 有負向作用，保留停止保護與舒適曲線。restart 雖可能不改 aTarget，仍會改 shouldStop；無前車適用性需重作。lead_memory active 不代表全部限制時間，UNKNOWN 仍會壓制輸出。
personality 本次效果為零，降級為未證明有效；ramp/overtake 稀疏，且 ramp 順序回放與原始持續性資格有差異。lca 屬橫向，不能因縱向 target 不變就說無效。
六個 planner 功能已做 leave-one-out；尚無八功能各自完整的 CAN 因果歸因，不將 UI ON、日誌改值與 sendcan 因果畫上等號。production path 未移除或改寫；處置為研究判定。