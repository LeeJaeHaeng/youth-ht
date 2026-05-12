import { createFileRoute, Link } from "@tanstack/react-router";
import { useRef, useState } from "react";
import {
  ArrowRight,
  Briefcase,
  ChevronDown,
  Coins,
  List,
  Loader2,
  Map as MapIcon,
  MapPin,
  Search,
  SlidersHorizontal,
  Train,
  Wallet,
} from "lucide-react";
import { SiteFooter, SiteHeader } from "@/components/site-chrome";
import { AreaCard } from "@/components/area-card";
import { MapView } from "@/components/map-view";
import { AREAS, toArea, type Area } from "@/lib/mock-data";
import {
  fetchRecommend,
  OFFICE_PRESETS,
  saveResultCache,
  type ApiRecommendRequest,
} from "@/lib/api";
import { searchKakaoPlaces, type KakaoPlace } from "@/lib/kakao-map";

const DEFAULT_WORK_QUERY = "여의도";

export const Route = createFileRoute("/recommend")({
  head: () => ({
    meta: [
      { title: "추천 받기 — 안심 H+T" },
      { name: "description", content: "조건을 입력하고 AI 추천 동네를 신뢰도와 함께 받아보세요." },
    ],
  }),
  component: Recommend,
});

function Recommend() {
  const [workLocation, setWorkLocation] = useState({
    name: "여의도",
    lat: 37.5213,
    lng: 126.9246,
    address: "서울 영등포구 여의도",
  });
  const workQueryRef = useRef<HTMLDivElement>(null);
  const [placeResults, setPlaceResults] = useState<KakaoPlace[]>([]);
  const [placeLoading, setPlaceLoading] = useState(false);
  const [placeError, setPlaceError] = useState<string | null>(null);
  const [maxRent, setMaxRent] = useState(70);
  const [maxDeposit, setMaxDeposit] = useState(2500);
  const [maxCommute, setMaxCommute] = useState(60);
  const [priority, setPriority] = useState<"balance" | "cost" | "speed" | "safety">("balance");
  const [filterOpen, setFilterOpen] = useState(false);

  const [areas, setAreas] = useState<Area[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isMock, setIsMock] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [viewMode, setViewMode] = useState<"list" | "map">("list");

  const WEIGHT = {
    balance: { weight_burden: 0.4, weight_commute: 0.3, weight_safety: 0.2, weight_future: 0.1 },
    cost: { weight_burden: 0.5, weight_commute: 0.2, weight_safety: 0.2, weight_future: 0.1 },
    speed: { weight_burden: 0.2, weight_commute: 0.55, weight_safety: 0.15, weight_future: 0.1 },
    safety: { weight_burden: 0.2, weight_commute: 0.2, weight_safety: 0.5, weight_future: 0.1 },
  };

  async function handlePlaceSearch() {
    const query = (workQueryRef.current?.textContent ?? DEFAULT_WORK_QUERY).trim();
    if (!query) return;

    setPlaceLoading(true);
    setPlaceError(null);
    try {
      const results = await searchKakaoPlaces(query);
      setPlaceResults(results);
      if (results.length === 0) {
        setPlaceError("검색 결과가 없습니다. 건물명이나 역명으로 다시 입력해주세요.");
      }
    } catch (e) {
      setPlaceResults([]);
      setPlaceError(e instanceof Error ? e.message : "장소 검색 실패");
    } finally {
      setPlaceLoading(false);
    }
  }

  function selectPlace(place: KakaoPlace) {
    setWorkLocation({
      name: place.name,
      lat: place.lat,
      lng: place.lng,
      address: place.address,
    });
    if (workQueryRef.current) workQueryRef.current.textContent = place.name;
    setPlaceResults([]);
    setPlaceError(null);
  }

  function selectPreset(name: string) {
    const coords = OFFICE_PRESETS[name];
    if (!coords) return;
    setWorkLocation({ name, lat: coords.lat, lng: coords.lng, address: "빠른 선택 위치" });
    if (workQueryRef.current) workQueryRef.current.textContent = name;
    setPlaceResults([]);
    setPlaceError(null);
  }

  async function handleSearch() {
    setLoading(true);
    setError(null);
    const req: ApiRecommendRequest = {
      age: 27,
      work_lat: workLocation.lat,
      work_lng: workLocation.lng,
      work_name: workLocation.name,
      budget_won: maxRent * 10_000,
      commute_limit_min: maxCommute,
      top_n: 10,
      ...WEIGHT[priority],
    };

    try {
      const res = await fetchRecommend(req);
      saveResultCache(res.items, req);
      const converted = res.items.map((it) => toArea(it, req));
      setAreas(converted);
      setIsMock(false);
    } catch (e) {
      // API 실패 시 mock 폴백
      const filtered = AREAS.filter(
        (a) => a.rentNow <= maxRent && a.deposit <= maxDeposit && a.commuteMin <= maxCommute,
      );
      setAreas(filtered);
      setIsMock(true);
      setError(e instanceof Error ? e.message : "API 연결 실패");
    } finally {
      setLoading(false);
      setHasSearched(true);
      setFilterOpen(false);
    }
  }

  return (
    <div className="min-h-screen">
      <SiteHeader />
      <section className="border-b border-border/60 bg-card/40">
        <div className="mx-auto max-w-7xl px-4 py-8 md:px-6 md:py-12">
          <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
            Step 1 · 조건
          </div>
          <h1 className="mt-2 font-display text-3xl font-semibold tracking-tight md:text-5xl">
            내 동네 찾기
          </h1>
          <p className="mt-3 max-w-2xl text-sm text-muted-foreground md:text-base">
            조건을 설정하고 AI 추천 버튼을 누르면 전국 데이터에서 최적 동네를 찾아드려요.
          </p>
        </div>
      </section>

      <section className="mx-auto grid max-w-7xl gap-6 px-4 py-8 md:px-6 md:py-12 lg:grid-cols-12 lg:gap-8">
        {/* Mobile filter toggle */}
        <button
          type="button"
          onClick={() => setFilterOpen((v) => !v)}
          className="flex items-center justify-between rounded-2xl border border-border bg-card px-4 py-3 text-left shadow-soft lg:hidden"
          aria-expanded={filterOpen}
        >
          <span className="flex items-center gap-2 text-sm font-medium">
            <SlidersHorizontal className="h-4 w-4" />
            조건 설정
          </span>
          <ChevronDown
            className={`h-4 w-4 transition-transform ${filterOpen ? "rotate-180" : ""}`}
          />
        </button>

        <aside
          className={`lg:col-span-4 xl:col-span-3 ${filterOpen ? "block" : "hidden"} lg:block`}
        >
          <div className="space-y-5 rounded-3xl border border-border bg-card p-5 shadow-soft md:space-y-6 md:p-6 lg:sticky lg:top-20">
            <Field icon={<Briefcase className="h-3.5 w-3.5" />} label="직장 위치">
              <div className="flex gap-2">
                <div
                  ref={workQueryRef}
                  contentEditable
                  role="textbox"
                  aria-label="직장 위치 검색어"
                  onKeyDown={(e) => {
                    if (e.key !== "Enter") return;
                    e.preventDefault();
                    void handlePlaceSearch();
                  }}
                  className="min-h-10 min-w-0 flex-1 overflow-hidden rounded-xl border border-border bg-background px-3 py-2.5 text-sm leading-tight focus:outline-none focus:ring-2 focus:ring-ring"
                  suppressContentEditableWarning
                >
                  {DEFAULT_WORK_QUERY}
                </div>
                <button
                  type="button"
                  onClick={() => void handlePlaceSearch()}
                  disabled={placeLoading}
                  className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-foreground text-background transition-opacity disabled:opacity-60"
                  aria-label="직장 위치 검색"
                >
                  {placeLoading ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Search className="h-4 w-4" />
                  )}
                </button>
              </div>

              <div className="mt-2 rounded-xl border border-border bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
                <div className="flex items-start gap-2">
                  <MapPin className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                  <div className="min-w-0">
                    <div className="truncate font-medium text-foreground">{workLocation.name}</div>
                    <div className="truncate">{workLocation.address}</div>
                  </div>
                </div>
              </div>

              {placeError && <div className="mt-2 text-xs text-warn">{placeError}</div>}

              {placeResults.length > 0 && (
                <div className="mt-2 max-h-48 overflow-auto rounded-xl border border-border bg-background shadow-soft">
                  {placeResults.map((place) => (
                    <button
                      key={place.id}
                      type="button"
                      onClick={() => selectPlace(place)}
                      className="block w-full border-b border-border/60 px-3 py-2 text-left text-xs transition-colors last:border-b-0 hover:bg-muted"
                    >
                      <div className="truncate font-medium text-foreground">{place.name}</div>
                      <div className="truncate text-muted-foreground">{place.address}</div>
                    </button>
                  ))}
                </div>
              )}

              <div className="mt-2 flex flex-wrap gap-1.5">
                {Object.keys(OFFICE_PRESETS)
                  .slice(0, 6)
                  .map((name) => (
                    <button
                      key={name}
                      type="button"
                      onClick={() => selectPreset(name)}
                      className="rounded-full border border-border px-2.5 py-1 text-[11px] text-muted-foreground transition-colors hover:border-foreground/50 hover:text-foreground"
                    >
                      {name}
                    </button>
                  ))}
              </div>
            </Field>

            <SliderField
              icon={<Wallet className="h-3.5 w-3.5" />}
              label="월세 상한"
              value={maxRent}
              onChange={setMaxRent}
              min={30}
              max={150}
              suffix="만원"
            />
            <SliderField
              icon={<Coins className="h-3.5 w-3.5" />}
              label="보증금 상한"
              value={maxDeposit}
              onChange={setMaxDeposit}
              min={500}
              max={5000}
              step={100}
              suffix="만원"
            />
            <SliderField
              icon={<Train className="h-3.5 w-3.5" />}
              label="통근 한계"
              value={maxCommute}
              onChange={setMaxCommute}
              min={15}
              max={90}
              suffix="분"
            />

            <Field label="우선순위">
              <div className="grid grid-cols-2 gap-2">
                {(
                  [
                    { k: "balance", l: "균형" },
                    { k: "cost", l: "가성비" },
                    { k: "speed", l: "통근" },
                    { k: "safety", l: "안전" },
                  ] as const
                ).map((p) => (
                  <button
                    key={p.k}
                    onClick={() => setPriority(p.k)}
                    className={`rounded-xl border px-3 py-2 text-sm transition-all ${
                      priority === p.k
                        ? "border-foreground bg-foreground text-background"
                        : "border-border text-muted-foreground hover:border-foreground/50 hover:text-foreground"
                    }`}
                  >
                    {p.l}
                  </button>
                ))}
              </div>
            </Field>

            <button
              type="button"
              onClick={handleSearch}
              disabled={loading}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-foreground px-4 py-3.5 text-sm font-semibold text-background transition-opacity disabled:opacity-60"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" /> AI 분석 중…
                </>
              ) : (
                "AI 추천 받기"
              )}
            </button>
          </div>
        </aside>

        <div className="lg:col-span-8 xl:col-span-9">
          <div className="mb-5 flex flex-col gap-4 md:mb-6 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                Step 2 · 결과
              </div>
              <h2 className="mt-2 font-display text-xl font-semibold tracking-tight md:text-2xl">
                {workLocation.name} 직장 기준 추천
              </h2>
            </div>
            <div className="flex items-center justify-between gap-3 sm:justify-end">
              {hasSearched && (
                <div className="font-mono text-xs text-muted-foreground">
                  {isMock ? "데모 데이터" : `AI 분석 · ${areas.length}곳`} · {priority}
                </div>
              )}
              {hasSearched && areas.length > 0 && (
                <div className="grid grid-cols-2 rounded-xl border border-border bg-card p-1 shadow-soft">
                  <button
                    type="button"
                    onClick={() => setViewMode("list")}
                    aria-pressed={viewMode === "list"}
                    className={`inline-flex h-9 items-center justify-center gap-1.5 rounded-lg px-3 text-xs font-medium transition-colors ${
                      viewMode === "list"
                        ? "bg-foreground text-background"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    <List className="h-3.5 w-3.5" />
                    목록
                  </button>
                  <button
                    type="button"
                    onClick={() => setViewMode("map")}
                    aria-pressed={viewMode === "map"}
                    className={`inline-flex h-9 items-center justify-center gap-1.5 rounded-lg px-3 text-xs font-medium transition-colors ${
                      viewMode === "map"
                        ? "bg-foreground text-background"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    <MapIcon className="h-3.5 w-3.5" />
                    지도
                  </button>
                </div>
              )}
            </div>
          </div>

          {hasSearched &&
            areas.length > 0 &&
            viewMode === "map" &&
            areas.every((a) => !a.lat || !a.lng) && (
              <div className="mb-4 rounded-2xl border border-warn/40 bg-warn/10 px-4 py-3 text-sm text-warn">
                현재 추천 결과에 좌표가 없어 지도 마커를 표시할 수 없습니다.
              </div>
            )}

          {hasSearched && areas.length > 0 && viewMode === "map" && (
            <div className="mb-4 rounded-2xl border border-border bg-card/70 px-4 py-3 text-xs text-muted-foreground">
              ★ {workLocation.name} 직장 위치와 추천 동네 순위 마커를 함께 표시합니다. 마커를 누르면
              핵심 지표와 상세 분석 링크를 볼 수 있습니다.
            </div>
          )}

          {(() => {
            const workCoords = { lat: workLocation.lat, lng: workLocation.lng };
            return (
              <>
                {error && (
                  <div className="mb-4 rounded-2xl border border-warn/40 bg-warn/10 px-4 py-3 text-sm text-warn">
                    백엔드 연결 실패 — 데모 데이터로 표시합니다. ({error})
                  </div>
                )}

                {!hasSearched ? (
                  <div className="rounded-3xl border border-dashed border-border bg-card p-8 text-center md:p-12">
                    <p className="text-sm text-muted-foreground">
                      조건을 설정하고 <strong>AI 추천 받기</strong> 버튼을 눌러주세요.
                    </p>
                  </div>
                ) : loading ? (
                  <div className="flex items-center justify-center py-20">
                    <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                  </div>
                ) : areas.length === 0 ? (
                  <div className="rounded-3xl border border-dashed border-border bg-card p-8 text-center md:p-12">
                    <p className="text-sm text-muted-foreground">
                      조건에 맞는 동네가 없어요. 슬라이더를 조금 풀어주세요.
                    </p>
                  </div>
                ) : viewMode === "map" ? (
                  <MapView
                    areas={areas}
                    workLat={workCoords.lat}
                    workLng={workCoords.lng}
                    workName={workLocation.name}
                  />
                ) : (
                  <div className="grid gap-4 sm:grid-cols-2 md:gap-5">
                    {areas.map((a, i) => (
                      <AreaCard key={a.id} area={a} rank={i + 1} />
                    ))}
                  </div>
                )}
              </>
            );
          })()}

          <Link
            to="/about"
            className="mt-8 inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground md:mt-10"
          >
            점수가 어떻게 계산되는지 보기 <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </section>
      <SiteFooter />
    </div>
  );
}

function Field({
  icon,
  label,
  children,
}: {
  icon?: React.ReactNode;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <div className="mb-2 flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
        {icon} {label}
      </div>
      {children}
    </div>
  );
}

function SliderField({
  icon,
  label,
  value,
  onChange,
  min,
  max,
  step = 1,
  suffix,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
  onChange: (v: number) => void;
  min: number;
  max: number;
  step?: number;
  suffix: string;
}) {
  return (
    <Field icon={icon} label={label}>
      <div className="flex items-baseline justify-between">
        <span className="font-display text-2xl font-semibold">
          {value.toLocaleString()}
          <span className="ml-1 text-xs font-normal text-muted-foreground">{suffix}</span>
        </span>
        <span className="font-mono text-[10px] text-muted-foreground">
          {min}–{max}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="mt-2 w-full accent-foreground"
      />
    </Field>
  );
}
