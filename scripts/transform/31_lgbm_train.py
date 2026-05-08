"""LightGBM 월세 예측 모델 학습 + SHAP 설명.

설계서 v2.2 §모델 학습 / §추천 설명.
입력: data/processed/lgbm_train.parquet  (30_lgbm_train_prep 산출)
출력:
- data/processed/lgbm_rent_model.txt        (LightGBM Booster 저장)
- data/processed/lgbm_rent_metrics.json     (MAE, RMSE, MAPE)
- data/processed/lgbm_shap_global.json      (전역 feature importance + 평균 |SHAP|)

CV는 group-aware (시군구 단위 K-fold) — 같은 시군구가 train/test에 겹치지 않게.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import lightgbm as lgb
import numpy as np
import polars as pl
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import GroupKFold

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "collect"))
from _http import PROCESSED_DIR  # noqa: E402

DATA = PROCESSED_DIR / "lgbm_train.parquet"
META = PROCESSED_DIR / "lgbm_train_meta.json"
MODEL_OUT = PROCESSED_DIR / "lgbm_rent_model.txt"
METRICS_OUT = PROCESSED_DIR / "lgbm_rent_metrics.json"
SHAP_OUT = PROCESSED_DIR / "lgbm_shap_global.json"


PARAMS = {
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


def main() -> int:
    if not DATA.exists():
        print(f"[FAIL] {DATA} 없음 — 30_lgbm_train_prep.py 먼저 실행")
        return 1
    meta = json.loads(META.read_text(encoding="utf-8"))
    feat_cols: list[str] = meta["feature_cols"]
    target_col: str = meta["target_col"]
    cat_cols: list[str] = meta.get("categorical", [])

    df = pl.read_parquet(DATA)
    n = len(df)
    print(f"학습 데이터: {n:,}행 × {len(feat_cols)} 피처")

    if n < 30:
        print(f"[WARN] 표본 부족 ({n}행) — 학습은 진행하나 결과는 신뢰 어려움 (1주차 본 수집 후 재학습)")

    X = df.select(feat_cols).to_numpy()
    y = df.select(target_col).to_series().to_numpy()
    groups = df.select("sigungu_code_int").to_series().to_numpy()

    # CV — 시군구 group K-fold (적은 시군구 수 고려)
    n_groups = len(np.unique(groups))
    n_splits = min(5, max(2, n_groups))
    print(f"CV: GroupKFold(n_splits={n_splits}) — 고유 시군구 {n_groups}개")

    cv_mae, cv_rmse, cv_mape = [], [], []
    cat_idx = [feat_cols.index(c) for c in cat_cols if c in feat_cols]

    if n_groups < 2:
        # group split 불가 — single split 80/20 fallback
        rng = np.random.default_rng(42)
        idx = np.arange(n)
        rng.shuffle(idx)
        cut = int(n * 0.8)
        splits = [(idx[:cut], idx[cut:])]
    else:
        gkf = GroupKFold(n_splits=n_splits)
        splits = list(gkf.split(X, y, groups))

    booster = None
    for fold, (tr, va) in enumerate(splits, 1):
        d_tr = lgb.Dataset(X[tr], label=y[tr], categorical_feature=cat_idx)
        d_va = lgb.Dataset(X[va], label=y[va], categorical_feature=cat_idx, reference=d_tr)
        booster = lgb.train(
            PARAMS, d_tr,
            num_boost_round=400,
            valid_sets=[d_va],
            callbacks=[lgb.early_stopping(30, verbose=False), lgb.log_evaluation(0)],
        )
        pred = booster.predict(X[va])
        mae = mean_absolute_error(y[va], pred)
        rmse = float(np.sqrt(mean_squared_error(y[va], pred)))
        mape = float(np.mean(np.abs((y[va] - pred) / np.maximum(y[va], 1))) * 100)
        cv_mae.append(mae); cv_rmse.append(rmse); cv_mape.append(mape)
        print(f"  Fold {fold}: MAE={mae:,.0f}원, RMSE={rmse:,.0f}원, MAPE={mape:.2f}%")

    # 최종 — 전체로 재학습
    d_full = lgb.Dataset(X, label=y, categorical_feature=cat_idx)
    final_booster = lgb.train(PARAMS, d_full, num_boost_round=booster.best_iteration if booster else 200)
    final_booster.save_model(str(MODEL_OUT))

    metrics = {
        "n_rows": n, "n_groups": int(n_groups),
        "cv_mae_mean": float(np.mean(cv_mae)), "cv_mae_std": float(np.std(cv_mae)),
        "cv_rmse_mean": float(np.mean(cv_rmse)),
        "cv_mape_mean": float(np.mean(cv_mape)),
        "best_iteration": int(booster.best_iteration) if booster else 0,
    }
    METRICS_OUT.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[METRICS] MAE={metrics['cv_mae_mean']:,.0f}원, MAPE={metrics['cv_mape_mean']:.2f}%")

    # SHAP — 전역 평균 |SHAP|
    try:
        shap_vals = final_booster.predict(X, pred_contrib=True)
        # 마지막 컬럼은 expected_value, 앞은 feature contributions
        contrib = np.asarray(shap_vals)[:, :-1]
        mean_abs = np.mean(np.abs(contrib), axis=0)
        shap_global = sorted(
            [{"feature": c, "mean_abs_shap": float(v)} for c, v in zip(feat_cols, mean_abs)],
            key=lambda d: -d["mean_abs_shap"],
        )
        SHAP_OUT.write_text(json.dumps(shap_global, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nSHAP Top 5:")
        for d in shap_global[:5]:
            print(f"  {d['feature']:25s} |SHAP|={d['mean_abs_shap']:,.0f}")
    except Exception as e:
        print(f"[WARN] SHAP 계산 실패: {e}")

    print(f"\n[DONE] 모델: {MODEL_OUT}, 지표: {METRICS_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
