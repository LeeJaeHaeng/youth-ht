# Kaggle 실행 가이드

## 실행 순서

```
Step 1: collect_rent.py  →  apt_rent_history.parquet + villa_rent_history.parquet
Step 2: train_lgbm.py    →  lgbm_rent_model.txt + sigungu_monthly_features.parquet
Step 3: train_gru.py     →  gru_rent_model.pt + gru_predictions.parquet
```

---

## Step 1: 실거래가 수집 (collect_rent.py)

### 설정
1. Kaggle New Notebook → **Script** 타입 선택
2. **Settings → Add-ons → Secrets** 에서 추가:
   - `DATA_GO_KR_KEY_DECODING`: 공공데이터포털 일반 인증키(Decoding)
3. `collect_rent.py` 전체 붙여넣기 후 실행

### 예상 소요 시간
- 약 2.4시간 (113 시군구 × 75개월 × 2종 = 16,950 호출)

### 출력
- `/kaggle/working/apt_rent_history.parquet`
- `/kaggle/working/villa_rent_history.parquet`

### 완료 후
- **Save Version** → "Save & Run All" → Dataset으로 저장 (New Dataset)
- Dataset 이름: `youth-ht-rent-data` (기억해두기)

---

## Step 2: LightGBM 학습 (train_lgbm.py)

### 설정
1. New Notebook → Script
2. **Add Data** → Step 1 저장한 `youth-ht-rent-data` Dataset 추가
3. **Secrets** 추가:
   - `ECOS_KEY`: 한국은행 ECOS API 키 (`DJPJZL9W3CLPPUYYZ9K4`)
4. `train_lgbm.py` 붙여넣기 후 실행

### 예상 소요 시간
- 약 10~30분 (GroupKFold 5-fold + SHAP 계산)

### 출력
- `lgbm_rent_model.txt` — LightGBM 모델
- `lgbm_rent_metrics.json` — 검증 지표
- `lgbm_shap_global.json` — 피처 중요도
- `sigungu_monthly_features.parquet` — 집계 피처 테이블

### 완료 후
- Save & Run → Dataset으로 저장 (`youth-ht-lgbm`)
- 4개 파일 다운로드 → `youth-ht/data/processed/` 에 배치

---

## Step 2.5: 보조 데이터 Dataset 업로드 (최초 1회)

아래 3개 parquet 파일을 Kaggle Dataset으로 업로드:

- `data/processed/pop_change_by_sido.parquet` (행안부 인구변화율)
- `data/processed/unsold_by_sido.parquet` (R-ONE 미분양)
- `data/processed/kosis_youth_wage.parquet` (KOSIS 청년임금)

1. kaggle.com → Datasets → New Dataset
2. Dataset 이름: `youth-ht-processed`
3. 위 3개 파일 업로드 → Create

---

## Step 3: GRU 학습 (train_gru.py)

### 설정
1. New Notebook → Script
2. **Add Data**: `youth-ht-rent-data` + `youth-ht-lgbm` + `youth-ht-processed`
3. **Accelerator**: GPU T4 x2 권장
4. `train_gru.py` 붙여넣기 후 실행

### 예상 소요 시간
- GPU: ~20분, CPU: ~3시간

### 출력
- `gru_rent_model.pt` — PyTorch GRU 모델
- `gru_rent_metrics.json` — 검증 지표
- `gru_predictions.parquet` — 시군구별 6개월 후 예측

### 완료 후
- Save & Run → Dataset 저장
- 3개 파일 다운로드 → `youth-ht/data/processed/` 에 배치

---

## 로컬 서버 재시작 (파일 배치 후)

```powershell
cd youth-ht
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

- FastAPI가 자동으로 실제 데이터 감지
- `sigungu_monthly_features.parquet` 113+ 시군구 → 실데이터 모드 활성화
- `gru_predictions.parquet` 있으면 6개월 예측 자동 적용

---

## 검증

```powershell
# E2E 검증
.\.venv\Scripts\python.exe scripts\verify\12_verify_api_e2e.py
```

`Stage1 통과: N개` 에서 N이 10 이상이면 정상 (드라이런 3개 → 실데이터 50+ 예상)

---

## 비용 가이드 (2026년 5월 기준)

| 항목 | 비용 |
| --- | --- |
| Kaggle 실행 | 무료 (주 30시간 GPU) |
| 공공데이터포털 API | 무료 |
| ECOS API | 무료 |
| Gemini 2.5 Flash | 약 0.08원/호출 (캐시 히트 시 무료) |
| 카카오 Directions | 무료 (월 30만 한도) |
