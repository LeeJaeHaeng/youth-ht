"""Kaggle LightGBM + XGBoost 앙상블 월세 예측 모델 학습 노트북.

## Kaggle 실행 방법
1. New Notebook → Script 타입
2. Input: collect_rent.py 노트북의 Output 데이터셋 추가
   - apt_rent_history.parquet
   - villa_rent_history.parquet
   - ecos_rate.parquet (이 스크립트에 ECOS 수집 포함)
   - hug_risk_by_sigungu.parquet (이 스크립트에 HUG 처리 포함)
3. Secrets: ECOS_KEY (ECOS 금리 수집용)
4. 실행 → Output: lgbm_rent_model.txt, xgb_rent_model.json,
                   ensemble_rent_metrics.json, lgbm_shap_global.json

## 로컬 실행 (수집 완료 후)
  python scripts/kaggle/train_lgbm.py
"""
from __future__ import annotations

import json
import os
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx
import lightgbm as lgb
import numpy as np
import polars as pl
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import GroupKFold

# ── 경로 설정 ─────────────────────────────────────────────────────────────────
IS_KAGGLE = Path("/kaggle").exists()
if IS_KAGGLE:
    INPUT_DIR = Path("/kaggle/input")
    # apt parquet 재귀 탐색 — /kaggle/input/datasets/<user>/<dataset>/ 등 깊이 무관
    _apt_found = next(INPUT_DIR.rglob("apt_rent_history.parquet"), None)
    RENT_DIR = _apt_found.parent if _apt_found else INPUT_DIR
    OUT_DIR = Path("/kaggle/working")
else:
    RENT_DIR = Path("data/processed")
    OUT_DIR = Path("data/processed")

OUT_DIR.mkdir(parents=True, exist_ok=True)

APT_PARQUET = RENT_DIR / "apt_rent_history.parquet"
VILLA_PARQUET = RENT_DIR / "villa_rent_history.parquet"
LGBM_MODEL_OUT = OUT_DIR / "lgbm_rent_model.txt"
XGB_MODEL_OUT = OUT_DIR / "xgb_rent_model.json"
METRICS_OUT = OUT_DIR / "ensemble_rent_metrics.json"
SHAP_OUT = OUT_DIR / "lgbm_shap_global.json"
FEATURES_OUT = OUT_DIR / "sigungu_monthly_features.parquet"

MODEL_OUT = LGBM_MODEL_OUT  # backward compat

if IS_KAGGLE:
    try:
        from kaggle_secrets import UserSecretsClient
        _sc = UserSecretsClient()
        ECOS_KEY = _sc.get_secret("ECOS_KEY")
    except Exception:
        ECOS_KEY = os.environ.get("ECOS_KEY", "")
else:
    ECOS_KEY = os.environ.get("ECOS_KEY", "")

ECOS_URL = "https://ecos.bok.or.kr/api/StatisticSearch"

# ── HUG 사고율 (직접 임베드 — 2025년 8월 기준 주요 시군구) ───────────────────
HUG_RATES: dict[str, float] = {
    "11110": 1.0, "11140": 0.4, "11170": 0.7, "11200": 2.1, "11215": 3.5,
    "11230": 2.8, "11260": 3.2, "11290": 1.5, "11305": 4.2, "11320": 3.8,
    "11350": 2.9, "11380": 3.0, "11410": 1.8, "11440": 2.0, "11470": 1.9,
    "11500": 1.6, "11530": 2.5, "11545": 3.1, "11560": 1.7, "11590": 2.7,
    "11620": 2.7, "11650": 0.9, "11680": 0.6, "11710": 1.5, "11740": 1.8,
    "26110": 0.5, "26140": 0.6, "26170": 0.7, "26200": 1.2, "26230": 1.1,
    "26260": 0.9, "26290": 1.0, "26320": 1.3, "26350": 0.8, "26380": 1.4,
    "26410": 1.1, "26440": 0.9, "26470": 1.0, "26500": 0.8, "26530": 1.2,
    "26710": 0.7, "27110": 0.4, "27140": 0.9, "27170": 0.8, "27200": 0.7,
    "27230": 0.8, "27260": 0.6, "27290": 0.7, "27710": 0.5,
    "28110": 0.9, "28140": 1.1, "28177": 1.5, "28185": 0.8, "28200": 1.2,
    "28237": 1.4, "28245": 1.3, "28260": 1.1, "28710": 0.6, "28720": 0.4,
    "29110": 0.8, "29140": 1.0, "29155": 1.1, "29170": 0.9, "29200": 1.2,
    "30110": 0.7, "30140": 0.8, "30170": 0.9, "30200": 0.6, "30230": 0.8,
    "31110": 0.6, "31140": 0.7, "31170": 0.8, "31200": 0.7, "31710": 0.5,
    "36110": 0.4,
    "41111": 1.2, "41113": 1.3, "41115": 1.4, "41117": 1.0,
    "41131": 1.2, "41133": 1.3, "41135": 1.2,
    "41150": 2.5, "41171": 1.8, "41173": 1.6,
    "41190": 2.2, "41210": 2.0, "41220": 1.5,
    "41271": 2.3, "41273": 2.1,
    "41281": 1.9, "41285": 1.8, "41287": 2.0,
    "41290": 1.1, "41310": 2.1, "41360": 2.3,
    "41370": 1.8, "41390": 2.4, "41410": 1.9, "41430": 1.7, "41450": 2.0,
    "41461": 1.6, "41463": 1.4, "41465": 1.3,
    "41480": 2.1, "41500": 1.5, "41550": 1.4,
    "41570": 2.2, "41590": 1.6, "41610": 1.8, "41630": 2.0, "41650": 1.5,
    "41670": 1.3,
}


