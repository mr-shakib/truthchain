'use client';

import { useEffect, useState, useCallback } from 'react';
import { useAuth } from '@/lib/auth';
import { createBillingApi, getApiError } from '@/lib/billing';
import type { SubscriptionDetails, InvoiceItem } from '@/lib/types';
import {
  CreditCard, CheckCircle2, XCircle, RefreshCw,
  ChevronUp, ChevronDown, Receipt, AlertTriangle, Star,
  Zap, Rocket, Building2, Crown,
} from 'lucide-react';

// ─── Static plan catalogue (renders immediately, no API needed) ─────────────

const PLANS = [
  {
    tier: 'free',
    label: 'Free',
    price_cents: 0,
    price_display: '$0 / month',
    monthly_quota: 1000,
    rpm: 10,
    color: '#4B5563',
    Icon: Zap,
    features: ['10 req / min', '1,000 validations / mo', 'Schema validation', 'Basic rules'],
  },
  {
    tier: 'startup',
    label: 'Startup',
    price_cents: 2900,
    price_display: '$29 / month',
    monthly_quota: 10000,
    rpm: 30,
    color: '#00D8FF',
    Icon: Rocket,
    features: ['30 req / min', '10,000 validations / mo', 'Auto-correction', 'Anomaly detection', 'Confidence scoring'],
    popular: true,
  },
  {
    tier: 'business',
    label: 'Business',
    price_cents: 9900,
    price_display: '$99 / month',
    monthly_quota: 100000,
    rpm: 100,
    color: '#A78BFA',
    Icon: Building2,
    features: ['100 req / min', '100,000 validations / mo', 'All Startup features', 'Priority support', 'Analytics API'],
  },
  {
    tier: 'enterprise',
    label: 'Enterprise',
    price_cents: 49900,
    price_display: '$499 / month',
    monthly_quota: 1000000,
    rpm: 500,
    color: '#FFC945',
    Icon: Crown,
    features: ['500 req / min', '1M+ validations / mo', 'All Business features', 'Dedicated support', 'SLA guarantee', 'Custom integrations'],
  },
] as const;

const TIER_ORDER = ['free', 'startup', 'business', 'enterprise'];

// ─── Helpers ────────────────────────────────────────────────────────────────

function fmt(n: number) { return n.toLocaleString(); }
function fmtDate(s: string | null) {
  if (!s) return '—';
  return new Date(s).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
}

// ─── Plan Card ───────────────────────────────────────────────────────────────

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
    <div
      style={{
        position: 'relative',
        borderRadius: '16px',
        border: `1px solid ${isCurrent ? color : 'rgba(255,255,255,0.08)'}`,
        background: isCurrent ? `${color}0F` : '#0C101A',
        padding: '28px 24px 24px',
        display: 'flex',
        flexDirection: 'column',
        gap: '20px',
        transition: 'border-color 0.2s, box-shadow 0.2s',
        boxShadow: isCurrent ? `0 0 24px ${color}28` : 'none',
        minHeight: '380px',
      }}
    >
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
            color: color, background: `${color}18`, border: `1px solid ${color}40`,
            padding: '3px 10px', borderRadius: '20px', letterSpacing: '0.08em',
          }}>
            ✓ CURRENT
          </span>
        )}
      </div>

      <div>
        <p style={{
          fontFamily: 'Syne, sans-serif', fontWeight: 800, fontSize: '20px',
          color: '#E8EAED', letterSpacing: '-0.01em', marginBottom: '6px',
        }}>
          {plan.label}
        </p>
        <p style={{
          fontFamily: 'Syne, sans-serif', fontWeight: 800, fontSize: '30px',
          color: color, letterSpacing: '-0.02em', lineHeight: 1,
        }}>
          {plan.price_display.split(' /')[0]}
          <span style={{ fontSize: '14px', fontWeight: 500, color: '#4B5563', marginLeft: '4px' }}>/mo</span>
        </p>
        <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: '#4B5563', marginTop: '6px' }}>
          {fmt(plan.monthly_quota)} validations · {plan.rpm} req/min
        </p>
      </div>

      <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '9px', flex: 1 }}>
        {plan.features.map((f: string) => (
          <li key={f} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <CheckCircle2 size={13} color={color} strokeWidth={2.5} style={{ flexShrink: 0 }} />
            <span style={{ fontSize: '13px', color: '#8B95A8' }}>{f}</span>
          </li>
        ))}
      </ul>

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
          transition: 'opacity 0.15s, filter 0.15s',
          opacity: loading ? 0.6 : 1,
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

// ─── Invoice Row ─────────────────────────────────────────────────────────────

