"""02 — Train the Usage_kWh and PF_Physical surrogate models.

features.parquet  ->  models/usage_model.json, models/pf_model.json (+ metrics)
"""
import json

import pandas as pd

import _bootstrap  # noqa: F401
from src import config, surrogate_model


def main() -> None:
    config.ensure_dirs()

    df = pd.read_parquet(config.FEATURES_PARQUET)
    print(f"Training surrogates on {len(df):,} rows, features={config.FEATURES}")

    model_usage, model_pf, metrics = surrogate_model.train_surrogates(df)
    surrogate_model.save_models(model_usage, model_pf)

    metrics_path = config.REPORTS_DIR / "surrogate_metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    print("✅ models saved:")
    print(f"   {config.USAGE_MODEL_PATH}")
    print(f"   {config.PF_MODEL_PATH}")
    print(f"   Usage : MAE={metrics['usage_mae']:.4f}  R2={metrics['usage_r2']:.4f}")
    print(f"   PF    : MAE={metrics['pf_mae']:.4f}  R2={metrics['pf_r2']:.4f}")
    print(f"   metrics -> {metrics_path}")


if __name__ == "__main__":
    main()
