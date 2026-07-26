# Market Structure Lab

把艾略特波浪的主观浪型，改造成可验证的量化状态模型：

**市场结构（外观） + 流动性（机制） + 订单流代理（证据） + 事件研究/回测（验证）**

不做“预测现在是第几浪”，而做：

> 用可计算的市场机制条件，定义浪型阶段候选，并检验其是否有统计优势。

## 一层一句话

| 层级 | 回答的问题 | 本仓库实现 |
|---|---|---|
| 波浪 / 市场结构 | 价格现在像哪个阶段？ | swing、BOS、Fibonacci 回撤、阶段候选状态 |
| 流动性 | 为什么会走出这种结构？ | 流动性池、刺破、收回（sweep & reclaim） |
| 订单流代理 | 这个判断是否真实？ | 失衡、吸收、效率、量价背离（OHLCV 代理） |
| 验证 | 有没有可重复的边？ | 事件研究 + 规则回测 + 合成潜变量对齐 |

## 快速开始

```bash
python -m pip install -e ".[dev]"
python -m market_structure.cli validate --source synthetic --bars 1200 --seed 42
```

产物默认写到 `artifacts/validation/`：

- `summary.md` / `summary.json`：结论与指标
- `event_study.csv`：各状态事件的远期收益
- `phase_alignment.csv`：合成数据上，检测状态 vs 潜在浪段对齐
- `overview.png` / `states.png`：价格、信号、状态路径
- `annotated_frame.csv`：全特征面板

### 真实行情（可选，士兰微）

```bash
python -m pip install yfinance
python -m market_structure.cli validate --config configs/silan_micro.yaml
```

样例产物见 `examples/sample_run/`（合成）与 `examples/silan_run/`（600460.SS）。

或 CSV：

```bash
python -m market_structure.cli validate --csv /path/to/ohlcv.csv --out artifacts/csv_run
```

## 核心状态（机制层，不是主观数浪）

微观结构循环：

`ACCUMULATE → SWEEP → ABSORB → TREND_EXPAND → MANUFACTURE_LIQUIDITY → ...`

波浪代理（用流动性条件定义）：

- `W2_END_CANDIDATE`：回撤 0.5–0.618 + 刺破前低 + 放量 + 快速收回 + 卖压衰竭
- `W3_EXPAND`：高效率 + 正向失衡 + BOS 向上
- `W4_CLEANUP`：浅回撤、未深刺破
- `W5_EXHAUST`：创新高但量能/效率下降
- `A_DISTRIBUTE` / `B_TRAP` / `C_SWEEP`：调整段的释放、诱多、再清扫

## 项目结构

```
market_structure/
  data/          # 合成路径 / CSV / yfinance
  features/      # swing、fib、liquidity、orderflow
  states/        # 状态机与浪型代理评分
  signals/       # 多因子融合进出场
  validation/    # 事件研究 + 回测
  report/        # markdown/json/图
configs/default.yaml
tests/
```

## 设计原则

1. **浪是外观，流动性是机制**：状态名可以借用 W2/W3，但触发条件必须是可计算市场机制。
2. **先验证状态，再谈交易**：默认先看事件研究 hit-rate / 净均值，再看规则回测 Sharpe。
3. **合成数据用于对齐检验**：生成带 `latent_phase` 的路径，检测器在推理时不可见该标签，只在验证时测 lift。
4. **OHLCV 订单流只是代理**：若后续有 tick/L2，可替换 `features/orderflow.py` 而不改状态机接口。

## 测试

```bash
python -m pytest -q
```
