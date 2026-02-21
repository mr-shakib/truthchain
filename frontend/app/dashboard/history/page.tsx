'use client';

import { useEffect, useState, useCallback } from 'react';
import { useAuth } from '@/lib/auth';
import { createAuthApi, getApiError } from '@/lib/api';
import type { ValidationHistoryItem, TopViolation } from '@/lib/types';
import { formatLatency, formatDateTime, confidenceColor } from '@/lib/utils';
import { RefreshCw, ShieldCheck, AlertTriangle, BarChart3, Filter } from 'lucide-react';

export default function HistoryPage() {
  const { apiKey } = useAuth();
  const [history, setHistory] = useState<ValidationHistoryItem[]>([]);
  const [violations, setViolations] = useState<TopViolation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState<'all' | 'passed' | 'failed'>('all');
  const [limit, setLimit] = useState(50);

  const fetchData = useCallback(async () => {
    if (!apiKey) return;
    setError('');
    try {
      const api = createAuthApi(apiKey);
      const [histData, violData] = await Promise.all([
        api.recentValidations(limit),
        api.topViolations(10),
      ]);
      setHistory(histData);
      setViolations(violData);
    } catch (err) {
      setError(getApiError(err));
    } finally {
      setLoading(false);
    }
  }, [apiKey, limit]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const filtered = filter === 'all' ? history : history.filter(h => h.status === filter);

  const maxViolCount = violations[0]?.count ?? 1;

  return (
    <div style={{ padding: '40px', maxWidth: '1200px' }}>
      {/* Header */}
      <div className="fade-up" style={{ marginBottom: '32px', display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div>
          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--text-muted)', letterSpacing: '0.1em', marginBottom: '6px' }}>
            AUDIT TRAIL
          </p>
          <h1 style={{ fontFamily: 'Syne, sans-serif', fontWeight: 800, fontSize: '28px', letterSpacing: '-0.02em', color: 'var(--text-primary)', marginBottom: '8px' }}>
            Validation History
          </h1>
          <p style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>
            Complete log of all validation requests for your organization.
          </p>
        </div>
        <button onClick={() => { setLoading(true); fetchData(); }} className="tc-btn-ghost"
          style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', padding: '8px 14px' }}>
          <RefreshCw size={13} />
          Refresh
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: '20px' }}>
        {/* Main table */}
        <div>
          {/* Filters */}
          <div className="fade-up-1" style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
            <Filter size={13} color="var(--text-muted)" />
            {(['all', 'passed', 'failed'] as const).map(f => (
              <button key={f} onClick={() => setFilter(f)} style={{
                padding: '6px 14px', borderRadius: '6px', cursor: 'pointer', fontSize: '12px',
                fontFamily: 'Syne, sans-serif', fontWeight: 700, textTransform: 'capitalize',
                background: filter === f ? 'var(--cyan-dim)' : 'transparent',
                color: filter === f ? 'var(--cyan)' : 'var(--text-muted)',
                border: `1px solid ${filter === f ? 'rgba(0,216,255,0.25)' : 'var(--border-subtle)'}`,
                transition: 'all 0.15s',
              }}>{f === 'all' ? `All (${history.length})` : f === 'passed' ? `Passed` : `Failed`}</button>
            ))}

            <select
              value={limit}
              onChange={e => setLimit(Number(e.target.value))}
              style={{
                marginLeft: 'auto', background: 'var(--bg-elevated)', border: '1px solid var(--border-default)',
                borderRadius: '6px', color: 'var(--text-secondary)', padding: '6px 10px',
                fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', cursor: 'pointer', outline: 'none',
              }}
            >
              <option value={20}>20 rows</option>
              <option value={50}>50 rows</option>
              <option value={100}>100 rows</option>
            </select>
          </div>

          <div className="glass-card fade-up-2" style={{ overflow: 'hidden' }}>
            {loading ? (
              <div style={{ padding: '40px', textAlign: 'center' }}>
                <RefreshCw size={20} color="var(--text-muted)" style={{ animation: 'spin 0.8s linear infinite', margin: '0 auto' }} />
              </div>
            ) : error ? (
              <div style={{ padding: '20px' }}>
                <p style={{ color: 'var(--red)', fontSize: '13px' }}>⚠ {error}</p>
              </div>
            ) : filtered.length === 0 ? (
              <div style={{ padding: '60px', textAlign: 'center' }}>
                <ShieldCheck size={32} color="var(--text-muted)" style={{ margin: '0 auto 12px', opacity: 0.3 }} />
                <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '12px', color: 'var(--text-muted)' }}>
                  No validations found
                </p>
              </div>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                      {['Validation ID', 'Status', 'Violations', 'Confidence', 'Corrected', 'Latency', 'Time'].map(h => (
                        <th key={h} style={{
                          textAlign: 'left', padding: '10px 14px',
                          fontFamily: 'JetBrains Mono, monospace', fontSize: '10px',
                          color: 'var(--text-muted)', letterSpacing: '0.1em', fontWeight: 600,
                          whiteSpace: 'nowrap',
                        }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.map((row, i) => (
                      <tr
                        key={row.id}
                        style={{
                          borderBottom: i < filtered.length - 1 ? '1px solid var(--border-subtle)' : 'none',
                          transition: 'background 0.1s',
                        }}
                        onMouseEnter={e => { (e.currentTarget as HTMLTableRowElement).style.background = 'rgba(255,255,255,0.02)'; }}
                        onMouseLeave={e => { (e.currentTarget as HTMLTableRowElement).style.background = 'transparent'; }}
                      >
                        <td style={{ padding: '11px 14px', fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--cyan)', whiteSpace: 'nowrap' }}>
                          {row.validation_id?.slice(0, 16)}...
                        </td>
                        <td style={{ padding: '11px 14px' }}>
                          <span className={
                            row.status === 'passed' ? 'badge-valid' :
                              row.status === 'failed' ? 'badge-invalid' : 'badge-warn'
                          }>
                            {row.status.toUpperCase()}
                          </span>
                        </td>
                        <td style={{ padding: '11px 14px', fontFamily: 'JetBrains Mono, monospace', fontSize: '12px', color: row.violations_count > 0 ? 'var(--red)' : 'var(--green)', textAlign: 'center' }}>
                          {row.violations_count}
                        </td>
                        <td style={{ padding: '11px 14px', fontFamily: 'JetBrains Mono, monospace', fontSize: '12px', color: row.confidence_score != null ? confidenceColor(row.confidence_score > 0.75 ? 'high' : row.confidence_score > 0.5 ? 'medium' : 'low') : 'var(--text-muted)' }}>
                          {row.confidence_score != null ? `${(row.confidence_score * 100).toFixed(0)}%` : '—'}
                        </td>
                        <td style={{ padding: '11px 14px', textAlign: 'center' }}>
                          {row.auto_corrected
                            ? <span style={{ color: 'var(--green)', fontSize: '14px' }}>✓</span>
                            : <span style={{ color: 'var(--text-muted)', fontSize: '14px' }}>—</span>
                          }
                        </td>
                        <td style={{ padding: '11px 14px', fontFamily: 'JetBrains Mono, monospace', fontSize: '12px', color: 'var(--amber)', whiteSpace: 'nowrap' }}>
                          {formatLatency(row.latency_ms)}
                        </td>
                        <td style={{ padding: '11px 14px', fontFamily: 'JetBrains Mono, monospace', fontSize: '10px', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                          {formatDateTime(row.created_at)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        {/* Top violations sidebar */}
        <div>
          <div className="glass-card fade-up-3" style={{ padding: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '20px' }}>
              <BarChart3 size={14} color="var(--amber)" />
              <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--text-muted)', letterSpacing: '0.08em' }}>
                TOP VIOLATIONS
              </p>
            </div>
            {violations.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '20px' }}>
                <AlertTriangle size={24} color="var(--text-muted)" style={{ margin: '0 auto 8px', opacity: 0.3 }} />
                <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--text-muted)' }}>No violations data</p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {violations.map((v) => (
                  <div key={`${v.rule_name}-${v.field}`}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                      <div>
                        <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--cyan)', fontWeight: 600 }}>
                          {v.field}
                        </span>
                        <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '10px', color: 'var(--text-muted)', marginLeft: '6px' }}>
                          {v.rule_name}
                        </span>
                      </div>
                      <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: v.severity === 'error' ? 'var(--red)' : 'var(--amber)' }}>
                        {v.count}
                      </span>
                    </div>
                    <div className="tc-progress-bar">
                      <div className="tc-progress-fill" style={{
                        width: `${(v.count / maxViolCount) * 100}%`,
                        background: v.severity === 'error' ? 'var(--red)' : 'var(--amber)',
                        opacity: 0.7,
                      }} />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
