'use client';

import { useEffect, useState, useCallback } from 'react';
import { useAuth } from '@/lib/auth';
import { createAuthApi, getApiError } from '@/lib/api';
import type { OverviewStats, DailyStat, ValidationHistoryItem, TopViolation } from '@/lib/types';
import { formatNumber, formatLatency, formatDateTime } from '@/lib/utils';
import StatCard from '@/components/StatCard';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import { ShieldCheck, AlertTriangle, Activity, Gauge, RefreshCw, ArrowRight, Zap, BarChart2, Clock } from 'lucide-react';
import Link from 'next/link';

// â”€â”€â”€ Sub-components â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

interface TooltipProps {
  active?: boolean;
  payload?: { color: string; name: string; value: number }[];
  label?: string;
}

function ChartTooltip({ active, payload, label }: TooltipProps) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: 'var(--bg-elevated)', border: '1px solid var(--border-default)',
      borderRadius: '8px', padding: '12px 16px', fontFamily: 'JetBrains Mono, monospace',
    }}>
      <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '8px' }}>{label}</p>
      {payload.map((p) => (
        <div key={p.name} style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '4px' }}>
          <span style={{ width: '8px', height: '8px', borderRadius: '2px', background: p.color, display: 'inline-block', flexShrink: 0 }} />
          <span style={{ fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'capitalize' }}>{p.name}:</span>
          <span style={{ fontSize: '12px', color: 'var(--text-primary)', fontWeight: 600 }}>{p.value}</span>
        </div>
      ))}
    </div>
  );
}

function QuotaRing({ pct, color }: { pct: number; color: string }) {
  const r = 34;
  const circ = 2 * Math.PI * r;
  const offset = circ * (1 - Math.min(pct, 100) / 100);
  return (
    <svg width="84" height="84" viewBox="0 0 84 84" style={{ flexShrink: 0 }}>
      <circle cx="42" cy="42" r={r} fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth="7" />
      <circle
        cx="42" cy="42" r={r} fill="none" stroke={color} strokeWidth="7"
        strokeDasharray={`${circ}`}
        strokeDashoffset={`${offset}`}
        strokeLinecap="round"
        transform="rotate(-90 42 42)"
        style={{ transition: 'stroke-dashoffset 0.9s cubic-bezier(0.34,1.56,0.64,1)' }}
      />
      <text x="42" y="47" textAnchor="middle"
        style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '13px', fontWeight: 700, fill: color } as React.CSSProperties}>
        {Math.round(pct)}%
      </text>
    </svg>
  );
}

// â”€â”€â”€ Page â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

