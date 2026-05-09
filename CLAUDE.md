# CLAUDE.md — 청년 안심 H+T 추천 시스템 진행 추적

> 이 문서는 Claude Code 세션 간 진행 상황을 추적합니다. 매 작업 후 시간/내용/결과/다음 단계를 기록합니다.

## 프로젝트 한 줄 요약

청년이 직장 위치·예산·통근 한계를 입력하면 전국 1km 격자에서 H+T 통합 부담률 + 전세사기 위험 + 통근시간 + 6개월 후 미래 부담률 + 신뢰도를 통합 평가해 **안심 거주지 Top 10 + DeepSeek 자연어 리포트**를 제공하는 모바일 서비스.

## 기술 스택

- Backend: FastAPI (Python 3.11) — 현재 venv는 Python 3.13.7 (0주차 검증용)
- Frontend: React Native
- DB: Supabase (PostgreSQL)
- 지도: 카카오맵 API
- 모델: LightGBM + XGBoost + GRU + DeepSeek-V3 API

## 디렉토리 구조

```text
youth-ht/
├── .env                # API 키 (gitignore)
├── .gitignore
├── CLAUDE.md           # 이 파일
├── requirements.txt
├── .venv/              # Python 가상환경
├── data/
│   ├── raw/            # 원본 데이터 (HUG Excel 등)
│   ├── processed/      # 전처리된 Parquet
│   └── verify/         # 검증 결과 샘플 JSON
├── scripts/
│   └── verify/         # 0주차 검증 스크립트 9개
└── docs/
    └── data_verification_report.md
```

## 진행 로그

### 2026-05-09~10 — GRU 재학습 완료 + creative-heartbeat-ui 웹 UI 전환 + E2E 검증 ✅

#### 행안부 인구 API 연동 완료 ✅

- `scripts/collect/08_collect_population.py` 완전 재작성
- 엔드포인트: `https://apis.data.go.kr/1741000/RegistrationPopulationByRegion/getRegistrationPopulationByRegion`
- 응답 구조: `{RegistrationPopulationByRegion: [{head:...}, {row:[...]}]}` (비표준 — 직접 파싱)
- 17 시도 × 2019~2024 = 87행, YoY `pop_change_rate` 산출
- 출력: `data/processed/pop_change_by_sido.parquet`

#### GRU Kaggle 재학습 완료 ✅

- 3개 피처 전부 실데이터로 교체 후 재학습 (pop_change_rate, unsold_units_norm, youth_wage_norm)
- `scripts/kaggle/train_gru.py` 수정: `load_population()` 추가, `build_features()`에 pop dict 주입
- Kaggle kernel push: `scripts/kaggle/kernel_push/kernel-metadata.json` 신규 생성
- 결과: best_val_huber=0.0625, **666 predictions** (111 시군구 × 6 horizon), CPU 122초
- `gru_predictions.parquet` + `gru_rent_model.pt` 다운로드 → `data/processed/` 배치

#### creative-heartbeat-ui 웹 UI 전환 및 FastAPI 백엔드 완전 연동 ✅

기존 React Native 모바일 앱과 별도로, `https://github.com/LeeJaeHaeng/creative-heartbeat-ui` (TanStack Start 기반 웹 앱)을 신규 웹 프론트엔드로 채택.

| 파일 | 변경 | 내용 |
| --- | --- | --- |
| `src/lib/api.ts` | 신규 | fetchRecommend, fetchReport, OFFICE_PRESETS 10개, resultCache |
| `src/lib/mock-data.ts` | 수정 | toArea() 변환 함수 추가, _raw/_req 필드 추가 |
| `src/routes/recommend.tsx` | 재작성 | 실 API 기반 AI 추천 받기 버튼, 가중치 preset, mock 폴백 |
| `src/routes/area.$id.tsx` | 재작성 | resultCache 상세 로드, Gemini AI 리포트 비동기, GRU 차트 |
| `.env.local` | 신규 | `VITE_API_URL=http://localhost:8000` |

#### E2E 전체 플로우 검증 결과 ✅ (2026-05-10)

