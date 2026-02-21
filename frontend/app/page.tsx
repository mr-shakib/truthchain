import Link from 'next/link';
import { ShieldCheck, Zap, BarChart3, Lock, RefreshCw, AlertTriangle, ArrowRight, CheckCircle2 } from 'lucide-react';

const DEMO_CODE = `POST /v1/validate
X-API-Key: tc_live_...

{
  "output": { "hours": 30, "rate": "invalid" },
  "rules": [
    {
      "type": "range", "field": "hours",
      "min": 0, "max": 24,
      "severity": "error"
    }
  ],
  "context": {
    "auto_correct": true,
    "calculate_confidence": true
  }
}`;

const DEMO_RESPONSE = `{
  "validation_id": "val_9f4c2e...",
  "status": "failed",
  "valid": false,
  "confidence_score": 0.65,
  "confidence_level": "medium",
  "violations": [
    {
      "field": "hours",
      "message": "Value 30 exceeds max 24",
      "severity": "error"
    }
  ],
  "auto_corrected": true,
  "corrected_output": { "hours": 24.0 },
  "latency_ms": 12
}`;

const features = [
  {
    icon: ShieldCheck,
    title: 'Schema Validation',
    desc: 'Validate AI outputs against JSON schemas, custom rules, and type constraints in milliseconds.',
    accent: 'var(--cyan)',
  },
  {
    icon: RefreshCw,
    title: 'Auto-Correction',
    desc: 'When violations are found, TruthChain automatically corrects values back within bounds.',
    accent: 'var(--green)',
  },
  {
    icon: AlertTriangle,
    title: 'Anomaly Detection',
    desc: 'ML-powered hallucination pattern detection catches impossible or implausible outputs.',
    accent: 'var(--amber)',
  },
  {
    icon: BarChart3,
    title: 'Confidence Scoring',
    desc: 'Every validation returns a multi-factor confidence score: high, medium, low, or very_low.',
    accent: 'var(--purple)',
  },
  {
    icon: Lock,
    title: 'Multi-Tenant Auth',
    desc: 'API key authentication with per-org quotas, rate limiting, and full audit logging.',
    accent: 'var(--cyan)',
  },
  {
    icon: Zap,
    title: 'Sub-20ms Latency',
    desc: 'Redis-cached validation results. Average latency under 20ms for cached entries.',
    accent: 'var(--green)',
  },
];

const tiers = [
  { name: 'Free', price: '$0', rpm: 10, quota: '1,000 / mo', color: 'var(--text-muted)' },
  { name: 'Startup', price: '$29', rpm: 30, quota: '10,000 / mo', color: 'var(--cyan)', highlight: false },
  { name: 'Business', price: '$99', rpm: 100, quota: '100,000 / mo', color: 'var(--purple)', highlight: true },
  { name: 'Enterprise', price: 'Custom', rpm: 500, quota: '1M+ / mo', color: 'var(--amber)' },
];

