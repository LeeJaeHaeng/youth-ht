import { Link, useLocation } from "@tanstack/react-router";
import { Menu, Sparkles, X } from "lucide-react";
import { useEffect, useState } from "react";

export function SiteHeader() {
  const { pathname } = useLocation();
  const [open, setOpen] = useState(false);
  const nav = [
    { to: "/", label: "홈" },
    { to: "/recommend", label: "추천 받기" },
    { to: "/about", label: "어떻게 작동해요?" },
  ];

  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  useEffect(() => {
    document.body.style.overflow = open ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  return (
    <header className="sticky top-0 z-40 border-b border-border/60 bg-background/85 backdrop-blur-md">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4 md:h-16 md:px-6">
        <Link to="/" className="flex items-center gap-2">
          <div className="grid h-8 w-8 place-items-center rounded-xl bg-gradient-hero text-primary-foreground shadow-soft md:h-9 md:w-9">
            <Sparkles className="h-3.5 w-3.5 md:h-4 md:w-4" />
          </div>
          <div className="leading-tight">
            <div className="font-display text-sm font-semibold tracking-tight md:text-base">
              안심 H+T
            </div>
            <div className="hidden text-[10px] uppercase tracking-[0.18em] text-muted-foreground sm:block">
              Housing · Transport AI
            </div>
          </div>
        </Link>
        <nav className="hidden items-center gap-1 md:flex">
          {nav.map((n) => {
            const active = pathname === n.to;
            return (
              <Link
                key={n.to}
                to={n.to}
                className={`rounded-full px-4 py-2 text-sm transition-colors ${
                  active
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {n.label}
              </Link>
            );
          })}
        </nav>
        <div className="flex items-center gap-2">
          <Link
            to="/recommend"
            className="hidden rounded-full bg-foreground px-4 py-2 text-sm font-medium text-background transition-opacity hover:opacity-90 md:inline-flex"
          >
            시작하기
          </Link>
          <button
            type="button"
            aria-label={open ? "메뉴 닫기" : "메뉴 열기"}
            aria-expanded={open}
            onClick={() => setOpen((v) => !v)}
            className="grid h-10 w-10 place-items-center rounded-xl border border-border bg-card text-foreground md:hidden"
          >
            {open ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
          </button>
        </div>
      </div>

      {open && (
        <div className="border-t border-border/60 bg-background md:hidden">
          <nav className="mx-auto flex max-w-7xl flex-col px-4 py-3">
            {nav.map((n) => {
              const active = pathname === n.to;
              return (
                <Link
                  key={n.to}
                  to={n.to}
                  className={`rounded-xl px-4 py-3 text-sm transition-colors ${
                    active ? "bg-secondary text-foreground font-medium" : "text-muted-foreground"
                  }`}
                >
                  {n.label}
                </Link>
              );
            })}
            <Link
              to="/recommend"
              className="mt-2 inline-flex items-center justify-center rounded-xl bg-foreground px-4 py-3 text-sm font-medium text-background"
            >
              시작하기
            </Link>
          </nav>
        </div>
      )}
    </header>
  );
}

export function SiteFooter() {
  return (
    <footer className="border-t border-border/60 bg-background">
      <div className="mx-auto flex max-w-7xl flex-col gap-2 px-4 py-8 text-xs text-muted-foreground md:flex-row md:items-center md:justify-between md:px-6 md:py-10">
        <div>© 2026 안심 H+T · 청년 주거+교통 의사결정 AI</div>
        <div className="font-mono text-[10px] md:text-xs">
          v2.2 · LightGBM + XGBoost + GRU + Gemini 2.5 Flash
        </div>
      </div>
    </footer>
  );
}
