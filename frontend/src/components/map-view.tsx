import { useNavigate } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import type { Area } from "@/lib/mock-data";
import { loadKakaoMaps } from "@/lib/kakao-map";

interface MapViewProps {
  areas: Area[];
  workLat: number;
  workLng: number;
  workName: string;
}

const RANK_COLORS = [
  "#f59e0b",
  "#8b5cf6",
  "#10b981",
  "#3b82f6",
  "#ef4444",
  "#f97316",
  "#06b6d4",
  "#ec4899",
  "#84cc16",
  "#6366f1",
];

function escapeHtml(value: string): string {
  return value.replace(
    /[&<>"']/g,
    (char) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char] ?? char,
  );
}

export function MapView({ areas, workLat, workLng, workName }: MapViewProps) {
  const navigate = useNavigate();
  const containerRef = useRef<HTMLDivElement>(null);
  const [mapError, setMapError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const container = containerRef.current;
    if (!container) return;

    setMapError(null);
    container.innerHTML = "";

    const handleAreaClick = (event: MouseEvent) => {
      const target = event.target instanceof Element ? event.target : null;
      const link = target?.closest<HTMLAnchorElement>("[data-area-id]");
      const id = link?.dataset.areaId;
      if (!id) return;

      event.preventDefault();
      void navigate({ to: "/area/$id", params: { id } });
    };

    document.addEventListener("click", handleAreaClick);

    loadKakaoMaps()
      .then((kakao) => {
        if (cancelled || !containerRef.current) return;

        const map = new kakao.maps.Map(containerRef.current, {
          center: new kakao.maps.LatLng(workLat, workLng),
          level: 8,
        });
        map.addControl(new kakao.maps.ZoomControl(), kakao.maps.ControlPosition.RIGHT);

        const bounds = new kakao.maps.LatLngBounds();
        const workPosition = new kakao.maps.LatLng(workLat, workLng);
        bounds.extend(workPosition);

        new kakao.maps.CustomOverlay({
          map,
          position: workPosition,
          yAnchor: 1.4,
          content: `<div style="background:#1a1a1a;color:white;padding:6px 10px;border-radius:20px;font-size:11px;font-weight:700;white-space:nowrap;box-shadow:0 2px 8px rgba(0,0,0,0.25);border:2px solid white">★ ${escapeHtml(workName)}</div>`,
        });

        areas
          .filter((area) => area.lat !== undefined && area.lng !== undefined)
          .forEach((area, i) => {
            const color = RANK_COLORS[i] ?? "#6b7280";
            const position = new kakao.maps.LatLng(area.lat!, area.lng!);
            bounds.extend(position);

            new kakao.maps.CustomOverlay({
              map,
              position,
              yAnchor: 1,
              content: `
                <div style="min-width:172px;transform:translateY(-10px);font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif">
                  <a href="/area/${encodeURIComponent(area.id)}" data-area-id="${escapeHtml(area.id)}" style="display:block;text-decoration:none;color:#111827;background:white;border:1px solid rgba(17,24,39,0.12);border-radius:14px;box-shadow:0 8px 22px rgba(17,24,39,0.18);overflow:hidden">
                    <div style="display:flex;align-items:center;gap:8px;padding:8px 10px 6px">
                      <div style="background:${color};color:white;width:28px;height:28px;border-radius:999px;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:800;border:2px solid white;box-shadow:0 1px 4px rgba(0,0,0,0.25)">${i + 1}</div>
                      <div style="min-width:0">
                        <div style="font-size:13px;font-weight:800;line-height:1.2;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:120px">${escapeHtml(area.name)}</div>
                        <div style="font-size:11px;color:#6b7280;line-height:1.2;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:120px">${escapeHtml(area.district)}</div>
                      </div>
                    </div>
                    <div style="display:flex;gap:8px;border-top:1px solid #eef2f7;padding:7px 10px;font-size:11px;color:#374151">
                      <span>월세 <b>${area.rentNow}만</b></span>
                      <span>통근 <b>${area.commuteMin}분</b></span>
                    </div>
                  </a>
                </div>
              `,
            });
          });

        if (!bounds.isEmpty()) {
          map.setBounds(bounds, 56, 56, 56, 56);
        }
      })
      .catch((error) => {
        if (!cancelled)
          setMapError(error instanceof Error ? error.message : "카카오맵을 불러오지 못했습니다.");
      });

    return () => {
      cancelled = true;
      document.removeEventListener("click", handleAreaClick);
      if (container) container.innerHTML = "";
    };
  }, [areas, navigate, workLat, workLng, workName]);

  return (
    <div className="relative overflow-hidden rounded-3xl border border-border shadow-soft">
      <div ref={containerRef} className="h-[520px] bg-muted" />
      {mapError && (
        <div className="absolute inset-0 z-10 flex items-center justify-center bg-card/90 p-6 text-center text-sm text-muted-foreground">
          {mapError}
        </div>
      )}
      <div className="absolute bottom-4 left-4 z-[2] rounded-2xl border border-border bg-card/90 p-3 backdrop-blur-sm">
        <div className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
          범례
        </div>
        <div className="flex items-center gap-2 text-xs">
          <div className="h-4 w-4 rounded-sm bg-foreground" />
          <span>직장</span>
        </div>
        {areas.slice(0, 5).map((area, i) => (
          <div key={area.id} className="mt-1 flex items-center gap-2 text-xs">
            <div
              className="flex h-4 w-4 items-center justify-center rounded-full text-[9px] font-bold text-white"
              style={{ background: RANK_COLORS[i] }}
            >
              {i + 1}
            </div>
            <span className="max-w-[80px] truncate">{area.name}</span>
            <span className="text-muted-foreground">{area.rentNow}만</span>
          </div>
        ))}
      </div>
    </div>
  );
}
