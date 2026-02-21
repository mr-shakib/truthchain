'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import { useAuth } from '@/lib/auth';
import { createAuthApi, getApiError } from '@/lib/api';
import type { ValidationHistoryItem, TopViolation, DailyStat } from '@/lib/types';
import { formatLatency, formatDateTime } from '@/lib/utils';
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell, ComposedChart, ReferenceLine,
} from 'recharts';
import { Activity, RefreshCw, Zap, AlertTriangle, ShieldCheck, TrendingUp } from 'lucide-react';

// ─── Helpers ────────────────────────────────────────────────────────────────

function violationColor(index: number): string {
  const palette = [
    'var(--red)', 'var(--red)', // top 2: danger red
    'var(--amber)', 'var(--amber)', 'var(--amber)', // 3-5: amber
    'var(--cyan)', 'var(--cyan)', 'var(--cyan)', // 6-8: cyan
  ];
  return palette[index] ?? 'var(--cyan)';
}

function LiveDot() {
  return (
    <span style={{ position: 'relative', display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
      <span style={{
        width: 7, height: 7, borderRadius: '50%',
        background: 'var(--green)',
        boxShadow: '0 0 0 0 rgba(0,255,163,0.5)',
        animation: 'tc-pulse 1.4s ease-out infinite',
        display: 'inline-block',
      }} />
      <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '10px', color: 'var(--green)', letterSpacing: '0.1em' }}>LIVE</span>
    </span>
  );
}

// ─── Page ───────────────────────────────────────────────────────────────────

