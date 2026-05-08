# 집에서 처리할 사용자 액션 — API 명세 3건 확보

> Claude Code가 자동 처리 시도했으나 **인증 + 첨부 파일 접근 필요**로 자동 처리 불가능. 아래 절차대로 정보만 모아 `youth-ht/.env` 또는 `youth-ht/docs/api_specs.md`에 기록하면, 다음 세션에서 검증 재시도하고 1주차 GRU 입력으로 사용 가능.

---

## A. 행정안전부 주민등록인구 OpenAPI 엔드포인트

### A-1. 절차

1. <https://www.data.go.kr> 로그인
2. 마이페이지 → **활용신청 현황** 진입
3. "행정안전부_통계연보_지역별 주민등록인구" 신청 건의 **상세보기** 클릭
4. 데이터셋 페이지: <https://www.data.go.kr/data/15107303/openapi.do>
5. 페이지 하단의 **"OpenAPI 명세서"** 또는 **"엔드포인트(End Point)"** 항목 확인
End Point	https://apis.data.go.kr/1741000/RegistrationPopulationByRegion

### A-2. 메모할 정보

```text
End Point:        ___________________________________________
요청 메서드:      GET / POST
인증 변수명:      serviceKey (보통)
페이징 파라미터:  pageNo, numOfRows
필수 파라미터 1:  ___________ (예: srchStdDtYy=2024)
필수 파라미터 2:  ___________
필수 파라미터 3:  ___________
응답 형식:        JSON / XML
주요 응답 필드:   행정구역코드, 시도명, 시군구명, 총인구, 세대수, 남자, 여자, ...
```

### A-3. 검증 방법 (메모 후)

`.env` 의 `POPULATION_API_URL` 슬롯에 메모한 URL 한 줄 채우고 `python scripts/verify/03_verify_population.py` 재실행.

---

## B. 한국부동산원 R-ONE 미분양 STATBL_ID

### B-1. 절차

1. <https://www.reb.or.kr/r-one/portal/openapi/openApiIntroPage.do> 회원가입 + 로그인
2. **마이페이지 → 인증키 발급** (이미 있으면 스킵)
3. **OpenAPI 신청 → 미분양·분양 통계** 신청 (즉시 승인)
4. 데이터셋 페이지: <https://www.data.go.kr/data/15134761/openapi.do> 의 **참고문서** 항목에서 `기술문서_부동산통계 Open API 서비스_240905.docx` 다운로드
5. 문서에서 다음을 찾아 메모:

!! 자동 발굴 완료: R-ONE SttsApiTbl.do API 쿼리로 STATBL_ID=T237973129847263 (주택도시보증공사 보증사고현황) 확인됨. .env REB_UNSOLD_STATBL_ID=T237973129847263 업데이트됨.

### B-2. 메모할 정보

```text
베이스 URL:       https://www.reb.or.kr/r-one/openapi/SttsApiTblData.do  (확인됨)
인증 파라미터:    KEY=<기존 키>
필수 파라미터:    Type=json, pIndex, pSize, STATBL_ID, DTACYCLE_CD, WRTTIME_IDTFR_ID

미분양주택현황 STATBL_ID:        ___________________
미분양주택현황 DTACYCLE_CD:      ___________________ (MM=월, YY=연)
미분양주택현황 WRTTIME_IDTFR_ID: ___________________ (예: 202503)

(참고로 지가변동률은 STATBL_ID=A_2024_00900, DTACYCLE_CD=YY 사용)
```

### B-3. 검증 방법

`.env` 의 `REB_UNSOLD_STATBL_ID` (필요 시 `REB_UNSOLD_DTACYCLE_CD`, `REB_UNSOLD_WRTTIME_START`도) 채운 뒤 `python scripts/verify/05_verify_reb.py` 재실행.

---
!!확인 문서 경로: C:\Users\leejh\OneDrive\바탕 화면\2026년 국토교통 데이터 활용 경진대회\기술문서_부동산통계 Open API 서비스_240905.docx
## C. 국토교통 통계누리 OpenAPI 엔드포인트

### C-1. 절차

1. <https://stat.molit.go.kr/portal/openapi/main.do> 로그인
2. **인증키 신청** (이미 발급됨 — `1fca2c4ee1c74ccc8eba280fb7fc2499`)
3. **OPEN API 신청 → 대중교통 / 자동차등록 등 활용 통계표 선택**
4. 관리자 승인 후 마이페이지에서 **API 호출 URL** 확인
5. 문의: 044-201-4834

### C-2. 메모할 정보

