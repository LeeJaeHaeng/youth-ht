# CLAUDE.md — 청년 안심 H+T 웹 프론트엔드 (creative-heartbeat-ui)

> 이 문서는 Claude Code 세션 간 진행 상황을 추적합니다. 매 작업 후 업데이트합니다.

## 프로젝트 한 줄 요약

`youth-ht` FastAPI 백엔드와 연동하는 웹 프론트엔드. 직장 위치·예산·통근 한계를 입력받아 AI 추천 결과(Top 10) + GRU 월세 예측 차트 + Gemini AI 리포트를 표시.

## 기술 스택

- **프레임워크**: Vite + React + TanStack Router (Vercel은 정적 SPA 엔트리 사용)
- **번들러**: Vite 7.x
- **스타일링**: Tailwind CSS v4 + 직접 구성한 컴포넌트
- **차트**: Recharts (AreaChart)
- **지도/장소 검색**: 카카오맵 JavaScript SDK (`VITE_KAKAO_JS_KEY`, `services.Places.keywordSearch`)
- **아이콘**: Lucide React
- **API 연동**: `fetch` + `VITE_API_URL` 환경 변수 (Vercel은 `/api` rewrite)
- **백엔드**: FastAPI EC2 `http://3.26.146.162`
- **프론트 배포**: Vercel `https://youth-ht-web.vercel.app`

## 디렉토리 구조

```text
creative-heartbeat-ui/
├── .env.local              # VITE_API_URL, VITE_KAKAO_JS_KEY (gitignore)
├── CLAUDE.md               # 이 파일
├── README.md               # 실행/배포 요약
├── index.html              # Vercel SPA 엔트리
├── vercel.json             # Vercel build/output/rewrite 설정
├── vite.spa.config.ts      # Vercel 정적 SPA 빌드 설정
├── src/
│   ├── spa.tsx             # Vercel SPA React 엔트리
│   ├── lib/
│   │   ├── api.ts          # fetchRecommend, fetchReport, OFFICE_PRESETS, resultCache
│   │   ├── kakao-map.ts    # 카카오맵 SDK 로더, 장소 검색
│   │   └── mock-data.ts    # Area 타입, toArea() 변환, AREAS mock 폴백
│   ├── components/
│   │   ├── area-card.tsx   # AreaCard, ConfidencePill, RiskBadge
│   │   ├── map-view.tsx    # 카카오맵 기반 추천 결과 지도
│   │   └── site-chrome.tsx # SiteHeader, SiteFooter
│   ├── routes/
│   │   ├── __root.tsx      # 루트 레이아웃
│   │   ├── index.tsx       # 홈 랜딩 페이지
│   │   ├── recommend.tsx   # 조건 입력 + AI 추천 결과 페이지
│   │   ├── area.$id.tsx    # 동네 상세 분석 페이지
│   │   └── about.tsx       # 작동 원리 페이지
│   └── routeTree.gen.ts    # TanStack Router 자동 생성 (수동 편집 금지)
└── package.json
```

## API 연동 구조

```
recommend.tsx
  ├─ handlePlaceSearch() → Kakao Places keywordSearch → work_lat/work_lng 갱신
  └─ handleSearch() → fetchRecommend(req) → POST /api/v1/recommend
       ↓ ApiRecommendItem[]
       ↓ toArea(item, req) → Area[]
       ↓ saveResultCache(res.items, req)  (메모리 + sessionStorage 캐시)

area.$id.tsx
  └─ resolveArea(id) → hydrateResultCache() → resultCache.items.find(id) → toArea() → Area
       └─ useEffect → fetchReport(area._raw, area._req) → GET /api/v1/recommend/report
```

## 직장 위치 입력

- 기본은 카카오 장소 검색. 회사명·건물명·역명을 검색하고 결과를 선택하면 해당 좌표로 추천 API를 호출한다.
- 빠른 선택 버튼으로 여의도, 강남, 판교, 광화문, 마곡, 구로디지털을 제공한다.
- `OFFICE_PRESETS`에는 여의도, 강남, 판교, 광화문, 마곡, 구로디지털, 을지로, 상암DMC, 동대문, 잠실 좌표가 있다.

## 주의 사항

- 추천 결과 캐시는 인메모리와 `sessionStorage`를 함께 사용한다. 같은 브라우저 세션에서는 지도 마커에서 `/area/:id`로 이동해도 API 결과 상세를 유지한다.
- 백엔드 연결 실패 시 `AREAS` mock 데이터로 자동 폴백.
- `routeTree.gen.ts`는 Vite dev server 기동 시 자동 갱신됨.
- 카카오맵 JavaScript 키는 카카오 Developers > 앱 설정 > 플랫폼 > Web에 현재 도메인이 등록되어 있어야 로드된다.
  - 로컬 검증: `http://localhost:3001`, `http://127.0.0.1:3001`
  - 배포 도메인: `https://youth-ht-web.vercel.app`
  - Preview 도메인도 직접 테스트하려면 해당 Preview URL을 추가 등록해야 한다.

## 로컬 실행

```powershell
npm install
npm run dev
# → http://localhost:3000 (3000 사용 중이면 3001로 자동 전환)
```

필수 환경 변수:

