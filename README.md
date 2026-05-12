# 청년 안심 H+T 추천 시스템

2026년 국토교통 데이터 활용 경진대회 출품작입니다. 청년이 직장 위치, 월 예산, 통근 한계를 입력하면 주거비와 교통 접근성, 전세보증 사고 위험, 6개월 후 월세 부담 예측, 데이터 신뢰도를 함께 평가해 안심 거주지 Top 10과 AI 자연어 리포트를 제공합니다.

이 저장소는 **프론트엔드, 백엔드, 모바일 앱, ML 학습/추론 코드, 데이터 수집/전처리 스크립트, 인프라 배포 스크립트**를 한 곳에서 관리하는 monorepo입니다.

## 서비스 현황

| 구성 | 상태 | 위치/주소 |
| --- | --- | --- |
| 웹 프론트엔드 | 운영 배포 | `frontend/`, <https://youth-ht-web.vercel.app> |
| FastAPI 백엔드 | EC2 운영 | `app/`, `http://3.26.146.162:8000` |
| 모바일 앱 | Expo 앱 구현 | `mobile/` |
| ML 모델 | 학습 완료 | LightGBM + XGBoost 앙상블, GRU 6개월 예측 |
| DB/캐시 | 연결 완료 | Supabase `llm_cache`, 로컬 `data/llm_cache.db` |
| 배포 | 운영 중 | Vercel 웹 SPA + AWS EC2 FastAPI |

## 핵심 기능

- 직장 위치 기반 거주 후보 추천: Kakao 장소 검색으로 직장 좌표를 정하고 추천 API에 전달
- Stage 1 하드 필터: 통근 시간, 예산, HUG 보증사고 위험, 월세 표본 수 기준으로 후보 제거
- Stage 2 가중 점수화: 부담률, 통근, 안전, 미래 부담 변화 점수를 사용자 가중치로 합산
- 지도 시각화: Kakao Maps JavaScript SDK로 직장 위치와 추천 후보 마커 표시
- 상세 분석: 추천 동네별 월세, 보증금, 통근 시간, 위험도, 부담률, 예측 차트 표시
- AI 리포트: Gemini 기반 추천 사유와 비교 리포트 생성, Supabase/SQLite 캐시 활용

## 기술 스택

| 영역 | 기술 |
| --- | --- |
| 웹 | Vite, React 19, TanStack Router, Tailwind CSS v4, Recharts, Lucide |
| 지도/장소 | Kakao Maps JavaScript SDK, Kakao Places keywordSearch |
| 백엔드 | Python, FastAPI, Pydantic, Uvicorn |
| 추천 엔진 | 룰 기반 Stage 1/2 필터 + 사용자 가중치 |
| ML | LightGBM, XGBoost, GRU, scikit-learn, PyTorch 모델 산출물 |
| 데이터 처리 | pandas, polars, pyarrow, geopandas, shapely, pyproj |
| DB/LLM | Supabase, Gemini 2.5 Flash |
| 모바일 | React Native, Expo |
| 인프라 | Vercel, AWS EC2, Nginx, systemd 배포 스크립트 |

## API

운영 백엔드 기준:

```text
GET  http://3.26.146.162:8000/api/v1/healthz
POST http://3.26.146.162:8000/api/v1/recommend
POST http://3.26.146.162:8000/api/v1/recommend/report
POST http://3.26.146.162:8000/api/v1/recommend/compare
```

추천 요청 예시:

```bash
curl -X POST http://3.26.146.162:8000/api/v1/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "age": 27,
    "work_lat": 37.5172,
    "work_lng": 127.0473,
    "work_name": "강남역",
    "budget_won": 800000,
    "commute_limit_min": 60,
    "top_n": 10
  }'
```

응답에는 추천 순위, 시군구명, 평균 월세/보증금, 통근 시간, HUG 사고율, 현재 부담률, 6개월 후 예측 부담률, 세부 점수, 신뢰도, 지도 좌표가 포함됩니다.

## 프론트엔드

경로: `frontend/`

역할:

- Vercel에 배포되는 실제 웹 앱
- `/recommend`에서 직장 위치, 예산, 통근 한계, 추천 성향을 입력
- Kakao Places 검색 결과를 선택해 `work_lat`, `work_lng`를 추천 API에 전달
- 추천 결과 카드, Kakao 지도, 상세 페이지, GRU 예측 차트, AI 리포트를 렌더링
- API 실패 시 `src/lib/mock-data.ts`의 mock 데이터로 폴백

주요 파일:

