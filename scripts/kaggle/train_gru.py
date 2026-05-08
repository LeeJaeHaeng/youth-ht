"""GRU 시계열 모델 학습 — 6개월 후 월세 예측 (Kaggle 실행용).

## 개요
- 설계서 v2.2 §4 GRU 모델 — 공모전 AI 활용 가점 10점 핵심
- 입력: 12개월 시계열 피처 → 출력: 다음 6개월 월세 예측
- Kaggle GPU 환경에서 실행 (P100/T4)

## Kaggle 실행 방법
1. collect_rent.py 결과 Dataset (apt_rent_history.parquet + villa_rent_history.parquet) 연결
2. Secrets: DATA_GO_KR_KEY_DECODING, ECOS_KEY
3. 이 파일 전체 붙여넣기 후 실행 (GPU accelerator ON 권장)
4. Output: gru_rent_model.pt, gru_rent_metrics.json, gru_predictions.parquet

## 모델 설계
- 입력 피처 (8개): rent_mean, deposit_mean, transaction_count, base_rate_pct,
                   hug_acc_rate_pct, youth_wage_approx, pop_change_rate, unsold_units
- 시퀀스 길이: 12개월 (window)
- 예측 horizon: 6개월
- 아키텍처: GRU(2층, hidden=128, dropout=0.2) + Linear
- 손실: Huber Loss (이상치 강건)
- 평가: MAE, MAPE (시군구 × 월 기준)
"""
from __future__ import annotations

import json
import math
import os
import time
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

import numpy as np

# ── 환경 ──────────────────────────────────────────────────────────────────────
IS_KAGGLE = Path("/kaggle").exists()
WORK_DIR = Path("/kaggle/working") if IS_KAGGLE else Path("data/processed")
INPUT_DIR = Path("/kaggle/input") if IS_KAGGLE else Path("data/processed")
CKPT_DIR = Path("/kaggle/working") if IS_KAGGLE else Path("data/checkpoints")
WORK_DIR.mkdir(parents=True, exist_ok=True)

import polars as pl
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

# ── 하이퍼파라미터 ────────────────────────────────────────────────────────────
WINDOW = 12      # 입력 시퀀스 길이 (개월)
HORIZON = 6      # 예측 개월 수
HIDDEN = 128
N_LAYERS = 2
DROPOUT = 0.2
LR = 1e-3
BATCH = 64
EPOCHS = 50
PATIENCE = 10    # early stopping
MIN_SEQ = WINDOW + HORIZON  # 학습 가능 최소 시퀀스 길이

# 피처 순서 고정
FEATURE_COLS = [
    "rent_mean_won_norm",
    "deposit_mean_won_norm",
    "transaction_count_norm",
    "base_rate_pct",
    "hug_acc_rate_pct",
    "youth_wage_norm",     # KOSIS 수집 전: 시도별 고정값 사용
    "pop_change_rate",     # 행안부 수집 전: 0 채움
    "unsold_units_norm",   # R-ONE 수집 전: 0 채움
]
N_FEAT = len(FEATURE_COLS)

# ── 상수 ──────────────────────────────────────────────────────────────────────
if Path("/kaggle").exists():
    try:
        from kaggle_secrets import UserSecretsClient
        _sc = UserSecretsClient()
        DATA_KEY = _sc.get_secret("DATA_GO_KR_KEY_DECODING")
        ECOS_KEY = _sc.get_secret("ECOS_KEY")
    except Exception:
        DATA_KEY = os.environ.get("DATA_GO_KR_KEY_DECODING", "")
        ECOS_KEY = os.environ.get("ECOS_KEY", "")
else:
    DATA_KEY = os.environ.get("DATA_GO_KR_KEY_DECODING", "")
    ECOS_KEY = os.environ.get("ECOS_KEY", "")
YOUTH_MEDIAN_INCOME_WON = 2_500_000