function InvoiceRow({ inv }: { inv: InvoiceItem }) {
  const colors: Record<string, string> = {
    paid: '#00FF88', free: '#4B5563', pending: '#FFC945', failed: '#FF4560',
  };
  const c = colors[inv.status] ?? '#4B5563';
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

// ─── Page ────────────────────────────────────────────────────────────────────

export default function BillingPage() {
  const { apiKey, tier: authTier } = useAuth();

  const [sub, setSub] = useState<SubscriptionDetails | null>(null);
  const [invoices, setInvoices] = useState<InvoiceItem[]>([]);
  const [subLoading, setSubLoading] = useState(true);
  const [subError, setSubError] = useState('');

  const currentTier = sub?.tier ?? authTier ?? 'free';
  const currentPlan = PLANS.find(p => p.tier === currentTier) ?? PLANS[0];

  const [upgrading, setUpgrading] = useState<string | null>(null);
  const [upgradeMsg, setUpgradeMsg] = useState('');
  const [actionError, setActionError] = useState('');
  const [canceling, setCanceling] = useState(false);
  const [confirmCancel, setConfirmCancel] = useState(false);

  const fetchSub = useCallback(async () => {
    if (!apiKey) return;
    setSubError('');
    setSubLoading(true);
    try {
      const api = createBillingApi(apiKey);
      const [subData, invoicesData] = await Promise.all([api.subscription(), api.invoices()]);
      setSub(subData);
      setInvoices(invoicesData);
    } catch (err) {
      setSubError(getApiError(err));
    } finally {
      setSubLoading(false);
    }
  }, [apiKey]);

  useEffect(() => { fetchSub(); }, [fetchSub]);

  async function handleSelect(tier: string) {
    if (!apiKey) return;
    setUpgrading(tier);
    setUpgradeMsg('');
    setActionError('');
    try {
      const api = createBillingApi(apiKey);
      const res = await api.upgrade({ tier: tier as never });
      setUpgradeMsg(res.message);
      await fetchSub();
    } catch (err) {
      setActionError(getApiError(err));
    } finally {
      setUpgrading(null);
    }
  }

  async function handleCancel() {
    if (!apiKey) return;
    setCanceling(true);
    setActionError('');
    try {
      const api = createBillingApi(apiKey);
      const res = await api.cancel();
      setUpgradeMsg(res.message);
      setConfirmCancel(false);
      await fetchSub();
    } catch (err) {
      setActionError(getApiError(err));
    } finally {
      setCanceling(false);
    }
  }

  const quotaPct = Math.min(sub?.quota_percentage ?? 0, 100);
  const statusColors: Record<string, string> = {
    active: '#00FF88', trialing: '#00D8FF', past_due: '#FFC945', canceled: '#FF4560',
  };
  const statusColor = statusColors[sub?.subscription_status ?? 'active'] ?? '#00FF88';

  return (
    <div style={{ padding: '40px', maxWidth: '1280px' }}>

      {/* Header */}
      <div className="fade-up" style={{ marginBottom: '40px', display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div>
          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: '#4B5563', letterSpacing: '0.12em', marginBottom: '6px' }}>
            SUBSCRIPTION
          </p>
          <h1 style={{ fontFamily: 'Syne, sans-serif', fontWeight: 800, fontSize: '28px', letterSpacing: '-0.02em', color: '#E8EAED' }}>
            Billing &amp; Plans
          </h1>
        </div>
        <button
          onClick={fetchSub}
          style={{
            display: 'flex', alignItems: 'center', gap: '6px', padding: '9px 16px', borderRadius: '8px',
            border: '1px solid rgba(255,255,255,0.1)', background: 'transparent',
            color: '#8B95A8', fontFamily: 'Syne, sans-serif', fontWeight: 600, fontSize: '13px', cursor: 'pointer',
          }}
        >
          <RefreshCw size={13} style={subLoading ? { animation: 'spin 0.7s linear infinite' } : {}} />
          Refresh
        </button>
      </div>

      {/* Banners */}
      {upgradeMsg && (
        <div className="fade-up" style={{
          background: 'rgba(0,255,136,0.08)', border: '1px solid rgba(0,255,136,0.25)',
          borderRadius: '10px', padding: '12px 18px', marginBottom: '24px',
          display: 'flex', alignItems: 'center', gap: '10px',
          fontFamily: 'JetBrains Mono, monospace', fontSize: '13px', color: '#00FF88',
        }}>
          <CheckCircle2 size={14} />{upgradeMsg}
          <button onClick={() => setUpgradeMsg('')} style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer', color: '#4B5563', fontSize: '16px' }}>✕</button>
        </div>
      )}
      {actionError && (
        <div className="fade-up" style={{
          background: 'rgba(255,69,96,0.08)', border: '1px solid rgba(255,69,96,0.25)',
          borderRadius: '10px', padding: '12px 18px', marginBottom: '24px',
          display: 'flex', alignItems: 'center', gap: '10px',
          fontFamily: 'JetBrains Mono, monospace', fontSize: '13px', color: '#FF4560',
        }}>
          <AlertTriangle size={14} />{actionError}
          <button onClick={() => setActionError('')} style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer', color: '#4B5563', fontSize: '16px' }}>✕</button>
        </div>
      )}

      {/* Current plan summary */}
      <div className="fade-up-1" style={{
        background: '#0C101A',
        border: `1px solid ${currentPlan.color}30`,
        borderRadius: '16px', padding: '28px', marginBottom: '40px',
        display: 'grid', gridTemplateColumns: '1fr 1px 1fr 1px 1fr', gap: '0',
        boxShadow: `0 0 32px ${currentPlan.color}10`,
      }}>
        {/* Active plan col */}
        <div style={{ paddingRight: '32px' }}>
          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '10px', color: '#4B5563', letterSpacing: '0.1em', marginBottom: '14px' }}>ACTIVE PLAN</p>
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <div style={{
              width: '48px', height: '48px', borderRadius: '12px',
              background: `${currentPlan.color}18`, border: `1px solid ${currentPlan.color}35`,
              display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
            }}>
              <currentPlan.Icon size={22} color={currentPlan.color} />
            </div>
            <div>
              <p style={{ fontFamily: 'Syne, sans-serif', fontWeight: 800, fontSize: '22px', color: '#E8EAED' }}>{currentPlan.label}</p>
              <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '12px', color: currentPlan.color, marginTop: '2px' }}>{currentPlan.price_display}</p>
            </div>
          </div>
          <div style={{ marginTop: '16px' }}>
            {subLoading ? (
              <div className="shimmer" style={{ height: '26px', width: '90px', borderRadius: '20px' }} />
            ) : sub ? (
              <span style={{
                fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', fontWeight: 700,
                color: statusColor, background: `${statusColor}18`, border: `1px solid ${statusColor}35`,
                padding: '4px 12px', borderRadius: '20px', letterSpacing: '0.08em', textTransform: 'uppercase',
              }}>● {sub.subscription_status}</span>
            ) : (
              <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '12px', color: '#4B5563' }}>
                {subError ? '⚠ Backend offline' : '—'}
              </span>
            )}
          </div>
        </div>

        {/* Divider */}
        <div style={{ background: 'rgba(255,255,255,0.06)', margin: '0 32px' }} />

        {/* Quota col */}
        <div style={{ padding: '0 32px' }}>
          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '10px', color: '#4B5563', letterSpacing: '0.1em', marginBottom: '14px' }}>QUOTA USAGE</p>
          {subLoading ? (
            <div className="shimmer" style={{ height: '70px', borderRadius: '8px' }} />
          ) : sub ? (
            <>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '10px' }}>
                <span style={{ fontFamily: 'Syne, sans-serif', fontWeight: 800, fontSize: '26px', color: '#E8EAED' }}>{fmt(sub.quota_used)}</span>
                <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '12px', color: '#4B5563' }}>/ {fmt(sub.monthly_quota)}</span>
              </div>
              <div style={{ background: 'rgba(255,255,255,0.06)', borderRadius: '8px', height: '8px', overflow: 'hidden', marginBottom: '8px' }}>
                <div style={{
                  height: '100%', borderRadius: '8px', transition: 'width 0.6s ease', width: `${quotaPct}%`,
                  background: quotaPct > 85 ? '#FF4560' : quotaPct > 60 ? '#FFC945' : `linear-gradient(90deg, ${currentPlan.color}, ${currentPlan.color}99)`,
                }} />
              </div>
              <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: '#4B5563' }}>{sub.quota_percentage.toFixed(1)}% used this month</p>
            </>
          ) : (
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '12px', color: '#4B5563' }}>{subError ? '⚠ Could not load' : '—'}</p>
          )}
        </div>

        {/* Divider */}
        <div style={{ background: 'rgba(255,255,255,0.06)', margin: '0 32px' }} />

        {/* Billing period col */}
        <div style={{ paddingLeft: '8px' }}>
          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '10px', color: '#4B5563', letterSpacing: '0.1em', marginBottom: '14px' }}>BILLING PERIOD</p>
          {subLoading ? (
            <div className="shimmer" style={{ height: '70px', borderRadius: '8px' }} />
          ) : sub ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div>
                <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '10px', color: '#4B5563', marginBottom: '3px' }}>RENEWS</p>
                <p style={{ fontFamily: 'Syne, sans-serif', fontWeight: 700, fontSize: '15px', color: '#E8EAED' }}>{fmtDate(sub.current_period_end)}</p>
              </div>
              <div>
                <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '10px', color: '#4B5563', marginBottom: '3px' }}>RATE LIMIT</p>
                <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '15px', fontWeight: 600, color: currentPlan.color }}>{sub.rpm_limit} req / min</p>
              </div>
            </div>
          ) : (
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '12px', color: '#4B5563' }}>{subError ? '—' : '—'}</p>
          )}
        </div>
      </div>

      {/* Plan selection grid */}
      <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: '#4B5563', letterSpacing: '0.12em', marginBottom: '20px' }}>
        CHOOSE A PLAN
      </p>
      <div className="fade-up-2" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '40px' }}>
        {PLANS.map(plan => (
          <PlanCard key={plan.tier} plan={plan} currentTier={currentTier} onSelect={handleSelect} busy={upgrading} />
        ))}
      </div>

      {/* Cancel subscription */}
      {currentTier !== 'free' && sub?.subscription_status !== 'canceled' && (
        <div className="fade-up-3" style={{
          background: '#0C101A', border: '1px solid rgba(255,255,255,0.06)',
          borderRadius: '14px', padding: '22px 28px', marginBottom: '40px',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '24px',
        }}>
          <div>
            <p style={{ fontFamily: 'Syne, sans-serif', fontWeight: 700, fontSize: '15px', color: '#E8EAED', marginBottom: '5px' }}>Cancel Subscription</p>
            <p style={{ fontSize: '13px', color: '#4B5563', fontFamily: 'JetBrains Mono, monospace' }}>
              Immediately downgrades to Free. All data and validation history is preserved.
            </p>
          </div>
          {!confirmCancel ? (
            <button
              onClick={() => setConfirmCancel(true)}
              style={{
                padding: '10px 20px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)',
                background: 'transparent', color: '#8B95A8',
                fontFamily: 'Syne, sans-serif', fontWeight: 600, fontSize: '13px', cursor: 'pointer', whiteSpace: 'nowrap',
              }}
            >Cancel plan</button>
          ) : (
            <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexShrink: 0 }}>
              <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '12px', color: '#8B95A8' }}>Confirm?</span>
              <button
                onClick={handleCancel} disabled={canceling}
                style={{
                  padding: '10px 18px', borderRadius: '8px', border: '1px solid #FF4560',
                  background: '#FF4560', color: '#fff',
                  fontFamily: 'Syne, sans-serif', fontWeight: 700, fontSize: '13px', cursor: 'pointer',
                  display: 'flex', alignItems: 'center', gap: '6px', whiteSpace: 'nowrap',
                }}
              >
                {canceling
                  ? <><RefreshCw size={12} style={{ animation: 'spin 0.7s linear infinite' }} />Canceling…</>
                  : <><XCircle size={13} />Yes, cancel</>}
              </button>
              <button
                onClick={() => setConfirmCancel(false)}
                style={{
                  padding: '10px 16px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)',
                  background: 'transparent', color: '#8B95A8',
                  fontFamily: 'Syne, sans-serif', fontWeight: 600, fontSize: '13px', cursor: 'pointer', whiteSpace: 'nowrap',
                }}
              >Keep plan</button>
            </div>
          )}
        </div>
      )}

      {/* Invoice history */}
      <div className="fade-up-4">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
          <Receipt size={14} color="#4B5563" />
          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: '#4B5563', letterSpacing: '0.12em' }}>INVOICE HISTORY</p>
        </div>
        {subLoading ? (
          <div className="shimmer" style={{ height: '80px', borderRadius: '12px' }} />
        ) : invoices.length === 0 ? (
          <div style={{
            background: '#0C101A', border: '1px solid rgba(255,255,255,0.06)',
            borderRadius: '12px', padding: '48px', textAlign: 'center',
          }}>
            <Receipt size={32} color="rgba(255,255,255,0.08)" style={{ margin: '0 auto 14px' }} />
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '13px', color: '#4B5563' }}>
              No invoices yet — they appear after your first plan change.
            </p>
          </div>
        ) : (
          <div style={{ background: '#0C101A', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '12px', overflow: 'hidden' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)', background: 'rgba(255,255,255,0.02)' }}>
                  {['Invoice ID', 'Plan', 'Amount', 'Status', 'Date'].map(h => (
                    <th key={h} style={{
                      padding: '11px 16px', textAlign: 'left',
                      fontFamily: 'JetBrains Mono, monospace', fontSize: '10px',
                      fontWeight: 600, color: '#4B5563', letterSpacing: '0.1em',
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

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