def collect_ecos() -> pl.DataFrame:
    """ECOS 기준금리 75개월 수집."""
    if not ECOS_KEY:
        print("[WARN] ECOS_KEY 없음 — 기준금리 fallback 사용 (고정 3.5%)")
        months = []
        from datetime import date
        y, m = 2020, 1
        today = date.today()
        end_y = today.year if today.month > 1 else today.year - 1
        end_m = today.month - 1 if today.month > 1 else 12
        while (y, m) <= (end_y, end_m):
            months.append({"year_month": f"{y:04d}{m:02d}", "base_rate_pct": 3.5})
            m += 1
            if m > 12:
                y, m = y + 1, 1
        return pl.DataFrame(months).with_columns(
            pl.col("year_month").str.strptime(pl.Date, "%Y%m")
        )

    url = f"{ECOS_URL}/{ECOS_KEY}/json/kr/1/100/722Y001/M/202001/{{}}"
    from datetime import date
    today = date.today()
    end_ym = f"{today.year}{today.month - 1:02d}" if today.month > 1 else f"{today.year - 1}12"
    url = f"{ECOS_URL}/{ECOS_KEY}/json/kr/1/100/722Y001/M/202001/{end_ym}"

    try:
        r = httpx.get(url, timeout=30)
        data = r.json()
        rows = data.get("StatisticSearch", {}).get("row", [])
        return pl.DataFrame([
            {"year_month": row["TIME"], "base_rate_pct": float(row["DATA_VALUE"])}
            for row in rows
        ]).with_columns(
            pl.col("year_month").str.strptime(pl.Date, "%Y%m")
        )
    except Exception as e:
        print(f"[WARN] ECOS 수집 실패: {e} — fallback 3.5%")
        return pl.DataFrame({"year_month": [], "base_rate_pct": []}).with_columns(
            pl.col("year_month").cast(pl.Date)
        )


def aggregate_rent(path: Path, btype: str) -> pl.DataFrame:
    """원시 실거래 parquet → 시군구 × 월 집계."""
    if not path.exists():
        print(f"[SKIP] {path} 없음")
        return pl.DataFrame()

    df = pl.read_parquet(path)
    print(f"  {path.name}: {len(df):,}행 로드")

    # year_month 빌드
    if "deal_ymd" in df.columns:
        df = df.with_columns(
            pl.col("deal_ymd").str.strptime(pl.Date, "%Y%m").alias("year_month")
        )
    else:
        df = df.with_columns(
            (pl.col("dealYear").cast(pl.Utf8) + pl.col("dealMonth").cast(pl.Utf8).str.zfill(2))
            .str.strptime(pl.Date, "%Y%m").alias("year_month")
        )

    # 청년 평형 + 월세 이상치 필터 (단위: 만원)
    df = df.filter(
        (pl.col("excluUseAr") <= 85)
        & (pl.col("monthlyRent") > 0)
        & (pl.col("monthlyRent").is_between(5, 1000))
    )

    # 집계 (만원 → 원 변환 * 10_000)
    return (
        df.group_by(["lawd_cd", "year_month"])
        .agg([
            (pl.col("monthlyRent").mean() * 10_000).alias("rent_mean_won"),
            (pl.col("monthlyRent").std() * 10_000).alias("rent_std_won"),
            (pl.col("deposit").mean() * 10_000).alias("deposit_mean_won"),
            pl.col("monthlyRent").count().alias("transaction_count"),
            pl.col("excluUseAr").mean().alias("area_mean_m2"),
            pl.col("buildYear").cast(pl.Float64).mean().alias("building_year_mean"),
        ])
        .with_columns(pl.lit(btype).alias("building_type"))
        .rename({"lawd_cd": "sigungu_code"})
    )