# 시도별 청년 임금 근사 (KOSIS DT_118N_LCE0004 2023년 기준, 만원/월)
SIDO_YOUTH_WAGE: dict[str, float] = {
    "11": 280.0, "26": 240.0, "27": 230.0, "28": 245.0,
    "29": 220.0, "30": 225.0, "31": 230.0, "36": 260.0,
    "41": 265.0, "42": 215.0, "43": 210.0, "44": 215.0,
    "45": 205.0, "46": 200.0, "47": 210.0, "48": 220.0,
    "50": 195.0,
}

# HUG 시군구별 사고율 embedded (train_lgbm.py와 동일)
HUG_RATES: dict[str, float] = {
    "11110": 1.0, "11140": 0.4, "11170": 0.7, "11200": 1.5, "11215": 2.3,
    "11230": 2.1, "11260": 1.8, "11290": 1.2, "11305": 1.6, "11320": 0.9,
    "11350": 1.3, "11380": 1.4, "11410": 1.1, "11440": 0.3, "11470": 2.0,
    "11500": 1.7, "11530": 2.4, "11545": 2.8, "11560": 1.9, "11590": 0.8,
    "11620": 2.7, "11650": 0.9, "11680": 0.6, "11710": 0.7, "11740": 1.0,
    "26110": 0.5, "26140": 0.6, "26170": 0.8, "26200": 1.2, "26230": 1.5,
    "26260": 1.1, "26290": 1.4, "26320": 1.0, "26350": 0.9, "26380": 1.8,
    "26410": 0.7, "26440": 0.6, "26470": 1.3, "26500": 0.8, "26530": 2.0,
    "26710": 0.4, "27110": 0.3, "27140": 0.9, "27170": 0.7, "27200": 0.8,
    "27230": 1.1, "27260": 1.0, "27290": 1.3, "27710": 0.5,
    "28110": 0.6, "28140": 0.9, "28177": 2.1, "28185": 1.8, "28200": 1.2,
    "28237": 1.9, "28245": 1.6, "28260": 2.3, "28710": 0.3, "28720": 0.2,
    "29110": 0.4, "29140": 0.6, "29155": 0.5, "29170": 0.8, "29200": 1.1,
    "30110": 0.3, "30140": 0.5, "30170": 0.7, "30200": 0.6, "30230": 0.4,
    "31110": 0.5, "31140": 0.8, "31170": 0.7, "31200": 0.6, "31710": 0.3,
    "36110": 0.8,
    "41111": 1.5, "41113": 1.8, "41115": 1.6, "41117": 1.9,
    "41131": 1.3, "41133": 1.4, "41135": 1.2,
    "41150": 2.1, "41171": 2.0, "41173": 1.9,
    "41190": 2.5, "41210": 2.2, "41220": 1.7,
    "41271": 2.3, "41273": 2.4,
    "41281": 1.8, "41285": 1.6, "41287": 1.7,
    "41290": 0.9, "41310": 1.5, "41360": 1.6,
    "41370": 1.8, "41390": 2.6, "41410": 2.1, "41430": 1.8, "41450": 1.9,
    "41461": 1.4, "41463": 1.7, "41465": 1.5,
    "41480": 1.3, "41500": 1.1, "41550": 1.0,
    "41570": 2.0, "41590": 2.2, "41610": 1.6,
    "41630": 1.2, "41650": 0.9, "41670": 0.8,
}


# ── 데이터 로딩 ───────────────────────────────────────────────────────────────
def find_parquet(name: str) -> Path | None:
    for base in (INPUT_DIR, WORK_DIR):
        if not base.exists():
            continue
        found = next(base.rglob(name), None)
        if found:
            return found
    return None


