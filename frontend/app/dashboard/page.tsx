'use client';

import { useEffect, useState, useCallback } from 'react';
import { useAuth } from '@/lib/auth';
import { createAuthApi, getApiError } from '@/lib/api';
import type { OverviewStats, DailyStat, ValidationHistoryItem, TopViolation } from '@/lib/types';
import { formatNumber, formatLatency, formatDateTime } from '@/lib/utils';
import StatCard from '@/components/StatCard';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, Cell
} from 'recharts';
import { ShieldCheck, AlertTriangle, Activity, Gauge, RefreshCw, ArrowRight } from 'lucide-react';
import Link from 'next/link';

interface CustomTooltipProps {
  active?: boolean;
  payload?: { color: string; name: string; value: number }[];
  label?: string;
}

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: 'var(--bg-elevated)', border: '1px solid var(--border-default)',
      borderRadius: '8px', padding: '12px 16px', fontFamily: 'JetBrains Mono, monospace',
    }}>
      <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '8px' }}>{label}</p>
      {payload.map((p) => (
        <div key={p.name} style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '4px' }}>
          <span style={{ width: '8px', height: '8px', borderRadius: '2px', background: p.color, display: 'inline-block' }} />
          <span style={{ fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'capitalize' }}>{p.name}:</span>
          <span style={{ fontSize: '12px', color: 'var(--text-primary)', fontWeight: 600 }}>{p.value}</span>
        </div>
      ))}
    </div>
  );
}

