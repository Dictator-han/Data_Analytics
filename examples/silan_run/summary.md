# Market Structure Validation Report

## Verdict

规则回测略偏正，需样本外复核；事件研究头部状态: TREND_EXPAND (n=62)

## Backtest

| Metric | Value |
|---|---|
| n_bars | 2074 |
| n_entries | 117 |
| n_trades | 97 |
| hold_bars | 5 |
| total_return | 0.1571 |
| cagr_proxy | 0.0179 |
| vol_ann | 0.2725 |
| sharpe | 0.2017 |
| max_drawdown | -0.4608 |
| hit_rate | 0.5361 |
| avg_trade | 0.0046 |
| profit_factor | 1.2120 |

## Top States (event study)

| state | n | side | net_mean_5 | hit_5 |
|---|---:|---:|---:|---:|
| TREND_EXPAND | 62 | 1 | 0.0085 | 0.5484 |
| B_TRAP | 88 | -1 | 0.0084 | 0.5227 |
| W2_END_CANDIDATE | 12 | 1 | 0.0061 | 0.5833 |
| W3_EXPAND | 44 | 1 | 0.0058 | 0.5000 |
| ABSORB | 6 | 1 | 0.0025 | 0.5000 |
| W5_EXHAUST | 39 | -1 | 0.0005 | 0.7179 |
| SWEEP_RECLAIM_LONG | 26 | 1 | -0.0005 | 0.6154 |
| W4_CLEANUP | 166 | 0 | -0.0061 | 0.4398 |

## Latent Phase Alignment (synthetic)

_Not available (needs synthetic latent labels)_

## Framework

- 波浪层：可计算阶段候选（非主观数浪）
- 流动性层：池 / 清扫 / 收回
- 订单流层：失衡 / 吸收 / 效率 / 背离代理
- 验证层：事件研究 + 规则回测
