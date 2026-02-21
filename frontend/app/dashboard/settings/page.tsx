'use client';

import { useEffect, useState, useCallback } from 'react';
import { useAuth } from '@/lib/auth';
import { createAuthApi, getApiError } from '@/lib/api';
import type { UsageStats } from '@/lib/types';
import { formatNumber, tierColor } from '@/lib/utils';
import { Settings, Zap, Shield, RefreshCw, ExternalLink, LogOut, CreditCard } from 'lucide-react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

const TIER_LIMITS: Record<string, { rpm: number; quota: string; features: string[] }> = {
  free: {
    rpm: 10,
    quota: '1,000/mo',
    features: ['10 req/min', '1,000 validations/month', 'Schema validation', 'Basic rules'],
  },
  startup: {
    rpm: 30,
    quota: '10,000/mo',
    features: ['30 req/min', '10,000 validations/month', 'Auto-correction', 'Anomaly detection', 'Confidence scoring'],
  },
  business: {
    rpm: 100,
    quota: '100,000/mo',
    features: ['100 req/min', '100,000 validations/month', 'All Startup features', 'Priority support', 'Analytics API'],
  },
  enterprise: {
    rpm: 500,
    quota: '1M+/mo',
    features: ['500 req/min', 'Unlimited validations', 'All Business features', 'Dedicated support', 'SLA guarantee', 'Custom integrations'],
  },
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8888';

export default function SettingsPage() {
  const { apiKey, orgName, tier, logout } = useAuth();
  const router = useRouter();
  const [usage, setUsage] = useState<UsageStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchUsage = useCallback(async () => {
    if (!apiKey) return;
    setError('');
    try {
      const api = createAuthApi(apiKey);
      const data = await api.usageStats();
      setUsage(data);
    } catch (err) {
      setError(getApiError(err));
    } finally {
      setLoading(false);
    }
  }, [apiKey]);

  useEffect(() => { fetchUsage(); }, [fetchUsage]);

  function handleLogout() {
    logout();
    router.push('/login');
  }

  const currentTier = TIER_LIMITS[tier ?? 'free'] ?? TIER_LIMITS.free;
  const color = tierColor(tier ?? 'free');

  return (
    <div style={{ padding: '40px', maxWidth: '800px' }}>
      {/* Header */}
      <div className="fade-up" style={{ marginBottom: '40px' }}>
        <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--text-muted)', letterSpacing: '0.1em', marginBottom: '6px' }}>
          CONFIGURATION
        </p>
        <h1 style={{ fontFamily: 'Syne, sans-serif', fontWeight: 800, fontSize: '28px', letterSpacing: '-0.02em', color: 'var(--text-primary)' }}>
          Settings
        </h1>
      </div>

      {/* Organization card */}
      <div className="glass-card fade-up-1" style={{ padding: '24px', marginBottom: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '20px' }}>
          <Zap size={14} color="var(--cyan)" />
          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--text-muted)', letterSpacing: '0.08em' }}>
            ORGANIZATION
          </p>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
          <div>
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '10px', color: 'var(--text-muted)', letterSpacing: '0.08em', marginBottom: '6px' }}>
              ORG NAME
            </p>
            <p style={{ fontSize: '15px', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'Syne, sans-serif' }}>
              {orgName ?? '—'}
            </p>
          </div>
          <div>
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '10px', color: 'var(--text-muted)', letterSpacing: '0.08em', marginBottom: '6px' }}>
              CURRENT PLAN
            </p>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{
                fontFamily: 'JetBrains Mono, monospace', fontWeight: 700, fontSize: '12px',
                color, background: `${color}18`, border: `1px solid ${color}33`,
                padding: '4px 10px', borderRadius: '6px', letterSpacing: '0.1em',
              }}>
                {(tier ?? 'FREE').toUpperCase()}
              </span>
            </div>
          </div>
          <div>
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '10px', color: 'var(--text-muted)', letterSpacing: '0.08em', marginBottom: '6px' }}>
              RATE LIMIT
            </p>
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '15px', fontWeight: 600, color: 'var(--cyan)' }}>
              {currentTier.rpm} req/min
            </p>
          </div>
          <div>
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '10px', color: 'var(--text-muted)', letterSpacing: '0.08em', marginBottom: '6px' }}>
              MONTHLY QUOTA
            </p>
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '15px', fontWeight: 600, color: 'var(--green)' }}>
              {currentTier.quota}
            </p>
          </div>
        </div>

        {/* Plan features */}
        <div style={{ marginTop: '20px', paddingTop: '20px', borderTop: '1px solid var(--border-subtle)' }}>
          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '10px', color: 'var(--text-muted)', letterSpacing: '0.08em', marginBottom: '12px' }}>
            PLAN INCLUDES
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
            {currentTier.features.map(f => (
              <span key={f} style={{
                fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--text-secondary)',
                background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)',
                padding: '4px 10px', borderRadius: '4px',
              }}>{f}</span>
            ))}
          </div>
        </div>

        {/* Billing link */}
        <div style={{ marginTop: '20px', paddingTop: '20px', borderTop: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <p style={{ fontFamily: 'Syne, sans-serif', fontWeight: 700, fontSize: '14px', color: 'var(--text-primary)', marginBottom: '3px' }}>
              Subscription &amp; Billing
            </p>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Upgrade plan, manage invoices, or cancel subscription.</p>
          </div>
          <Link href="/dashboard/billing" style={{ textDecoration: 'none' }}>
            <button className="tc-btn-ghost" style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', padding: '9px 14px', whiteSpace: 'nowrap' }}>
              <CreditCard size={13} />
              Manage Billing
            </button>
          </Link>
        </div>
      </div>

      {/* Usage card */}
      <div className="glass-card fade-up-2" style={{ padding: '24px', marginBottom: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Settings size={14} color="var(--amber)" />
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--text-muted)', letterSpacing: '0.08em' }}>
              QUOTA USAGE
            </p>
          </div>
          <button onClick={fetchUsage} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}>
            <RefreshCw size={13} />
          </button>
        </div>

        {loading ? (
          <div style={{ height: '80px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <RefreshCw size={20} color="var(--text-muted)" style={{ animation: 'spin 0.8s linear infinite' }} />
          </div>
        ) : error ? (
          <p style={{ color: 'var(--red)', fontSize: '13px' }}>⚠ {error}</p>
        ) : usage && (
          <>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px', marginBottom: '20px' }}>
              {[
                { label: 'USED', value: formatNumber(usage.quota_used), color: 'var(--cyan)' },
                { label: 'TOTAL', value: formatNumber(usage.quota_total), color: 'var(--text-secondary)' },
                { label: 'REMAINING', value: formatNumber(usage.quota_total - usage.quota_used), color: 'var(--green)' },
              ].map(({ label, value, color: c }) => (
                <div key={label} style={{ textAlign: 'center', background: 'var(--bg-void)', borderRadius: '8px', padding: '16px' }}>
                  <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '22px', fontWeight: 700, color: c }}>{value}</p>
                  <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '9px', color: 'var(--text-muted)', marginTop: '4px', letterSpacing: '0.1em' }}>{label}</p>
                </div>
              ))}
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '10px', color: 'var(--text-muted)' }}>Quota utilization</span>
                <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', fontWeight: 700, color: usage.quota_percentage > 80 ? 'var(--red)' : 'var(--cyan)' }}>
                  {(usage.quota_percentage ?? 0).toFixed(1)}%
                </span>
              </div>
              <div className="tc-progress-bar" style={{ height: '6px' }}>
                <div className="tc-progress-fill" style={{
                  width: `${Math.min(usage.quota_percentage, 100)}%`,
                  background: usage.quota_percentage > 80
                    ? 'linear-gradient(90deg, var(--amber), var(--red))'
                    : 'linear-gradient(90deg, var(--cyan), var(--green))',
                }} />
              </div>
            </div>
          </>
        )}
      </div>

      {/* API Info */}
      <div className="glass-card fade-up-3" style={{ padding: '24px', marginBottom: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
          <Shield size={14} color="var(--purple)" />
          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--text-muted)', letterSpacing: '0.08em' }}>
            API ENDPOINT
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <code style={{
            flex: 1, fontFamily: 'JetBrains Mono, monospace', fontSize: '13px',
            background: 'var(--bg-void)', border: '1px solid var(--border-subtle)',
            borderRadius: '8px', padding: '10px 14px', color: 'var(--cyan)',
          }}>
            {API_BASE}
          </code>
          <a href={`${API_BASE}/docs`} target="_blank" rel="noopener noreferrer" style={{ textDecoration: 'none' }}>
            <button className="tc-btn-ghost" style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', padding: '10px 14px', whiteSpace: 'nowrap' }}>
              <ExternalLink size={13} />
              API Docs
            </button>
          </a>
        </div>

        <div style={{ marginTop: '16px', fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--text-muted)', lineHeight: 2 }}>
          <p>Auth: <span style={{ color: 'var(--cyan)' }}>X-API-Key</span> header</p>
          <p>Validation: <span style={{ color: 'var(--green)' }}>POST {API_BASE}/v1/validate</span></p>
          <p>Analytics: <span style={{ color: 'var(--green)' }}>GET {API_BASE}/v1/analytics/overview</span></p>
        </div>
      </div>

      {/* Danger zone */}
      <div style={{ padding: '20px', borderRadius: '12px', border: '1px solid rgba(255,69,96,0.2)', background: 'rgba(255,69,96,0.04)' }}>
        <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--red)', letterSpacing: '0.1em', marginBottom: '12px' }}>
          DANGER ZONE
        </p>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <p style={{ fontFamily: 'Syne, sans-serif', fontWeight: 700, fontSize: '14px', color: 'var(--text-primary)', marginBottom: '4px' }}>
              Sign out
            </p>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Remove your API key from this device
            </p>
          </div>
          <button onClick={handleLogout} className="tc-btn-danger" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <LogOut size={13} />
            Sign Out
          </button>
        </div>
      </div>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
