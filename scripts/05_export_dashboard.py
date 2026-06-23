"""05 — Export slim streaming CSVs for the realtime dashboard.

data/processed/sim_<scenario>.parquet + config
    -> data/processed/final_2018ver.csv   (from 2018 opt3)
    -> data/processed/final_2026ver.csv   (from 2026 opt3)
"""
import argparse
import json

import pandas as pd

import _bootstrap  # noqa: F401
from src import config, dashboard_export, psi


def _output_name(scenario_key: str) -> str:
    if "2018" in scenario_key:
        return "final_2018ver.csv"
    if "2026" in scenario_key:
        return "final_2026ver.csv"
    return f"final_{scenario_key}.csv"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenarios", nargs="+", default=config.DEFAULT_SCENARIOS)
    args = parser.parse_args()

    config.ensure_dirs()
    with open(config.CONFIG_JSON, "r", encoding="utf-8") as f:
        config_master = json.load(f)

    for key in args.scenarios:
        sim_path = config.PROCESSED_DIR / f"sim_{key}.parquet"
        if not sim_path.exists():
            print(f"⚠️ missing {sim_path} — run 03 first; skipping {key}")
            continue

        df_res = pd.read_parquet(sim_path)
        scenario_config = config_master["scenarios"][key]
        original_max_values = psi.get_psi_baseline_maxima(df_res)

        stream_df = dashboard_export.prepare_dashboard_stream_data(
            df_res, scenario_config, original_max_values
        )
        out = config.PROCESSED_DIR / _output_name(key)
        stream_df.to_csv(out, index=False, encoding="utf-8-sig")
        print(f"✅ {key}: {len(stream_df):,} rows -> {out}")


if __name__ == "__main__":
    main()
