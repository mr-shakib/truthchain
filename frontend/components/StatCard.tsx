'use client';

import { cn } from '@/lib/utils';

interface StatCardProps {
  label: string;
  value: string | number;
  sub?: string;
  accent?: 'cyan' | 'green' | 'red' | 'amber' | 'purple';
  delay?: number;
  icon?: React.ReactNode;
}

const accentMap = {
  cyan: { color: 'var(--cyan)', bg: 'var(--cyan-dim)', shadow: '0 0 30px rgba(0,216,255,0.15)' },
  green: { color: 'var(--green)', bg: 'var(--green-dim)', shadow: '0 0 30px rgba(0,255,136,0.15)' },
  red: { color: 'var(--red)', bg: 'var(--red-dim)', shadow: '0 0 30px rgba(255,69,96,0.15)' },
  amber: { color: 'var(--amber)', bg: 'var(--amber-dim)', shadow: '0 0 30px rgba(255,201,69,0.15)' },
  purple: { color: 'var(--purple)', bg: 'rgba(167,139,250,0.1)', shadow: '0 0 30px rgba(167,139,250,0.15)' },
};

export default function StatCard({ label, value, sub, accent = 'cyan', delay = 0, icon }: StatCardProps) {
  const a = accentMap[accent];
  return (
    <div
      className="glass-card p-6 relative overflow-hidden fade-up"
      style={{
        animationDelay: `${delay}ms`,
        boxShadow: a.shadow,
        borderColor: `rgba(255,255,255,0.1)`,
      }}
    >
      {/* Accent corner */}
      <div
        style={{
          position: 'absolute', top: 0, left: 0, right: 0,
          height: '2px',
          background: `linear-gradient(90deg, ${a.color}66, transparent)`,
        }}
      />
      {/* Icon */}
      {icon && (
        <div
          className="mb-3 w-8 h-8 flex items-center justify-center rounded-lg"
          style={{ background: a.bg, color: a.color }}
        >
          {icon}
        </div>
      )}
      <p className="text-xs font-semibold tracking-widest uppercase mb-2"
        style={{ color: 'var(--text-muted)', fontFamily: 'JetBrains Mono, monospace' }}>
        {label}
      </p>
      <p className="text-3xl font-bold mono" style={{ color: a.color, fontFamily: 'JetBrains Mono, monospace' }}>
        {value}
      </p>
      {sub && (
        <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>{sub}</p>
      )}
    </div>
  );
}

export function cn_unused(..._: unknown[]) { return ''; }
