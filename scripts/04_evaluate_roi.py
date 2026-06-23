"""04 — Financial ROI evaluation + final KEPCO-ready dataframe.

data/processed/sim_<scenario>.parquet + config
    -> reports/roi_summary.csv
    -> data/processed/final_opt3_kepco_ready.csv   (for 2018 opt3)
"""
import argparse
import io
import json
from contextlib import redirect_stdout

import pandas as pd

import _bootstrap  # noqa: F401
from src import config, economics

FINAL_DF_SCENARIO = "2018_industrial_HV_A_opt3"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenarios", nargs="+", default=config.DEFAULT_SCENARIOS)
    parser.add_argument("--labor-premium", type=float, default=config.DEFAULT_LABOR_PREMIUM)
    args = parser.parse_args()

    config.ensure_dirs()
    with open(config.CONFIG_JSON, "r", encoding="utf-8") as f:
        config_master = json.load(f)

    rows = []
    for key in args.scenarios:
        sim_path = config.PROCESSED_DIR / f"sim_{key}.parquet"
        if not sim_path.exists():
            print(f"⚠️ missing {sim_path} — run 03 first; skipping {key}")
            continue
        df_res = pd.read_parquet(sim_path)
        scenario_config = config_master["scenarios"][key]

        # PF penalty table prints internally; suppress it for a clean summary.
        with io.StringIO() as buf, redirect_stdout(buf):
            roi = economics.calculate_advanced_financial_roi(
                df_res, scenario_config, labor_premium=args.labor_premium
            )
        roi["Scenario"] = key
        rows.append(roi)

    if not rows:
        print("No scenarios evaluated.")
        return

    df_summary = pd.DataFrame(rows).set_index("Scenario")
    df_summary_m = (df_summary / 1_000_000).round(2)  # 백만 원

    summary_path = config.REPORTS_DIR / "roi_summary.csv"
    df_summary_m.to_csv(summary_path, encoding="utf-8-sig")
    print("=== 💰 재무 성과 요약 (백만 원) ===")
    print(df_summary_m[["Base_Savings", "Energy_Savings", "Net_Elec_Savings", "Extra_Labor", "Final_Real_ROI"]])
    print(f"-> {summary_path}")

    # 최종 KEPCO-ready DF (2018 opt3)
    if FINAL_DF_SCENARIO in args.scenarios:
        sim_path = config.PROCESSED_DIR / f"sim_{FINAL_DF_SCENARIO}.parquet"
        if sim_path.exists():
            df_res = pd.read_parquet(sim_path)
            scenario_config = config_master["scenarios"][FINAL_DF_SCENARIO]
            final_df = economics.build_final_kepco_df(df_res, scenario_config)
            out = config.PROCESSED_DIR / "final_opt3_kepco_ready.csv"
            final_df.to_csv(out, index=False, encoding="utf-8-sig")
            print(f"✅ final KEPCO-ready df -> {out} ({final_df.shape[0]:,} rows)")


if __name__ == "__main__":
    main()