- **추천 페이지** (여의도 기준, balance): 10개 결과 — #1 인천 동구 23만/33분, #2 서울 동작구 50만/11분 등
- **상세 페이지** (동작구 `/area/11590`): GRU 차트(과거5개월+현재+예측6개월) 정상 렌더링
- **Gemini AI 리포트**: "27세 직장인 고객님께 서울특별시 동작구는 여의도 직장과의 짧은 통근 시간과 저렴한 월세로 매우 매력적인 선택지입니다..." 완전 로드
- **핵심 지표**: 월 소득 대비 부담 19.1%, 6개월 후 부담 예측 23.0%, HUG 보증사고율 0.60%

#### 현재 상태 (2026-05-10 기준)

| 항목 | 상태 |
| --- | --- |
| FastAPI 백엔드 | localhost:8000 실행 중 |
| creative-heartbeat-ui | localhost:3001 실행 중 (git push 미완) |
| youth-ht 백엔드 | git push 미완 |
| EC2 배포 | SSH 연결 타임아웃 — 미완 |

---

### 2026-05-09 — 행안부·KOSIS·R-ONE 실데이터 GRU 피처 연동 완료

#### 데이터 융합 가점(5점) 대응 — 3개 피처 실데이터 교체 ✅

| 피처 | 이전 | 이후 |
| --- | --- | --- |
| `pop_change_rate` | 0.0 하드코딩 | 행안부 주민등록인구 API (17 시도 × 2019~2024, 87행) |
| `unsold_units_norm` | 0.0 하드코딩 | R-ONE 미분양 API (17 시도 × 75개월, 1,275행) |
| `youth_wage_norm` | 시도별 상수 dict | KOSIS 청년임금 API (29세이하 2,601,000원/월, 2024) |

#### 수정 파일 요약

- `scripts/collect/08_collect_population.py`: 행안부 RegistrationPopulationByRegion API, YoY 인구변화율 산출
- `scripts/collect/09_collect_unsold.py`: R-ONE SttsApiTblData paginated 수집 (55,249행 → 1,275행 필터)
- `scripts/collect/10_collect_kosis_wage.py`: KOSIS DT_118N_LCE0004, C1_NM=전체근로자 필터 (신규)
- `app/services/data_loader.py`: YOUTH_MEDIAN_INCOME_WON 동적 로드, `_load_unsold_by_sido()` 추가
- `scripts/kaggle/train_gru.py`: `load_population()` 추가, 3개 피처 실데이터 반영
- `scripts/kaggle/KAGGLE_GUIDE.md`: Step 2.5 보조 데이터 Dataset 업로드 절차 추가

#### 다음 단계

- Kaggle Dataset `youth-ht-processed` 업로드 (3개 parquet)
- GRU 재학습 (Kaggle Step 3 실행)
- EC2 배포 (현재 연결 불가 — 재시도 필요)
- 다운로드된 `gru_predictions.parquet` → `data/processed/` 배치 후 FastAPI E2E 재검증

---

### 2026-05-08 (3차) — GitHub 초기 푸시 + Supabase llm_cache 연동

#### GitHub 초기 커밋·푸시 ✅
- `mobile/.git` (중첩 저장소) 제거 → 일반 파일로 스테이징
- `dist-preview/`, `dist-preview2/` `.gitignore` 추가
- 86개 파일 초기 커밋 → `https://github.com/LeeJaeHaeng/youth-ht.git` master 브랜치 push ✅

#### Supabase llm_cache 연동 ✅
- `.env`에 `SUPABASE_URL`, `SUPABASE_KEY`, `DATABASE_URL` 추가
- `migrations/0002` (add_llm_cache_token_columns): `prompt_tokens/completion_tokens` 컬럼 추가, `response` JSONB→TEXT 변경
- `llm.py` 수정: Supabase 우선 캐시, 연결 실패 시 SQLite fallback
- Supabase read/write 테스트 ✅, E2E 재검증 ✅

---

### 2026-05-08 (2차) — 카카오맵 지도 화면 + GRU 학습 진행중

#### 카카오맵 지도 화면 추가 ✅
- `recommender.py` 수정: `RegionFeature`에 `lat/lng` 필드 추가 (default 0.0)
- `data_loader.py` 수정: `_load_sigungu_centroid()` → names/lats/lngs 반환, RegionFeature에 주입
- `schemas.py` 수정: `RecommendItem`에 `lat/lng` 필드 추가
- `types/index.ts` 수정: `lat?: number`, `lng?: number` 추가
- `MapScreen.tsx` ✅ (신규):
  - Kakao Maps JS API + react-native-webview
  - 순위별 색상 마커 (1위=오렌지, 2위=보라, 3위=초록, ...)
  - 직장 위치 별 마커 별도 표시
  - 마커 탭 → 하단 슬라이드업 카드 (지역명/월세/통근/점수/신뢰도)
  - "AI 리포트 보기" 버튼 → DetailScreen 이동
