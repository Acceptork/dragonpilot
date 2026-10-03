# BRANCH_CONSOLIDATION_REPORT

狀態：GitHub 整理完成；保留車端 updater 相容分支。DEVICE DEPLOYMENT = NOT RUN。

## 最終分支

原有 32 條；新增三條後 35 條；刪除 31 條；最終 4 條。Default branch = my-crv-latest。

| Branch | Exact runtime HEAD |
| --- | --- |
| my-crv-experimental | 9469a5ce68ed4a5636c77151491d37e42235d296 |
| my-crv-latest | 80e190108b86ed3d2fa7634546dc2b1fa88ae69c |
| my-crv-v2-baseline | a1e028371cdfe87471f694c87fc3d17060f969c4 |
| my-crv-v3.2-rc-candidate | 80e190108b86ed3d2fa7634546dc2b1fa88ae69c |

experimental 的後續 publication commit 僅新增本報告與 docs/mycrv-consolidation 證據；其 parent 為上列已測 runtime SHA。最終 publication HEAD 記錄於 branch_consolidation/publication_verified.json，並以 runtime tree 排除文件後完全相同作驗證。

## 保留已部署 RC 的原因

stable commit 已由 latest 與 archive/v3.2-rc-80e190108b86 永久可達；experimental 包含 latest 歷史。v2 baseline 及 archive/long-tune-v2-a1e028371cdf 保留回退基準。

在 stable80e 的 system/updated/updated.py，target_branch 讀 UpdaterTargetBranch，未設定則使用目前 checkout branch；check_for_update 對消失的 target 回報 no remote update available，fetch_update 仍 fetch 指定 target。更改 GitHub default 不會自動遷移此設定。因此保留 my-crv-v3.2-rc-candidate，避免車端失去更新來源；沒有讀取或修改車端。

## 測試與回放

latest 80e：native build、cruise/helper/diagnostic unit、Honda/longitudinal/MPC、panda Honda safety、UI 均 exit 0；42 段 continuous native replay 完成。部署工具另有整合單元測試證據。

experimental 9469：native build PASS；354 unit passed；Honda/long/MPC 48 passed + 58 subtests；panda 311 tests / 52 skipped；UI 209 passed / 2 skipped。原生 isolation 140 cases、combined stop controlsd 六種場景 × 四組開關、部署/回退工具測試通過。

最終 42/42 全 OFF 對 latest：PASS_IDENTITY。alignment mismatch 0；控制/CAN 差異 0；lost BRAKE_REQUEST 0；GAS increases 0；lost FCW/shouldStop 0；longActive mismatch 0。這是 fixed-input replay 證據，不宣稱實車物理結果。

控制功能八個開關預設 OFF；仍保留各功能 commit 與獨立 archive tag。stop taper 尚有四個 downhill overrun plant 反例，初次測試限平地；overtake Stage 2 仍 BLOCKED。未改 panda/FCW/steering safety。

## 舊分支與封存

MERGED 僅代表 HEAD ancestry 可證明；不以功能相似冒充已 merge。其餘只 archived，歷史與失敗證據完整保存。刪除使用 exact SHA lease 與 atomic push，刪除前後核對 annotated tag object / peeled commit。

