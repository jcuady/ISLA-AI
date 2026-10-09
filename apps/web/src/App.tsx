import { useCallback, useEffect, useState } from "react";
import { PanelLeft, Wifi, WifiOff } from "lucide-react";
import { api, type AirgapResult, type Health } from "./lib/api";
import { AppSidebar, type ViewId } from "./components/app-sidebar";
import { Button } from "./components/ui/button";
import { StatusBadge } from "./components/ui/status-badge";
import { Sheet, SheetContent, SheetTrigger, SheetTitle } from "./components/ui/sheet";
import Copilot from "./screens/Copilot";
import EgressGuard from "./screens/EgressGuard";
import Ledger from "./screens/Ledger";

const TITLES: Record<ViewId, { title: string; sub: string }> = {
  copilot: { title: "DPA Copilot", sub: "Citation-first answers from Philippine privacy law" },
  egress: { title: "Egress Guard", sub: "Detect and redact before data leaves" },
  ledger: { title: "Audit Ledger", sub: "Cryptographic proof that never stores customer text" },
};

const VIEWS: ViewId[] = ["copilot", "egress", "ledger"];

/**
 * The active control lives in the URL, so an officer can send a colleague a
 * link to exactly the screen they are looking at, and Back works. An
 * unrecognised value falls back to the Copilot rather than rendering nothing.
 */
function viewFromLocation(): ViewId {
  const v = new URLSearchParams(window.location.search).get("view");
  return VIEWS.includes(v as ViewId) ? (v as ViewId) : "copilot";
}

export default function App() {
  const [view, setView] = useState<ViewId>(viewFromLocation);
  const [gap, setGap] = useState<AirgapResult | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [gapError, setGapError] = useState<string | null>(null);
  const [chatKey, setChatKey] = useState(0);
  const [question, setQuestion] = useState<{ q: string; nonce: number } | null>(null);
  const [mobileOpen, setMobileOpen] = useState(false);

  const refresh = useCallback(async () => {
    try {
      setGap(await api.airgap());
      setGapError(null);
    } catch (e) {
      setGapError(e instanceof Error ? e.message : String(e));
    }
    try {
      setHealth(await api.health());
    } catch {
      /* health is advisory only */
    }
  }, []);

  useEffect(() => {
    void refresh();
    // Re-probe on a timer so the chip reflects reality if a cable is pulled.
    const id = setInterval(() => void refresh(), 20000);
    return () => clearInterval(id);
  }, [refresh]);

  // Back/forward must move between controls, not just restore the page.
  useEffect(() => {
    const onPop = () => setView(viewFromLocation());
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  /** `copilot` is the canonical default, so it carries no query string. */
  const syncUrl = useCallback((next: ViewId) => {
    const url = new URL(window.location.href);
    if (next === "copilot") url.searchParams.delete("view");
    else url.searchParams.set("view", next);
    window.history.pushState(null, "", url.toString());
  }, []);

  const navigate = useCallback(
    (next: ViewId) => {
      setView(next);
      syncUrl(next);
      setMobileOpen(false);
    },
    [syncUrl],
  );

  const startNewChat = useCallback(() => {
    setView("copilot");
    syncUrl("copilot");
    setQuestion(null);
    setChatKey((k) => k + 1);
    setMobileOpen(false);
  }, [syncUrl]);

  const askFromSidebar = useCallback(
    (q: string) => {
      setView("copilot");
      syncUrl("copilot");
      setQuestion({ q, nonce: Date.now() });
      setMobileOpen(false);
    },
    [syncUrl],
  );

  const meta = TITLES[view];
  const airGapped = gap?.air_gapped ?? false;

  return (
    <div className="bg-abyss-field flex h-screen overflow-hidden text-white">
      {/* persistent sidebar from lg up */}
      <AppSidebar
        active={view}
        onNavigate={navigate}
        gap={gap}
        gapError={gapError}
        health={health}
        onNewChat={startNewChat}
        canNewChat={view === "copilot"}
        onStarter={askFromSidebar}
        className="hidden lg:flex"
      />

      <div className="flex min-w-0 flex-1 flex-col">
        {/* top bar */}
        <header className="flex h-14 shrink-0 items-center gap-3 border-b border-white/8 bg-abyss-900/60 px-4 backdrop-blur-sm sm:px-5">
          <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon" className="lg:hidden" aria-label="Open navigation">
                <PanelLeft className="size-4" aria-hidden="true" />
              </Button>
            </SheetTrigger>
            <SheetContent side="left" aria-describedby={undefined}>
              <SheetTitle className="sr-only">Navigation</SheetTitle>
              <AppSidebar
                active={view}
                onNavigate={navigate}
                gap={gap}
                gapError={gapError}
                health={health}
                onNewChat={startNewChat}
                canNewChat={view === "copilot"}
                onStarter={askFromSidebar}
                className="w-full border-r-0"
              />
            </SheetContent>
          </Sheet>

          <div className="min-w-0 flex-1">
            <h1 className="truncate font-display text-[15px] font-semibold tracking-tight">
              {meta.title}
            </h1>
            <p className="hidden truncate text-[11.5px] text-white/40 sm:block">{meta.sub}</p>
          </div>

          <StatusBadge
            tone={gapError ? "block" : airGapped ? "safe" : "caution"}
            label={gapError ? "Probe error" : airGapped ? "Air-gapped" : "Connected"}
            icon={
              airGapped && !gapError ? (
                <WifiOff className="size-3.5" aria-hidden="true" />
              ) : (
                <Wifi className="size-3.5" aria-hidden="true" />
              )
            }
            className="hidden sm:inline-flex"
          />

          <span className="sm:hidden">
            <StatusBadge
              size="sm"
              tone={gapError ? "block" : airGapped ? "safe" : "caution"}
              label={gapError ? "Error" : airGapped ? "Offline" : "Online"}
            />
          </span>
        </header>

        {/* view */}
        <main className="min-h-0 flex-1 overflow-hidden">
          {view === "copilot" && (
            <Copilot key={chatKey} resetKey={chatKey} externalQuestion={question} />
          )}
          {view === "egress" && (
            <div className="h-full overflow-y-auto">
              <EgressGuard />
            </div>
          )}
          {view === "ledger" && (
            <div className="h-full overflow-y-auto">
              <Ledger />
            </div>
          )}
        </main>
      </div>
    </div>
  );
}