- `ResultsScreen.tsx` 수정: 목록/지도 탭 토글 (세그먼트 컨트롤 스타일)
- TypeScript 오류 없음 ✅
- API lat/lng 응답 확인: 노원구 37.6542, 127.0568 ✅

#### GRU 학습 완료 + FastAPI 연동 ✅
- Kaggle CPU 학습 완료 (CUDA 아키텍처 불일치로 CPU fallback)
- `gru_predictions.parquet` (666행, 111 시군구 × 6 horizon) + `gru_rent_model.pt` (601KB)
- **버그 수정**: `sigungu_code`가 `list[str]` 타입으로 저장 → `data_loader.py`에서 `list.first()` 정규화
- GRU 연동 후 E2E 재검증: 동작구 1위(56.3점), 노원구 2위(56.1점) — GRU 예측 반영으로 순위 변동 확인 ✅
- `gru_predictions.parquet` → 111개 시군구 6개월 후 월세 예측값 정상 로드

---

### 2026-05-08 — Kaggle ML 학습 완료 + 실데이터 E2E 검증 통과

#### Kaggle 데이터 수집 완료
- `collect_rent.py` 수집 완료: apt 403,079행 + villa 1,491,021행 (2020-01 ~ 2026-04, 76개월)
- Kaggle Secrets fix: `UserSecretsClient().get_secret()` 방식 적용
- `train_lgbm.py` 경로 버그 수정: `INPUT_DIR.glob("*")` → `INPUT_DIR.rglob("apt_rent_history.parquet")` (재귀 탐색)

#### LightGBM + XGBoost 앙상블 학습 완료 (Kaggle)
- 학습 데이터: 9,161행 × 10 피처 (113 시군구 × 76개월)
- LightGBM CV OOF MAE: 97,781원
- XGBoost CV OOF MAE: 61,449원
- **앙상블 (60%LGB+40%XGB) MAE: 77,873원, MAPE: 16.2%** ✅
- SHAP 1위 피처: sigungu_code_int (69,271원)
- 출력물 다운로드 완료: `lgbm_rent_model.txt`, `xgb_rent_model.json`, `ensemble_rent_metrics.json`, `lgbm_shap_global.json`, `sigungu_monthly_features.parquet` → `data/processed/`

#### FastAPI 실데이터 E2E 재검증 ✅
- `scripts/verify/12_verify_api_e2e.py` 실행 성공
- Stage1 통과: **44개 시군구** (실 데이터 기반)
- Top3: #1 노원구 373,148원, #2 동작구 495,964원, #3 성남수정구 474,090원
- Gemini 리포트 0.07원, 비교 분석 0.05원 정상 응답
- `data_loader.py` 스키마 호환 확인 (year_month: Date, rent_mean_won: Float64 등)

---

### 2026-05-06 (3차) — 격자 centroid + 실데이터 연동 + GRU + React Native

#### SGIS 1km 격자 centroid 생성

- `scripts/transform/21_grid_centroid.py` 수정: `SPO_NO_CD`→grid_id, `SECT_CD`→sigungu_code
- `data/processed/grid_centroid.parquet` ✅ — 120,910 격자 (위경도 + 시군구 코드)

#### FastAPI 실데이터 연동

- `app/services/data_loader.py` ✅ (신규):
  - `sigungu_monthly_features.parquet` 최신 월 데이터 로드
  - `kakao_od.parquet` 가장 가까운 직장 클러스터 commute_min 조회
  - `hug_risk_by_sigungu.parquet` 사고율 join
  - `gru_predictions.parquet` 6개월 예측값 통합 (있을 때만)
  - 데이터 부족 시 mock 자동 fallback
- `app/routers/recommend.py` 수정: `_load_region_features()` → `_get_region_features(work_lat, work_lng)` (실데이터 우선)
- E2E 검증 ✅ — 실 5개 시군구 (마포구 1위, 관악구 2위, 남동구 3위)

#### GRU 시계열 학습 스크립트 (Kaggle용)