export default function DashboardPage() {
  const { apiKey, orgName, tier } = useAuth();
  const [stats, setStats] = useState<OverviewStats | null>(null);
  const [daily, setDaily] = useState<DailyStat[]>([]);
  const [recent, setRecent] = useState<ValidationHistoryItem[]>([]);
  const [violations, setViolations] = useState<TopViolation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  const fetchData = useCallback(async () => {
    if (!apiKey) return;
    setError('');
    try {
      const api = createAuthApi(apiKey);
      const [overviewData, dailyData, recentData, violData] = await Promise.all([
        api.overview(),
        api.dailyStats(14),
        api.recentValidations(5),
        api.topViolations(6),
      ]);
      setStats(overviewData);
      setDaily(dailyData);
      setRecent(recentData);
      setViolations(violData);
      setLastRefresh(new Date());
    } catch (err) {
      setError(getApiError(err));
    } finally {
      setLoading(false);
    }
  }, [apiKey]);

  // Initial load + auto-refresh every 30 seconds
  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30_000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const chartData = daily.map(d => ({
    date: new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    passed: d.passed,
    failed: d.failed,
    total: d.total,
    latency: Math.round(d.avg_latency_ms),
  }));

  const todayStats = daily[daily.length - 1] ?? null;
  const sevenDayTotal = daily.slice(-7).reduce((s, d) => s + d.total, 0);
  const maxLatency = Math.max(...chartData.map(d => d.latency), 1);
  const maxViol = violations[0]?.count ?? 1;

  const quotaColor = stats
    ? stats.quota_percentage > 80 ? 'var(--red)'
    : stats.quota_percentage > 60 ? 'var(--amber)'
    : 'var(--cyan)'
    : 'var(--cyan)';

  return (
    <div style={{ padding: '40px', maxWidth: '1400px' }}>

      {/* â”€â”€ Header â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
      <div className="fade-up" style={{ marginBottom: '32px' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '24px' }}>
          <div>
            {/* Eyebrow with live indicator */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
              <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--text-muted)', letterSpacing: '0.12em' }}>
                OVERVIEW
              </span>
              <span
                className="pulse-dot"
                style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--green)', display: 'inline-block' }}
              />
              <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '10px', color: 'var(--green)', letterSpacing: '0.1em' }}>
                LIVE
              </span>
            </div>

            <h1 style={{ fontFamily: 'Syne, sans-serif', fontWeight: 800, fontSize: '32px', letterSpacing: '-0.025em', color: 'var(--text-primary)', lineHeight: 1 }}>
              Dashboard
            </h1>

            {/* Org + tier badge */}
            {orgName && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '10px' }}>
                <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '12px', color: 'var(--text-secondary)' }}>
                  {orgName}
                </span>
                {tier && (
                  <span style={{
                    fontFamily: 'JetBrains Mono, monospace', fontSize: '9px', letterSpacing: '0.1em',
                    padding: '2px 7px', borderRadius: '3px',
                    background: 'var(--cyan-dim)', color: 'var(--cyan)', border: '1px solid rgba(0,216,255,0.2)',
                  }}>
                    {tier.toUpperCase()}
                  </span>
                )}
              </div>
            )}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '4px' }}>
            {lastRefresh && (
              <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--text-muted)' }}>
                {lastRefresh.toLocaleTimeString()}
              </span>
            )}
            <button
              onClick={fetchData}
              className="tc-btn-ghost"
              style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', padding: '8px 14px' }}
            >
              <RefreshCw size={13} />
              Refresh
            </button>
          </div>
        </div>

        {/* â”€â”€ Today metrics strip â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
        {!loading && stats && (
          <div style={{
            display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)',
            background: 'var(--bg-surface)',
            border: '1px solid var(--border-subtle)',
            borderRadius: '10px',
            overflow: 'hidden',
          }}>
            {[
              { key: 'ALL TIME', val: formatNumber(stats.total_validations), color: 'var(--cyan)' },
              { key: 'TODAY', val: todayStats ? formatNumber(todayStats.total) : 'â€”', color: 'var(--text-primary)' },
              { key: 'LAST 7 DAYS', val: formatNumber(sevenDayTotal), color: 'var(--text-primary)' },
              {
                key: 'SUCCESS RATE',
                val: `${(stats.success_rate ?? 0).toFixed(1)}%`,
                color: (stats.success_rate ?? 0) >= 90 ? 'var(--green)'
                  : (stats.success_rate ?? 0) >= 70 ? 'var(--amber)' : 'var(--red)',
              },
            ].map((item, i) => (
              <div
                key={item.key}
                style={{
                  padding: '16px 24px',
                  borderRight: i < 3 ? '1px solid var(--border-subtle)' : 'none',
                }}
              >
                <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '10px', color: 'var(--text-muted)', letterSpacing: '0.1em', marginBottom: '6px' }}>
                  {item.key}
                </p>
                <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '18px', fontWeight: 700, color: item.color }}>
                  {item.val}
                </p>
              </div>
            ))}
          </div>
        )}
        {loading && (
          <div className="shimmer" style={{ height: '66px', borderRadius: '10px' }} />
        )}
      </div>

      {/* â”€â”€ Error â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
      {error && (
        <div style={{ padding: '18px 20px', borderRadius: '12px', background: 'var(--red-dim)', border: '1px solid rgba(255,69,96,0.2)', marginBottom: '28px' }}>
          <p style={{ color: 'var(--red)', fontSize: '14px' }}>âš  {error}</p>
        </div>
      )}

      {/* â”€â”€ Stat Cards â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
      {loading ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '24px' }}>
          {[...Array(4)].map((_, i) => (
            <div key={i} className="glass-card shimmer" style={{ height: '120px' }} />
          ))}
        </div>
      ) : stats && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '24px' }}>
          <StatCard label="Total Validations" value={formatNumber(stats.total_validations)} sub="All time" accent="cyan" delay={0} icon={<ShieldCheck size={16} />} />
          <StatCard label="Success Rate" value={`${(stats.success_rate ?? 0).toFixed(1)}%`} sub={`${formatNumber(stats.passed)} passed`} accent="green" delay={80} icon={<Gauge size={16} />} />
          <StatCard label="Failed" value={formatNumber(stats.failed)} sub="Violations detected" accent="red" delay={160} icon={<AlertTriangle size={16} />} />
          <StatCard label="Avg Latency" value={formatLatency(stats.avg_latency_ms)} sub="Per validation" accent="amber" delay={240} icon={<Activity size={16} />} />
        </div>
      )}

      {/* â”€â”€ Main: Area chart + Right panel â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
      {!loading && daily.length > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 280px', gap: '16px', marginBottom: '16px' }}>

          {/* Area chart */}
          <div className="glass-card fade-up-2" style={{ padding: '24px' }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '20px' }}>
              <div>
                <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--text-muted)', letterSpacing: '0.1em', marginBottom: '4px' }}>
                  VALIDATION TREND
                </p>
                <p style={{ fontFamily: 'Syne, sans-serif', fontWeight: 700, fontSize: '16px', color: 'var(--text-primary)' }}>
                  Last 14 days
                </p>
              </div>
              <div style={{ display: 'flex', gap: '16px' }}>
                {[{ color: 'var(--green)', label: 'Passed' }, { color: 'var(--red)', label: 'Failed' }].map(l => (
                  <div key={l.label} style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                    <span style={{ width: 8, height: 8, borderRadius: '2px', background: l.color, display: 'inline-block' }} />
                    <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '10px', color: 'var(--text-muted)' }}>
                      {l.label}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={chartData} margin={{ top: 5, right: 8, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="passedGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--green)" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="var(--green)" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="failedGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--red)" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="var(--red)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                <XAxis dataKey="date" tick={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} />
                <Tooltip content={<ChartTooltip />} />
                <Area type="monotone" dataKey="passed" stroke="var(--green)" strokeWidth={2} fill="url(#passedGrad)" name="passed" />
                <Area type="monotone" dataKey="failed" stroke="var(--red)" strokeWidth={2} fill="url(#failedGrad)" name="failed" />
              </AreaChart>
            </ResponsiveContainer>

            {/* Latency mini-bars strip */}
            <div style={{ marginTop: '16px', paddingTop: '14px', borderTop: '1px solid var(--border-subtle)' }}>
              <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '10px', color: 'var(--text-muted)', letterSpacing: '0.1em', marginBottom: '8px' }}>
                AVG LATENCY (ms)
              </p>
              <div style={{ display: 'flex', alignItems: 'flex-end', gap: '4px', height: '36px' }}>
                {chartData.map((d, i) => (
                  <div
                    key={i}
                    title={`${d.date}: ${d.latency}ms`}
                    style={{
                      flex: 1, minWidth: '4px',
                      height: `${Math.max(8, (d.latency / maxLatency) * 100)}%`,
                      background: 'var(--amber)',
                      borderRadius: '2px 2px 0 0',
                      opacity: 0.55,
                      cursor: 'default',
                    }}
                  />
                ))}
              </div>
            </div>
          </div>

          {/* â”€â”€ Right column â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>

            {/* Quota ring card */}
            {stats && (
              <div className="glass-card fade-up-2" style={{ padding: '20px 22px', display: 'flex', alignItems: 'center', gap: '18px' }}>
                <QuotaRing pct={stats.quota_percentage} color={quotaColor} />
                <div style={{ minWidth: 0 }}>
                  <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '10px', color: 'var(--text-muted)', letterSpacing: '0.1em', marginBottom: '6px' }}>
                    MONTHLY QUOTA
                  </p>
                  <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '20px', fontWeight: 700, color: quotaColor, lineHeight: 1 }}>
                    {formatNumber(stats.quota_used)}
                  </p>
                  <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '10px', color: 'var(--text-muted)', marginTop: '4px' }}>
                    of {formatNumber(stats.quota_total)} used
                  </p>
                  {stats.quota_percentage > 80 && (
                    <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '10px', color: 'var(--red)', marginTop: '6px' }}>
                      âš  Near limit
                    </p>
                  )}
                </div>
              </div>
            )}

            {/* Quick access card */}
            <div className="glass-card fade-up-3" style={{ padding: '18px', flex: 1 }}>
              <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '10px', color: 'var(--text-muted)', letterSpacing: '0.1em', marginBottom: '12px' }}>
                QUICK ACCESS
              </p>
              {[
                { label: 'Run Validation', href: '/dashboard/validate', icon: <Zap size={13} />, color: 'var(--cyan)', bg: 'var(--cyan-dim)' },
                { label: 'Analytics', href: '/dashboard/analytics', icon: <BarChart2 size={13} />, color: 'var(--purple)', bg: 'rgba(167,139,250,0.1)' },
                { label: 'History', href: '/dashboard/history', icon: <Clock size={13} />, color: 'var(--amber)', bg: 'var(--amber-dim)' },
              ].map(link => (
                <Link
                  key={link.href}
                  href={link.href}
                  style={{
                    display: 'flex', alignItems: 'center', gap: '10px',
                    padding: '10px 12px', borderRadius: '8px',
                    textDecoration: 'none', color: 'var(--text-secondary)',
                    fontSize: '13px', fontFamily: 'Syne, sans-serif', fontWeight: 600,
                    background: 'rgba(255,255,255,0.02)',
                    border: '1px solid transparent',
                    marginBottom: '6px',
                  }}
                >
                  <span style={{
                    width: 28, height: 28, borderRadius: '7px',
                    background: link.bg, color: link.color,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    flexShrink: 0,
                  }}>
                    {link.icon}
                  </span>
                  {link.label}
                  <ArrowRight size={12} style={{ marginLeft: 'auto', color: link.color, opacity: 0.5 }} />
                </Link>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* â”€â”€ Bottom: validations feed + violations sidebar â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
      <div style={{ display: 'grid', gridTemplateColumns: violations.length > 0 ? '1fr 256px' : '1fr', gap: '16px' }}>

        {/* Recent validations */}
        <div className="glass-card fade-up-4" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '18px' }}>
            <div>
              <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--text-muted)', letterSpacing: '0.1em', marginBottom: '4px' }}>
                RECENT ACTIVITY
              </p>
              <p style={{ fontFamily: 'Syne, sans-serif', fontWeight: 700, fontSize: '15px', color: 'var(--text-primary)' }}>
                Latest validations
              </p>
            </div>
            <Link href="/dashboard/history" style={{ textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '12px', color: 'var(--cyan)', fontWeight: 600, fontFamily: 'Syne, sans-serif' }}>
              View all <ArrowRight size={12} />
            </Link>
          </div>

          {loading ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {[...Array(4)].map((_, i) => <div key={i} className="shimmer" style={{ height: '48px', borderRadius: '8px' }} />)}
            </div>
          ) : recent.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
              <ShieldCheck size={32} style={{ margin: '0 auto 12px', opacity: 0.3 }} />
              <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '12px' }}>No validations yet. Start validating!</p>
            </div>
          ) : (
            <>
              {/* Column headers */}
              <div style={{
                display: 'grid', gridTemplateColumns: '72px 1fr 64px 60px 72px 92px',
                gap: '10px', padding: '0 14px 8px',
                borderBottom: '1px solid var(--border-subtle)', marginBottom: '8px',
              }}>
                {['STATUS', 'ID', 'VIOLATIONS', 'CONF', 'LATENCY', 'TIME'].map(h => (
                  <span key={h} style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '9px', color: 'var(--text-muted)', letterSpacing: '0.1em' }}>
                    {h}
                  </span>
                ))}
              </div>

              {/* Rows */}
              {recent.map((r) => {
                const rowAccent = r.status === 'passed' ? 'var(--green)' : r.status === 'failed' ? 'var(--red)' : 'var(--amber)';
                return (
                  <div
                    key={r.id}
                    style={{
                      display: 'grid', gridTemplateColumns: '72px 1fr 64px 60px 72px 92px',
                      gap: '10px', alignItems: 'center',
                      padding: '11px 14px', borderRadius: '8px',
                      borderLeft: `3px solid ${rowAccent}`,
                      background: 'rgba(255,255,255,0.02)',
                      marginBottom: '5px',
                    }}
                  >
                    <span className={r.status === 'passed' ? 'badge-valid' : r.status === 'failed' ? 'badge-invalid' : 'badge-warn'}>
                      {r.status.toUpperCase()}
                    </span>
                    <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '10px', color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {(r.validation_id ?? r.id ?? '').slice(0, 14)}â€¦
                    </span>
                    <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '12px', fontWeight: 600, color: r.violations_count > 0 ? 'var(--red)' : 'var(--green)', textAlign: 'right' }}>
                      {r.violations_count > 0 ? `${r.violations_count} Ã—` : 'â€”'}
                    </span>
                    <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--text-secondary)', textAlign: 'right' }}>
                      {r.confidence_score != null ? `${(r.confidence_score * 100).toFixed(0)}%` : 'â€”'}
                    </span>
                    <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--amber)', textAlign: 'right' }}>
                      {formatLatency(r.latency_ms)}
                    </span>
                    <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '10px', color: 'var(--text-muted)', textAlign: 'right' }}>
                      {formatDateTime(r.created_at)}
                    </span>
                  </div>
                );
              })}
            </>
          )}
        </div>

        {/* Top violations mini-sidebar */}
        {violations.length > 0 && (
          <div className="glass-card fade-up-4" style={{ padding: '20px' }}>
            <div style={{ marginBottom: '16px' }}>
              <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--text-muted)', letterSpacing: '0.1em', marginBottom: '4px' }}>
                TOP VIOLATIONS
              </p>
              <p style={{ fontFamily: 'Syne, sans-serif', fontWeight: 700, fontSize: '14px', color: 'var(--text-primary)' }}>
                Rule breakdown
              </p>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '16px' }}>
              {violations.map((v, i) => {
                const barColor = i === 0 ? 'var(--red)' : i <= 2 ? 'var(--amber)' : 'var(--cyan)';
                return (
                  <div key={v.rule_name}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '5px' }}>
                      <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '10px', color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '170px' }}>
                        {v.rule_name}
                      </span>
                      <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: barColor, fontWeight: 700, flexShrink: 0, marginLeft: '8px' }}>
                        {v.count}
                      </span>
                    </div>
                    <div style={{ height: '4px', background: 'rgba(255,255,255,0.06)', borderRadius: '2px', overflow: 'hidden' }}>
                      <div style={{
                        height: '100%',
                        width: `${Math.max(4, (v.count / maxViol) * 100)}%`,
                        background: barColor, borderRadius: '2px', opacity: 0.8,
                        transition: 'width 0.6s cubic-bezier(0.34,1.56,0.64,1)',
                      }} />
                    </div>
                  </div>
                );
              })}
            </div>

            <Link
              href="/dashboard/analytics"
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '5px',
                padding: '9px', borderRadius: '8px',
                background: 'var(--cyan-dim)', border: '1px solid rgba(0,216,255,0.15)',
                textDecoration: 'none', color: 'var(--cyan)',
                fontFamily: 'Syne, sans-serif', fontSize: '12px', fontWeight: 700,
              }}
            >
              Full analytics <BarChart2 size={12} />
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
