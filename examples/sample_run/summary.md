# Market Structure Validation Report

## Verdict

规则回测略偏正，需样本外复核；合成潜变量对齐最好的是 A_DISTRIBUTE→A (lift=2.95)；事件研究头部状态: W3_EXPAND (n=30)

## Backtest

| Metric | Value |
|---|---|
| n_bars | 1200 |
| n_entries | 86 |
| n_trades | 70 |
| hold_bars | 5 |
| total_return | 0.1923 |
| cagr_proxy | 0.0376 |
| vol_ann | 0.1678 |
| sharpe | 0.3054 |
| max_drawdown | -0.1978 |
| hit_rate | 0.5286 |
| avg_trade | 0.0018 |
| profit_factor | 1.1382 |

## Top States (event study)

| state | n | side | net_mean_5 | hit_5 |
|---|---:|---:|---:|---:|
| W3_EXPAND | 30 | 1 | 0.0098 | 0.6667 |
| SWEEP_RECLAIM_SHORT | 14 | -1 | 0.0085 | 0.5714 |
| TREND_EXPAND | 52 | 1 | 0.0037 | 0.5769 |
| A_DISTRIBUTE | 33 | -1 | 0.0022 | 0.5455 |
| W2_END_CANDIDATE | 6 | 1 | -0.0014 | 0.3333 |
| ACCUMULATE | 2 | 1 | -0.0044 | 0.5000 |
| W4_CLEANUP | 89 | 0 | -0.0056 | 0.5227 |
| W5_EXHAUST | 17 | -1 | -0.0070 | 0.4375 |

## Latent Phase Alignment (synthetic)

| state | target | n | hit | baseline | lift |
|---|---|---:|---:|---:|---:|
| A_DISTRIBUTE | A | 33 | 0.2727 | 0.0925 | 2.9484 |
| W3_EXPAND | W3 | 30 | 0.6333 | 0.2183 | 2.9008 |
| W5_EXHAUST | W5 | 17 | 0.4118 | 0.1483 | 2.7759 |
| B_TRAP | B | 33 | 0.1515 | 0.0742 | 2.0429 |
| W4_CLEANUP | W4 | 89 | 0.1461 | 0.0958 | 1.5242 |
| SWEEP_RECLAIM_LONG | W2|W3 | 22 | 0.2273 | 0.3333 | 0.6818 |
| SWEEP_RECLAIM_SHORT | A|C | 14 | 0.0000 | 0.2050 | 0.0000 |

## Framework

- 波浪层：可计算阶段候选（非主观数浪）
- 流动性层：池 / 清扫 / 收回
- 订单流层：失衡 / 吸收 / 效率 / 背离代理
- 验证层：事件研究 + 规则回测
