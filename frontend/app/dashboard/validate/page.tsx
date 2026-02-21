'use client';

import { useState } from 'react';
import { useAuth } from '@/lib/auth';
import { createAuthApi, getApiError } from '@/lib/api';
import type { ValidateResponse } from '@/lib/types';
import { Play, CheckCircle2, XCircle, AlertTriangle, Zap, RefreshCw, Info } from 'lucide-react';
import { formatLatency, confidenceColor } from '@/lib/utils';

const EXAMPLE_OUTPUT = `{
  "hours_worked": 30,
  "hourly_rate": "invalid_rate",
  "employee_name": "",
  "department": "ENGINEERING"
}`;

const EXAMPLE_RULES = `[
  {
    "type": "range",
    "name": "hours_check",
    "field": "hours_worked",
    "min": 0,
    "max": 24,
    "severity": "error"
  },
  {
    "type": "required",
    "name": "name_required",
    "field": "employee_name",
    "severity": "error"
  },
  {
    "type": "enum",
    "name": "dept_check",
    "field": "department",
    "values": ["ENGINEERING", "PRODUCT", "SALES", "MARKETING"],
    "severity": "warning"
  }
]`;

export default function ValidatePage() {
  const { apiKey } = useAuth();
  const [outputText, setOutputText] = useState(EXAMPLE_OUTPUT);
  const [rulesText, setRulesText] = useState(EXAMPLE_RULES);
  const [autoCorrect, setAutoCorrect] = useState(true);
  const [detectAnomalies, setDetectAnomalies] = useState(true);
  const [calcConfidence, setCalcConfidence] = useState(true);
  const [result, setResult] = useState<ValidateResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [outputParseErr, setOutputParseErr] = useState('');
  const [rulesParseErr, setRulesParseErr] = useState('');

  async function handleValidate() {
    if (!apiKey) return;
    setOutputParseErr('');
    setRulesParseErr('');
    setError('');

    let output: Record<string, unknown>;
    let rules: unknown[];
    try { output = JSON.parse(outputText); } catch {
      setOutputParseErr('Invalid JSON — check your output'); return;
    }
    try { rules = JSON.parse(rulesText); } catch {
      setRulesParseErr('Invalid JSON — check your rules'); return;
    }

    setLoading(true);
    try {
      const api = createAuthApi(apiKey);
      const res = await api.validate({
        output,
        rules: rules as never,
        context: {
          auto_correct: autoCorrect,
          detect_anomalies: detectAnomalies,
          auto_detect_anomalies: detectAnomalies,
          calculate_confidence: calcConfidence,
        },
      });
      setResult(res);
    } catch (err) {
      setError(getApiError(err));
    } finally {
      setLoading(false);
    }
  }

  const statusColor = result
    ? result.valid ? 'var(--green)' : result.status === 'warning' ? 'var(--amber)' : 'var(--red)'
    : 'var(--text-muted)';

  return (
    <div style={{ padding: '40px', maxWidth: '1400px' }}>
      {/* Header */}
      <div className="fade-up" style={{ marginBottom: '32px' }}>
        <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--text-muted)', letterSpacing: '0.1em', marginBottom: '6px' }}>
          PLAYGROUND
        </p>
        <h1 style={{ fontFamily: 'Syne, sans-serif', fontWeight: 800, fontSize: '28px', letterSpacing: '-0.02em', color: 'var(--text-primary)', marginBottom: '8px' }}>
          Validation Playground
        </h1>
        <p style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>
          Test your validation rules against AI outputs in real-time.
        </p>
      </div>

      {/* Options row */}
      <div className="glass-card fade-up-1" style={{ padding: '16px 20px', marginBottom: '24px', display: 'flex', alignItems: 'center', gap: '24px', flexWrap: 'wrap' }}>
        <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--text-muted)', letterSpacing: '0.08em' }}>OPTIONS:</span>
        {[
          { label: 'Auto-Correct', value: autoCorrect, set: setAutoCorrect },
          { label: 'Anomaly Detection', value: detectAnomalies, set: setDetectAnomalies },
          { label: 'Confidence Score', value: calcConfidence, set: setCalcConfidence },
        ].map(({ label, value, set }) => (
          <label key={label} style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', userSelect: 'none' }}>
            <div
              onClick={() => set(!value)}
              style={{
                width: '32px', height: '18px', borderRadius: '9px', position: 'relative', cursor: 'pointer',
                background: value ? 'var(--cyan)' : 'var(--border-default)',
                transition: 'background 0.2s',
                boxShadow: value ? '0 0 8px var(--cyan-glow)' : 'none',
              }}
            >
              <div style={{
                position: 'absolute', top: '2px', left: value ? '16px' : '2px',
                width: '14px', height: '14px', borderRadius: '50%',
                background: value ? 'var(--bg-void)' : 'var(--text-muted)',
                transition: 'left 0.2s',
              }} />
            </div>
            <span style={{ fontFamily: 'Syne, sans-serif', fontSize: '13px', color: value ? 'var(--text-primary)' : 'var(--text-muted)', fontWeight: 600 }}>
              {label}
            </span>
          </label>
        ))}
      </div>

      {/* Main 2-column layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
        {/* Input column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* AI Output */}
          <div className="glass-card fade-up-2" style={{ padding: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
              <Info size={13} color="var(--cyan)" />
              <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--text-muted)', letterSpacing: '0.08em' }}>
                AI OUTPUT (JSON)
              </span>
            </div>
            <textarea
              value={outputText}
              onChange={e => setOutputText(e.target.value)}
              spellCheck={false}
              style={{
                width: '100%', minHeight: '180px', resize: 'vertical',
                background: 'var(--bg-void)', border: `1px solid ${outputParseErr ? 'var(--red)' : 'var(--border-subtle)'}`,
                borderRadius: '8px', color: 'var(--text-primary)',
                fontFamily: 'JetBrains Mono, monospace', fontSize: '12px', lineHeight: 1.7,
                padding: '14px', outline: 'none', transition: 'border-color 0.2s',
              }}
              onFocus={e => { e.target.style.borderColor = outputParseErr ? 'var(--red)' : 'var(--cyan)'; }}
              onBlur={e => { e.target.style.borderColor = outputParseErr ? 'var(--red)' : 'var(--border-subtle)'; }}
            />
            {outputParseErr && <p style={{ fontSize: '12px', color: 'var(--red)', marginTop: '6px' }}>{outputParseErr}</p>}
          </div>

          {/* Rules */}
          <div className="glass-card fade-up-3" style={{ padding: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
              <Zap size={13} color="var(--amber)" />
              <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--text-muted)', letterSpacing: '0.08em' }}>
                VALIDATION RULES (JSON array)
              </span>
            </div>
            <textarea
              value={rulesText}
              onChange={e => setRulesText(e.target.value)}
              spellCheck={false}
              style={{
                width: '100%', minHeight: '240px', resize: 'vertical',
                background: 'var(--bg-void)', border: `1px solid ${rulesParseErr ? 'var(--red)' : 'var(--border-subtle)'}`,
                borderRadius: '8px', color: 'var(--text-primary)',
                fontFamily: 'JetBrains Mono, monospace', fontSize: '12px', lineHeight: 1.7,
                padding: '14px', outline: 'none', transition: 'border-color 0.2s',
              }}
              onFocus={e => { e.target.style.borderColor = rulesParseErr ? 'var(--red)' : 'var(--amber)'; }}
              onBlur={e => { e.target.style.borderColor = rulesParseErr ? 'var(--red)' : 'var(--border-subtle)'; }}
            />
            {rulesParseErr && <p style={{ fontSize: '12px', color: 'var(--red)', marginTop: '6px' }}>{rulesParseErr}</p>}
          </div>

          <button
            onClick={handleValidate}
            disabled={loading}
            className="tc-btn-primary"
            style={{ width: '100%', padding: '14px', fontSize: '14px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}
          >
            {loading ? <><RefreshCw size={15} style={{ animation: 'spin 0.8s linear infinite' }} /> Validating...</> : <><Play size={15} /> Run Validation</>}
          </button>
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>

        {/* Results column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {error && (
            <div className="glass-card" style={{ padding: '16px', background: 'var(--red-dim)', border: '1px solid rgba(255,69,96,0.2)' }}>
              <p style={{ color: 'var(--red)', fontSize: '13px' }}>⚠ {error}</p>
            </div>
          )}

          {!result && !error && (
            <div className="glass-card" style={{
              padding: '60px 20px', display: 'flex', flexDirection: 'column',
              alignItems: 'center', justifyContent: 'center', textAlign: 'center',
              border: '1px dashed var(--border-subtle)',
            }}>
              <Play size={32} color="var(--text-muted)" style={{ marginBottom: '12px', opacity: 0.4 }} />
              <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '12px', color: 'var(--text-muted)' }}>
                Results will appear here after validation
              </p>
            </div>
          )}

          {result && (
            <>
              {/* Status card */}
              <div className="glass-card fade-up" style={{
                padding: '20px', borderColor: `${statusColor}33`,
                boxShadow: `0 0 20px ${statusColor}14`,
              }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    {result.valid
                      ? <CheckCircle2 size={20} color="var(--green)" />
                      : result.status === 'warning'
                        ? <AlertTriangle size={20} color="var(--amber)" />
                        : <XCircle size={20} color="var(--red)" />
                    }
                    <span style={{
                      fontFamily: 'JetBrains Mono, monospace', fontWeight: 700, fontSize: '14px',
                      color: statusColor, letterSpacing: '0.05em',
                    }}>
                      {result.status.toUpperCase()}
                    </span>
                  </div>
                  <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--amber)' }}>
                    {formatLatency(result.latency_ms)}
                  </span>
                </div>

                {/* Metrics */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
                  {[
                    { label: 'VIOLATIONS', value: String(result.violations.length), color: result.violations.length > 0 ? 'var(--red)' : 'var(--green)' },
                    {
                      label: 'CONFIDENCE', value: result.confidence_score != null ? `${(result.confidence_score * 100).toFixed(0)}%` : '—',
                      color: result.confidence_level ? confidenceColor(result.confidence_level) : 'var(--text-muted)',
                    },
                    { label: 'ANOMALIES', value: String(result.anomalies_detected), color: result.anomalies_detected > 0 ? 'var(--amber)' : 'var(--green)' },
                  ].map(({ label, value, color }) => (
                    <div key={label} style={{ textAlign: 'center', background: 'var(--bg-void)', borderRadius: '8px', padding: '12px' }}>
                      <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '20px', fontWeight: 700, color }}>{value}</p>
                      <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '9px', color: 'var(--text-muted)', marginTop: '4px', letterSpacing: '0.1em' }}>{label}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Violations */}
              {result.violations.length > 0 && (
                <div className="glass-card fade-up-1" style={{ padding: '20px' }}>
                  <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--text-muted)', letterSpacing: '0.08em', marginBottom: '12px' }}>
                    VIOLATIONS ({result.violations.length})
                  </p>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {result.violations.map((v, i) => (
                      <div key={i} style={{
                        padding: '12px 14px', borderRadius: '8px',
                        background: 'var(--bg-void)', borderLeft: `3px solid ${v.severity === 'error' ? 'var(--red)' : 'var(--amber)'}`,
                      }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                          <span style={{
                            fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', fontWeight: 600,
                            color: 'var(--cyan)',
                          }}>{v.field}</span>
                          <span className={v.severity === 'error' ? 'badge-invalid' : 'badge-warn'}>{v.severity}</span>
                        </div>
                        <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--text-secondary)' }}>{v.message}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Auto-corrected output */}
              {result.auto_corrected && result.corrected_output && (
                <div className="glass-card fade-up-2" style={{ padding: '20px', borderColor: 'rgba(0,255,136,0.2)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                    <CheckCircle2 size={13} color="var(--green)" />
                    <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--green)', letterSpacing: '0.08em' }}>
                      AUTO-CORRECTED OUTPUT
                    </span>
                  </div>
                  {result.corrections_applied && result.corrections_applied.length > 0 && (
                    <div style={{ marginBottom: '12px' }}>
                      {result.corrections_applied.map((c, i) => (
                        <p key={i} style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px' }}>
                          → {c}
                        </p>
                      ))}
                    </div>
                  )}
                  <pre className="code-block" style={{ fontSize: '12px', margin: 0 }}>
                    {JSON.stringify(result.corrected_output, null, 2)}
                  </pre>
                </div>
              )}

              {/* Validation ID */}
              <div style={{ textAlign: 'center', marginTop: '4px' }}>
                <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '10px', color: 'var(--text-muted)' }}>
                  validation_id: {result.validation_id}
                </p>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