def build_features() -> pl.DataFrame:
    """Features 빌드: 집계 + ECOS 금리 + HUG 사고율."""
    apt_agg = aggregate_rent(APT_PARQUET, "apt")
    villa_agg = aggregate_rent(VILLA_PARQUET, "villa")

    if apt_agg.is_empty() and villa_agg.is_empty():
        raise RuntimeError("실거래가 데이터 없음 — collect_rent.py 먼저 실행")

    rent = pl.concat([df for df in [apt_agg, villa_agg] if not df.is_empty()])
    print(f"rent 집계: {len(rent):,}행")

    # ECOS 금리 조인
    ecos = collect_ecos()
    if not ecos.is_empty():
        rent = rent.join(ecos, on="year_month", how="left")
        rent = rent.with_columns(
            pl.col("base_rate_pct").fill_null(strategy="forward").fill_null(3.5)
        )

    # HUG 사고율 (embedded dict)
    hug_df = pl.DataFrame({
        "sigungu_code": list(HUG_RATES.keys()),
        "hug_acc_rate_pct": list(HUG_RATES.values()),
    })
    rent = rent.join(hug_df, on="sigungu_code", how="left")
    rent = rent.with_columns(pl.col("hug_acc_rate_pct").fill_null(2.0))

    return rent.sort(["sigungu_code", "year_month", "building_type"])


# ── 학습 ──────────────────────────────────────────────────────────────────────
FEATURE_COLS = [
    "deposit_mean_won", "transaction_count", "area_mean_m2", "building_year_mean",
    "base_rate_pct", "hug_acc_rate_pct", "year", "month", "sigungu_code_int", "is_villa",
]
TARGET_COL = "rent_mean_won"

LGBM_PARAMS = {
    "objective": "regression",
    "metric": "mae",
    "learning_rate": 0.05,
    "num_leaves": 63,
    "min_data_in_leaf": 20,
    "feature_fraction": 0.9,
    "bagging_fraction": 0.85,
    "bagging_freq": 4,
    "verbose": -1,
}

XGB_PARAMS = {
    "objective": "reg:absoluteerror",
    "eval_metric": "mae",
    "learning_rate": 0.05,
    "max_depth": 6,
    "min_child_weight": 20,
    "subsample": 0.85,
    "colsample_bytree": 0.9,
    "tree_method": "hist",
    "device": "cuda" if os.environ.get("KAGGLE_KERNEL_RUN_TYPE") else "cpu",
    "verbosity": 0,
}

ENSEMBLE_W_LGBM = 0.60
ENSEMBLE_W_XGB = 0.40


def _build_splits(X: np.ndarray, y: np.ndarray, groups: np.ndarray) -> list:
    n_groups = len(np.unique(groups))
    n_splits = min(5, max(2, n_groups))
    if n_groups < 2:
        rng = np.random.default_rng(42)
        idx = np.arange(len(X)); rng.shuffle(idx)
        cut = int(len(X) * 0.8)
        return [(idx[:cut], idx[cut:])], 1
    return list(GroupKFold(n_splits=n_splits).split(X, y, groups)), n_splits


def train_lgbm_cv(X: np.ndarray, y: np.ndarray, groups: np.ndarray, cat_idx: list) -> tuple:
    """LightGBM GroupKFold CV → (oof_pred, best_iter, cv_stats)."""
    splits, n_splits = _build_splits(X, y, groups)
    oof = np.zeros(len(y))
    cv_mae, cv_rmse, cv_mape = [], [], []
    best_iters = []

    print(f"\n[LightGBM] GroupKFold(n_splits={n_splits})")
    booster = None
    for fold, (tr, va) in enumerate(splits, 1):
        d_tr = lgb.Dataset(X[tr], label=y[tr], categorical_feature=cat_idx)
        d_va = lgb.Dataset(X[va], label=y[va], categorical_feature=cat_idx, reference=d_tr)
        booster = lgb.train(
            LGBM_PARAMS, d_tr, num_boost_round=500,
            valid_sets=[d_va],
            callbacks=[lgb.early_stopping(40, verbose=False), lgb.log_evaluation(0)],
        )
        oof[va] = booster.predict(X[va])
        mae = mean_absolute_error(y[va], oof[va])
        rmse = float(np.sqrt(mean_squared_error(y[va], oof[va])))
        mape = float(np.mean(np.abs((y[va] - oof[va]) / np.maximum(y[va], 1))) * 100)
        cv_mae.append(mae); cv_rmse.append(rmse); cv_mape.append(mape)
        best_iters.append(booster.best_iteration)
        print(f"  Fold {fold}: MAE={mae:,.0f}원  RMSE={rmse:,.0f}원  MAPE={mape:.2f}%")

    cv_stats = {
        "lgbm_cv_mae_mean": float(np.mean(cv_mae)),
        "lgbm_cv_mae_std": float(np.std(cv_mae)),
        "lgbm_cv_rmse_mean": float(np.mean(cv_rmse)),
        "lgbm_cv_mape_mean": float(np.mean(cv_mape)),
        "lgbm_best_iter_mean": int(np.mean(best_iters)),
    }
    return oof, int(np.mean(best_iters)), cv_stats