- `scripts/kaggle/train_gru.py` ✅ — PyTorch GRU (2층, hidden=128, Huber Loss)
  - 입력 피처 8개: rent_mean, deposit_mean, transaction_count, base_rate, hug_rate, youth_wage, pop_change_rate, unsold_units
  - 시퀀스 window=12개월 → horizon=6개월 예측
  - Early stopping (patience=10)
  - 출력: `gru_rent_model.pt`, `gru_rent_metrics.json`, `gru_predictions.parquet`
  - **주의**: PyTorch 로컬 미설치 → Kaggle 전용. 드라이런 데이터(5 시군구×1개월)는 시퀀스 부족 → Kaggle 실데이터 필요

#### React Native 앱 — Claude 디자인 전면 리디자인 ✅

- **테마 시스템** `mobile/src/theme/index.ts`: primary=#DA7756(오렌지), bg=#FAF9F6(크림), 타이포/그림자/반경 토큰
- **컴포넌트 라이브러리**:
  - `Button.tsx` — primary/outline/ghost × sm/md/lg, loading 상태
  - `Card.tsx` — touchable/static, elevated 옵션, borderColor
  - `ScoreBar.tsx` — 라벨 + 진행 바 + 퍼센트
  - `Tag.tsx` — success/warning/danger/info/default 변형
- **HomeScreen**: 오렌지 히어로 배너, 6개 직장 프리셋 칩, InputField(label/suffix/hint), 통계 3종
- **ResultsScreen**: 오렌지 서머리 헤더, RegionCard(rank원/이름/태그/점수), MetricPill 행, 4개 ScoreBar
- **DetailScreen**: 히어로(순위배지+지역명+3지표), ScoreCard 4개(색상 상단 테두리), InfoRow 목록, AI 리포트(오렌지 따옴표 바), 신뢰도 상세
- `App.tsx` — Home 자체 히어로(headerShown:false), Results/Detail 오렌지 헤더
- `npx expo export --platform web` ✅ 빌드 성공 (743KB bundle)
- TypeScript 오류 없음 ✅
- API URL: `http://localhost:8000/api/v1` (로컬 FastAPI 연동)

#### 인구 API 현황

- `https://apis.data.go.kr/1741000/RegistrationPopulationByRegion` → 500 오류 지속
- GRU `pop_change_rate` 피처: 현재 0으로 채움 (데이터 없을 때 fallback)
- 대안: KOSIS 인구통계 (추후 탐색)

#### Kaggle ML 노트북 — XGBoost 앙상블 추가

- `scripts/kaggle/train_lgbm.py` 수정: LightGBM + XGBoost 앙상블 (60%:40%)
- XGBoost: `tree_method=hist`, Kaggle GPU(`device=cuda`) 자동 감지
- 별도 GroupKFold CV `train_xgb_cv()` + OOF 앙상블 평가
- 출력: `lgbm_rent_model.txt`, `xgb_rent_model.json`, `ensemble_rent_metrics.json`

#### 모바일 앱 — 비교 분석 화면 추가

- `types/index.ts`: `RootStackParamList`에 `Compare` 화면 타입 추가
- `CompareScreen.tsx` ✅ (신규):
  - 지역 A/B 컬럼 헤더 (오렌지/보라 상단 테두리)
  - 종합 분석 VerdictCard (승자 배지 + 차이 서술)
  - 핵심 지표 비교 행 (좋음/나쁨 색상 표시)
  - 점수 바 쌍 비교 (A vs B 각 4개 점수)
  - 신뢰도 비교 + 20점 이상 차이 경고
- `ResultsScreen.tsx` 수정:
  - "비교 선택" 토글 버튼 (메타 바 우측)
  - 선택 모드: 카드에 체크박스, 최대 2개 선택
  - 선택 배너 ("비교 분석하기" 버튼)
- `Card.tsx` 수정: `style?: StyleProp<ViewStyle>`, `borderColor?` prop 추가

#### 가중치 슬라이더 UI + 백엔드 연동

- `WeightSlider.tsx` ✅ (신규 컴포넌트):
  - 4개 항목 (H+T 부담/통근/안전/미래) 5% 단위 +/- 조절
  - 진행 바 + 퍼센트 표시, 색상 구분
  - 합계 ≠ 100% 시 "자동 조정" 버튼 노출
