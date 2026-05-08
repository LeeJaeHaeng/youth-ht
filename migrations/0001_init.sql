-- 청년 안심 H+T 추천 시스템 — Supabase 초기 스키마
-- 설계서 v2.2 §1주차 그대로. 1주차 Day 3에 적용.

-- 1km 격자 (SGIS 기반)
CREATE TABLE IF NOT EXISTS grid_1km (
  grid_id            INT PRIMARY KEY,
  sido_code          SMALLINT,
  sigungu_code       INT,
  dong_code          INT,
  centroid_lat       NUMERIC(9,6) NOT NULL,
  centroid_lng       NUMERIC(9,6) NOT NULL,
  youth_pop          INT,
  total_pop          INT,
  station_within_1km SMALLINT,
  hug_risk_score     NUMERIC(4,3)
);

CREATE INDEX IF NOT EXISTS idx_grid_sigungu ON grid_1km(sigungu_code);

-- 실거래가 이력 (LightGBM rent 모델 학습용)
CREATE TABLE IF NOT EXISTS rent_history (
  id               BIGSERIAL PRIMARY KEY,
  grid_id          INT REFERENCES grid_1km,
  contract_date    DATE NOT NULL,
  area_m2          NUMERIC(6,2),
  deposit_won      BIGINT,
  monthly_rent_won INT,
  building_type    SMALLINT      -- 0=apt, 1=villa, 2=row, 3=detached
);

CREATE INDEX IF NOT EXISTS idx_rent_grid_date
  ON rent_history(grid_id, contract_date DESC);

-- GRU 학습용 시계열 집계
CREATE TABLE IF NOT EXISTS grid_monthly_features (
  grid_id           INT REFERENCES grid_1km,
  year_month        DATE,
  rent_mean         INT,
  rent_std          INT,
  transaction_count SMALLINT,
  base_rate         NUMERIC(5,2),
  pop_change_rate   NUMERIC(5,3),
  new_supply_units  SMALLINT,
  hug_cum_rate      NUMERIC(5,4),
  sido_youth_wage   INT,
  PRIMARY KEY (grid_id, year_month)
);

-- 직장 클러스터 (Stage 1 후보 추출 + OD 빌드 기준)
CREATE TABLE IF NOT EXISTS work_cluster (
  cluster_id       SMALLINT PRIMARY KEY,
  name             TEXT NOT NULL,
  lat              NUMERIC(9,6) NOT NULL,
  lng              NUMERIC(9,6) NOT NULL,
  youth_employment INT
);

-- 격자 → 직장 통근 OD (카카오맵 Directions 결과)
CREATE TABLE IF NOT EXISTS od_commute (
  origin_grid        INT REFERENCES grid_1km,
  dest_cluster       SMALLINT REFERENCES work_cluster,
  travel_min_peak    SMALLINT,
  travel_min_offpeak SMALLINT,
  cost_won           INT,
  PRIMARY KEY (origin_grid, dest_cluster)
);

-- DeepSeek 응답 캐시 (자연어 리포트 비용 절감)
CREATE TABLE IF NOT EXISTS llm_cache (
  cache_key  VARCHAR(64) PRIMARY KEY,
  response   JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  expires_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_llm_cache_expires ON llm_cache(expires_at);