def train_xgb_cv(X: np.ndarray, y: np.ndarray, groups: np.ndarray) -> tuple:
    """XGBoost GroupKFold CV → (oof_pred, best_iter, cv_stats)."""
    splits, n_splits = _build_splits(X, y, groups)
    oof = np.zeros(len(y))
    cv_mae, cv_rmse, cv_mape = [], [], []
    best_iters = []

    print(f"\n[XGBoost] GroupKFold(n_splits={n_splits})")
    booster = None
    for fold, (tr, va) in enumerate(splits, 1):
        dtrain = xgb.DMatrix(X[tr], label=y[tr], feature_names=FEATURE_COLS)
        dval = xgb.DMatrix(X[va], label=y[va], feature_names=FEATURE_COLS)
        booster = xgb.train(
            XGB_PARAMS, dtrain,
            num_boost_round=600,
            evals=[(dval, "val")],
            early_stopping_rounds=40,
            verbose_eval=False,
        )
        oof[va] = booster.predict(dval)
        mae = mean_absolute_error(y[va], oof[va])
        rmse = float(np.sqrt(mean_squared_error(y[va], oof[va])))
        mape = float(np.mean(np.abs((y[va] - oof[va]) / np.maximum(y[va], 1))) * 100)
        cv_mae.append(mae); cv_rmse.append(rmse); cv_mape.append(mape)
        best_iters.append(booster.best_iteration)
        print(f"  Fold {fold}: MAE={mae:,.0f}원  RMSE={rmse:,.0f}원  MAPE={mape:.2f}%")

    cv_stats = {
        "xgb_cv_mae_mean": float(np.mean(cv_mae)),
        "xgb_cv_mae_std": float(np.std(cv_mae)),
        "xgb_cv_rmse_mean": float(np.mean(cv_rmse)),
        "xgb_cv_mape_mean": float(np.mean(cv_mape)),
        "xgb_best_iter_mean": int(np.mean(best_iters)),
    }
    return oof, int(np.mean(best_iters)), cv_stats