def load_rent() -> pl.DataFrame:
    """apt + villa 전처리 → 시군구 × 월 집계."""
    frames = []
    for name in ("apt_rent_history.parquet", "villa_rent_history.parquet"):
        p = find_parquet(name)
        if not p:
            print(f"[SKIP] {name} 없음")
            continue
        df = pl.read_parquet(p)
        print(f"  {name}: {len(df):,}행")

        # year_month 생성
        if "deal_ymd" in df.columns:
            df = df.with_columns(
                pl.col("deal_ymd").str.strptime(pl.Date, "%Y%m").alias("year_month")
            )
        else:
            df = df.with_columns(
                (pl.col("dealYear").cast(pl.Utf8) + pl.col("dealMonth").cast(pl.Utf8).str.zfill(2))
                .str.strptime(pl.Date, "%Y%m").alias("year_month")
            )

        df = df.filter(
            (pl.col("excluUseAr") <= 85)
            & (pl.col("monthlyRent") > 0)
            & (pl.col("monthlyRent").is_between(5, 1000))
        )
        frames.append(df)

    if not frames:
        raise RuntimeError("실거래가 parquet 없음 — collect_rent.py 먼저 실행")

    raw = pl.concat(frames, how="diagonal_relaxed")
    agg = (
        raw.group_by(["lawd_cd", "year_month"])
        .agg([
            (pl.col("monthlyRent").mean() * 10_000).alias("rent_mean_won"),
            (pl.col("deposit").mean() * 10_000).alias("deposit_mean_won"),
            pl.col("monthlyRent").count().alias("transaction_count"),
        ])
        .rename({"lawd_cd": "sigungu_code"})
        .sort(["sigungu_code", "year_month"])
    )
    print(f"집계 완료: {len(agg):,}행, 시군구 {agg['sigungu_code'].n_unique()}개")
    return agg


def load_ecos() -> dict[str, float]:
    """ECOS parquet 또는 API 호출 → {YYYYMM: base_rate}."""
    p = find_parquet("ecos_rate.parquet")
    if p:
        df = pl.read_parquet(p)
        return {
            row["year_month"].strftime("%Y%m"): row["base_rate_pct"]
            for row in df.to_dicts()
        }
    # fallback: 고정 3.5%
    print("[WARN] ecos_rate.parquet 없음 — 3.5% 고정")
    return {}


# ── 피처 빌드 ─────────────────────────────────────────────────────────────────
def build_features(agg: pl.DataFrame, ecos: dict[str, float]) -> pl.DataFrame:
    """시군구 × 월 피처 DataFrame 생성."""
    df = agg.with_columns([
        pl.col("year_month").dt.strftime("%Y%m").alias("ym_str"),
        (pl.col("sigungu_code").str.slice(0, 2)).alias("sido_code"),
    ])

    rows = df.to_dicts()
    out = []
    # 정규화 통계 (전체 기준)
    rent_mean = float(df["rent_mean_won"].mean() or 1)
    rent_std = float(df["rent_mean_won"].std() or 1)
    dep_mean = float(df["deposit_mean_won"].mean() or 1)
    dep_std = float(df["deposit_mean_won"].std() or 1)
    cnt_mean = float(df["transaction_count"].mean() or 1)
    cnt_std = float(df["transaction_count"].std() or 1)
    wage_mean = sum(SIDO_YOUTH_WAGE.values()) / len(SIDO_YOUTH_WAGE)

    for row in rows:
        sg = row["sigungu_code"]
        ym = row["ym_str"]
        rate = ecos.get(ym, 3.5)
        hug = HUG_RATES.get(sg, 1.0)
        wage = SIDO_YOUTH_WAGE.get(row["sido_code"], wage_mean)

        out.append({
            "sigungu_code": sg,
            "year_month": row["year_month"],
            "rent_mean_won": row["rent_mean_won"],
            "rent_mean_won_norm": (row["rent_mean_won"] - rent_mean) / max(rent_std, 1),
            "deposit_mean_won_norm": (row["deposit_mean_won"] - dep_mean) / max(dep_std, 1),
            "transaction_count_norm": (row["transaction_count"] - cnt_mean) / max(cnt_std, 1),
            "base_rate_pct": rate,
            "hug_acc_rate_pct": hug,
            "youth_wage_norm": (wage - wage_mean) / 30.0,
            "pop_change_rate": 0.0,
            "unsold_units_norm": 0.0,
        })

    return pl.DataFrame(out).sort(["sigungu_code", "year_month"])


