import { useState } from "react";
import { api, type CopilotAnswer } from "../lib/api";

const DEMO_QUERIES = [
  "Pwede ba ipasa ang CDR ng customer ko sa vendor namin sa Singapore?",
  "Ilang oras dapat ko i-report ang data breach?",
  "Kailangan ba mag-register ng AI credit scoring model ang banko namin?",
  "May karapatang humingi ng data ng customer ko ang collection agency?",
  "Ilang taon dapat itinatago ang transaction records?",
  "Can our call center use AI to score our agents?",
];

const OUT_OF_CORPUS = [
  "Ano ang stock price ng BDO ngayong araw?",
  "Who won the 2025 FIFA World Cup?",
];

export default function Copilot() {
  const [question, setQuestion] = useState(DEMO_QUERIES[0]);
  const [answer, setAnswer] = useState<CopilotAnswer | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function ask(q: string) {
    setQuestion(q);
    setBusy(true);
    setError(null);
    try {
      setAnswer(await api.ask(q));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setAnswer(null);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="card" style={{ marginBottom: 16 }}>
        <h2>DPA Copilot</h2>
        <p className="hint">
          Answers strictly from the local Philippine privacy corpus, in Taglish, with a citation
          on every legal claim. Ask something outside the corpus and it will refuse.
        </p>

        <div className="muted" style={{ marginTop: 4, marginBottom: 4 }}>
          Demo questions
        </div>
        <div className="chips">
          {DEMO_QUERIES.map((q) => (
            <button key={q} className="chip" onClick={() => void ask(q)}>
              {q.length > 62 ? `${q.slice(0, 62)}…` : q}
            </button>
          ))}
        </div>

        <div className="muted" style={{ marginBottom: 4 }}>
          Out of corpus — must refuse
        </div>
        <div className="chips">
          {OUT_OF_CORPUS.map((q) => (
            <button key={q} className="chip" onClick={() => void ask(q)}>
              {q}
            </button>
          ))}
        </div>

        <div className="row" style={{ marginTop: 8 }}>
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && question.trim()) void ask(question);
            }}
            placeholder="Magtanong sa Taglish o English…"
          />
          <button
            className="btn"
            onClick={() => void ask(question)}
            disabled={busy || !question.trim()}
          >
            {busy ? "Retrieving…" : "Ask"}
          </button>
        </div>

        {error && <div className="err">{error}</div>}
      </div>

      {answer && (
        <div className="card">
          <div className={`verdict ${answer.refused ? "redact" : "safe"}`}>
            <span className="vlabel">
              {answer.refused ? "REFUSED — NO CORPUS BASIS" : "GROUNDED ANSWER"}
            </span>
            <span className="muted">
              confidence {answer.confidence.toFixed(2)} · {answer.retrieval_mode}
              {answer.llm_used ? " · LLM" : " · extractive"}
            </span>
            <span className="vmeta">{answer.latency_ms.toFixed(0)} ms</span>
          </div>

          <div className={answer.refused ? "refusal answer" : "answer"}>{answer.answer}</div>

          {answer.citations.length > 0 && (
            <>
              <div className="muted" style={{ marginTop: 16, marginBottom: 6 }}>
                Citations
              </div>
              <div>
                {answer.citations.map((c) => (
                  <span key={c.id} className="cite" title={`${c.doc_title} — ${c.section}`}>
                    {c.label}
                  </span>
                ))}
              </div>
              <table style={{ marginTop: 12 }}>
                <thead>
                  <tr>
                    <th>Document</th>
                    <th>Issuer</th>
                    <th>Section</th>
                    <th>Effective</th>
                    <th>Score</th>
                  </tr>
                </thead>
                <tbody>
                  {answer.citations.map((c) => (
                    <tr key={c.id}>
                      <td>{c.doc_title.slice(0, 58)}</td>
                      <td className="muted">{c.issuer}</td>
                      <td className="mono">{c.section.slice(0, 40)}</td>
                      <td className="mono muted">{c.effective_date}</td>
                      <td className="mono">{c.score.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}

          <div className="muted" style={{ marginTop: 16, fontStyle: "italic" }}>
            {answer.footer}
          </div>
        </div>
      )}
    </>
  );
}