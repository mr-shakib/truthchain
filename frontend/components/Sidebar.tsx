'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import {
  LayoutDashboard, ShieldCheck, KeyRound, History,
  Settings, LogOut, Activity, ChevronRight, Zap, CreditCard
} from 'lucide-react';

const nav = [
  { href: '/dashboard', label: 'Overview', icon: LayoutDashboard },
  { href: '/dashboard/validate', label: 'Validate', icon: ShieldCheck },
  { href: '/dashboard/history', label: 'History', icon: History },
  { href: '/dashboard/api-keys', label: 'API Keys', icon: KeyRound },
  { href: '/dashboard/billing', label: 'Billing', icon: CreditCard },
  { href: '/dashboard/settings', label: 'Settings', icon: Settings },
];

const tierBadge: Record<string, { label: string; color: string }> = {
  free: { label: 'FREE', color: 'var(--text-muted)' },
  startup: { label: 'STARTUP', color: 'var(--cyan)' },
  business: { label: 'BUSINESS', color: 'var(--purple)' },
  enterprise: { label: 'ENTERPRISE', color: 'var(--amber)' },
};

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { orgName, tier, logout } = useAuth();
  const badge = tierBadge[tier ?? 'free'] ?? tierBadge.free;

  function handleLogout() {
    logout();
    router.push('/login');
  }

  return (
    <aside style={{
      width: '240px',
      minHeight: '100vh',
      background: 'var(--bg-surface)',
      borderRight: '1px solid var(--border-subtle)',
      display: 'flex',
      flexDirection: 'column',
      flexShrink: 0,
      position: 'sticky',
      top: 0,
      height: '100vh',
    }}>
      {/* Logo */}
      <div style={{ padding: '24px 20px 16px', borderBottom: '1px solid var(--border-subtle)' }}>
        <Link href="/dashboard" style={{ textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            width: '32px', height: '32px', borderRadius: '8px',
            background: 'linear-gradient(135deg, var(--cyan), #7B61FF)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 0 16px var(--cyan-glow)',
          }}>
            <Zap size={18} color="var(--bg-void)" strokeWidth={2.5} />
          </div>
          <span style={{ fontFamily: 'Syne, sans-serif', fontWeight: 800, fontSize: '16px', color: 'var(--text-primary)', letterSpacing: '-0.02em' }}>
            TruthChain
          </span>
        </Link>
        {/* Status indicator */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '12px' }}>
          <span className="pulse-dot" style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--green)', display: 'inline-block' }} />
          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '10px', color: 'var(--text-muted)', letterSpacing: '0.05em' }}>
            API LIVE
          </span>
          <Activity size={10} color="var(--text-muted)" />
        </div>
      </div>

      {/* Org info */}
      <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-subtle)' }}>
        <p style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '4px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {orgName ?? 'My Organization'}
        </p>
        <span style={{
          fontFamily: 'JetBrains Mono, monospace', fontSize: '10px', fontWeight: 600,
          color: badge.color, letterSpacing: '0.1em',
          padding: '2px 6px', borderRadius: '4px',
          background: `${badge.color}18`,
          border: `1px solid ${badge.color}30`,
        }}>
          {badge.label}
        </span>
      </div>

      {/* Nav */}
      <nav style={{ flex: 1, padding: '12px 12px', overflow: 'auto' }}>
        {nav.map(({ href, label, icon: Icon }) => {
          const exact = href === '/dashboard';
          const active = exact ? pathname === href : pathname.startsWith(href);
          return (
            <Link key={href} href={href} style={{ textDecoration: 'none', display: 'block', marginBottom: '2px' }}>
              <div style={{
                display: 'flex', alignItems: 'center', gap: '10px',
                padding: '9px 12px', borderRadius: '8px',
                fontSize: '13px', fontWeight: active ? 700 : 500,
                fontFamily: 'Syne, sans-serif',
                color: active ? 'var(--bg-void)' : 'var(--text-secondary)',
                background: active ? 'var(--cyan)' : 'transparent',
                transition: 'all 0.15s',
                boxShadow: active ? '0 0 16px var(--cyan-glow)' : 'none',
              }}
                onMouseEnter={e => {
                  if (!active) {
                    (e.currentTarget as HTMLDivElement).style.background = 'rgba(255,255,255,0.04)';
                    (e.currentTarget as HTMLDivElement).style.color = 'var(--text-primary)';
                  }
                }}
                onMouseLeave={e => {
                  if (!active) {
                    (e.currentTarget as HTMLDivElement).style.background = 'transparent';
                    (e.currentTarget as HTMLDivElement).style.color = 'var(--text-secondary)';
                  }
                }}
              >
                <Icon size={14} strokeWidth={active ? 2.5 : 2} />
                <span style={{ flex: 1 }}>{label}</span>
                {active && <ChevronRight size={12} strokeWidth={3} />}
              </div>
            </Link>
          );
        })}
      </nav>

      {/* Bottom */}
      <div style={{ padding: '16px 12px', borderTop: '1px solid var(--border-subtle)' }}>
        <Link href="/" style={{ textDecoration: 'none', display: 'block', marginBottom: '4px' }}>
          <div style={{
            display: 'flex', alignItems: 'center', gap: '10px',
            padding: '9px 12px', borderRadius: '8px', fontSize: '13px', fontWeight: 500,
            color: 'var(--text-muted)', fontFamily: 'Syne, sans-serif', cursor: 'pointer', transition: 'all 0.15s',
          }}
            onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.color = 'var(--text-secondary)'; }}
            onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.color = 'var(--text-muted)'; }}
          >
            <Zap size={14} strokeWidth={2} />
            <span>Home</span>
          </div>
        </Link>
        <button onClick={handleLogout} style={{
          width: '100%', display: 'flex', alignItems: 'center', gap: '10px',
          padding: '9px 12px', borderRadius: '8px', fontSize: '13px', fontWeight: 500,
          color: 'var(--text-muted)', fontFamily: 'Syne, sans-serif', cursor: 'pointer',
          background: 'transparent', border: 'none', transition: 'all 0.15s', textAlign: 'left',
        }}
          onMouseEnter={e => {
            (e.currentTarget as HTMLButtonElement).style.color = 'var(--red)';
            (e.currentTarget as HTMLButtonElement).style.background = 'var(--red-dim)';
          }}
          onMouseLeave={e => {
            (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-muted)';
            (e.currentTarget as HTMLButtonElement).style.background = 'transparent';
          }}
        >
          <LogOut size={14} strokeWidth={2} />
          <span>Sign Out</span>
        </button>
      </div>
    </aside>
  );
}
