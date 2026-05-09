# 청년 안심 H+T 추천 시스템

> 2026년 국토교통 데이터 활용 경진대회 출품작.
> 청년이 직장 위치·예산·통근 한계를 입력하면 H+T(주거+교통) 통합 부담률, 전세사기 위험, 통근시간, 6개월 후 미래 부담률, 신뢰도를 통합 평가해 **안심 거주지 Top 10 + AI 자연어 리포트**를 제공하는 모바일 서비스.

## 서비스 현황

| 구성 | 상태 | 주소 |
|------|------|------|
| **FastAPI 백엔드** | ✅ EC2 운영중 | `http://3.26.146.162:8000` |
| **React Native 앱** | ✅ 빌드 완료 | 로컬 Expo / EC2 연동 가능 |
| **Supabase DB** | ✅ 연결됨 | llm_cache 연동 |
| **Kaggle ML** | ✅ 학습 완료 | LightGBM+XGBoost+GRU |

## API 엔드포인트

```
GET  http://3.26.146.162:8000/api/v1/healthz          # 헬스체크
POST http://3.26.146.162:8000/api/v1/recommend        # 거주지 추천
POST http://3.26.146.162:8000/api/v1/recommend/report # AI 리포트
POST http://3.26.146.162:8000/api/v1/recommend/compare # 비교 분석
```

### 추천 요청 예시

```bash
curl -X POST http://3.26.146.162:8000/api/v1/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "work_lat": 37.5172,
    "work_lng": 127.0473,
    "work_name": "강남역",
    "budget_won": 800000,
    "commute_limit_min": 60,
    "age": 27
  }'
```

## 기술 스택

| 레이어 | 기술 |
|--------|------|
| 백엔드 | FastAPI + uvicorn (AWS EC2 t3.micro) |
| 모바일 | React Native (Expo) |
| DB | Supabase (PostgreSQL, ap-south-1) |
| 지도 | 카카오맵 JS API (WebView) |
| ML 모델 | LightGBM + XGBoost (앙상블) + GRU (시계열) |
| LLM | Gemini 2.5 Flash (자연어 리포트) |

## ML 성능

| 모델 | MAE | MAPE |
|------|-----|------|
| LightGBM | 97,781원 | — |
| XGBoost | 61,449원 | — |
| **앙상블 (60:40)** | **77,873원** | **16.2%** |
| GRU (6개월 예측) | — | 111 시군구 |

## 로컬 개발

```powershell
# 가상환경 활성화
.\.venv\Scripts\Activate.ps1

# FastAPI 서버 실행
uvicorn app.main:app --reload

# E2E 검증
python scripts/verify/12_verify_api_e2e.py
```

## EC2 배포

```bash
# 초기 세팅 (최초 1회)
ssh -i ~/.ssh/youth-ht.pem ubuntu@3.26.146.162 'bash -s' < scripts/deploy/setup_ec2.sh

# 데이터 업로드
bash scripts/deploy/upload_data.sh 3.26.146.162 ~/.ssh/youth-ht.pem

# 코드 업데이트
ssh -i ~/.ssh/youth-ht.pem ubuntu@3.26.146.162 'bash ~/youth-ht/scripts/deploy/deploy.sh'
```

## 모바일 앱 (Expo)

```bash
cd mobile
npm install
# 로컬 개발
npx expo start

# EC2 연결 빌드
echo "EXPO_PUBLIC_API_URL=http://3.26.146.162:8000/api/v1" > .env
npx expo export --platform web
```

## 디렉토리 구조

```text
youth-ht/
├── .env                      # API 키 (gitignore)
├── app/
│   ├── main.py               # FastAPI 앱
│   ├── models/schemas.py     # Pydantic 스키마
│   ├── routers/recommend.py  # 추천 엔드포인트
│   └── services/
│       ├── recommender.py    # Stage1/2 필터·점수
│       ├── data_loader.py    # parquet → RegionFeature
│       ├── confidence.py     # 신뢰도 산출
│       └── llm.py            # Gemini + Supabase 캐시
├── mobile/
│   └── src/screens/          # Home/Results/Map/Detail/Compare
├── scripts/
│   ├── kaggle/               # collect_rent, train_lgbm, train_gru
│   ├── collect/              # 데이터 수집기
│   ├── transform/            # 전처리·피처 빌더
│   ├── verify/               # E2E 검증
│   └── deploy/               # EC2 배포 스크립트
├── data/processed/           # Parquet (gitignore)
├── migrations/0001_init.sql  # Supabase 스키마
└── docs/work_clusters.csv    # 108개 직장 클러스터
```

## 진행 상태

- ✅ 데이터 수집 — 아파트 403K + 연립 1.49M 실거래 (76개월)
- ✅ ML 학습 — LightGBM+XGBoost 앙상블, GRU 6개월 예측
- ✅ FastAPI 백엔드 — 추천/리포트/비교 엔드포인트
- ✅ React Native 앱 — 홈/결과/지도/상세/비교 5개 화면
- ✅ 카카오맵 지도 — 순위별 마커 + 하단 카드
- ✅ Supabase 연동 — llm_cache 테이블
- ✅ AWS EC2 배포 — `3.26.146.162:8000` 운영중
- ⬜ 앱 스토어 배포 (EAS Build)
- ⬜ HTTPS / 도메인 설정

## 가점 전략

15/25점 (AI 활용 10점 + 데이터 융합 5점).