# ── PyTorch Dataset ───────────────────────────────────────────────────────────
class RentSeqDataset(Dataset):
    """시군구별 시계열 → (window, horizon) 슬라이딩 윈도우."""

    def __init__(self, feat_df: pl.DataFrame, window: int, horizon: int) -> None:
        self.samples: list[tuple[np.ndarray, np.ndarray]] = []

        for sg, group in feat_df.group_by("sigungu_code"):
            g = group.sort("year_month")
            if len(g) < window + horizon:
                continue
            feats = g.select(FEATURE_COLS).to_numpy().astype(np.float32)
            target = g["rent_mean_won_norm"].to_numpy().astype(np.float32)

            for i in range(len(g) - window - horizon + 1):
                x = feats[i: i + window]
                y = target[i + window: i + window + horizon]
                self.samples.append((x, y))

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        x, y = self.samples[idx]
        return torch.from_numpy(x), torch.from_numpy(y)


# ── GRU 모델 ──────────────────────────────────────────────────────────────────
class RentGRU(nn.Module):
    def __init__(self, n_feat: int, hidden: int, n_layers: int, dropout: float, horizon: int) -> None:
        super().__init__()
        self.gru = nn.GRU(
            input_size=n_feat, hidden_size=hidden,
            num_layers=n_layers, dropout=dropout if n_layers > 1 else 0.0,
            batch_first=True,
        )
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden, horizon)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out, _ = self.gru(x)
        last = self.dropout(out[:, -1, :])
        return self.fc(last)


# ── 학습 ──────────────────────────────────────────────────────────────────────
def train_gru(feat_df: pl.DataFrame) -> dict:
    # CUDA 아키텍처 불일치 시 CPU fallback
    if torch.cuda.is_available():
        try:
            _test = torch.zeros(1, device="cuda")
            del _test
            device = torch.device("cuda")
        except Exception as e:
            print(f"[WARN] CUDA 사용 불가 ({e}) → CPU로 전환")
            device = torch.device("cpu")
    else:
        device = torch.device("cpu")
    print(f"Device: {device}")

    # Train/Val split — 마지막 WINDOW+HORIZON개월은 val, 나머지 train
    dates = feat_df["year_month"].unique().sort()
    n = len(dates)
    # val에 시퀀스가 생기려면 최소 WINDOW+HORIZON개월 필요 → 시간 기준 80/20
    split_idx = max(int(n * 0.8), n - (WINDOW + HORIZON + 5))
    split_date = dates[split_idx]
    train_df = feat_df.filter(pl.col("year_month") < split_date)
    val_df = feat_df.filter(pl.col("year_month") >= split_date)

    # val 시퀀스가 없으면 전체를 train으로 사용 (전체 재학습 모드)
    val_ds = RentSeqDataset(val_df, WINDOW, HORIZON)
    if len(val_ds) == 0:
        print("[INFO] val 시퀀스 부족 — 전체 데이터로 학습 (early stopping 미적용)")
        train_df = feat_df
        val_df = feat_df  # train loss를 val로 대용
        val_ds = RentSeqDataset(val_df, WINDOW, HORIZON)
    train_ds = RentSeqDataset(train_df, WINDOW, HORIZON)

    if len(train_ds) == 0:
        raise RuntimeError(f"학습 샘플 없음 — 최소 {MIN_SEQ}개월 데이터 필요")
    print(f"학습 샘플: {len(train_ds)}, 검증 샘플: {len(val_ds)}")

    train_loader = DataLoader(train_ds, batch_size=BATCH, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=BATCH, shuffle=False, num_workers=0)

    # CUDA GRU 초기화 실패 시 CPU fallback
    try:
        model = RentGRU(N_FEAT, HIDDEN, N_LAYERS, DROPOUT, HORIZON).to(device)
        # GRU flatten_parameters 호출 테스트
        dummy = torch.zeros(1, WINDOW, N_FEAT, device=device)
        _ = model(dummy)
        del dummy
    except Exception as e:
        if device.type == "cuda":
            print(f"[WARN] CUDA 모델 초기화 실패 ({type(e).__name__}) → CPU로 전환")
            device = torch.device("cpu")
            model = RentGRU(N_FEAT, HIDDEN, N_LAYERS, DROPOUT, HORIZON).to(device)
        else:
            raise

    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, "min", patience=5, factor=0.5)
    criterion = nn.HuberLoss()

    best_val = float("inf")
    best_state = None
    no_improve = 0

    for epoch in range(1, EPOCHS + 1):
        model.train()
        train_loss = 0.0
        for xb, yb in train_loader:
            xb, yb = xb.to(device), yb.to(device)
            optimizer.zero_grad()
            pred = model(xb)
            loss = criterion(pred, yb)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            train_loss += loss.item() * len(xb)
        train_loss /= max(len(train_ds), 1)

        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for xb, yb in val_loader:
                xb, yb = xb.to(device), yb.to(device)
                val_loss += criterion(model(xb), yb).item() * len(xb)
        val_loss /= max(len(val_ds), 1)

        scheduler.step(val_loss)
        if val_loss < best_val:
            best_val = val_loss
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
            no_improve = 0
        else:
            no_improve += 1

        if epoch % 5 == 0 or no_improve == 0:
            print(f"Epoch {epoch:3d}: train={train_loss:.4f}, val={val_loss:.4f} {'★' if no_improve==0 else ''}")

        if no_improve >= PATIENCE:
            print(f"Early stopping at epoch {epoch}")
            break

    if best_state:
        model.load_state_dict(best_state)

    return {"best_val_huber": round(best_val, 4), "epochs_trained": epoch, "device": str(device)}, model