export default function LandingPage() {
  return (
    <div style={{ background: 'var(--bg-void)', minHeight: '100vh', overflowX: 'hidden' }}>

      {/* ── Nav ──────────────────────────────────────────────────────── */}
      <nav style={{
        position: 'sticky', top: 0, zIndex: 50,
        background: 'rgba(6,8,15,0.85)',
        backdropFilter: 'blur(12px)',
        borderBottom: '1px solid var(--border-subtle)',
        padding: '0 40px',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        height: '60px',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            width: '28px', height: '28px', borderRadius: '7px',
            background: 'linear-gradient(135deg, var(--cyan), #7B61FF)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 0 12px var(--cyan-glow)',
          }}>
            <Zap size={15} color="var(--bg-void)" strokeWidth={3} />
          </div>
          <span style={{ fontFamily: 'Syne, sans-serif', fontWeight: 800, fontSize: '15px', letterSpacing: '-0.03em', color: 'var(--text-primary)' }}>
            TruthChain
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Link href="/login" style={{ textDecoration: 'none' }}>
            <button className="tc-btn-ghost" style={{ padding: '7px 16px', fontSize: '13px' }}>Sign In</button>
          </Link>
          <Link href="/signup" style={{ textDecoration: 'none' }}>
            <button className="tc-btn-primary" style={{ padding: '7px 16px', fontSize: '13px' }}>Get Started</button>
          </Link>
        </div>
      </nav>

      {/* ── Hero ─────────────────────────────────────────────────────── */}
      <section className="grid-texture" style={{ padding: '100px 40px 80px', position: 'relative', overflow: 'hidden' }}>
        {/* Glowing orbs */}
        <div style={{
          position: 'absolute', top: '10%', left: '15%',
          width: '400px', height: '400px', borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(0,216,255,0.08) 0%, transparent 70%)',
          filter: 'blur(40px)', pointerEvents: 'none',
        }} />
        <div style={{
          position: 'absolute', top: '20%', right: '10%',
          width: '300px', height: '300px', borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(123,97,255,0.08) 0%, transparent 70%)',
          filter: 'blur(40px)', pointerEvents: 'none',
        }} />

        <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
          {/* Eyebrow badge */}
          <div className="fade-up" style={{ marginBottom: '28px', display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
            <span style={{
              fontFamily: 'JetBrains Mono, monospace', fontSize: '11px',
              color: 'var(--cyan)', background: 'var(--cyan-dim)',
              border: '1px solid rgba(0,216,255,0.2)', borderRadius: '99px',
              padding: '5px 14px', letterSpacing: '0.08em', fontWeight: 600,
              display: 'flex', alignItems: 'center', gap: '6px',
            }}>
              <CheckCircle2 size={12} />
              AI OUTPUT VALIDATION · PRODUCTION-READY API
            </span>
          </div>

          {/* Headline */}
          <h1 className="fade-up-1" style={{
            fontFamily: 'Syne, sans-serif', fontWeight: 800, fontSize: 'clamp(44px, 6vw, 80px)',
            lineHeight: 1.05, letterSpacing: '-0.04em', maxWidth: '720px', marginBottom: '24px',
          }}>
            <span style={{ color: 'var(--text-primary)' }}>Stop trusting</span>
            <br />
            <span className="gradient-text-cyan">AI blindly.</span>
          </h1>

          <p className="fade-up-2" style={{
            fontSize: '18px', color: 'var(--text-secondary)', maxWidth: '520px',
            lineHeight: 1.7, marginBottom: '40px', fontWeight: 400,
          }}>
            TruthChain validates AI-generated outputs against your schemas, rules, and business logic —
            with auto-correction, anomaly detection, and sub-20ms latency.
          </p>

          <div className="fade-up-3" style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', marginBottom: '60px' }}>
            <Link href="/signup" style={{ textDecoration: 'none' }}>
              <button className="tc-btn-primary" style={{ fontSize: '15px', padding: '13px 28px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                Start for free <ArrowRight size={16} />
              </button>
            </Link>
            <Link href="/login" style={{ textDecoration: 'none' }}>
              <button className="tc-btn-ghost" style={{ fontSize: '15px', padding: '13px 28px' }}>
                View Dashboard
              </button>
            </Link>
          </div>

          {/* Stats row */}
          <div className="fade-up-4" style={{ display: 'flex', gap: '40px', flexWrap: 'wrap' }}>
            {[
              { label: 'Avg Latency', value: '<20ms' },
              { label: 'Uptime', value: '99.9%' },
              { label: 'Validation Types', value: '6+' },
              { label: 'Auto-Corrections', value: 'Real-time' },
            ].map(({ label, value }) => (
              <div key={label}>
                <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '24px', fontWeight: 600, color: 'var(--cyan)', lineHeight: 1 }}>{value}</p>
                <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px', fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.05em' }}>{label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Code Demo ────────────────────────────────────────────────── */}
      <section style={{ padding: '0 40px 100px' }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
          <div style={{
            display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2px',
            borderRadius: '16px', overflow: 'hidden',
            border: '1px solid var(--border-default)',
            boxShadow: '0 0 60px rgba(0,216,255,0.06)',
          }}>
            {/* Request */}
            <div style={{ background: 'var(--bg-surface)', padding: '28px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
                <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#FF4560' }} />
                <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#FFC945' }} />
                <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#00FF88' }} />
                <span style={{ marginLeft: '8px', fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--text-muted)' }}>
                  request.json
                </span>
              </div>
              <pre className="code-block" style={{ margin: 0, background: 'transparent', border: 'none', padding: 0, fontSize: '12px', lineHeight: '1.7' }}>
                <span style={{ color: 'var(--cyan)' }}>POST /v1/validate</span>{'\n'}
                <span style={{ color: 'var(--text-muted)' }}>X-API-Key: tc_live_...</span>{'\n\n'}
                <span style={{ color: '#E8EAED' }}>{`{
  "output": { "hours": 30, "rate": "invalid" },
  "rules": [
    {
      "type": "range", "field": "hours",
      "min": 0, "max": 24,
      "severity": "error"
    }
  ],
  "context": {
    "auto_correct": true,
    "calculate_confidence": true
  }
}`}</span>
              </pre>
            </div>

            {/* Response */}
            <div style={{ background: 'var(--bg-elevated)', padding: '28px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
                <span className="badge-invalid">VALIDATION FAILED</span>
                <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--green)' }}>→ AUTO-CORRECTED</span>
              </div>
              <pre className="code-block" style={{ margin: 0, background: 'transparent', border: 'none', padding: 0, fontSize: '12px', lineHeight: '1.7' }}>
                <span style={{ color: 'var(--text-muted)' }}>{`{
  "validation_id": "`}</span><span style={{ color: 'var(--cyan)' }}>val_9f4c2e...</span><span style={{ color: 'var(--text-muted)' }}>{`",
  "status": "`}</span><span style={{ color: 'var(--red)' }}>failed</span><span style={{ color: 'var(--text-muted)' }}>{`",
  "confidence_score": `}</span><span style={{ color: 'var(--amber)' }}>0.65</span><span style={{ color: 'var(--text-muted)' }}>{`,
  "violations": [{
    "field": `}</span><span style={{ color: 'var(--cyan)' }}>"hours"</span><span style={{ color: 'var(--text-muted)' }}>{`,
    "message": "Value 30 exceeds max 24"
  }],
  "auto_corrected": `}</span><span style={{ color: 'var(--green)' }}>true</span><span style={{ color: 'var(--text-muted)' }}>{`,
  "corrected_output": { "hours": `}</span><span style={{ color: 'var(--green)' }}>24.0</span><span style={{ color: 'var(--text-muted)' }}>{` },
  "latency_ms": `}</span><span style={{ color: 'var(--amber)' }}>12</span>
              </pre>
            </div>
          </div>
        </div>
      </section>

      {/* ── Features ─────────────────────────────────────────────────── */}
      <section style={{ padding: '0 40px 100px' }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: '60px' }}>
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--text-muted)', letterSpacing: '0.15em', marginBottom: '12px' }}>
              CAPABILITIES
            </p>
            <h2 style={{ fontFamily: 'Syne, sans-serif', fontWeight: 800, fontSize: 'clamp(28px, 4vw, 44px)', letterSpacing: '-0.03em', color: 'var(--text-primary)' }}>
              Everything AI outputs need
            </h2>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '16px' }}>
            {features.map(({ icon: Icon, title, desc, accent }) => (
              <div key={title} className="glass-card" style={{ padding: '28px', position: 'relative', overflow: 'hidden' }}>
                <div style={{
                  position: 'absolute', top: 0, left: 0, right: 0, height: '1px',
                  background: `linear-gradient(90deg, ${accent}44, transparent)`,
                }} />
                <div style={{
                  width: '36px', height: '36px', borderRadius: '10px',
                  background: `${accent}18`, display: 'flex', alignItems: 'center', justifyContent: 'center',
                  marginBottom: '16px', border: `1px solid ${accent}30`,
                }}>
                  <Icon size={18} color={accent} strokeWidth={2} />
                </div>
                <h3 style={{ fontFamily: 'Syne, sans-serif', fontWeight: 700, fontSize: '15px', color: 'var(--text-primary)', marginBottom: '8px' }}>
                  {title}
                </h3>
                <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                  {desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Pricing ──────────────────────────────────────────────────── */}
      <section style={{ padding: '0 40px 100px' }}>
        <div style={{ maxWidth: '1000px', margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: '60px' }}>
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--text-muted)', letterSpacing: '0.15em', marginBottom: '12px' }}>
              PRICING
            </p>
            <h2 style={{ fontFamily: 'Syne, sans-serif', fontWeight: 800, fontSize: 'clamp(28px, 4vw, 44px)', letterSpacing: '-0.03em', color: 'var(--text-primary)' }}>
              Simple, transparent plans
            </h2>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px' }}>
            {tiers.map(({ name, price, rpm, quota, color, highlight }) => (
              <div key={name} className="glass-card" style={{
                padding: '28px 20px',
                border: highlight ? `1px solid ${color}44` : undefined,
                boxShadow: highlight ? `0 0 30px ${color}14` : undefined,
                position: 'relative', overflow: 'hidden',
              }}>
                {highlight && (
                  <div style={{
                    position: 'absolute', top: 0, left: 0, right: 0, height: '2px',
                    background: `linear-gradient(90deg, transparent, ${color}, transparent)`,
                  }} />
                )}
                {highlight && (
                  <div style={{
                    position: 'absolute', top: '10px', right: '10px',
                    fontFamily: 'JetBrains Mono, monospace', fontSize: '9px', fontWeight: 700,
                    color: color, background: `${color}18`, border: `1px solid ${color}30`,
                    padding: '2px 6px', borderRadius: '4px', letterSpacing: '0.1em',
                  }}>POPULAR</div>
                )}
                <p style={{ fontFamily: 'Syne, sans-serif', fontWeight: 700, fontSize: '13px', color, marginBottom: '8px' }}>{name}</p>
                <p style={{ fontFamily: 'JetBrains Mono, monospace', fontWeight: 600, fontSize: '28px', color: 'var(--text-primary)', marginBottom: '16px' }}>
                  {price}
                </p>
                <div style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 2, fontFamily: 'JetBrains Mono, monospace' }}>
                  <div>{rpm} req/min</div>
                  <div>{quota}</div>
                </div>
                <Link href="/signup" style={{ textDecoration: 'none', display: 'block', marginTop: '20px' }}>
                  <button className={highlight ? 'tc-btn-primary' : 'tc-btn-ghost'} style={{ width: '100%', fontSize: '13px', padding: '9px 0' }}>
                    {price === '$0' ? 'Get started free' : 'Choose plan'}
                  </button>
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ──────────────────────────────────────────────────────── */}
      <section style={{ padding: '0 40px 100px' }}>
        <div style={{
          maxWidth: '900px', margin: '0 auto',
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-default)',
          borderRadius: '20px', padding: '80px 60px', textAlign: 'center',
          position: 'relative', overflow: 'hidden',
          boxShadow: '0 0 80px rgba(0,216,255,0.06)',
        }}>
          <div style={{
            position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)',
            width: '500px', height: '300px', borderRadius: '50%',
            background: 'radial-gradient(circle, rgba(0,216,255,0.06) 0%, transparent 70%)',
            filter: 'blur(30px)', pointerEvents: 'none',
          }} />
          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--cyan)', letterSpacing: '0.15em', marginBottom: '16px' }}>
            START VALIDATING TODAY
          </p>
          <h2 style={{ fontFamily: 'Syne, sans-serif', fontWeight: 800, fontSize: 'clamp(28px, 4vw, 48px)', letterSpacing: '-0.03em', color: 'var(--text-primary)', marginBottom: '16px' }}>
            Your AI deserves a<br /><span className="gradient-text-cyan">fact-checker.</span>
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '16px', marginBottom: '36px', maxWidth: '420px', margin: '0 auto 36px' }}>
            Sign up free. No credit card required. Start validating AI outputs in minutes.
          </p>
          <Link href="/signup" style={{ textDecoration: 'none' }}>
            <button className="tc-btn-primary" style={{ fontSize: '15px', padding: '14px 36px', display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
              Create Free Account <ArrowRight size={16} />
            </button>
          </Link>
        </div>
      </section>

      {/* ── Footer ───────────────────────────────────────────────────── */}
      <footer style={{ padding: '40px', borderTop: '1px solid var(--border-subtle)' }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Zap size={14} color="var(--cyan)" />
            <span style={{ fontFamily: 'Syne, sans-serif', fontWeight: 700, fontSize: '13px', color: 'var(--text-muted)' }}>TruthChain</span>
          </div>
          <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--text-muted)' }}>
            AI Validation as a Service · v1.0.0
          </p>
        </div>
      </footer>
    </div>
  );
}
