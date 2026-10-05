# 出彎上限與解除

H2 確認 BAD03 的主要限制不是 selector。介入前 3 秒，e2e 中位數 0.956、MPC 1.464，但合成正上限中位數為 0。

原公式使用車速、扣除 angleOffset 的方向盤角、固定 CP steerRatio 和 wheelbase。逐 frame 重算與原 turn cap 一致。公式估計側向加速度中位數 2.883；controlsState 的 VehicleModel 推導值 2.376；模型未來路徑側向負荷 2.767。當時總額度 1.700，因此不是單純 stale curvature 或 selector 應加速卻不加速。

原公式確有與 VehicleModel 不同的估計，但不能直接把差值當成可用油門空間。上限解除還受既有每個模型 frame +0.05 的平滑限制；此次保留這一層。

## 狀態審查

區分 CURVE_APPROACH、CURVE_ACTIVE、CURVE_EXIT_PENDING、CURVE_EXIT_CLEAR 的必要性成立。本次建立診斷時間線，而不是把尚未驗證的狀態機接上控制。

在 BAD03 最後 60 frame 中，有 51 frame 當前側向負荷仍高於 recovery 所用的 0.5 門檻；只有最後 9 frame 同時滿足低當前曲率、低未來曲率、turn cap 已釋放的幾何條件。第一次約在駕駛介入前 0.424 秒，甚至不足原候選 0.6 秒清晰道路等待。

因此，「入彎／彎中限制確已結束」與「駕駛主觀覺得應該加速」需要新的同步動態／影像證據校準。不能把車輛仍在轉彎的資料硬標 EXIT_CLEAR。

## 獨立公式候選與淘汰

H2-VM-CAP 僅替換當前側向負荷來源，維持相同總額度、selector、MPC、停止／跟車／memory，沒有 H1 recovery。

BAD03 平均 target：0.15833→0.21005，最大單 frame 增量 0.150。持續正 target 的開始由介入前 0.774 秒變成 0.925 秒，約提前 0.151 秒。但這發生在既定 EXIT_CLEAR 幾何條件之前，不能把它稱為已安全解除後的成功恢復。

TRAIN 有控制權時增加 225 frame，其中 216 frame 仍符合曲率／未來曲率風險標記。最大新增 0.35 時，當前側向負荷約 1.396、未來約 1.657，並非低曲率道路。VALIDATION 有控制權的 2,380 frame 沒有實質 target 差異。

這個候選未證明獨立出彎效益，且作用位置不符合狹義 EXIT_CLEAR，故淘汰，未與 H1 組合。不能把全部非控制區段出現的 target 差異當成實際煞車退化；詳見反例報告。

最佳保留的 H1-R20 在 BAD02 入彎窗、停止正例及出彎 holdout 的 final target 均未改變。這只證明沒有修改該批 planner 軌跡，不能證明出彎問題已解決。