export default function AnalyticsPage() {
  const { apiKey } = useAuth();

  // State
  const [feed, setFeed] = useState<ValidationHistoryItem[]>([]);
  const [violations, setViolations] = useState<TopViolation[]>([]);
  const [daily, setDaily] = useState<DailyStat[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);
  const [newIds, setNewIds] = useState<Set<string>>(new Set());
  const prevFeedIds = useRef<Set<string>>(new Set());

  // ── Fetch all analytics data ─────────────────────────────────────────────
  const fetchData = useCallback(async () => {
    if (!apiKey) return;
    setError('');
    try {
      const api = createAuthApi(apiKey);
      const [feedData, violData, dailyData] = await Promise.all([
        api.recentValidations(20),
        api.topViolations(10),
        api.dailyStats(30),
      ]);

      // Detect newly arriving items in feed
      const incoming = feedData.map(f => f.validation_id ?? f.id ?? '');
      const freshIds = new Set(incoming.filter(id => !prevFeedIds.current.has(id)));
      setNewIds(freshIds);
      prevFeedIds.current = new Set(incoming);
      setTimeout(() => setNewIds(new Set()), 2000); // clear highlight after 2s

      setFeed(feedData);
      setViolations(violData);
      setDaily(dailyData);
      setLastRefresh(new Date());
    } catch (err) {
      setError(getApiError(err));
    } finally {
      setLoading(false);
    }
  }, [apiKey]);

  // Initial load
  useEffect(() => { fetchData(); }, [fetchData]);

  // Auto-refresh every 15 seconds
  useEffect(() => {
    const id = setInterval(fetchData, 15_000);
    return () => clearInterval(id);
  }, [fetchData]);

  // ── Derived chart data ───────────────────────────────────────────────────

  // Anomaly timeline: flag days where failed/(total||1) > 0.25
  const timelineData = daily.map(d => {
    const failRate = d.total > 0 ? d.failed / d.total : 0;
    return {
      date: new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      passed: d.passed,
      failed: d.failed,
      total: d.total,
      anomaly: failRate > 0.25 ? d.failed : null,
    };
  });

  // Group violations by rule category (first word / prefix)
  const categoryMap: Record<string, number> = {};
  violations.forEach(v => {
    const cat = v.rule_name?.split('_')[0]?.toUpperCase() ?? 'OTHER';
    categoryMap[cat] = (categoryMap[cat] ?? 0) + v.count;
  });
  const categoryData = Object.entries(categoryMap)
    .sort((a, b) => b[1] - a[1])
    .map(([cat, count]) => ({ cat, count }));

  const maxViol = violations[0]?.count ?? 1;

  // ── Render ───────────────────────────────────────────────────────────────
  return (
    <div style={{ padding: '40px', maxWidth: '1400px' }}>

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="fade-up" style={{ marginBottom: '40px', display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div>
          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--text-muted)', letterSpacing: '0.1em', marginBottom: '6px' }}>
            ANALYTICS
          </p>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <h1 style={{ fontFamily: 'Syne, sans-serif', fontWeight: 800, fontSize: '28px', letterSpacing: '-0.02em', color: 'var(--text-primary)' }}>
              Live Analytics
            </h1>
            <LiveDot />
          </div>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '6px' }}>
            Auto-refreshes every 15 seconds
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {lastRefresh && (
            <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--text-muted)' }}>
              {lastRefresh.toLocaleTimeString()}
            </span>
          )}
          <button onClick={fetchData} className="tc-btn-ghost"
            style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', padding: '8px 14px' }}>
            <RefreshCw size={13} />
            Refresh now
          </button>
        </div>
      </div>

      {/* ── Error ──────────────────────────────────────────────────────────── */}
      {error && (
        <div style={{ padding: '16px 20px', borderRadius: '10px', background: 'rgba(255,69,96,0.08)', border: '1px solid rgba(255,69,96,0.2)', marginBottom: '24px' }}>
          <p style={{ color: 'var(--red)', fontFamily: 'JetBrains Mono, monospace', fontSize: '13px' }}>⚠ {error}</p>
        </div>
      )}

      {/* ── Top row: Live feed + Violation breakdown ────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '20px' }}>

        {/* Live Validation Feed */}
        <div className="glass-card fade-up-1" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
            <div>
              <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--text-muted)', letterSpacing: '0.1em', marginBottom: '4px' }}>
                LIVE FEED
              </p>
              <p style={{ fontFamily: 'Syne, sans-serif', fontWeight: 700, fontSize: '15px', color: 'var(--text-primary)' }}>
                Validation stream
              </p>
            </div>
            <Activity size={16} style={{ color: 'var(--cyan)', opacity: 0.7 }} />
          </div>

          {loading ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {[...Array(5)].map((_, i) => (
                <div key={i} className="shimmer" style={{ height: '44px', borderRadius: '8px' }} />
              ))}
            </div>
          ) : feed.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)' }}>
              <ShieldCheck size={28} style={{ margin: '0 auto 10px', opacity: 0.3 }} />
              <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '12px' }}>No activity yet</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', maxHeight: '380px', overflowY: 'auto' }}>
              {feed.map((item) => {
                const itemId = item.validation_id ?? item.id ?? '';
                const isNew = newIds.has(itemId);
                return (
                  <div
                    key={itemId}
                    style={{
                      display: 'grid',
                      gridTemplateColumns: '64px 1fr auto auto',
                      alignItems: 'center',
                      gap: '10px',
                      padding: '10px 12px',
                      borderRadius: '8px',
                      background: isNew ? 'rgba(0,255,163,0.06)' : 'rgba(255,255,255,0.02)',
                      border: isNew ? '1px solid rgba(0,255,163,0.2)' : '1px solid transparent',
                      transition: 'all 0.4s ease',
                    }}
                  >
                    <span className={item.status === 'passed' ? 'badge-valid' : item.status === 'failed' ? 'badge-invalid' : 'badge-warn'}>
                      {item.status.toUpperCase()}
                    </span>
                    <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '10px', color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {itemId.slice(0, 16)}…
                    </span>
                    <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: item.violations_count > 0 ? 'var(--red)' : 'var(--green)', whiteSpace: 'nowrap' }}>
                      {item.violations_count} viol
                    </span>
                    <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '10px', color: 'var(--amber)', whiteSpace: 'nowrap' }}>
                      {formatLatency(item.latency_ms)}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Violation Breakdown Bar Chart */}
        <div className="glass-card fade-up-1" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
            <div>
              <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--text-muted)', letterSpacing: '0.1em', marginBottom: '4px' }}>
                RULE VIOLATIONS
              </p>
              <p style={{ fontFamily: 'Syne, sans-serif', fontWeight: 700, fontSize: '15px', color: 'var(--text-primary)' }}>
                Breakdown by rule
              </p>
            </div>
            <AlertTriangle size={16} style={{ color: 'var(--red)', opacity: 0.7 }} />
          </div>

          {loading ? (
            <div className="shimmer" style={{ height: '300px', borderRadius: '8px' }} />
          ) : violations.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)' }}>
              <ShieldCheck size={28} style={{ margin: '0 auto 10px', opacity: 0.3 }} />
              <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '12px' }}>No violations recorded</p>
            </div>
          ) : (
            <>
              {/* Manual horizontal bars — proportional to maxViol */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {violations.map((v, i) => (
                  <div key={v.rule_name} style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{
                      fontFamily: 'JetBrains Mono, monospace', fontSize: '10px',
                      color: 'var(--text-secondary)', width: '130px',
                      overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                      flexShrink: 0, textAlign: 'right',
                    }}>
                      {v.rule_name}
                    </span>
                    <div style={{ flex: 1, height: '14px', borderRadius: '3px', background: 'rgba(255,255,255,0.04)', overflow: 'hidden' }}>
                      <div style={{
                        height: '100%',
                        width: `${Math.max(4, (v.count / maxViol) * 100)}%`,
                        background: violationColor(i),
                        borderRadius: '3px',
                        opacity: 0.85,
                        transition: 'width 0.5s ease',
                      }} />
                    </div>
                    <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: violationColor(i), width: '32px', flexShrink: 0 }}>
                      {v.count}
                    </span>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>

      {/* ── Anomaly Timeline ────────────────────────────────────────────────── */}
      <div className="glass-card fade-up-2" style={{ padding: '24px', marginBottom: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
          <div>
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--text-muted)', letterSpacing: '0.1em', marginBottom: '4px' }}>
              ANOMALY TIMELINE
            </p>
            <p style={{ fontFamily: 'Syne, sans-serif', fontWeight: 700, fontSize: '15px', color: 'var(--text-primary)' }}>
              30-day pass / fail trend · anomaly spikes highlighted
            </p>
          </div>
          <TrendingUp size={16} style={{ color: 'var(--amber)', opacity: 0.7 }} />
        </div>

        {loading ? (
          <div className="shimmer" style={{ height: '200px', borderRadius: '8px' }} />
        ) : timelineData.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)' }}>
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '12px' }}>No data for the past 30 days</p>
          </div>
        ) : (
          <>
            <ResponsiveContainer width="100%" height={240}>
              <ComposedChart data={timelineData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="passGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--green)" stopOpacity={0.2} />
                    <stop offset="95%" stopColor="var(--green)" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="failGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--red)" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="var(--red)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                <XAxis
                  dataKey="date"
                  tick={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, fill: 'var(--text-muted)' }}
                  axisLine={false} tickLine={false}
                  interval={Math.floor(timelineData.length / 8)}
                />
                <YAxis tick={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} />
                <Tooltip
                  content={({ active, payload, label }) => {
                    if (!active || !payload?.length) return null;
                    return (
                      <div style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-default)', borderRadius: '8px', padding: '10px 14px' }}>
                        <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--text-muted)', marginBottom: '6px' }}>{label}</p>
                        {payload.map((p) => (
                          <p key={p.dataKey as string} style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '12px', color: p.color as string, fontWeight: 600 }}>
                            {p.dataKey}: {p.value}
                          </p>
                        ))}
                        {payload[0]?.payload?.anomaly != null && (
                          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--amber)', marginTop: '4px' }}>
                            ⚠ Anomaly spike
                          </p>
                        )}
                      </div>
                    );
                  }}
                />
                {/* Reference lines for anomaly days */}
                {timelineData
                  .filter(d => d.anomaly !== null)
                  .map(d => (
                    <ReferenceLine
                      key={d.date}
                      x={d.date}
                      stroke="var(--amber)"
                      strokeDasharray="4 3"
                      strokeWidth={1}
                      opacity={0.5}
                    />
                  ))}
                <Area type="monotone" dataKey="passed" stroke="var(--green)" strokeWidth={1.5} fill="url(#passGrad)" name="passed" />
                <Area type="monotone" dataKey="failed" stroke="var(--red)" strokeWidth={1.5} fill="url(#failGrad)" name="failed" />
              </ComposedChart>
            </ResponsiveContainer>
            <div style={{ display: 'flex', alignItems: 'center', gap: '20px', marginTop: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <div style={{ width: 10, height: 10, borderRadius: '2px', background: 'var(--green)', opacity: 0.8 }} />
                <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '10px', color: 'var(--text-muted)' }}>passed</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <div style={{ width: 10, height: 10, borderRadius: '2px', background: 'var(--red)', opacity: 0.8 }} />
                <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '10px', color: 'var(--text-muted)' }}>failed</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <div style={{ width: 10, height: 2, background: 'var(--amber)', opacity: 0.7 }} />
                <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '10px', color: 'var(--text-muted)' }}>anomaly spike (&gt;25% fail rate)</span>
              </div>
            </div>
          </>
        )}
      </div>

      {/* ── Rule Category Heat Strip ─────────────────────────────────────────── */}
      {categoryData.length > 0 && (
        <div className="glass-card fade-up-3" style={{ padding: '24px' }}>
          <div style={{ marginBottom: '20px' }}>
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--text-muted)', letterSpacing: '0.1em', marginBottom: '4px' }}>
              RULE CATEGORY HEATMAP
            </p>
            <p style={{ fontFamily: 'Syne, sans-serif', fontWeight: 700, fontSize: '15px', color: 'var(--text-primary)' }}>
              Violations grouped by rule type
            </p>
          </div>

          <ResponsiveContainer width="100%" height={160}>
            <BarChart data={categoryData} margin={{ top: 4, right: 10, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
              <XAxis dataKey="cat" tick={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, fill: 'var(--text-secondary)' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} />
              <Tooltip
                content={({ active, payload }) => {
                  if (!active || !payload?.length) return null;
                  return (
                    <div style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-default)', borderRadius: '8px', padding: '10px 14px' }}>
                      <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px' }}>{payload[0].payload.cat}</p>
                      <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '13px', color: 'var(--red)', fontWeight: 700 }}>{payload[0].value} violations</p>
                    </div>
                  );
                }}
              />
              <Bar dataKey="count" radius={[4, 4, 0, 0]} name="violations">
                {categoryData.map((_, idx) => (
                  <Cell key={idx} fill={violationColor(idx)} opacity={0.8} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>

          {/* Heat strip */}
          <div style={{ display: 'flex', gap: '4px', marginTop: '16px', height: '20px' }}>
            {categoryData.map((c, i) => {
              const maxCat = categoryData[0]?.count ?? 1;
              const intensity = c.count / maxCat;
              return (
                <div
                  key={c.cat}
                  title={`${c.cat}: ${c.count}`}
                  style={{
                    flex: c.count,
                    borderRadius: '4px',
                    background: violationColor(i),
                    opacity: 0.3 + intensity * 0.65,
                    cursor: 'default',
                    transition: 'opacity 0.3s',
                    minWidth: '4px',
                  }}
                />
              );
            })}
          </div>
          <div style={{ display: 'flex', gap: '4px', marginTop: '6px' }}>
            {categoryData.map((c, i) => {
              const maxCat = categoryData[0]?.count ?? 1;
              const intensity = c.count / maxCat;
              return (
                <div key={c.cat} style={{ flex: c.count, textAlign: 'center', minWidth: '4px' }}>
                  {intensity > 0.15 && (
                    <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '9px', color: 'var(--text-muted)' }}>
                      {c.cat}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── Speed Metrics strip ──────────────────────────────────────────────── */}
      <div className="glass-card fade-up-4" style={{ padding: '20px 24px', marginTop: '20px', display: 'flex', alignItems: 'center', gap: '32px' }}>
        <Zap size={18} style={{ color: 'var(--cyan)', flexShrink: 0 }} />
        <div style={{ flex: 1 }}>
          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--text-muted)', letterSpacing: '0.08em', marginBottom: '4px' }}>THROUGHPUT (30 DAYS)</p>
          <div style={{ display: 'flex', gap: '32px' }}>
            <div>
              <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '20px', fontWeight: 700, color: 'var(--cyan)' }}>
                {timelineData.reduce((s, d) => s + d.total, 0).toLocaleString()}
              </p>
              <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '10px', color: 'var(--text-muted)' }}>TOTAL VALIDATIONS</p>
            </div>
            <div>
              <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '20px', fontWeight: 700, color: 'var(--green)' }}>
                {timelineData.reduce((s, d) => s + d.passed, 0).toLocaleString()}
              </p>
              <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '10px', color: 'var(--text-muted)' }}>PASSED</p>
            </div>
            <div>
              <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '20px', fontWeight: 700, color: 'var(--red)' }}>
                {timelineData.reduce((s, d) => s + d.failed, 0).toLocaleString()}
              </p>
              <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '10px', color: 'var(--text-muted)' }}>FAILED</p>
            </div>
            <div>
              <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '20px', fontWeight: 700, color: 'var(--amber)' }}>
                {timelineData.filter(d => d.anomaly !== null).length}
              </p>
              <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '10px', color: 'var(--text-muted)' }}>ANOMALY DAYS</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