```text
베이스 URL:       _____________________________________________________
인증 변수명:      KEY (또는 apiKey, serviceKey 중 하나)
응답 형식:        JSON
필수 파라미터:    pIndex, pSize, STATBL_ID(또는 statTblId)
시계열 제한:      최대 5년

활용할 통계표 1: ____________ (예: 대중교통이용현황 — STATBL_ID = ?)
활용할 통계표 2: ____________
```

### C-3. 검증 방법

`.env` 의 `MOLIT_STAT_BASE_URL`, `MOLIT_STAT_AUTH_PARAM`, `MOLIT_STAT_TBL_IDS` 채우고 `python scripts/verify/06_verify_molit_stat.py` 재실행.

---

## 메모 완료 후

위 3건 정보를 `youth-ht/docs/api_specs.md`(직접 작성)에 기록한 뒤, Claude Code 세션에서 다음 한 줄로 재검증 요청:

> "api_specs.md 기반으로 03·05·06 검증 스크립트 재작성·재실행해줘"

---

!! 통계누리 => 교통카드 빅데이터 통합정보 시스템으로 변경 데이터 명: 15분단위OD 
API 요청 URL
https://stcis.go.kr/openapi/quarterod.json?apikey=(인증받은 API키)&opratDate=(운행일자)&stgEmdCd=(읍면동코드)&arrEmdCd=(읍면동코드)
요청 파라미터
파라미터	필수/선택	설명	유효값
quarterod.json	필수	요청 서비스명	-
apikey	필수	발급받은 api key	-
opratDate	필수	운행일자	조회 대상 일자 8자리
stgEmdCd	필수	출발지 읍/면/동 코드	읍/면/동 코드 10자리
arrEmdCd	필수	도착지 읍/면/동 코드	읍/면/동 코드 10자리
응답결과
항목명	타입	설명
count	숫자	응답결과 건수
status	문자	상태값: OK(성공), NOT_FOUND(결과없음)
result		
opratDate	문자	응답결과 운행일자
stgSdCd	문자	응답결과 출발지 시/도 코드
stgSdNm	문자	응답결과 출발지 시/도 명
stgSggCd	문자	응답결과 출발지 시/군/구 코드
stgSggNm	문자	응답결과 출발지 시/군/구 명
stgEmdCd	문자	응답결과 출발지 읍/면/동 코드
stgEmdNm	문자	응답결과 출발지 읍/면/동 명
arrSdCd	문자	응답결과 도착지 시/도 코드
arrSdNm	문자	응답결과 도착지 시/도 명
arrSggCd	문자	응답결과 도착지 시/군/구 코드
arrSggNm	문자	응답결과 도착지 시/군/구 명
arrEmdCd	문자	응답결과 도착지 읍/면/동 코드
arrEmdNm	문자	응답결과 도착지 읍/면/동 명
tzon	문자	응답결과 시간대
quater	문자	응답결과 15분단위
useStf	문자	응답결과 이용인원수
useTm	문자	응답결과 평균 통행시간
오류 응답결과
항목명	문자	에러정보 Root
error	문자	에러정보 Root
level	숫자	에러레벨
code	문자	에러코드
text	문자	에러메세지
status	문자	처리 결과의 상태 표시, 유효값 : OK(성공), NOT_FOUND(결과없음), ERROR(에러)
오류메세지
코드	레벨	메세지	비고
PARAM_REQUIRED	1	필수 파라미터인 <%S1>가 없어서 요청을 처리할수 없습니다.	%S1 : 파라미터 이름
INVALID_TYPE	1	<%S1> 파라미터 타입이 유효하지 않습니다.
유효한 파라미터 타입 : <%S2>
입력한 파라미터 값 : <%S3>	%S1 : 파라미터 이름
%S2 : 유효한 파라미터 값의 유형
%S3 : 입력한 파라미터 값
INVALID_RANGE	1	<%S1> 파라미터의 값이 유효한 범위를 넘었습니다.
유효한 파라미터 타입 : <%S2>
입력한 파라미터 값 : <%S3>	%S1 : 파라미터 이름
%S2 : 유효한 파라미터 값의 범위
%S3 : 입력한 파라미터 값
INVALID_KEY	2	등록되지 않은 인증키입니다.	

## G. DeepSeek-V3 API 잔액 충전 (가점 10점 — AI 활용 핵심)

DeepSeek API 키 자체는 ✅ 정상 (HTTP 200 인증). 단 잔액 0이라 호출 시 `HTTP 402 Insufficient Balance`.

### G-1. 절차