| 舊 branch | HEAD | 類別 | tag | latest ancestor | experimental ancestor | Remote |
| --- | --- | --- | --- | --- | --- | --- |
| installer-my-crv | 8cca12d56b4c835bce284292b23a24385934c9d8 | SUPERSEDED | archive/installer-my-crv-8cca12d56b4c | False | False | DELETED |
| my-crv | 418216c4f8b87403aa22177a998af8c7b5c77a8c | MERGED | archive/my-crv-418216c4f8b8 | True | True | DELETED |
| my-crv-alerts-zh-tw-candidate | ca36a14e32ec4eb90a46712c5c87082faf2921d4 | SUPERSEDED | archive/alerts-zh-tw-ca36a14e32ec | False | False | DELETED |
| my-crv-bookmark-v1-candidate | 4b7c7b4b43bf9b873dab0f47d00152eb9c381c7b | SUPERSEDED | archive/bookmark-v1-4b7c7b4b43bf | False | False | DELETED |
| my-crv-buttons10-isolation-candidate | d5fc787f067a8f49452e7d9ee2421dab18635945 | FAILED | failed/buttons10-isolation-d5fc787f067a | False | False | DELETED |
| my-crv-buttons10-single-v1-candidate | c568e2782d00f96d79d38e4f91e942309b6e152e | SUPERSEDED | archive/buttons10-single-v1-c568e2782d00 | False | False | DELETED |
| my-crv-buttons10-v32-candidate | ed015216129ed430e8f6216a33fd1ab16a001216 | SUPERSEDED | archive/buttons10-v32-ed015216129e | False | False | DELETED |
| my-crv-deploy-hardening-v1-candidate | b97e7e24f5318163e277936465fe8019ec53ceea | SUPERSEDED | archive/deploy-hardening-v1-b97e7e24f531 | False | False | DELETED |
| my-crv-dynamic-alerts-zh-tw-candidate | 1a849d5a311781a0d9527da7ffe72ed28d06580d | SUPERSEDED | archive/dynamic-alerts-zh-tw-1a849d5a3117 | False | False | DELETED |
| my-crv-lateral-return-v1-candidate | 539fcad41075ee322ce9ac7c89620a40d92a1810 | RESEARCH | archive/lateral-return-v1-539fcad41075 | False | False | DELETED |
| my-crv-lca-v1-candidate | 1a81fb776e5b389ce0aa9be15361e490f753b006 | RESEARCH | archive/lca-v1-1a81fb776e5b | False | False | DELETED |
| my-crv-lca-v2-candidate | 2eef6f2eb41a3c7e42cd09d15fba556896a9af29 | RESEARCH | archive/lca-v2-2eef6f2eb41a | False | False | DELETED |
| my-crv-lca-v32-candidate | ee63696ff09768948762d0dded4508ffb41876d1 | RESEARCH | archive/lca-v32-ee63696ff097 | False | False | DELETED |
| my-crv-lead-memory-v32-shadow | c836c6d731e15e30ba2d406f6e4baa1c03e7e21b | RESEARCH | archive/lead-memory-v32-shadow-c836c6d731e1 | False | False | DELETED |
| my-crv-long-tune-v2 | a1e028371cdfe87471f694c87fc3d17060f969c4 | MERGED | archive/long-tune-v2-a1e028371cdf | True | True | DELETED |
| my-crv-long-tune-v3-candidate | a201e6cb75296bb1700dadf9268d857a9a597016 | MERGED | archive/long-tune-v3-a201e6cb7529 | True | True | DELETED |
| my-crv-long-v3.1-candidate | 01772318a8ced599f90a3ea0b0cbec8cc25b2a1d | SUPERSEDED | archive/long-v3.1-01772318a8ce | False | False | DELETED |
| my-crv-overtake-preaccel-v1-candidate | 68094e06c4029005e1ea01b4395bbb759216ff15 | RESEARCH | archive/overtake-preaccel-v1-68094e06c402 | False | False | DELETED |
| my-crv-overtake-v32-research | c4ee2073d055e00caa860a76d1ccb125fe5300bc | RESEARCH | archive/overtake-v32-research-c4ee2073d055 | False | False | DELETED |
| my-crv-personality-v32-candidate | b84f559815fd8dadcab4e448b39d2fcdf0cd443a | FAILED | failed/personality-v32-b84f559815fd | False | False | DELETED |
| my-crv-planner-trace-v32 | e845f70ee3270d327097360aa943894401699d92 | SUPERSEDED | archive/planner-trace-v32-e845f70ee327 | False | False | DELETED |
| my-crv-resume-v31-candidate | a14b0a4f707a6d32588d13832d844f2351c6e56c | SUPERSEDED | archive/resume-v31-a14b0a4f707a | False | False | DELETED |
| my-crv-set30-isolation-candidate | 177d55b52508a65fda8700f4216ffad55a18ab37 | FAILED | failed/set30-isolation-177d55b52508 | False | False | DELETED |
| my-crv-set30-v32-candidate | de4ae3f962281939297fee430d16c8a49845b15c | SUPERSEDED | archive/set30-v32-de4ae3f96228 | False | False | DELETED |
| my-crv-stop-intent-v32-shadow | 8a692943afd62d8593e845e6abbfd0f0159065b5 | RESEARCH | archive/stop-intent-v32-shadow-8a692943afd6 | False | False | DELETED |
| my-crv-stop-v2-candidate | e488f0fbd8013df0f6bd053807381f1ba7f889a6 | RESEARCH | archive/stop-v2-e488f0fbd801 | False | False | DELETED |
| my-crv-v3.1-deploy-tools-candidate | efaad26731712cd4dfd13746ffdf97fb9164a9cf | SUPERSEDED | archive/v3.1-deploy-tools-efaad2673171 | False | False | DELETED |
| my-crv-v3.1-rc1 | c791595652c2b7e24bbdf7165f65d4b217b08c4e | MERGED | archive/v3.1-rc1-c791595652c2 | True | True | DELETED |
| my-crv-v3.2-candidate | 80e190108b86ed3d2fa7634546dc2b1fa88ae69c | MERGED | archive/v3.2-80e190108b86 | True | True | DELETED |
| my-crv-v3.2-rc-candidate | 80e190108b86ed3d2fa7634546dc2b1fa88ae69c | MERGED | archive/v3.2-rc-80e190108b86 | True | True | KEEP updater compatibility |
| my-crv-zh-tw-complete | a422934c1576b84ea90e29223546e9fd42850c4b | SUPERSEDED | archive/zh-tw-complete-a422934c1576 | False | False | DELETED |
| pre-build | 94ad85cfda64773a960d048dc11cac02d4aa86a5 | MERGED | archive/pre-build-94ad85cfda64 | True | True | DELETED |

## Reachability

原始本地盤點中的 86 個 unique unreachable commits 全部已由 86 個已重新驗證 remote recovery tags 保存。部分舊本地 clone 仍會顯示 unreachable，因尚未 fetch recovery refs；不是歷史遺失。publication repository fsck：0 unreachable commits。無法直接檢查 GitHub server 的 object database，因此不宣稱全伺服器零 unreachable。

## 證據

docs/mycrv-consolidation/evidence 內包含 remote exact refs、default branch、刪除前後 tags、reachability、latest tests、experimental software gate、42 段 identity 與 feature gates。所有原始 replay 大型資料留在本地，未將未通過物理驗證改標 production。
