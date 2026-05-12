# 청년 안심 H+T 웹 프론트엔드

`youth-ht` FastAPI 백엔드와 연결되는 웹 SPA입니다. 사용자가 직장 위치, 예산, 통근 한계를 입력하면 추천 API를 호출해 안심 거주지 Top 10, 부담률, 전세 위험, 통근 시간, 6개월 후 예측, AI 리포트 화면을 제공합니다.

## 현재 상태

- 프레임워크: Vite + React + TanStack Router
- 배포 방식: Vercel 정적 SPA (`npm run build:vercel`, 출력 `dist-vercel`)
- API 연결: 로컬은 `VITE_API_URL`, Vercel은 `/api/*` rewrite로 EC2 `http://3.26.146.162/api/*` 프록시
- 지도/장소 검색: Kakao Maps JavaScript SDK, `services.Places.keywordSearch`
- 프로덕션 URL: `https://youth-ht-web.vercel.app`

## 로컬 실행

```powershell
npm install
npm run dev
```

기본 개발 서버는 `http://localhost:3000`입니다. 포트가 사용 중이면 Vite가 다른 포트를 안내합니다.

## 환경 변수

`.env.local`에 설정합니다.

```text
VITE_KAKAO_JS_KEY=<카카오 JavaScript 키>
VITE_API_URL=http://3.26.146.162
```

Vercel 배포에서는 `VITE_API_URL`을 비워 두고 같은 origin의 `/api/*`를 호출하는 구성이 기준입니다.

## 빌드

```powershell
npm run build:vercel
```

일반 Vite 빌드는 다음 명령입니다.

```powershell
npm run build
```

## 핵심 파일

| 파일                           | 역할                                                   |
| ------------------------------ | ------------------------------------------------------ |
| `src/routes/recommend.tsx`     | 조건 입력, Kakao 장소 검색, 추천 API 호출, 결과 렌더링 |
| `src/routes/area.$id.tsx`      | 추천 동네 상세, GRU 예측 차트, AI 리포트               |
| `src/components/map-view.tsx`  | Kakao 지도와 추천 후보 마커                            |
| `src/components/area-card.tsx` | 추천 결과 카드와 위험/신뢰도 표시                      |
| `src/lib/api.ts`               | EC2 API 클라이언트, mock fallback, 결과 캐시           |
| `src/lib/kakao-map.ts`         | Kakao SDK 로더와 장소 검색                             |
| `vite.spa.config.ts`           | Vercel 정적 SPA 빌드 설정                              |
| `vercel.json`                  | Vercel 빌드 명령, 출력 디렉터리, API rewrite           |

## 검증 체크리스트

1. `npm run build:vercel` 성공.
2. Kakao Developers 웹 플랫폼에 로컬/배포 도메인 등록.
3. `/recommend`에서 장소 검색 결과 선택 후 추천 요청.
4. 지도 토글 시 직장 위치와 추천 후보 마커 표시.
5. 상세 페이지에서 캐시 기반 데이터와 AI 리포트 호출 확인.