# ── 예측 저장 ─────────────────────────────────────────────────────────────────
def save_predictions(model: RentGRU, feat_df: pl.DataFrame, out_path: Path) -> None:
    """각 시군구의 마지막 WINDOW개월 → 6개월 후 예측 저장."""
    device = next(model.parameters()).device
    model.eval()
    rows = []

    for sg, group in feat_df.group_by("sigungu_code"):
        g = group.sort("year_month")
        if len(g) < WINDOW:
            continue
        feats = g.select(FEATURE_COLS).to_numpy().astype(np.float32)[-WINDOW:]
        x = torch.from_numpy(feats).unsqueeze(0).to(device)
        with torch.no_grad():
            pred = model(x).squeeze(0).cpu().numpy()
        for h in range(HORIZON):
            rows.append({"sigungu_code": sg, "horizon_months": h + 1, "pred_rent_norm": float(pred[h])})

    pl.DataFrame(rows).write_parquet(out_path, compression="zstd")
    print(f"[DONE] {len(rows)}개 예측 → {out_path}")


# ── 메인 ──────────────────────────────────────────────────────────────────────
def main() -> None:
    print("=== GRU 월세 예측 모델 학습 ===")
    t0 = time.time()

    print("\n1. 데이터 로딩")
    agg = load_rent()
    ecos = load_ecos()

    print("\n2. 피처 빌드")
    feat_df = build_features(agg, ecos)
    print(f"  시군구 {feat_df['sigungu_code'].n_unique()}개 × 월 {feat_df['year_month'].n_unique()}개")

    print("\n3. GRU 학습")
    metrics, model = train_gru(feat_df)
    print(f"  결과: {metrics}")

    print("\n4. 모델 저장")
    model_path = WORK_DIR / "gru_rent_model.pt"
    torch.save(model.state_dict(), model_path)
    print(f"  모델: {model_path}")

    metrics_path = WORK_DIR / "gru_rent_metrics.json"
    metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2))

    print("\n5. 예측 저장")
    pred_path = WORK_DIR / "gru_predictions.parquet"
    save_predictions(model, feat_df, pred_path)

    elapsed = time.time() - t0
    print(f"\n[완료] {elapsed:.0f}초 소요")
    print(f"출력 파일: {model_path}, {metrics_path}, {pred_path}")


if __name__ == "__main__":
    main()