```powershell
VITE_API_URL=http://3.26.146.162
VITE_KAKAO_JS_KEY=<카카오 JavaScript 키>
```

Vercel 배포에서는 `VITE_API_URL`을 비워 두고 같은 origin의 `/api/*`를 호출한다. `vercel.json`이 `/api/:path*`를 `http://3.26.146.162/api/:path*`로 프록시한다.

백엔드도 함께 실행 필요:

```powershell
cd ../youth-ht
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

## 진행 로그

### 2026-05-12 — 프로젝트 정리와 문서 최신화 ✅

#### 작업 내용

- Vercel/로컬 빌드 산출물 `dist`, `dist-vercel` 삭제
- 로컬 실행 로그 `dev-spa.*.log`, `preview.*.log`, `serve.*.log` 삭제
- 현재 앱에서 참조되지 않는 shadcn 템플릿 묶음 `src/components/ui`, `src/hooks/use-mobile.tsx`, `src/lib/utils.ts`, `components.json` 삭제
- 도구 임시 폴더 `.serena`와 상위 `.playwright-mcp` 삭제
- 루트 `README.md`와 `creative-heartbeat-ui/README.md` 추가

#### 남은 확인

- `npm run build:vercel`로 정리 후 빌드 확인
- 배포 URL에서 Kakao 장소 검색, 추천, 지도, 상세 페이지 흐름 재검증

### 2026-05-09~10 — 초기 FastAPI 연동 완료 + E2E 검증 ✅

#### 작업 내용

- `src/lib/api.ts` 신규: FastAPI 클라이언트 (VITE_API_URL, fetchRecommend, fetchReport, resultCache)
- `src/lib/mock-data.ts` 수정: ApiRecommendItem → Area 변환 함수 `toArea()` 추가, `_raw/_req` 필드 추가
- `src/routes/recommend.tsx` 재작성: 실 API 기반 AI 추천 받기 버튼, 가중치 preset 4종(균형/가성비/통근/안전), mock 폴백
- `src/routes/area.$id.tsx` 재작성: resultCache 상세 로드, Gemini AI 리포트 비동기 렌더링, GRU 예측 차트(Recharts)
- `.env.local` 신규: `VITE_API_URL=http://localhost:8000`

#### E2E 검증 결과 (2026-05-10, 여의도 기준)

- 추천 결과: 10개 정상 (인천 동구 23만/33분, 서울 동작구 50만/11분, 경기 광명시 53만/15분 등)
- 동작구 상세 페이지: GRU 차트 정상, Gemini AI 리포트 완전 로드
- 실거래 데이터: 부담률 19.1%, 6개월 후 예측 23.0%, HUG 0.60%

#### 다음 단계

- git commit & push (이 문서 포함)
- EC2 배포 시 `.env.local` → `VITE_API_URL=https://<EC2-IP>:8000` 으로 교체 (빌드 시점 반영)

### 2026-05-10 — 웹 UI 카카오맵/장소 검색 전환 ✅

#### 작업 내용

- `src/lib/kakao-map.ts` 신규: 카카오맵 JavaScript SDK 동적 로드, `services.Places.keywordSearch()` 기반 장소 검색, 로드 실패 재시도 처리
- `src/components/map-view.tsx` 신규: Leaflet/OpenStreetMap 대신 카카오맵 `CustomOverlay`로 직장 위치와 추천 동네 순위 마커 표시
- `src/routes/recommend.tsx` 수정: 직장 위치 select를 카카오 장소 검색 입력으로 교체, 선택 장소의 `lat/lng/name`을 추천 API 요청에 반영
- 기존 직장 프리셋은 빠른 선택 버튼으로 유지
- `Area` 타입과 API 변환에 `lat/lng` 반영, mock 폴백 데이터에도 좌표 추가

#### 검증 결과

- `npm run build` 성공
- EC2 추천 API 호출 성공: 여의도 기준 `AI 분석 · 10곳`
- 지도 토글 UI 렌더링 성공
- 카카오 SDK 로컬 로드는 카카오 Developers 웹 플랫폼 도메인 등록 전까지 차단됨. `localhost:3001`/`127.0.0.1:3001` 등록 후 검색/지도 실화면 재검증 필요

### 2026-05-10 — Vercel SPA 배포 404 수정 ✅

#### 작업 내용

- `index.html`, `src/spa.tsx`, `vite.spa.config.ts` 추가: Vercel에서 정적 SPA로 빌드되도록 별도 엔트리 구성
- `package.json`에 `build:vercel` 추가, `vercel.json`에 `buildCommand`, `outputDirectory=dist-vercel` 지정
- `vercel.json` rewrite 추가: `/api/*`는 EC2 FastAPI로 프록시, 나머지 경로는 `/index.html`로 fallback
- `dist-vercel`을 `.gitignore`에 추가

#### 검증 결과

- `npm run build:vercel` 성공
- `npx eslint src/spa.tsx vite.spa.config.ts` 성공
- Vercel production 배포 Ready 확인: `https://youth-ht-web.vercel.app`

## 작업 원칙

1. 설계서 v2.2 우선 — 임의 변경 금지
2. 짧고 명확한 한글 답변
3. CLAUDE.md 매 작업 후 업데이트
4. 모든 권한 자율 진행