- `HomeScreen.tsx` 수정: "가중치 설정" 섹션 추가 (접기/펼치기 토글)
- `types/index.ts` 수정: `weight_burden/commute/safety/future` 옵션 필드 추가
- `app/models/schemas.py` 수정: `RecommendRequest`에 가중치 4개 필드 추가 (선택)
- `app/services/recommender.py` 수정: `_effective_weights()` — 사용자 입력 우선, fallback 설계서 기본값
- `app/routers/recommend.py` 수정: `UserQuery`에 가중치 전달
- TypeScript 오류 없음 ✅
- Python 임포트 검증 ✅

#### 모바일 앱 빌드 최종 상태

- `npx expo export --platform web` ✅ 빌드 성공 (772KB bundle)
- TypeScript 오류 없음 ✅
- API URL: `http://localhost:8000/api/v1` (로컬 FastAPI 연동)
- Kaggle 가이드: `scripts/kaggle/KAGGLE_GUIDE.md` ✅

---

### 2026-05-03 — 명세 미확보 영역 정상 로직 완성 + features 빌더 prototype

- **시군구 코드**: SAMPLE 5개 → KNOWN_METRO 113개로 확장 (서울 25 + 경기 38 + 인천 10 + 부산 16 + 대구 8 + 광주 5 + 대전 5 + 울산 5 + 세종 1). 전국 250개는 사용자 csv 보강.
- **`.env` 명세 슬롯 추가**: 사용자가 집에서 한 줄 채우면 즉시 작동
  - `POPULATION_API_URL`, `POPULATION_API_FORMAT`, `POPULATION_EXTRA_PARAMS`
  - `REB_UNSOLD_STATBL_ID`, `REB_UNSOLD_DTACYCLE_CD`, `REB_UNSOLD_WRTTIME_START`
  - `MOLIT_STAT_BASE_URL`, `MOLIT_STAT_AUTH_PARAM`, `MOLIT_STAT_TBL_IDS`
- **검증·수집기 정상 로직 작성**:
  - [verify/03_verify_population.py](youth-ht/scripts/verify/03_verify_population.py) — `POPULATION_API_URL` 채워지면 정상 모드, 미채움 시 fallback 후보 탐색
  - [verify/05_verify_reb.py](youth-ht/scripts/verify/05_verify_reb.py) — 베이스 URL 가용성 ✅ 확인 (ERROR-300 정상 응답)
  - [verify/06_verify_molit_stat.py](youth-ht/scripts/verify/06_verify_molit_stat.py) — `MOLIT_STAT_BASE_URL` 채우면 정상 모드
  - [collect/08_collect_population.py](youth-ht/scripts/collect/08_collect_population.py) — 페이징 + JSON/XML 자동 처리 + 컬럼 매핑 후보 자동 시도
  - [collect/09_collect_unsold.py](youth-ht/scripts/collect/09_collect_unsold.py) — R-ONE SttsApiTblData 표준 응답 처리
  - [collect/10_collect_molit_stat.py](youth-ht/scripts/collect/10_collect_molit_stat.py) — 통계누리 다중 테이블 수집
- **직장 클러스터 100개**: `docs/work_clusters_seed.csv` 108행 → 카카오 키워드 검색으로 좌표 자동 부여 → `docs/work_clusters.csv` 100개 확보. 단 미스매칭 3건(부산 연산/대전 둔산/대전 정부청사) + 누락 8건(창원·김해·청주·천안·춘천·전주·여수·제주)은 사용자 검수.
- **features 빌더 prototype**:
  - [transform/20_build_sigungu_features.py](youth-ht/scripts/transform/20_build_sigungu_features.py) — 시군구 × 월 features (rent_mean/std, deposit_mean, transaction_count, area_mean, building_year, base_rate, hug_acc_rate). 5 시군구 × 2 building_type = 10행 prototype 산출 ✅
  - [transform/21_grid_centroid.py](youth-ht/scripts/transform/21_grid_centroid.py) — SGIS Shapefile → centroid + 시군구 매핑 스켈레톤 (사용자 다운로드 대기)
  - [transform/30_lgbm_train_prep.py](youth-ht/scripts/transform/30_lgbm_train_prep.py) — 학습 데이터 X/y 분리 + meta JSON ✅
- **사용자 액션 가이드 확장**: D(시군구 csv) + E(SGIS 격자) + F(직장 클러스터 검수) 추가
- **다음**: 사용자가 집에서 A/B/F 처리 후 03·05 즉시 검증 + 시군구 본 수집 GO

### 2026-05-06 (2차) — Kaggle 수집 노트북 + OD 매트릭스 완료 + ML 학습 파이프라인

