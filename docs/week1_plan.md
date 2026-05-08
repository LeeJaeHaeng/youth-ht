# 1주차 실행 플랜 — 데이터 수집 + DB 설계

> 설계서 v2.2 §1주차 그대로 따르되 **0주차 검증에서 확정된 내용**(공공데이터포털 resultCode=000, 연립다세대 대지권 없음, KOSIS 5세 구간 등)을 반영.
>
> **시작 가능 시점**: 즉시 (검증 통과 영역만으로 1주차 절반 진행)
>
> **사용자 액션 의존 영역**: 행안부 인구·R-ONE·통계누리 명세 확보 후 (`docs/user_action_required.md`)

## 1주차 목표

- 9개 데이터 소스 5년치 본격 수집
- Supabase 스키마 생성 + 마이그레이션
- 격자(SGIS 1km) + HUG 시군구 매핑 테이블 완성
- LightGBM 학습 데이터셋 1차 빌드 (LGBM 본 학습은 2주차)

## 단계별 작업 (요일 기준은 설계서 매핑, 실제는 진척도 기준 유연 운영)

### Day 1 (월) — 환경 보강 + 실거래가 수집 시작

- [ ] **추가 패키지 설치**: `lightgbm xgboost pyarrow geopandas shapely pyproj supabase httpx tenacity tqdm`
- [ ] **카카오 디렉션 호출용 비동기 클라이언트** 스켈레톤 작성
- [ ] **`scripts/collect/01_collect_apt_rent.py`** 작성 — 250 시군구 × 60개월 호출 (rate limit + 재시도 + checkpoint)
- [ ] 강남구·관악구 등 5개 시군구로 **소규모 dry-run** (1개월씩만)
- [ ] 결과: `data/processed/apt_rent_dryrun.parquet`

### Day 2 (화) — 실거래가 5년치 본 수집 + 연립다세대

- [ ] `01_collect_apt_rent.py` **전국 5년치 백그라운드 실행** (예상 15시간, rate-limit 1초 1회 가정)
- [ ] `scripts/collect/02_collect_villa_rent.py` 작성·실행
- [ ] 진행 모니터링 (체크포인트 / 실패 시군구·월 자동 재시도)

### Day 3 (수) — Supabase 스키마 + HUG 가공

- [ ] **Supabase 프로젝트 생성** (Free Tier)
- [ ] `migrations/0001_init.sql` — 설계서 §1주차 SQL 그대로 (`grid_1km, rent_history, grid_monthly_features, work_cluster, od_commute, llm_cache`)
- [ ] `scripts/transform/03_hug_to_sigungu.py` — HUG Excel(`data/raw/HUG_*.xlsx`) → `hug_risk_by_sigungu.parquet` (시군구코드, 사고건수, 사고금액, 사고율)

### Day 4 (목) — 격자(SGIS) 수집 + 매핑

- [ ] SGIS 1km 격자 Shapefile 다운로드 (사용자가 sgis.kostat.go.kr에서 발급 후 `data/raw/grid_1km/` 배치)
- [ ] `scripts/transform/04_grid_centroid.py` — 격자 → centroid (lat,lng) + 시군구코드 부착
- [ ] `scripts/transform/05_join_hug_to_grid.py` — 시군구별 HUG 사고율 → 격자에 broadcast
- [ ] **30,000 격자 후보 추출** (청년 인구 0 격자 제외 — 행안부 인구 확보 후 정밀화, 지금은 전체 사용)

### Day 5 (금) — 카카오맵 OD 매트릭스 + ECOS 시계열

- [ ] **직장 클러스터 100개 좌표 정의** (`docs/work_clusters.csv` 수동 작성 — 강남·여의도·판교·구로·홍대·종로·...)
- [ ] `scripts/collect/06_kakao_od.py` — 30,000 격자 × 100 클러스터 = 3M 호출 → **샘플링 전략**
  - 1차: 1km 격자 무작위 샘플 5,000개 × 100 클러스터 = 500K 호출 → 월 30만 한도 / 일 10K 추정 가능
  - 2차: 학습 후 부족 영역만 추가 호출
