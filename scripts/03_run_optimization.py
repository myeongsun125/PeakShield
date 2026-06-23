"""03 — Run the digital-twin optimization for one or more tariff scenarios.

features.parquet + models + config  ->  data/processed/sim_<scenario>.parquet

  --scenarios A B    explicit scenario keys (default: config.DEFAULT_SCENARIOS)
  --limit N          run on the first N rows only (fast smoke test)
  --labor-premium X  야간 인건비 할증 (원/kWh), default 20.0
"""
import argparse
import json

import pandas as pd

import _bootstrap  # noqa: F401
from src import config, surrogate_model
from src.simulator import HybridFastSimulator


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenarios", nargs="+", default=config.DEFAULT_SCENARIOS)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--labor-premium", type=float, default=config.DEFAULT_LABOR_PREMIUM)
    args = parser.parse_args()

    config.ensure_dirs()

    df = pd.read_parquet(config.FEATURES_PARQUET)
    if args.limit:
        df = df.iloc[: args.limit].reset_index(drop=True)
        print(f"[smoke] limited to first {len(df):,} rows")

    with open(config.REACTIVE_MAXIMA_JSON, "r", encoding="utf-8") as f:
        maxima = json.load(f)

    model_usage, model_pf = surrogate_model.load_models()

    simulator = HybridFastSimulator(
        model_usage, model_pf, config.FEATURES,
        str(config.CONFIG_JSON), maxima["max_lagging"], maxima["max_leading"],
    )
    simulator.precompute_grid(df)

    for key in args.scenarios:
        result_df = simulator.run_scenario(df, key, labor_premium=args.labor_premium)
        out = config.PROCESSED_DIR / f"sim_{key}.parquet"
        result_df.to_parquet(out)

        final_deficit = result_df.iloc[-1]["Deficit_Status"]
        print(f"✅ {key}: {len(result_df):,} rows -> {out}  (final deficit={final_deficit:.2f})")


if __name__ == "__main__":
    main()