#### 데이터 수집 전략 결정 (하이브리드)

| 작업 | 위치 | 이유 |
| --- | --- | --- |
| 아파트+연립 5년치 수집 | Kaggle | 서버에서 실행, 로컬 디스크 절약 |
| 카카오 OD 매트릭스 | 로컬 | 한국 IP, 이미 완료 |
| LightGBM/GRU 학습 | Kaggle | GPU 활용 |

#### 카카오 OD 매트릭스 수집 완료

- `scripts/collect/06_kakao_od.py` ✅ — 268 시군구 × 108 클러스터 = 28,944 쌍
- `data/processed/kakao_od.parquet` ✅ — commute_min (자동차 기준, 지방↔서울 haversine fallback 포함)
- 통근시간 범위: 0 ~ 1,188분 (지방 시군구는 Stage1에서 자동 필터)

#### Kaggle 수집 노트북

- `scripts/kaggle/collect_rent.py` — 자체완결형 Kaggle Script
  - 수도권+광역시 113 시군구 × 75개월 × 2종류 = 16,950 호출
  - 예상 소요: 2.4시간 (2 calls/sec)
  - Secrets: `DATA_GO_KR_KEY_DECODING`
  - 출력: `apt_rent_history.parquet`, `villa_rent_history.parquet`

#### Kaggle ML 학습 노트북

- `scripts/kaggle/train_lgbm.py` — 자체완결형 Kaggle Script
  - 집계(만원→원 변환) + ECOS 금리 + HUG 사고율 embedded dict 포함
  - GroupKFold CV + SHAP + 전체 재학습
  - 출력: `lgbm_rent_model.txt`, `lgbm_rent_metrics.json`, `lgbm_shap_global.json`

#### 피처 빌더 단위 수정

- `scripts/transform/20_build_sigungu_features.py` — `monthlyRent * 10_000` (만원→원), 청년 평형 85m² 이하
- `scripts/transform/30_lgbm_train_prep.py` — 검증 완료 ✅
- 로컬 dry-run 결과: MAE=335,419원 (MAPE=49% — 10행 과적합 예상, Kaggle 실데이터로 재학습 시 개선)

---

### 2026-05-06 — DeepSeek→Gemini 전환 + FastAPI E2E 완료 + 시군구 centroid 268건

#### LLM 서비스 레이어 (DeepSeek → Gemini 2.5 Flash)

- DeepSeek API 잔액 0 → Gemini 2.5 Flash (`gemini-2.5-flash-preview-05-20`)로 전환
- `app/services/llm.py` 완성: SQLite 캐시(SHA256 키), `render_recommendation_report`, `render_comparison_report`
- Gemini thinking_budget=0 설정 (응답 잘림 버그 해결 — thinking 토큰이 max_output_tokens 소비)
- 검증: `scripts/verify/10_verify_gemini.py` ✅ — 한글 63.5%, 0.08원/호출

#### STCIS 15분단위OD API 검증

- `scripts/verify/11_verify_stcis_od.py` ✅ — 2024-10-15 기준 84건 확인
- STCIS 최근 14일 데이터 미적재 → 약 6개월 전 날짜로 fallback 필요

#### 법정동코드 API → 전국 268 시군구 CSV

- `scripts/collect/11_collect_sigungu_codes.py` ✅ → `data/raw/sigungu_codes.csv` 268행
- `scripts/collect/11b_fill_missing_clusters.py` ✅ → work_clusters 8건 자동 보강 → 총 108개

#### 추천 룰 엔진 + 신뢰도 점수

- `app/services/recommender.py` — Stage1 필터(예산+통근) + Stage2 가중치 점수(burden 0.40, commute 0.30, safety 0.20, future 0.10) + Top N
- `app/services/confidence.py` — 신뢰도 0~100 (sample 30 + hug 20 + commute 20 + model 30)

#### LightGBM 스켈레톤 + SHAP

- `scripts/transform/31_lgbm_train.py` — GroupKFold CV + SHAP pred_contrib 저장

#### FastAPI 백엔드 E2E

- `app/main.py`, `app/models/schemas.py`, `app/routers/recommend.py` 완성
- 엔드포인트: POST /recommend, /recommend/report, /recommend/compare, GET /healthz
- `scripts/verify/12_verify_api_e2e.py` ✅ — Stage1 통과 6개, Top5, Gemini 리포트 0.077원, 비교 매트릭스

