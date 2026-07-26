# Data_Analytics

A股数据分析项目。

## 国家产业投资基金持股筛选

基于最新财报（优先半年报，未充分披露则用一季报）的十大流通股东数据，筛选股东名称同时包含「国家」与「产业投资基金」的个股，并计算自 2026 年以来的最高涨幅倍数。

### 运行

```bash
pip install -r requirements.txt
python scripts/national_industry_fund_analysis.py
```

### 输出

- `output/matched_holders_detail.csv`：匹配到的股东明细
- `output/national_industry_fund_stocks.csv`：个股汇总与涨幅
- `output/report.md`：可读报告