- [ ] `scripts/collect/07_ecos_rate_history.py` — 2020-01~현재 기준금리 시계열 → `data/processed/ecos_rate.parquet`

### Day 6-7 (토일, 검증/예비) — 1주차 점검

- [ ] 모든 수집 데이터 polars로 통합 → `data/processed/grid_monthly_features.parquet` 1차 빌드 (확보된 입력만)
- [ ] **사용자 액션(A/B/C) 확보 정도에 따라**:
  - A 확보 → `scripts/collect/08_population.py` 실행
  - B 확보 → `scripts/collect/09_unsold.py` 실행
- [ ] 1주차 회고 + 2주차(EDA + Feature Engineering) 진입

## 진입 전 체크리스트

| 항목 | 상태 |
| --- | --- |
| Python 가상환경 활성화 가능 | ✅ |
| 검증 통과 6/9 데이터 소스 | ✅ |
| HUG Excel 파싱 검증 | ✅ |
| 카카오 Directions 호출 검증 | ✅ |
| ECOS 호출 검증 | ✅ |
| 행안부 인구 명세 | ⏳ 사용자 처리 (A) |
| R-ONE 미분양 명세 | ⏳ 사용자 처리 (B) |
| 통계누리 명세 | ⏳ 사용자 처리 (C) |
| Supabase 프로젝트 | ⬜ Day 3에 생성 |
| SGIS 격자 Shapefile | ⬜ Day 4에 사용자 다운로드 |

## 작업 산출물 트리 (1주차 완료 시점)

```text
youth-ht/
├── migrations/
│   └── 0001_init.sql
├── scripts/
│   ├── collect/
│   │   ├── 01_collect_apt_rent.py
│   │   ├── 02_collect_villa_rent.py
│   │   ├── 06_kakao_od.py
│   │   ├── 07_ecos_rate_history.py
│   │   ├── 08_population.py        # A 확보 후
│   │   └── 09_unsold.py            # B 확보 후
│   ├── transform/
│   │   ├── 03_hug_to_sigungu.py
│   │   ├── 04_grid_centroid.py
│   │   └── 05_join_hug_to_grid.py
│   └── verify/                      # 0주차에 완성됨
└── data/
    ├── raw/
    │   ├── HUG_전국보증사고현황_25년8월.xlsx
    │   └── grid_1km/                # SGIS Shapefile
    └── processed/
        ├── apt_rent_history.parquet
        ├── villa_rent_history.parquet
        ├── hug_risk_by_sigungu.parquet
        ├── grid_centroid.parquet
        ├── grid_with_hug_risk.parquet
        ├── kakao_od_sample.parquet
        ├── ecos_rate.parquet
        └── grid_monthly_features.parquet  # GRU 학습용 (Day 6-7)
```

## 위험 + 완화

| 위험 | 영향 | 완화 |
| --- | --- | --- |
| 공공데이터포털 일 1,000회 한도 초과 | 5년치 수집 차질 | 시군구당 60개월 = 60회 호출, 250 시군구 × 60 = 15,000회 → 약 15일 분산. 또는 신청 시 **트래픽 증가 신청** |
| 카카오 30만/월 한도 | OD 빌드 일부 누락 | 첫 달은 5,000 격자 샘플로 시작, 학습 후 빈 영역 보강 |
| 행안부·R-ONE·통계누리 명세 미확보 | GRU #5/#6/#8 입력 결손 | 1주차 후반 또는 2주차 진입 시 처리 (병렬) |
| Python 3.13에서 LightGBM/PyTorch 미지원 가능성 | 모델 학습 차질 | 1주차 패키지 설치 시 사전 확인 — 호환 안 되면 Python 3.11 별도 venv 분리 |
| Supabase Free Tier 500MB 초과 | 8M 행 저장 시 압박 | 학습용 raw는 로컬 Parquet, Supabase는 집계+API용으로 한정 |

## 다음 단계 (2주차 미리보기)

- 전처리·EDA + Feature Engineering
- Supabase 적재 자동화 + DBT 류 의존성 명세
- LightGBM 본 학습 시작 (로컬 CPU)
- GRU 데이터 준비 → Kaggle 업로드