#### 시군구 centroid 268건 완료

- `scripts/transform/12_resolve_sigungu_centroid.py` — Kakao API quota 초과로 static 좌표 테이블(전국 268 시군구 하드코딩) + resume 체크포인트 추가
- `data/processed/sigungu_centroid.parquet` ✅ 268건 저장

---

### 2026-05-03 — 1주차 실행 준비 완료 (저녁 추가 작업)

- **3건 명세 자동 처리 시도**: WebSearch + WebFetch로 시도. R-ONE 베이스 URL `https://www.reb.or.kr/r-one/openapi/SttsApiTblData.do` 확인됨. 그러나 행안부·R-ONE STATBL_ID·통계누리는 모두 **로그인 + 첨부 파일 다운로드 필요**라 자동 처리 불가능. 사용자 액션 가이드 작성: `docs/user_action_required.md`
- **1주차 실행 플랜 작성**: `docs/week1_plan.md` (Day 1~7, 위험 + 완화)
- **추가 패키지 설치 (1주차)**: httpx, tenacity, tqdm, pyarrow, geopandas, shapely, pyproj, supabase, lightgbm, xgboost, scikit-learn — 모두 Python 3.13 호환 확인
- **스켈레톤 작성**:
  - `scripts/collect/_http.py` — httpx + tenacity 재시도 + RateLimiter + Checkpoint 공통 유틸
  - `scripts/collect/sigungu_codes.py` — 시군구 코드 리스트 (Sample 5 + load_all)
  - `scripts/collect/01_collect_apt_rent.py` — 아파트 5년치 수집기 (`--dry-run`/`--full`/`--resume`)
  - `scripts/collect/02_collect_villa_rent.py` — 연립다세대 수집기 (01과 모듈 공유)
  - `scripts/collect/07_ecos_rate_history.py` — ECOS 75개월 시계열 한 번에 저장
  - `scripts/transform/03_hug_to_sigungu.py` — HUG Excel → 252 시군구 Parquet
  - `migrations/0001_init.sql` — Supabase 6개 테이블 (grid_1km, rent_history, grid_monthly_features, work_cluster, od_commute, llm_cache)
  - `docs/work_clusters.csv` — 직장 클러스터 시드 10개 (1주차 Day 5에 100개로 확장)
  - `README.md` — 프로젝트 README + 빠른 시작
- **실행 검증 (실제 호출)**:
  - HUG 변환 ✅ → 252 시군구 → `data/processed/hug_risk_by_sigungu.parquet`
  - ECOS 수집 ✅ → 75개월 → `data/processed/ecos_rate.parquet`
  - 아파트 dry-run ✅ → 5 시군구 × 1개월 → 6,891행
  - 연립다세대 dry-run ✅ → 5 시군구 × 1개월 → 2,453행
- **다음**: 사용자 명세 3건(A/B/C) 확보 → 03·05·06 검증 재실행 → 1주차 본 수집 GO

### 2026-05-03 — 0주차 데이터 검증 완료

- **Step 1**: 환경 셋업 — `.venv` (Python 3.13.7), 패키지 6종 설치, `.env`/`.gitignore`/`CLAUDE.md` 생성
- **Step 2**: 디렉토리 트리 + HUG Excel `data/raw/HUG_전국보증사고현황_25년8월.xlsx` 복사
- **Step 3**: 9개 검증 스크립트 + 공통 유틸(`_common.py`) 작성
- **Step 4**: 9개 스크립트 순차 실행 → **6 ✅ / 1 ⚠️ / 2 ❌**
- **Step 5**: 보고서 작성 → `docs/data_verification_report.md`
- **Step 6**: 본 CLAUDE.md 업데이트

### 검증 결과 요약 (상세는 `docs/data_verification_report.md`)

| # | 소스 | 결과 | 핵심 메모 |
| --- | --- | --- | --- |
| 01 | 아파트 전월세 | ✅ | resultCode 신규 명세 `000` (3자리) |
| 02 | 연립다세대 | ✅ | **대지권면적 필드 응답에 없음** |
| 03 | 행안부 인구 | ❌ | 엔드포인트 5개 모두 실패 — 사용자 확인 필요 |
| 04 | ECOS 금리 | ✅ | 75개월 시계열 (2020-01 ~ 2026-03, 최근 2.5%) |
| 05 | R-ONE | ⚠️ | 키 OK, SERVICE 파라미터 명세 필요 |
| 06 | 통계누리 | ❌ | 베이스 URL 미상 — 사용자 확인 필요 |
| 07 | KOSIS 청년임금 | ✅ | 연령 5세 구간 단위 (1세 단위 X) |
| 08 | 카카오 길찾기 | ✅ | 강남→판교 27분 / 18,400원 |
| 09 | HUG Excel | ✅ | 273행 멀티헤더, 4개 핵심 컬럼 검출 |

