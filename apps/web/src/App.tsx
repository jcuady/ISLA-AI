import { useCallback, useEffect, useState } from "react";
import { api, type AirgapResult, type Health } from "./lib/api";
import EgressGuard from "./screens/EgressGuard";
import Copilot from "./screens/Copilot";
import Ledger from "./screens/Ledger";
import KalixMark from "./components/KalixMark";

type Tab = "egress" | "copilot" | "ledger";

export default function App() {
  const [tab, setTab] = useState<Tab>("egress");
  const [gap, setGap] = useState<AirgapResult | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [gapError, setGapError] = useState<string | null>(null);

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
    // Re-probe on a timer so the badge reflects reality if a cable is pulled.
    const id = setInterval(() => void refresh(), 20000);
    return () => clearInterval(id);
  }, [refresh]);

  const airGapped = gap?.air_gapped ?? false;

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <KalixMark />
          KALIX
        </div>
        <div className="tagline">Walang datos na lumalabas.</div>
        <div className="spacer" />
        {gapError ? (
          <span className="badge online" title={gapError}>
            <span className="dot" /> PROBE ERROR
          </span>
        ) : (
          <span
            className={`badge ${airGapped ? "gap" : "online"}`}
            title={gap?.note ?? "probing..."}
          >
            <span className="dot" />
            {airGapped ? "NETWORK: AIR-GAPPED" : "NETWORK: CONNECTED"}
          </span>
        )}
      </header>

      <nav className="tabs">
        <button
          className={`tab ${tab === "egress" ? "active" : ""}`}
          onClick={() => setTab("egress")}
        >
          Egress Guard
        </button>
        <button
          className={`tab ${tab === "copilot" ? "active" : ""}`}
          onClick={() => setTab("copilot")}
        >
          DPA Copilot
        </button>
        <button
          className={`tab ${tab === "ledger" ? "active" : ""}`}
          onClick={() => setTab("ledger")}
        >
          Audit Ledger
        </button>
      </nav>

      <main className="content">
        {tab === "egress" && <EgressGuard health={health} />}
        {tab === "copilot" && <Copilot />}
        {tab === "ledger" && <Ledger />}
      </main>

      <footer className="footer-note">
        Every inference runs on this machine. KALIX opens no outbound socket.
        <br />
        Corpus: RA 10173, its IRR, and NPC/BSP issuances — verified{" "}
        {health?.corpus?.documents ?? 0} documents,{" "}
        {health?.corpus?.chunks ?? 0} citable sections.
        <br />
        AI-generated. Verified against the local corpus. Not a substitute for legal advice.
      </footer>
    </div>
  );
}