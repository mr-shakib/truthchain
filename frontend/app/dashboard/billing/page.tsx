'use client';

import { useEffect, useState, useCallback } from 'react';
import { useAuth } from '@/lib/auth';
import { createBillingApi, getApiError } from '@/lib/billing';
import type { SubscriptionDetails, InvoiceItem } from '@/lib/types';
import {
  CheckCircle2, XCircle, RefreshCw,
  ChevronUp, ChevronDown, Receipt, AlertTriangle, Star,
  Zap, Rocket, Building2, Crown,
} from 'lucide-react';

// ─── Static plan catalogue — renders immediately, no API needed ──────────────

const PLANS = [
  {
    tier: 'free' as const,
    label: 'Free',
    price_display: '$0 / month',
    monthly_quota: 1000,
    rpm: 10,
    color: '#4B5563',
    Icon: Zap,
    features: ['10 req / min', '1,000 validations / mo', 'Schema validation', 'Basic rules'],
  },
  {
    tier: 'startup' as const,
    label: 'Startup',
    price_display: '$29 / month',
    monthly_quota: 10000,
    rpm: 30,
    color: '#00D8FF',
    Icon: Rocket,
    features: ['30 req / min', '10,000 validations / mo', 'Auto-correction', 'Anomaly detection', 'Confidence scoring'],
    popular: true,
  },
  {
    tier: 'business' as const,
    label: 'Business',
    price_display: '$99 / month',
    monthly_quota: 100000,
    rpm: 100,
    color: '#A78BFA',
    Icon: Building2,
    features: ['100 req / min', '100,000 validations / mo', 'All Startup features', 'Priority support', 'Analytics API'],
  },
  {
    tier: 'enterprise' as const,
    label: 'Enterprise',
    price_display: '$499 / month',
    monthly_quota: 1000000,
    rpm: 500,
    color: '#FFC945',
    Icon: Crown,
    features: ['500 req / min', '1M+ validations / mo', 'All Business features', 'Dedicated support', 'SLA guarantee', 'Custom integrations'],
  },
];

const TIER_ORDER = ['free', 'startup', 'business', 'enterprise'];

const STATUS_COLORS: Record<string, string> = {
  active: '#00FF88', trialing: '#00D8FF', past_due: '#FFC945', canceled: '#FF4560',
};

function fmt(n: number) { return n.toLocaleString(); }
function fmtDate(s: string | null) {
  if (!s) return '—';
  return new Date(s).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
}

// ── Plan card ────────────────────────────────────────────────────────────

type PlanDef = (typeof PLANS)[number];