| 파일 | 역할 |
| --- | --- |
| `frontend/src/routes/recommend.tsx` | 추천 입력/검색/결과 페이지 |
| `frontend/src/routes/area.$id.tsx` | 동네 상세 분석 및 AI 리포트 |
| `frontend/src/components/map-view.tsx` | Kakao 지도 마커 |
| `frontend/src/components/area-card.tsx` | 추천 결과 카드 |
| `frontend/src/lib/api.ts` | 백엔드 API 클라이언트와 결과 캐시 |
| `frontend/src/lib/kakao-map.ts` | Kakao SDK 로더와 장소 검색 |
| `frontend/vercel.json` | Vercel SPA 빌드 및 `/api/*` rewrite |

로컬 실행:

```powershell
cd frontend
npm install
npm run dev
```

빌드/검증:

```powershell
cd frontend
npm run lint
npm run build:vercel
```

환경 변수:

```text
VITE_KAKAO_JS_KEY=<카카오 JavaScript 키>
VITE_API_URL=http://3.26.146.162
```

Vercel 운영 배포에서는 `VITE_API_URL`을 비워 두고 `frontend/vercel.json`의 `/api/:path* -> http://3.26.146.162/api/:path*` rewrite를 사용합니다.

## 백엔드

경로: `app/`

역할:

- 추천 API, AI 리포트 API, 비교 리포트 API 제공
- `data/processed/*.parquet`에서 시군구 피처 로드
- 데이터가 없거나 로드 실패 시 mock region 데이터로 폴백
- Gemini 호출과 캐시 처리

주요 파일:

| 파일 | 역할 |
| --- | --- |
| `app/main.py` | FastAPI 앱, CORS, 라우터 등록 |
| `app/models/schemas.py` | 요청/응답 Pydantic 스키마 |
| `app/routers/recommend.py` | `/recommend`, `/recommend/report`, `/recommend/compare` |
| `app/services/recommender.py` | Stage 1 필터, Stage 2 점수화 |
| `app/services/data_loader.py` | Parquet 피처 로딩 |
| `app/services/confidence.py` | 데이터 신뢰도 산출 |
| `app/services/llm.py` | Gemini 리포트 생성 및 캐시 |

로컬 실행:

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

검증:

```powershell
python scripts/verify/12_verify_api_e2e.py
```

## ML

현재 모델 구성:

| 모델 | 목적 | 산출물 |
| --- | --- | --- |
| LightGBM | 월세 예측 baseline | `data/processed/lgbm_rent_model.txt` |
| XGBoost | 월세 예측 보조 모델 | `data/processed/xgb_rent_model.json` |
| 앙상블 | LightGBM/XGBoost 결합 | `data/processed/ensemble_rent_metrics.json` |
| GRU | 6개월 후 부담률/월세 흐름 예측 | `data/processed/gru_rent_model.pt`, `gru_predictions.parquet` |

기록된 성능:

| 모델 | MAE | MAPE |
| --- | --- | --- |
| LightGBM | 97,781원 | - |
| XGBoost | 61,449원 | - |
| 앙상블 60:40 | 77,873원 | 16.2% |
| GRU | - | 111 시군구 예측 |

학습/전처리 스크립트:

| 경로 | 역할 |
| --- | --- |
| `scripts/transform/30_lgbm_train_prep.py` | 월세 모델 학습 데이터 생성 |
| `scripts/transform/31_lgbm_train.py` | LightGBM 학습 |
| `scripts/kaggle/train_lgbm.py` | Kaggle용 LightGBM 학습 |
| `scripts/kaggle/train_gru.py` | GRU 학습 |
| `scripts/kaggle/kernel_push/train_gru.py` | Kaggle Kernel 제출용 GRU 학습 스크립트 |

## 데이터셋

`data/`는 원천/처리 데이터와 모델 산출물을 담는 로컬 데이터 디렉터리입니다. 대용량 파일과 민감할 수 있는 데이터는 `.gitignore`로 제외되어 있으며, GitHub에는 수집/전처리/검증 스크립트를 중심으로 관리합니다.

활용 데이터:

| 데이터 | 용도 | 주요 파일/스크립트 |
| --- | --- | --- |
| 국토부 아파트 전월세 실거래 | 월세/보증금 학습 | `scripts/collect/01_collect_apt_rent.py`, `apt_rent_history.parquet` |
| 국토부 연립다세대 전월세 | 월세/보증금 학습 | `scripts/collect/02_collect_villa_rent.py`, `villa_rent_history.parquet` |
| HUG 보증사고 현황 | 전세사기/보증 위험도 | `data/raw/HUG_전국보증사고현황_25년8월.xlsx`, `hug_risk_by_sigungu.parquet` |
| Kakao OD/길찾기 | 통근 시간 | `scripts/collect/06_kakao_od.py`, `kakao_od.parquet` |
| 한국은행 ECOS 기준금리 | 시계열 보조 피처 | `scripts/collect/07_ecos_rate_history.py`, `ecos_rate.parquet` |
| 행안부 인구 | 지역 인구 변화 피처 | `scripts/collect/08_collect_population.py`, `pop_change_by_sido.parquet` |
| 한국부동산원 R-ONE 미분양 | 시장 위험/수급 피처 | `scripts/collect/09_collect_unsold.py`, `unsold_by_sido.parquet` |
| KOSIS 청년 임금 | 청년 소득 근사 | `scripts/collect/10_collect_kosis_wage.py`, `kosis_youth_wage.parquet` |
| STCIS 15분 OD | 대중교통/통행 보조 | `scripts/verify/11_verify_stcis_od.py` |
| SGIS 1km 격자 | 격자 단위 확장 | `data/raw/grid_1km/`, `scripts/transform/21_grid_centroid.py` |
| 법정동/시군구 코드 | 지역 매핑 | `data/raw/sigungu_codes.csv`, `scripts/collect/11_collect_sigungu_codes.py` |

검증 결과는 `data/verify/*.json`과 `docs/data_verification_report.md`에 기록합니다.

## 모바일 앱

경로: `mobile/`

역할:

- React Native/Expo 기반 모바일 UI
- 홈, 추천 결과, 지도, 상세, 비교 화면 구현
- EC2 API와 연동 가능한 클라이언트 구조

실행:

```bash
cd mobile
npm install
npx expo start
```

EC2 API 연결:

```bash
echo "EXPO_PUBLIC_API_URL=http://3.26.146.162:8000/api/v1" > .env
```

## 인프라와 배포

### 웹 프론트엔드

- Vercel 프로젝트: `youth-ht-web`
- GitHub 연결 repo: `LeeJaeHaeng/youth-ht`
- Vercel Root Directory: `frontend`
- Build Command: `npm run build:vercel`
- Output Directory: `dist-vercel`
- 운영 URL: <https://youth-ht-web.vercel.app>

`frontend/vercel.json`은 다음 동작을 담당합니다.

- `npm run build:vercel`로 정적 SPA 생성
- `/api/*` 요청을 EC2 FastAPI `http://3.26.146.162/api/*`로 프록시
- 그 외 경로는 `/index.html`로 fallback

### 백엔드

- AWS EC2: `3.26.146.162`
- FastAPI 실행: Uvicorn
- 배포 스크립트: `scripts/deploy/`
- Nginx 설정 예시: `scripts/deploy/youth-ht.nginx.conf`

배포 명령:

```bash
# 초기 세팅
ssh -i ~/.ssh/youth-ht.pem ubuntu@3.26.146.162 'bash -s' < scripts/deploy/setup_ec2.sh

# 데이터 업로드
bash scripts/deploy/upload_data.sh 3.26.146.162 ~/.ssh/youth-ht.pem

# 코드 업데이트
ssh -i ~/.ssh/youth-ht.pem ubuntu@3.26.146.162 'bash ~/youth-ht/scripts/deploy/deploy.sh'
```

## 저장소 구조

```text
youth-ht/
├── app/                         # FastAPI 백엔드
├── frontend/                    # Vercel 웹 SPA
├── mobile/                      # Expo 모바일 앱
├── scripts/
│   ├── collect/                 # 원천 데이터 수집
│   ├── transform/               # 피처 생성/모델 학습 전처리
│   ├── verify/                  # API/데이터 검증
│   ├── kaggle/                  # Kaggle 학습/업로드
│   └── deploy/                  # EC2 배포
├── migrations/                  # Supabase 스키마
├── docs/                        # 검증 보고서/작업 가이드
├── data/                        # 로컬 데이터/모델 산출물, gitignore
├── requirements.txt             # Python 의존성
└── README.md
```

## 빠른 검증

```powershell
# 백엔드 헬스체크
Invoke-WebRequest http://3.26.146.162:8000/api/v1/healthz

# 백엔드 E2E
python scripts/verify/12_verify_api_e2e.py

# 프론트엔드
cd frontend
npm run lint
npm run build:vercel
```

## 진행 상태

- 완료: 데이터 수집/검증 11종, 월세 모델 학습, GRU 예측, FastAPI 추천 API, Gemini 리포트, React 웹 SPA, Kakao 장소 검색/지도, Vercel 배포, EC2 백엔드 운영
- 진행 필요: 앱 스토어 배포, HTTPS/API 도메인 정식 연결, 데이터 산출물 재현 절차 자동화, npm 의존성 취약점 정리, 추천 품질 사용자 테스트

## 가점 전략

- AI 활용: Gemini 자연어 추천 리포트, GRU 미래 부담 예측, ML 월세 예측 모델
- 데이터 융합: 실거래, 보증사고, 통근, 금리, 인구, 미분양, 임금, 격자/시군구 공간 데이터 결합
