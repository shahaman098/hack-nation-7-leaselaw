import { useCallback, useEffect, useState } from 'react';
import {
  AlertTriangle,
  Calendar,
  CheckCircle2,
  ClipboardList,
  FileText,
  Loader2,
  Scale,
  Shield,
  Sparkles,
} from 'lucide-react';

const DEMO_HINT =
  'Paste a decision letter or pick a sample case, then run analysis to diff governing guidance vs current rules.';

function formatDaysLabel(days) {
  if (days > 0) return `${days} days remaining in governing window`;
  if (days === 0) return 'Deadline is today (governing rule)';
  return `${Math.abs(days)} days past governing deadline`;
}

export default function App() {
  const [samples, setSamples] = useState([]);
  const [selectedSample, setSelectedSample] = useState('');
  const [noticeText, setNoticeText] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [apiOk, setApiOk] = useState(null);

  useEffect(() => {
    fetch('/api/health')
      .then((r) => r.json())
      .then((d) => setApiOk(d.status === 'ok'))
      .catch(() => setApiOk(false));
  }, []);

  useEffect(() => {
    fetch('/api/samples')
      .then((r) => r.json())
      .then((d) => setSamples(d.samples || []))
      .catch(() => setSamples([]));
  }, []);

  const loadSample = useCallback(
    (id) => {
      const row = samples.find((s) => s.id === id);
      if (row) {
        setSelectedSample(id);
        setNoticeText(row.text);
        setResult(null);
        setError('');
      }
    },
    [samples]
  );

  const runAnalysis = async () => {
    const trimmed = noticeText.trim();
    if (!trimmed) {
      setError('Add notice text or choose a sample case first.');
      return;
    }
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const res = await fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ notice_text: trimmed }),
      });
      if (!res.ok) {
        const body = await res.text();
        throw new Error(body || `Analysis failed (${res.status})`);
      }
      setResult(await res.json());
    } catch (e) {
      setError(e.message || 'Could not reach AppealPath API. Start the API on port 8001.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-shell">
      <header className="hero">
        <div className="hero-text">
          <p className="eyebrow">Hack-Nation build · Appeal Path Diff</p>
          <h1>Administrative time machine</h1>
          <p className="lede">
            Reconstruct which rule version applied on the decision date, diff it against current
            guidance, and emit an auditable appeal evidence pack.
          </p>
        </div>
        <div className="hero-meta">
          <span className={`pill ${apiOk ? 'pill-ok' : apiOk === false ? 'pill-bad' : ''}`}>
            {apiOk === null ? 'Checking API…' : apiOk ? 'API connected' : 'API offline'}
          </span>
          <span className="pill pill-muted">Fixture corpus · deterministic diff</span>
        </div>
      </header>

      <main className="layout">
        <section className="panel input-panel" aria-labelledby="input-heading">
          <div className="panel-head">
            <FileText size={20} aria-hidden />
            <h2 id="input-heading">Decision notice</h2>
          </div>
          <p className="hint">{DEMO_HINT}</p>

          <label className="field-label" htmlFor="sample-select">Sample cases</label>
          <select
            id="sample-select"
            className="select"
            value={selectedSample}
            onChange={(e) => loadSample(e.target.value)}
          >
            <option value="">— Choose a demo notice —</option>
            {samples.map((s) => (
              <option key={s.id} value={s.id}>{s.title}</option>
            ))}
          </select>

          <label className="field-label" htmlFor="notice-text">Notice text</label>
          <textarea
            id="notice-text"
            className="textarea"
            rows={14}
            value={noticeText}
            onChange={(e) => {
              setNoticeText(e.target.value);
              setSelectedSample('');
            }}
            placeholder="Paste decision letter text…"
          />

          {error && (
            <div className="alert alert-error" role="alert">
              <AlertTriangle size={18} aria-hidden />
              <span>{error}</span>
            </div>
          )}

          <button
            type="button"
            className="btn-primary"
            onClick={runAnalysis}
            disabled={loading}
          >
            {loading ? (
              <>
                <Loader2 className="spin" size={18} aria-hidden />
                Analyzing…
              </>
            ) : (
              <>
                <Sparkles size={18} aria-hidden />
                Run rule diff &amp; evidence pack
              </>
            )}
          </button>
        </section>

        <section className="panel results-panel" aria-live="polite">
          {!result && !loading && (
            <div className="empty-state">
              <Scale size={40} strokeWidth={1.25} aria-hidden />
              <p>Output appears here after analysis.</p>
            </div>
          )}

          {result && (
            <>
              <div className="panel-head">
                <Shield size={20} aria-hidden />
                <h2>Appeal pack outline</h2>
              </div>

              <div className="summary-grid">
                <article className="stat-card">
                  <span className="stat-label">Case</span>
                  <strong>{result.case_number}</strong>
                  <span className="stat-sub">{result.claimant_name}</span>
                </article>
                <article className="stat-card">
                  <span className="stat-label">Decision date</span>
                  <strong>{result.decision_date}</strong>
                  <span className="stat-sub">{result.governing_rule_version}</span>
                </article>
                <article className="stat-card">
                  <span className="stat-label">
                    <Calendar size={14} aria-hidden /> Governing deadline
                  </span>
                  <strong>{result.appeal_filing_deadline}</strong>
                  <span className="stat-sub">{formatDaysLabel(result.days_remaining_or_overdue)}</span>
                </article>
                <article className="stat-card">
                  <span className="stat-label">Appeal window</span>
                  <strong>
                    {result.statutory_window_days_applied} → {result.statutory_window_days_current} days
                  </strong>
                  <span className="stat-sub">Applied vs current corpus</span>
                </article>
              </div>

              {result.wrongful_application_detected && (
                <div className="alert alert-warn" role="status">
                  <AlertTriangle size={18} aria-hidden />
                  <div>
                    <strong>Wrong rule version suspected</strong>
                    <p>{result.wrongful_application_summary}</p>
                  </div>
                </div>
              )}

              <h3 className="section-title">Clause diff</h3>
              <ul className="clause-list">
                {result.clause_diffs.map((c) => (
                  <li key={c.clause_id} className={c.has_changed ? 'clause changed' : 'clause'}>
                    <div className="clause-head">
                      <code>{c.clause_id}</code>
                      <span>{c.title}</span>
                      {c.has_changed && <span className="tag">Changed</span>}
                    </div>
                    <p className="impact">{c.impact_note}</p>
                    <details>
                      <summary>View governing vs current text</summary>
                      <div className="diff-columns">
                        <pre>{c.decision_version_text}</pre>
                        <pre>{c.current_version_text}</pre>
                      </div>
                    </details>
                  </li>
                ))}
              </ul>

              <h3 className="section-title">
                <ClipboardList size={18} aria-hidden /> Evidence checklist
              </h3>
              <ul className="checklist">
                {result.required_evidence_checklist.map((item, i) => (
                  <li key={i} className={item.is_missing_or_vulnerable ? 'check warn' : 'check ok'}>
                    {item.is_missing_or_vulnerable ? (
                      <AlertTriangle size={16} aria-hidden />
                    ) : (
                      <CheckCircle2 size={16} aria-hidden />
                    )}
                    <div>
                      <strong>{item.requirement}</strong>
                      <p>{item.actionable_remedy}</p>
                    </div>
                  </li>
                ))}
              </ul>

              <h3 className="section-title">Audit trail</h3>
              <pre className="audit">{JSON.stringify(result.audit_trail, null, 2)}</pre>
            </>
          )}
        </section>
      </main>
    </div>
  );
}
