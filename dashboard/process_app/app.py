# dashboard/process_app/app.py
# Standalone process-flow dashboard (the "공정" page), run separately from the
# main energy/carbon dashboard. Secret key and port are read from the
# environment (.env), never hardcoded.
import os
from pathlib import Path

from flask import Flask, render_template, request, jsonify
import random
import requests

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


_load_dotenv(REPO_ROOT / ".env")

SERVICE_KEY = os.environ.get("DATA_GO_KR_SERVICE_KEY", "")
BASE_URL = "https://apis.data.go.kr/1160100/service/GetGeneralProductInfoService/getCertifiedEmissionReductionPriceInfo"
PROCESS_PORT = int(os.environ.get("DASHBOARD_PROCESS_PORT", "4444"))

app = Flask(__name__)


@app.template_filter("fmt")
def fmt(v):
    try:
        return f"{int(v):,}"
    except Exception:
        return v


@app.get("/")
def home():
    # 예시 데이터 (모델 결과로 교체 가능)
    current_cost = 35640
    previous_cost = 32500
    potential_savings = 804000
    unit = "원"

    cost_change = current_cost - previous_cost
    change_percentage = (cost_change / previous_cost * 100) if previous_cost else 0.0
    is_increase = cost_change > 0

    cost_trend_data = [
        {"time": "09:00", "actual": 28500, "projected": 28500},
        {"time": "10:00", "actual": 32000, "projected": 30500},
        {"time": "11:00", "actual": 35000, "projected": 31800},
        {"time": "12:00", "actual": 38500, "projected": 33200},
        {"time": "13:00", "actual": 42000, "projected": 34500},
        {"time": "14:00", "actual": 35000, "projected": 30100},
        {"time": "15:00", "actual": 33000, "projected": 28800},
        {"time": "16:00", "actual": 37000, "projected": 31500},
    ]

    processes = [
        {"processName": "원자재 입고", "powerConsumption": 45.2, "maxPower": 60, "cost": 5424, "efficiency": 85, "status": "normal"},
        {"processName": "전처리 공정", "powerConsumption": 88.5, "maxPower": 100, "cost": 10620, "efficiency": 72, "status": "warning"},
        {"processName": "조립 라인", "powerConsumption": 125.8, "maxPower": 130, "cost": 15096, "efficiency": 65, "status": "critical"},
        {"processName": "품질 검사", "powerConsumption": 32.5, "maxPower": 50, "cost": 3900, "efficiency": 88, "status": "normal"},
    ]

    return render_template(
        "index.html",
        current_cost=current_cost,
        previous_cost=previous_cost,
        potential_savings=potential_savings,
        unit=unit,
        is_increase=is_increase,
        change_percentage=change_percentage,
        cost_trend_data=cost_trend_data,
        processes=processes,
        monthly_cost=current_cost,
        monthly_savings=potential_savings,
    )


@app.post("/api/analyze")
def api_analyze():
    data = request.get_json(silent=True) or {}
    module_name = (data.get("module") or "").strip()
    try:
        user_value = float(data.get("value", 0))
    except Exception:
        user_value = 0.0

    trend_data = [round(user_value * (1 + random.uniform(-0.05, 0.05)), 1) for _ in range(7)]

    status = "정상 작동 중"
    if module_name == "제선" and user_value > 1500:
        status = "고온 경고! 냉각 필요"
    elif module_name == "압연" and user_value < 5:
        status = "두께 부족! 공정 재확인"

    return jsonify({
        "module": module_name,
        "status": status,
        "trend": trend_data,
        "labels": ["09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00"],
    })


@app.get("/api/kau25-monthly")
def api_kau25_monthly():
    start_ym = "202502"
    end_ym = "202602"

    def month_range(yyyymm_start, yyyymm_end):
        ys, ms = int(yyyymm_start[:4]), int(yyyymm_start[4:])
        ye, me = int(yyyymm_end[:4]), int(yyyymm_end[4:])
        out = []
        y, m = ys, ms
        while (y < ye) or (y == ye and m <= me):
            out.append(f"{y:04d}{m:02d}")
            m += 1
            if m == 13:
                y += 1
                m = 1
        return out

    months_full = month_range(start_ym, end_ym)

    def extract_items(data):
        items = (
            data.get("response", {}).get("body", {}).get("items", {}).get("item", [])
        )
        if isinstance(items, dict):
            return [items]
        if isinstance(items, list):
            return items
        return []

    date_keys = ["basDt", "trdDd", "date"]
    close_keys = ["clpr", "close", "clsPrc"]
    name_keys = ["itmsNm", "itemName", "prodNm"]

    def pick(d, keys):
        for k in keys:
            v = d.get(k)
            if v not in (None, ""):
                return v
        return None

    monthly_best = {}  # ym -> (yyyymmdd, close)

    page = 1
    max_pages = 20
    while page <= max_pages:
        params = {
            "serviceKey": SERVICE_KEY,
            "pageNo": page,
            "numOfRows": 1000,
            "resultType": "json",
        }
        r = requests.get(BASE_URL, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()

        items = extract_items(data)
        if not items:
            break

        for it in items:
            nm = pick(it, name_keys)
            if nm and "KAU25" not in str(nm):
                continue

            raw_dt = pick(it, date_keys)
            raw_close = pick(it, close_keys)
            if raw_dt is None or raw_close is None:
                continue

            sdt = str(raw_dt).replace("-", "").replace(".", "").replace("/", "").strip()
            if len(sdt) >= 8:
                sdt = sdt[:8]
            else:
                continue

            ym = sdt[:6]
            if ym < start_ym or ym > end_ym:
                continue

            try:
                close_v = float(str(raw_close).replace(",", ""))
            except Exception:
                continue

            prev = monthly_best.get(ym)
            if (prev is None) or (sdt > prev[0]):
                monthly_best[ym] = (sdt, close_v)

        page += 1

    labels = [f"{m[:4]}/{m[4:]}" for m in months_full]
    closes = [monthly_best[m][1] if m in monthly_best else None for m in months_full]
    return jsonify({"labels": labels, "closes": closes})


if __name__ == "__main__":
    app.run(debug=True, port=PROCESS_PORT)