## 사용자 액션 필요 (3건)

다음 명세를 확보해야 행안부 인구·R-ONE·통계누리 검증 재시도 가능:

- **A. 행안부 인구 OpenAPI URL**: 공공데이터포털 마이페이지 → 활용신청 현황 → 해당 데이터셋 상세
- **B. R-ONE OpenAPI 명세**: reb.or.kr/r-one → OpenAPI 가이드 (필수 SERVICE 값, STATBL_ID)
- **C. 통계누리 OpenAPI 진입점**: stat.molit.go.kr → OpenAPI 메뉴 (베이스 URL, 인증 형식)

## 다음 단계 (1주차 본 작업)

### 사용자 액션 (집에서 처리 — 우선순위 A>B>C)

1. **A. 행안부 인구 OpenAPI End Point** — 가이드 `docs/user_action_required.md` §A
2. **B. R-ONE 미분양 STATBL_ID** — 가이드 `docs/user_action_required.md` §B
3. **C. 통계누리 OpenAPI 진입점** — 가이드 `docs/user_action_required.md` §C

A·B 확보 시 GRU 입력 8개 모두 충족.

### 즉시 시작 가능 명령어 (1주차 본 수집 GO)

```powershell
# 아파트 5년치 (250 시군구 × 60개월, rate-limit 1초/회 → 약 4.2시간)
.\.venv\Scripts\python.exe scripts\collect\01_collect_apt_rent.py --full --start 2020-01

# 연립다세대 5년치
.\.venv\Scripts\python.exe scripts\collect\02_collect_villa_rent.py --full --start 2020-01

# 검증 통과 영역 추가 진행
# - SGIS 1km 격자 다운로드 (사용자 수동, sgis.kostat.go.kr)
# - Supabase 프로젝트 생성 + migrations/0001_init.sql 적용
# - work_clusters.csv 100개로 확장
# - 카카오 Directions OD 매트릭스 빌드 (5,000 격자 × 100 클러스터 샘플링)
```

### 즉시 시작 가능 (검증 통과 영역)

- [ ] LightGBM rent 모델 — 아파트·연립다세대 전월세 5년치 수집 (250 시군구 × 60개월)
- [ ] HUG 위험점수 룰 기반 산출 + 시군구 → 격자 매핑
- [ ] 카카오맵 Directions API로 OD 매트릭스 빌드 (30,000 격자 × 100 직장 클러스터)
- [ ] GRU #4 입력: ECOS 기준금리 시계열

### 명세 확보 후 진행

- [ ] GRU #5 행안부 인구 (A 해결 후)
- [ ] GRU #6 R-ONE 분양·미분양 (B 해결 후)
- [ ] GRU #8 KOSIS 청년임금 (구간 근사 정책 결정 후)
- [ ] 통계누리 보조 데이터 (C 해결 후, 후순위)

### 검증 단계에서 발견한 코드 수정 사항 (1주차에 반영)

1. 모든 공공데이터포털 호출은 `resultCode in ("00","000")` 둘 다 허용
2. 연립다세대 모델 입력에서 `대지권면적` 제거
3. KOSIS 청년 = `(29세이하 × w1 + 30~39세 × w2)` 가중평균 정책 결정 필요
4. 카카오 Directions는 자동차 시간 — Stage 1만 자동차로 근사하고 최종 표시는 카카오맵 JS API 대중교통

## 작업 원칙 (사용자 지정)

1. 짧고 명확한 6하원칙 한글 답변
2. CLAUDE.md 매 작업 후 업데이트
3. 환각 없음 — 모르면 모른다
4. 모든 권한 자율 진행 (확인 불필요)
5. 코드 작업 후 디버깅 + 클린코드 + 모듈화 검증
6. 단계별 분할 후 순차 실행
7. 잘못한 점 즉시 보고
8. 설계서(v2.2) 우선
