# 士兰微 (600460.SS) sample validation

```bash
python -m market_structure.cli validate --config configs/silan_micro.yaml
```

Note: no latent-phase alignment on real data. Judge states via `event_study.csv`
forward returns / hit-rates, then decide which states enter the tradeable set.