function PlanCard({
  plan,
  currentTier,
  onSelect,
  busy,
}: {
  plan: PlanDef;
  currentTier: string;
  onSelect: (tier: string) => void;
  busy: string | null;
}) {
  const isCurrent = plan.tier === currentTier;
  const rankPlan = TIER_ORDER.indexOf(plan.tier);
  const rankCurrent = TIER_ORDER.indexOf(currentTier);
  const isUpgrade = rankPlan > rankCurrent;
  const loading = busy === plan.tier;
  const { color, Icon } = plan;

  return (
    <div style={{
      position: 'relative',
      borderRadius: '16px',
      border: `1px solid ${isCurrent ? color : 'rgba(255,255,255,0.08)'}`,
      background: isCurrent ? `${color}0F` : '#0C101A',
      padding: '28px 24px 24px',
      display: 'flex', flexDirection: 'column', gap: '20px',
      transition: 'border-color 0.2s, box-shadow 0.2s',
      boxShadow: isCurrent ? `0 0 24px ${color}28` : 'none',
      minHeight: '380px',
    }}>
      {/* Popular badge */}
      {'popular' in plan && plan.popular && (
        <div style={{
          position: 'absolute', top: '-13px', left: '50%', transform: 'translateX(-50%)',
          background: '#00D8FF', color: '#06080F',
          fontFamily: 'JetBrains Mono, monospace', fontSize: '10px', fontWeight: 700,
          letterSpacing: '0.1em', padding: '3px 12px', borderRadius: '20px',
          display: 'flex', alignItems: 'center', gap: '4px', whiteSpace: 'nowrap',
        }}>
          <Star size={9} fill="currentColor" /> MOST POPULAR
        </div>
      )}

      {/* Icon + current badge */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div style={{
          width: '40px', height: '40px', borderRadius: '10px',
          background: `${color}18`, border: `1px solid ${color}30`,
          display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
        }}>
          <Icon size={18} color={color} />
        </div>
        {isCurrent && (
          <span style={{
            fontFamily: 'JetBrains Mono, monospace', fontSize: '10px', fontWeight: 700,
            color, background: `${color}18`, border: `1px solid ${color}40`,
            padding: '3px 10px', borderRadius: '20px', letterSpacing: '0.08em',
          }}>✓ CURRENT</span>
        )}
      </div>

      {/* Name + price */}
      <div>
        <p style={{ fontFamily: 'Syne, sans-serif', fontWeight: 800, fontSize: '20px', color: '#E8EAED', letterSpacing: '-0.01em', marginBottom: '6px' }}>
          {plan.label}
        </p>
        <p style={{ fontFamily: 'Syne, sans-serif', fontWeight: 800, fontSize: '30px', color, letterSpacing: '-0.02em', lineHeight: 1 }}>
          {plan.price_display.split(' /')[0]}
          <span style={{ fontSize: '14px', fontWeight: 500, color: '#4B5563', marginLeft: '4px' }}>/mo</span>
        </p>
        <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: '#4B5563', marginTop: '6px' }}>
          {fmt(plan.monthly_quota)} validations · {plan.rpm} req/min
        </p>
      </div>

      {/* Features */}
      <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '9px', flex: 1 }}>
        {plan.features.map((f: string) => (
          <li key={f} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <CheckCircle2 size={13} color={color} strokeWidth={2.5} style={{ flexShrink: 0 }} />
            <span style={{ fontSize: '13px', color: '#8B95A8' }}>{f}</span>
          </li>
        ))}
      </ul>

      {/* CTA */}
      <button
        disabled={isCurrent || loading}
        onClick={() => onSelect(plan.tier)}
        style={{
          width: '100%', padding: '12px', borderRadius: '10px',
          border: isCurrent ? '1px solid rgba(255,255,255,0.08)' : isUpgrade ? 'none' : `1px solid ${color}`,
          background: isCurrent ? 'transparent' : isUpgrade ? color : 'transparent',
          color: isCurrent ? '#4B5563' : isUpgrade ? '#06080F' : color,
          fontFamily: 'Syne, sans-serif', fontWeight: 700, fontSize: '13px',
          cursor: isCurrent ? 'default' : 'pointer',
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px',
          transition: 'opacity 0.15s', opacity: loading ? 0.6 : 1,
          letterSpacing: '0.02em',
        }}
      >
        {loading ? (
          <><RefreshCw size={13} style={{ animation: 'spin 0.7s linear infinite' }} /> Processing…</>
        ) : isCurrent ? (
          'Current Plan'
        ) : isUpgrade ? (
          <><ChevronUp size={14} /> Upgrade to {plan.label}</>
        ) : (
          <><ChevronDown size={14} /> Switch to {plan.label}</>
        )}
      </button>
    </div>
  );
}

// ── Invoice row ────────────────────────────────────────────────────────────