1. <https://platform.deepseek.com> 로그인 (`dlwogod2479@gmail.com` 계정)
2. 좌측 **Top up** 또는 **Billing** 메뉴
3. **$5 ~ $10 충전** (DeepSeek-V3 input $0.14/1M tokens, output $0.28/1M → 1만 호출 약 6,000원)
4. 충전 완료되면 `python scripts/verify/10_verify_deepseek.py` 재실행 — 즉시 통과

### G-2. 비용 가이드 (설계서 §1 비용)

| 충전액 | 예상 호출 수 | 6.5개월 사용 |
| --- | --- | --- |
| $5 (≈ 7,000원) | 약 1.1만 호출 | 시연 + 베타 |
| $10 (≈ 14,000원) | 약 2.3만 호출 | 본 서비스 운영 |

대회 시연 + GitHub 공개 코드에서 호출 보여주려면 최소 $5 권장.

!! GEMINI_API_KEY로 변경 key값 env파일에 업데이트 완료 

## D. 전국 시군구 코드 250개 CSV (선택 — 본 수집 범위 확장용)

현재 수도권 + 광역시 113개 시군구는 코드에 박혀있어 즉시 사용 가능. 전국 250개 풀 사용을 원하면:

1. <https://www.data.go.kr/data/15077871/openapi.do> 행정안전부_행정표준코드_법정동코드 활용신청
2. 또는 <https://www.code.go.kr/stdcodesrch/codeAllDownloadL.do> 에서 CSV 다운로드
3. 5자리 unique 추출 → `youth-ht/data/raw/sigungu_codes.csv` 로 저장
4. CSV 헤더: `code,name` (예: `11680,서울 강남구`)

수집 시 `python scripts/collect/01_collect_apt_rent.py --full --codes-csv data/raw/sigungu_codes.csv` 형태로 옵션 추가.

!! 행정안전부_행정표준코드_법정동코드 추가 완료 아래 KEY ENV파일에 업데이트 필요
데이터포맷	JSON+XML
End Point	https://apis.data.go.kr/1741000/StanReginCd
일반 인증키
(Encoding)	
HJOdD3Trr61EsxDzydEROTFwvnXDRFbJ0GKKTYsjqFedi0vq%2Fxe0ZuApiCcV7BrVr5ljmTY0vTMszBmMYrzWiQ%3D%3D
일반 인증키
(Decoding)	
HJOdD3Trr61EsxDzydEROTFwvnXDRFbJ0GKKTYsjqFedi0vq/xe0ZuApiCcV7BrVr5ljmTY0vTMszBmMYrzWiQ==

## E. SGIS 1km 격자 Shapefile (격자 단위 본 학습 진입 시 필수)

1. <https://sgis.kostat.go.kr/> 회원가입·로그인
2. "통계지리정보서비스 → 통계지도 → 격자형 1km 경계" 다운로드 신청
3. ZIP 풀어서 `youth-ht/data/raw/grid_1km/grid_1km.shp` (+ .dbf, .prj 등) 배치
4. `python scripts/transform/21_grid_centroid.py` 실행

!!완료

## F. 직장 클러스터 좌표 검수 (자동 부여 후 미스매칭 3건)

`docs/work_clusters.csv` 의 다음 행은 카카오 키워드 검색이 잘못된 곳을 1순위로 반환:

- `cluster_id 85` 부산 연산 (현재: 36.21, 127.20 — 실제 부산 연산은 35.18, 129.08)
- `cluster_id 94` 대전 둔산 (현재: 37.57, 126.98 — 실제 대전 둔산은 36.35, 127.39)
- `cluster_id 96` 대전 정부청사 (현재: 37.43, 126.99 — 실제 대전 청사는 36.36, 127.39)

또한 카카오 검색 미적중 8건(창원·김해·청주·천안·춘천·전주·여수·제주)은 누락. 사용자가 직접 좌표 입력 또는 query를 더 구체적으로 변경 후 `11_resolve_work_clusters.py` 재실행.

---

!! 부산연산, 대전 둔산, 대전 정부청사는 위경도 수정 완료. 미적중8건 자동 탐색 후 추가

## 우선순위 가이드 (집에서 시간 부족 시)

1. **A 행안부 인구** (가장 중요 — GRU #5 입력, 즉시 작동)
2. **B R-ONE 미분양** (GRU #6 입력, 즉시 작동 — 베이스 URL 확인 완료)
3. **F 직장 클러스터 검수** (3건만 수정, 5분)
4. **E SGIS 격자** (격자 단위 본 학습 시작 전)
5. **D 전국 시군구 csv** (113개로 1주차 절반 가능, 풀 사용 시)
6. **C 통계누리** (보조 — 카카오맵이 메인이라 후순위)

A·B 해결되면 GRU 학습 8개 입력 모두 확보. C는 1주차 후반에도 충분.