export default function DashboardPage() {
  const { apiKey } = useAuth();
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

  return (
    <div style={{ padding: '40px', maxWidth: '1400px' }}>
      {/* Header */}
      <div className="fade-up" style={{ marginBottom: '40px', display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div>
          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--text-muted)', letterSpacing: '0.1em', marginBottom: '6px' }}>
            OVERVIEW
          </p>
          <h1 style={{ fontFamily: 'Syne, sans-serif', fontWeight: 800, fontSize: '28px', letterSpacing: '-0.02em', color: 'var(--text-primary)' }}>
            Dashboard
          </h1>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {lastRefresh && (
            <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--text-muted)' }}>
              Updated {lastRefresh.toLocaleTimeString()}
            </span>
          )}
          <button onClick={fetchData} className="tc-btn-ghost" style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', padding: '8px 14px' }}>
            <RefreshCw size={13} />
            Refresh
          </button>
        </div>
      </div>

      {loading ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '32px' }}>
          {[...Array(4)].map((_, i) => (
            <div key={i} className="glass-card shimmer" style={{ height: '120px' }} />
          ))}
        </div>
      ) : error ? (
        <div style={{ padding: '20px', borderRadius: '12px', background: 'var(--red-dim)', border: '1px solid rgba(255,69,96,0.2)', marginBottom: '32px' }}>
          <p style={{ color: 'var(--red)', fontSize: '14px' }}>⚠ {error}</p>
        </div>
      ) : stats && (
        <>
          {/* ── Stat Cards ─────────────────────────────────────────── */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '32px' }}>
            <StatCard
              label="Total Validations"
              value={formatNumber(stats.total_validations)}
              sub="All time"
              accent="cyan"
              delay={0}
              icon={<ShieldCheck size={16} />}
            />
            <StatCard
              label="Success Rate"
              value={`${(stats.success_rate ?? 0).toFixed(1)}%`}
              sub={`${formatNumber(stats.passed)} passed`}
              accent="green"
              delay={100}
              icon={<Gauge size={16} />}
            />
            <StatCard
              label="Failed"
              value={formatNumber(stats.failed)}
              sub="Violations detected"
              accent="red"
              delay={200}
              icon={<AlertTriangle size={16} />}
            />
            <StatCard
              label="Avg Latency"
              value={formatLatency(stats.avg_latency_ms)}
              sub="Per validation"
              accent="amber"
              delay={300}
              icon={<Activity size={16} />}
            />
          </div>

          {/* ── Quota Bar ──────────────────────────────────────────── */}
          <div className="glass-card fade-up-1" style={{ padding: '20px 24px', marginBottom: '32px', display: 'flex', alignItems: 'center', gap: '24px' }}>
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--text-muted)', letterSpacing: '0.08em' }}>MONTHLY QUOTA</span>
                <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--text-secondary)' }}>
                  {formatNumber(stats.quota_used)} / {formatNumber(stats.quota_total)}
                </span>
              </div>
              <div className="tc-progress-bar">
                <div className="tc-progress-fill" style={{
                  width: `${Math.min(stats.quota_percentage, 100)}%`,
                  background: stats.quota_percentage > 80
                    ? 'var(--red)'
                    : stats.quota_percentage > 60
                      ? 'var(--amber)'
                      : 'var(--cyan)',
                }} />
              </div>
            </div>
            <div style={{ textAlign: 'right', flexShrink: 0 }}>
              <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '20px', fontWeight: 700, color: 'var(--cyan)' }}>
                {stats.quota_percentage.toFixed(1)}%
              </p>
              <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '10px', color: 'var(--text-muted)' }}>USED</p>
            </div>
          </div>
        </>
      )}

      {/* ── Charts Row ─────────────────────────────────────────────── */}
      {daily.length > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '16px', marginBottom: '32px' }}>
          {/* Area chart */}
          <div className="glass-card fade-up-2" style={{ padding: '24px' }}>
            <div style={{ marginBottom: '20px' }}>
              <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--text-muted)', letterSpacing: '0.1em', marginBottom: '4px' }}>
                VALIDATION TREND
              </p>
              <p style={{ fontFamily: 'Syne, sans-serif', fontWeight: 700, fontSize: '15px', color: 'var(--text-primary)' }}>
                Last 14 days
              </p>
            </div>
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="passedGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--green)" stopOpacity={0.2} />
                    <stop offset="95%" stopColor="var(--green)" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="failedGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--red)" stopOpacity={0.2} />
                    <stop offset="95%" stopColor="var(--red)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                <XAxis dataKey="date" tick={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} />
                <Tooltip content={<CustomTooltip />} />
                <Area type="monotone" dataKey="passed" stroke="var(--green)" strokeWidth={2} fill="url(#passedGrad)" name="passed" />
                <Area type="monotone" dataKey="failed" stroke="var(--red)" strokeWidth={2} fill="url(#failedGrad)" name="failed" />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* Bar chart - latency */}
          <div className="glass-card fade-up-3" style={{ padding: '24px' }}>
            <div style={{ marginBottom: '20px' }}>
              <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--text-muted)', letterSpacing: '0.1em', marginBottom: '4px' }}>
                AVG LATENCY
              </p>
              <p style={{ fontFamily: 'Syne, sans-serif', fontWeight: 700, fontSize: '15px', color: 'var(--text-primary)' }}>
                ms per day
              </p>
            </div>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                <XAxis dataKey="date" tick={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="latency" fill="var(--cyan)" opacity={0.8} radius={[3, 3, 0, 0]} name="latency" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* ── Top Violations ──────────────────────────────────────────── */}
      {violations.length > 0 && (
        <div className="glass-card fade-up-3" style={{ padding: '24px', marginBottom: '32px' }}>
          <div style={{ marginBottom: '20px' }}>
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--text-muted)', letterSpacing: '0.1em', marginBottom: '4px' }}>
              VIOLATION BREAKDOWN
            </p>
            <p style={{ fontFamily: 'Syne, sans-serif', fontWeight: 700, fontSize: '15px', color: 'var(--text-primary)' }}>
              Top rule violations
            </p>
          </div>
          <ResponsiveContainer width="100%" height={Math.max(140, violations.length * 36)}>
            <BarChart data={violations} layout="vertical" margin={{ top: 0, right: 24, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" horizontal={false} />
              <XAxis type="number" tick={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} />
              <YAxis
                type="category"
                dataKey="rule_name"
                width={160}
                tick={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, fill: 'var(--text-secondary)' }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                content={({ active, payload }) => {
                  if (!active || !payload?.length) return null;
                  return (
                    <div style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-default)', borderRadius: '8px', padding: '10px 14px' }}>
                      <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px' }}>{payload[0].payload.rule_name}</p>
                      <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '13px', color: 'var(--red)', fontWeight: 700 }}>{payload[0].value} violations</p>
                    </div>
                  );
                }}
              />
              <Bar dataKey="count" radius={[0, 4, 4, 0]} name="violations">
                {violations.map((_, idx) => (
                  <Cell key={idx} fill={idx === 0 ? 'var(--red)' : idx <= 2 ? 'var(--amber)' : 'var(--cyan)'} opacity={0.85} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* ── Recent Validations ─────────────────────────────────────── */}
      <div className="glass-card fade-up-4" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
          <div>
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--text-muted)', letterSpacing: '0.1em', marginBottom: '4px' }}>
              RECENT ACTIVITY
            </p>
            <p style={{ fontFamily: 'Syne, sans-serif', fontWeight: 700, fontSize: '15px', color: 'var(--text-primary)' }}>
              Latest validations
            </p>
          </div>
          <Link href="/dashboard/history" style={{ textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '12px', color: 'var(--cyan)', fontWeight: 600 }}>
            View all <ArrowRight size={12} />
          </Link>
        </div>

        {recent.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
            <ShieldCheck size={32} style={{ margin: '0 auto 12px', opacity: 0.3 }} />
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '12px' }}>No validations yet. Start validating!</p>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  {['ID', 'Status', 'Violations', 'Confidence', 'Latency', 'Time'].map(h => (
                    <th key={h} style={{
                      textAlign: 'left', padding: '8px 12px',
                      fontFamily: 'JetBrains Mono, monospace', fontSize: '10px',
                      color: 'var(--text-muted)', letterSpacing: '0.1em',
                      borderBottom: '1px solid var(--border-subtle)',
                    }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {recent.map((r, i) => (
                  <tr key={r.id} style={{ borderBottom: i < recent.length - 1 ? '1px solid var(--border-subtle)' : 'none' }}>
                    <td style={{ padding: '12px 12px', fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--text-muted)' }}>
                      {r.validation_id?.slice(0, 12)}...
                    </td>
                    <td style={{ padding: '12px 12px' }}>
                      <span className={r.status === 'passed' ? 'badge-valid' : r.status === 'failed' ? 'badge-invalid' : 'badge-warn'}>
                        {r.status.toUpperCase()}
                      </span>
                    </td>
                    <td style={{ padding: '12px 12px', fontFamily: 'JetBrains Mono, monospace', fontSize: '12px', color: r.violations_count > 0 ? 'var(--red)' : 'var(--green)' }}>
                      {r.violations_count}
                    </td>
                    <td style={{ padding: '12px 12px', fontFamily: 'JetBrains Mono, monospace', fontSize: '12px', color: 'var(--text-secondary)' }}>
                      {r.confidence_score != null ? `${(r.confidence_score * 100).toFixed(0)}%` : '—'}
                    </td>
                    <td style={{ padding: '12px 12px', fontFamily: 'JetBrains Mono, monospace', fontSize: '12px', color: 'var(--amber)' }}>
                      {formatLatency(r.latency_ms)}
                    </td>
                    <td style={{ padding: '12px 12px', fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--text-muted)' }}>
                      {formatDateTime(r.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