function InvoiceRow({ inv }: { inv: InvoiceItem }) {
  const cc: Record<string, string> = { paid: '#00FF88', free: '#4B5563', pending: '#FFC945', failed: '#FF4560' };
  const c = cc[inv.status] ?? '#4B5563';
  return (
    <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
      <td style={{ padding: '13px 16px', fontFamily: 'JetBrains Mono, monospace', fontSize: '12px', color: '#4B5563' }}>{inv.id}</td>
      <td style={{ padding: '13px 16px', fontSize: '13px', color: '#8B95A8', textTransform: 'capitalize' }}>{inv.tier}</td>
      <td style={{ padding: '13px 16px', fontFamily: 'JetBrains Mono, monospace', fontSize: '13px', color: '#E8EAED', fontWeight: 600 }}>{inv.amount_display}</td>
      <td style={{ padding: '13px 16px' }}>
        <span style={{
          fontFamily: 'JetBrains Mono, monospace', fontSize: '10px', fontWeight: 700,
          color: c, background: `${c}18`, border: `1px solid ${c}30`,
          padding: '3px 9px', borderRadius: '20px', letterSpacing: '0.06em', textTransform: 'uppercase',
        }}>{inv.status}</span>
      </td>
      <td style={{ padding: '13px 16px', fontFamily: 'JetBrains Mono, monospace', fontSize: '12px', color: '#4B5563' }}>{fmtDate(inv.created_at)}</td>
    </tr>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────

export default function BillingPage() {
  const { apiKey, tier: authTier } = useAuth();

  const [sub, setSub] = useState<SubscriptionDetails | null>(null);
  const [invoices, setInvoices] = useState<InvoiceItem[]>([]);
  const [subLoading, setSubLoading] = useState(true);
  const [invoicesLoading, setInvoicesLoading] = useState(true);
  const [error, setError] = useState('');
  const [upgrading, setUpgrading] = useState<string | null>(null);
  const [upgradeMsg, setUpgradeMsg] = useState('');
  const [canceling, setCanceling] = useState(false);
  const [confirmCancel, setConfirmCancel] = useState(false);

  const currentTier = sub?.tier ?? authTier ?? 'free';
  const currentPlan = PLANS.find(p => p.tier === currentTier) ?? PLANS[0];

  const fetchSubscription = useCallback(async () => {
    if (!apiKey) { setSubLoading(false); return; }
    setSubLoading(true);
    try {
      const api = createBillingApi(apiKey);
      setSub(await api.subscription());
    } catch {
      // silent — plan cards still render from static data
    } finally {
      setSubLoading(false);
    }
  }, [apiKey]);

  const fetchInvoices = useCallback(async () => {
    if (!apiKey) { setInvoicesLoading(false); return; }
    setInvoicesLoading(true);
    try {
      const api = createBillingApi(apiKey);
      setInvoices(await api.invoices());
    } catch {
      // silent
    } finally {
      setInvoicesLoading(false);
    }
  }, [apiKey]);

  const fetchAll = useCallback(() => {
    fetchSubscription();
    fetchInvoices();
  }, [fetchSubscription, fetchInvoices]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  async function handleUpgrade(tier: string) {
    if (!apiKey) return;
    setUpgrading(tier);
    setUpgradeMsg('');
    setError('');
    try {
      const api = createBillingApi(apiKey);
      const res = await api.upgrade({ tier: tier as never });
      setUpgradeMsg(res.message);
      await fetchSubscription();
    } catch (err) {
      setError(getApiError(err));
    } finally {
      setUpgrading(null);
    }
  }

  async function handleCancel() {
    if (!apiKey) return;
    setCanceling(true);
    setError('');
    try {
      const api = createBillingApi(apiKey);
      const res = await api.cancel();
      setUpgradeMsg(res.message);
      setConfirmCancel(false);
      await fetchSubscription();
    } catch (err) {
      setError(getApiError(err));
    } finally {
      setCanceling(false);
    }
  }

  const statusColor = STATUS_COLORS[sub?.subscription_status ?? 'active'] ?? '#00FF88';
  const quotaPct = Math.min(sub?.quota_percentage ?? 0, 100);

  return (
    <div style={{ padding: '40px', maxWidth: '1200px' }}>
      {/* Header */}
      <div className="fade-up" style={{ marginBottom: '40px', display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div>
          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: '#4B5563', letterSpacing: '0.1em', marginBottom: '6px' }}>SUBSCRIPTION</p>
          <h1 style={{ fontFamily: 'Syne, sans-serif', fontWeight: 800, fontSize: '28px', letterSpacing: '-0.02em', color: '#E8EAED' }}>Billing &amp; Plans</h1>
        </div>
        <button onClick={fetchAll} className="tc-btn-ghost" style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', padding: '8px 14px' }}>
          <RefreshCw size={13} />Refresh
        </button>
      </div>

      {/* Success banner */}
      {upgradeMsg && (
        <div className="fade-up" style={{
          background: 'rgba(0,255,136,0.08)', border: '1px solid rgba(0,255,136,0.2)',
          borderRadius: '10px', padding: '12px 16px', marginBottom: '24px',
          display: 'flex', alignItems: 'center', gap: '8px',
          fontFamily: 'JetBrains Mono, monospace', fontSize: '13px', color: '#00FF88',
        }}>
          <CheckCircle2 size={14} />{upgradeMsg}
          <button onClick={() => setUpgradeMsg('')} style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer', color: '#4B5563', lineHeight: 1 }}>✕</button>
        </div>
      )}

      {/* Error banner */}
      {error && (
        <div className="fade-up" style={{
          background: 'rgba(255,69,96,0.08)', border: '1px solid rgba(255,69,96,0.2)',
          borderRadius: '10px', padding: '12px 16px', marginBottom: '24px',
          display: 'flex', alignItems: 'center', gap: '8px',
          fontFamily: 'JetBrains Mono, monospace', fontSize: '13px', color: '#FF4560',
        }}>
          <AlertTriangle size={14} />{error}
          <button onClick={() => setError('')} style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer', color: '#4B5563', lineHeight: 1 }}>✕</button>
        </div>
      )}

      {/* Subscription summary card */}
      <div className="glass-card fade-up-1" style={{ padding: '24px', marginBottom: '36px' }}>
        {subLoading ? (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '24px' }}>
            {[...Array(3)].map((_, i) => <div key={i} className="shimmer" style={{ height: '72px', borderRadius: '8px' }} />)}
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '24px', alignItems: 'center' }}>
            {/* Plan info */}
            <div>
              <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '10px', color: '#4B5563', letterSpacing: '0.08em', marginBottom: '8px' }}>ACTIVE PLAN</p>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div style={{
                  width: '36px', height: '36px', borderRadius: '10px',
                  background: `${currentPlan.color}18`, border: `1px solid ${currentPlan.color}30`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  <currentPlan.Icon size={16} color={currentPlan.color} />
                </div>
                <div>
                  <p style={{ fontFamily: 'Syne, sans-serif', fontWeight: 800, fontSize: '18px', color: '#E8EAED', textTransform: 'capitalize' }}>{currentTier}</p>
                  <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: currentPlan.color }}>{sub?.price_display ?? currentPlan.price_display}</p>
                </div>
              </div>
            </div>

            {/* Status */}
            <div>
              <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '10px', color: '#4B5563', letterSpacing: '0.08em', marginBottom: '8px' }}>STATUS</p>
              <span style={{
                fontFamily: 'JetBrains Mono, monospace', fontSize: '12px', fontWeight: 700,
                color: statusColor, background: `${statusColor}18`, border: `1px solid ${statusColor}30`,
                padding: '4px 10px', borderRadius: '8px', textTransform: 'uppercase',
              }}>{sub?.subscription_status ?? 'active'}</span>
              {sub?.current_period_end && (
                <p style={{ fontSize: '12px', color: '#4B5563', marginTop: '6px', fontFamily: 'JetBrains Mono, monospace' }}>Renews {fmtDate(sub.current_period_end)}</p>
              )}
            </div>

            {/* Quota bar */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '10px', color: '#4B5563', letterSpacing: '0.08em' }}>QUOTA USED</p>
                {sub && <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: '#8B95A8' }}>{fmt(sub.quota_used)} / {fmt(sub.monthly_quota)}</p>}
              </div>
              <div style={{ background: 'rgba(255,255,255,0.08)', borderRadius: '6px', height: '8px', overflow: 'hidden' }}>
                <div style={{
                  height: '100%', borderRadius: '6px', transition: 'width 0.4s',
                  background: quotaPct > 85 ? '#FF4560' : quotaPct > 60 ? '#FFC945' : currentPlan.color,
                  width: `${quotaPct}%`,
                }} />
              </div>
              {sub && <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: '#4B5563', marginTop: '6px' }}>{sub.quota_percentage.toFixed(1)}% of monthly quota</p>}
            </div>
          </div>
        )}
      </div>

      {/* Plan cards — always rendered from static data */}
      <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: '#4B5563', letterSpacing: '0.1em', marginBottom: '20px' }}>AVAILABLE PLANS</p>
      <div className="fade-up-2" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '40px' }}>
        {PLANS.map(plan => (
          <PlanCard
            key={plan.tier}
            plan={plan}
            currentTier={currentTier}
            onSelect={handleUpgrade}
            busy={upgrading}
          />
        ))}
      </div>

      {/* Cancel section */}
      {!subLoading && sub && sub.tier !== 'free' && sub.subscription_status !== 'canceled' && (
        <div className="glass-card fade-up-3" style={{
          padding: '20px 24px', marginBottom: '40px',
          border: '1px solid rgba(255,255,255,0.06)',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          <div>
            <p style={{ fontFamily: 'Syne, sans-serif', fontWeight: 700, fontSize: '14px', color: '#E8EAED', marginBottom: '4px' }}>Cancel Subscription</p>
            <p style={{ fontSize: '13px', color: '#4B5563' }}>Immediately downgrades you to the Free plan. All data is preserved.</p>
          </div>
          {!confirmCancel ? (
            <button onClick={() => setConfirmCancel(true)} style={{
              padding: '9px 18px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.12)',
              background: 'transparent', color: '#8B95A8',
              fontFamily: 'Syne, sans-serif', fontWeight: 600, fontSize: '13px', cursor: 'pointer',
            }}>Cancel plan</button>
          ) : (
            <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
              <span style={{ fontSize: '13px', color: '#8B95A8', fontFamily: 'JetBrains Mono, monospace' }}>Are you sure?</span>
              <button onClick={handleCancel} disabled={canceling} style={{
                padding: '9px 18px', borderRadius: '8px', border: '1px solid #FF4560',
                background: '#FF4560', color: '#fff',
                fontFamily: 'Syne, sans-serif', fontWeight: 700, fontSize: '13px', cursor: 'pointer',
                display: 'flex', alignItems: 'center', gap: '6px',
              }}>
                {canceling ? <><RefreshCw size={12} className="spin" />Canceling…</> : <><XCircle size={13} />Yes, cancel</>}
              </button>
              <button onClick={() => setConfirmCancel(false)} style={{
                padding: '9px 14px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.08)',
                background: 'transparent', color: '#4B5563',
                fontFamily: 'Syne, sans-serif', fontWeight: 600, fontSize: '13px', cursor: 'pointer',
              }}>Keep plan</button>
            </div>
          )}
        </div>
      )}

      {/* Invoice history */}
      <div className="fade-up-4">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
          <Receipt size={14} color="#4B5563" />
          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: '#4B5563', letterSpacing: '0.1em' }}>INVOICE HISTORY</p>
        </div>
        {invoicesLoading ? (
          <div className="glass-card shimmer" style={{ height: '120px' }} />
        ) : invoices.length === 0 ? (
          <div className="glass-card" style={{ padding: '36px', textAlign: 'center' }}>
            <Receipt size={28} color="rgba(255,255,255,0.12)" style={{ margin: '0 auto 12px' }} />
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '13px', color: '#4B5563' }}>No invoices yet — they appear after your first plan change.</p>
          </div>
        ) : (
          <div className="glass-card" style={{ overflow: 'hidden' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
                  {['Invoice ID', 'Plan', 'Amount', 'Status', 'Date'].map(h => (
                    <th key={h} style={{
                      padding: '10px 16px', textAlign: 'left',
                      fontFamily: 'JetBrains Mono, monospace', fontSize: '10px',
                      fontWeight: 600, color: '#4B5563', letterSpacing: '0.08em',
                    }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {invoices.map(inv => <InvoiceRow key={inv.id} inv={inv} />)}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        .spin { animation: spin 0.7s linear infinite; }
      `}</style>
    </div>
  );
}
