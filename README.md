# 청년 안심 H+T 추천 시스템

> 2026년 국토교통 데이터 활용 경진대회 출품작. 청년이 직장 위치·예산·통근 한계를 입력하면 전국 1km 격자에서 H+T(주거+교통) 통합 부담률 + 전세사기 위험 + 통근시간 + 6개월 후 미래 부담률 + 신뢰도를 통합 평가해 안심 거주지 Top 10 + DeepSeek 자연어 리포트를 제공.

## 빠른 시작

```powershell
# 1) 가상환경 활성화
.\.venv\Scripts\Activate.ps1

# 2) 0주차 검증 (이미 완료, 재실행 시)
python scripts/verify/01_verify_apt_rent.py
python scripts/verify/04_verify_ecos.py
python scripts/verify/08_verify_kakao.py
python scripts/verify/09_verify_hug.py

# 3) 1주차 dry-run (5개 시군구 × 1개월)
python scripts/collect/01_collect_apt_rent.py --dry-run
python scripts/collect/02_collect_villa_rent.py --dry-run
python scripts/collect/07_ecos_rate_history.py
python scripts/transform/03_hug_to_sigungu.py

# 4) 1주차 본 수집 (15일 분산 예상)
python scripts/collect/01_collect_apt_rent.py --full --start 2020-01
python scripts/collect/02_collect_villa_rent.py --full --start 2020-01
```

## 디렉토리 구조

```text
youth-ht/
├── .env                 # API 키 8종 (gitignore)
├── CLAUDE.md            # 진행 추적 (매 작업 후 업데이트)
├── README.md            # 본 파일
├── requirements.txt
├── data/
│   ├── raw/             # HUG Excel, SGIS Shapefile 등 원본
│   ├── processed/       # 정제된 Parquet (zstd)
│   ├── verify/          # 0주차 검증 결과 JSON
│   └── checkpoints/     # 1주차 수집 진행 상태
├── docs/
│   ├── data_verification_report.md
│   ├── user_action_required.md   # 행안부·R-ONE·통계누리 명세 확보 가이드
│   ├── week1_plan.md
│   └── work_clusters.csv         # 100개 직장 클러스터 (현재 10개 시드)
├── migrations/
│   └── 0001_init.sql
└── scripts/
    ├── verify/          # 0주차 (완료)
    ├── collect/         # 1주차 수집기 (스켈레톤)
    └── transform/       # 1주차 변환기 (스켈레톤)
```

## 진행 상태

- ✅ 0주차 — 데이터 검증 완료 (6 ✅ / 1 ⚠️ / 2 ❌, 사용자 명세 확인 대기)
- ⏳ 1주차 — 실행 준비 완료, 사용자 승인 시 dry-run → 본 수집 시작
- ⬜ 2주차 — 전처리 + EDA + Feature Engineering
- ⬜ 3~4주차 — LightGBM/XGBoost/GRU 학습
- ⬜ 5주차 — DeepSeek 통합 + FastAPI
- ⬜ 6주차 — React Native + 배포
- ⬜ 6.5주차 — 최적화 + 시연 영상

## 가점 전략

15/25점 (AI 활용 10점 + 데이터 융합 5점). 안심구역·가명결합 가점 10점은 시설 일시중단으로 포기 결정. 본점수에서 결판.

## 작업 원칙

- 짧고 명확한 6하원칙 한글 응답
- CLAUDE.md 매 작업 후 업데이트
- 환각 금지, 모르면 모른다
- 모든 권한 자율 진행
- 디버깅 + 클린코드 + 모듈화 검증
- 단계별 분할 후 순차 실행
- 잘못한 점 즉시 보고
- 설계서 v2.2 우선
