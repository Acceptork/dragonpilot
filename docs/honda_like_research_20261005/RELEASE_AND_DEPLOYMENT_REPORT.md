公開彙總版。完整逐事件分析、時間同步、人工分類與私有證據保留於本機；本檔不含可識別行車元資料。

# 發布與部署 — RESEARCH_ONLY / NOT_DEPLOYABLE

CANDIDATE_BRANCH = my-crv-v3.3-honda-like-research-public-20261005
CANDIDATE_CODE_COMMIT = 3a81678fd4636ed86396ec8bb9a3adfb95238df2
TOTAL_ANNOTATIONS = 41/41
ANALYSIS_COMPLETE = PARTIAL_EVIDENCE_LIMITED
COMMA_DEPLOYED = NO
GITHUB_TAG = NOT_CREATED_GATES_NOT_PASSED

候選程式、測試與彙總報告可公開；未修改既有穩定分支、未 force push。
新分支不包含原始影片、raw CAN、逐事件人工分類、精確行車時間、route ID 或 Params 快照。
車端仍是原 experimental commit，沒有 reboot 或變更使用者設定。
不部署原因：未證明任何改善，完整候選多程序 CAN gate、可接受的回放忠實度、獨立 holdout release gate 與部署 rollback 演練尚未全部成立。
回退基準 commit 在車端仍存在，但没有部署，不需執行 rollback；未假稱驗證過實際行車效果。

公開程式 SHA 的測試結果以同資料夾 SOFTWARE_TEST_RESULTS.md 為準；報告提交為純文件後代，不改控制程式。