def train(df: pl.DataFrame) -> dict:
    df = df.with_columns([
        pl.col("year_month").dt.year().alias("year"),
        pl.col("year_month").dt.month().alias("month"),
        pl.col("sigungu_code").cast(pl.Int64).alias("sigungu_code_int"),
        (pl.col("building_type") == "villa").cast(pl.Int8).alias("is_villa"),
    ])

    df_train = df.select([*FEATURE_COLS, TARGET_COL]).drop_nulls()
    n = len(df_train)
    print(f"학습 데이터: {n:,}행 × {len(FEATURE_COLS)} 피처")
    if n < 30:
        print(f"[WARN] 표본 부족 ({n}행) — Kaggle 수집 완료 후 재학습 권장")

    X = df_train.select(FEATURE_COLS).to_numpy().astype(np.float32)
    y = df_train.select(TARGET_COL).to_series().to_numpy().astype(np.float32)
    groups = df_train.select("sigungu_code_int").to_series().to_numpy()
    cat_idx = [FEATURE_COLS.index(c) for c in ["sigungu_code_int", "is_villa", "month"]]

    # ── LightGBM CV ───────────────────────────────────────────────────────────
    lgbm_oof, lgbm_best_iter, lgbm_stats = train_lgbm_cv(X, y, groups, cat_idx)

    # ── XGBoost CV ────────────────────────────────────────────────────────────
    xgb_oof, xgb_best_iter, xgb_stats = train_xgb_cv(X, y, groups)

    # ── 앙상블 OOF 평가 ───────────────────────────────────────────────────────
    ens_oof = ENSEMBLE_W_LGBM * lgbm_oof + ENSEMBLE_W_XGB * xgb_oof
    ens_mae = mean_absolute_error(y, ens_oof)
    ens_rmse = float(np.sqrt(mean_squared_error(y, ens_oof)))
    ens_mape = float(np.mean(np.abs((y - ens_oof) / np.maximum(y, 1))) * 100)
    print(f"\n[Ensemble {ENSEMBLE_W_LGBM:.0%}LGBM+{ENSEMBLE_W_XGB:.0%}XGB] "
          f"MAE={ens_mae:,.0f}원 ({ens_mae/10000:.1f}만원)  MAPE={ens_mape:.2f}%")

    # ── 전체 재학습 (LightGBM) ────────────────────────────────────────────────
    print("\n[전체 재학습] LightGBM ...")
    d_full = lgb.Dataset(X, label=y, categorical_feature=cat_idx)
    final_lgbm = lgb.train(LGBM_PARAMS, d_full, num_boost_round=lgbm_best_iter or 200)
    final_lgbm.save_model(str(LGBM_MODEL_OUT))
    print(f"  저장: {LGBM_MODEL_OUT}")

    # ── 전체 재학습 (XGBoost) ─────────────────────────────────────────────────
    print("[전체 재학습] XGBoost ...")
    dtrain_full = xgb.DMatrix(X, label=y, feature_names=FEATURE_COLS)
    final_xgb = xgb.train(
        XGB_PARAMS, dtrain_full,
        num_boost_round=xgb_best_iter or 300,
        verbose_eval=False,
    )
    final_xgb.save_model(str(XGB_MODEL_OUT))
    print(f"  저장: {XGB_MODEL_OUT}")

    # ── 메트릭 저장 ───────────────────────────────────────────────────────────
    metrics: dict = {
        "n_rows": n, "n_groups": int(len(np.unique(groups))),
        "feature_cols": FEATURE_COLS, "target_col": TARGET_COL,
        "ensemble_weights": {"lgbm": ENSEMBLE_W_LGBM, "xgb": ENSEMBLE_W_XGB},
        "ensemble_oof_mae": float(ens_mae),
        "ensemble_oof_rmse": float(ens_rmse),
        "ensemble_oof_mape": float(ens_mape),
        **lgbm_stats,
        **xgb_stats,
    }
    METRICS_OUT.write_text(json.dumps(metrics, ensure_ascii=False, indent=2))

    # ── SHAP (LightGBM 기반) ──────────────────────────────────────────────────
    try:
        shap_vals = np.asarray(final_lgbm.predict(X, pred_contrib=True))[:, :-1]
        mean_abs = np.mean(np.abs(shap_vals), axis=0)
        shap_global = sorted(
            [{"feature": c, "mean_abs_shap": float(v)} for c, v in zip(FEATURE_COLS, mean_abs)],
            key=lambda d: -d["mean_abs_shap"],
        )
        SHAP_OUT.write_text(json.dumps(shap_global, ensure_ascii=False, indent=2))
        print("\nSHAP Top 5 (LightGBM):")
        for d in shap_global[:5]:
            print(f"  {d['feature']:25s} |SHAP|={d['mean_abs_shap']:,.0f}원")
    except Exception as e:
        print(f"[WARN] SHAP 실패: {e}")

    return metrics


# ── 메인 ─────────────────────────────────────────────────────────────────────
print("=== LightGBM + XGBoost 앙상블 월세 예측 모델 학습 ===")

features = build_features()
features.write_parquet(FEATURES_OUT, compression="zstd")
print(f"Features 저장: {len(features):,}행 → {FEATURES_OUT}")

metrics = train(features)

print(f"\n[DONE] LightGBM 모델: {LGBM_MODEL_OUT}")
print(f"       XGBoost 모델:  {XGB_MODEL_OUT}")
print(f"       앙상블 지표:   {METRICS_OUT}")
print(f"       SHAP:          {SHAP_OUT}")
print(f"       Features:      {FEATURES_OUT}")
print(f"\n       앙상블 MAE: {metrics['ensemble_oof_mae']:,.0f}원 "
      f"({metrics['ensemble_oof_mae']/10000:.1f}만원)")

# 출력 파일 목록
print("\n=== Output 파일 ===")
for ext in ("*.txt", "*.json", "*.parquet"):
    for f in sorted(OUT_DIR.glob(ext)):
        print(f"  {f.name}: {f.stat().st_size / 1024:.1f}KB")
