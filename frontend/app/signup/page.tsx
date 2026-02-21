'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Zap, Eye, EyeOff, ArrowRight, CheckCircle2, Copy, Check, ShieldAlert } from 'lucide-react';
import { publicApi, getApiError } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import type { Tier } from '@/lib/types';

const schema = z.object({
  name: z.string().min(2, 'Organization name must be at least 2 characters'),
  email: z.string().email('Enter a valid email'),
  password: z.string().min(8, 'Password must be at least 8 characters')
    .regex(/[A-Z]/, 'Must contain uppercase letter')
    .regex(/[0-9]/, 'Must contain a number')
    .regex(/[!@#$%^&*]/, 'Must contain a special character'),
  tier: z.enum(['free', 'startup', 'business', 'enterprise'] as const),
});

type FormData = z.infer<typeof schema>;

const tierOptions: { value: Tier; label: string; rpm: string; quota: string; color: string }[] = [
  { value: 'free', label: 'Free', rpm: '10 req/min', quota: '1K/mo', color: 'var(--text-muted)' },
  { value: 'startup', label: 'Startup', rpm: '30 req/min', quota: '10K/mo', color: 'var(--cyan)' },
  { value: 'business', label: 'Business', rpm: '100 req/min', quota: '100K/mo', color: 'var(--purple)' },
  { value: 'enterprise', label: 'Enterprise', rpm: '500 req/min', quota: '1M/mo', color: 'var(--amber)' },
];

export default function SignupPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [apiKeyResult, setApiKeyResult] = useState<string | null>(null);
  const [orgNameResult, setOrgNameResult] = useState('');
  const [copied, setCopied] = useState(false);

  const { register, handleSubmit, watch, setValue, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { tier: 'free' },
  });

  const selectedTier = watch('tier');

  async function onSubmit(data: FormData) {
    setError('');
    try {
      const res = await publicApi.signup(data);
      // Store auth immediately so dashboard works, but show key first
      login(res.api_key, res.name, res.organization_id, res.tier);
      setOrgNameResult(res.name);
      setApiKeyResult(res.api_key);
    } catch (err) {
      setError(getApiError(err));
    }
  }

  async function copyKey() {
    if (!apiKeyResult) return;
    await navigator.clipboard.writeText(apiKeyResult);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  }

  return (
    <div style={{
      minHeight: '100vh', background: 'var(--bg-void)',
      display: 'flex', alignItems: 'stretch',
    }}>
      {/* Left panel */}
      <div className="grid-texture" style={{
        flex: 1, padding: '60px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
        borderRight: '1px solid var(--border-subtle)', maxWidth: '480px',
        position: 'relative', overflow: 'hidden',
      }}>
        <div style={{
          position: 'absolute', bottom: '10%', left: '-10%',
          width: '400px', height: '400px', borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(0,216,255,0.06) 0%, transparent 70%)',
          filter: 'blur(40px)', pointerEvents: 'none',
        }} />
        <Link href="/" style={{ textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            width: '32px', height: '32px', borderRadius: '8px',
            background: 'linear-gradient(135deg, var(--cyan), #7B61FF)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 0 16px var(--cyan-glow)',
          }}>
            <Zap size={18} color="var(--bg-void)" strokeWidth={3} />
          </div>
          <span style={{ fontFamily: 'Syne, sans-serif', fontWeight: 800, fontSize: '16px', color: 'var(--text-primary)' }}>TruthChain</span>
        </Link>

        <div>
          <h2 style={{ fontFamily: 'Syne, sans-serif', fontWeight: 800, fontSize: '32px', letterSpacing: '-0.03em', color: 'var(--text-primary)', marginBottom: '16px', lineHeight: 1.2 }}>
            AI outputs, validated.
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '14px', lineHeight: 1.7, marginBottom: '40px' }}>
            Join thousands of engineers using TruthChain to keep AI-generated data reliable, accurate, and within bounds.
          </p>
          {[
            'Sub-20ms validation latency',
            'Auto-correct out-of-bounds values',
            'Anomaly & hallucination detection',
            'Full audit logging & analytics',
          ].map((item) => (
            <div key={item} style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px' }}>
              <CheckCircle2 size={14} color="var(--green)" />
              <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>{item}</span>
            </div>
          ))}
        </div>

        <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--text-muted)' }}>
          AI Validation as a Service · v1.0.0
        </p>
      </div>

      {/* Right form panel */}
      <div style={{
        flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '60px 40px',
      }}>
        <div style={{ width: '100%', maxWidth: '440px' }}>
          <div className="fade-up" style={{ marginBottom: '32px' }}>
            <h1 style={{ fontFamily: 'Syne, sans-serif', fontWeight: 800, fontSize: '28px', letterSpacing: '-0.03em', color: 'var(--text-primary)', marginBottom: '8px' }}>
              Create your account
            </h1>
            <p style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>
              Already have an account?{' '}
              <Link href="/login" style={{ color: 'var(--cyan)', textDecoration: 'none', fontWeight: 600 }}>Sign in</Link>
            </p>
          </div>

          {apiKeyResult ? (
            <div className="fade-up" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              {/* Success header */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '16px 20px', borderRadius: '12px', background: 'var(--green-dim)', border: '1px solid rgba(0,255,136,0.2)' }}>
                <CheckCircle2 size={20} color="var(--green)" style={{ flexShrink: 0 }} />
                <div>
                  <p style={{ color: 'var(--green)', fontWeight: 700, fontSize: '14px' }}>Account created!</p>
                  <p style={{ color: 'var(--text-secondary)', fontSize: '12px', marginTop: '2px' }}>Welcome, {orgNameResult}</p>
                </div>
              </div>

              {/* API key reveal */}
              <div style={{ padding: '20px', borderRadius: '12px', background: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                  <ShieldAlert size={14} color="var(--amber)" />
                  <p style={{ fontSize: '11px', fontWeight: 700, color: 'var(--amber)', letterSpacing: '0.08em', fontFamily: 'JetBrains Mono, monospace' }}>SAVE THIS API KEY — SHOWN ONLY ONCE</p>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '12px 14px', borderRadius: '8px', background: 'var(--bg-void)', border: '1px solid var(--border-subtle)' }}>
                  <p style={{ flex: 1, fontFamily: 'JetBrains Mono, monospace', fontSize: '12px', color: 'var(--cyan)', wordBreak: 'break-all' }}>{apiKeyResult}</p>
                  <button type="button" onClick={copyKey} style={{
                    flexShrink: 0, padding: '6px', border: '1px solid var(--border-default)', borderRadius: '6px',
                    background: copied ? 'var(--green-dim)' : 'var(--bg-elevated)', cursor: 'pointer',
                    color: copied ? 'var(--green)' : 'var(--text-muted)', transition: 'all 0.15s',
                  }}>
                    {copied ? <Check size={14} /> : <Copy size={14} />}
                  </button>
                </div>
                <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '10px' }}>
                  This key grants full API access. Store it in your environment variables or password manager.
                </p>
              </div>

              <button
                onClick={() => router.push('/dashboard')}
                className="tc-btn-primary"
                style={{ width: '100%', padding: '13px', fontSize: '14px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}
              >
                Go to Dashboard <ArrowRight size={16} />
              </button>
            </div>
          ) : (
            <form className="fade-up-1" onSubmit={handleSubmit(onSubmit)} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {/* Org name */}
              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '6px', letterSpacing: '0.08em', fontFamily: 'JetBrains Mono, monospace' }}>
                  ORGANIZATION NAME
                </label>
                <input {...register('name')} className="tc-input" placeholder="Acme AI" />
                {errors.name && <p style={{ fontSize: '12px', color: 'var(--red)', marginTop: '4px' }}>{errors.name.message}</p>}
              </div>

              {/* Email */}
              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '6px', letterSpacing: '0.08em', fontFamily: 'JetBrains Mono, monospace' }}>
                  EMAIL
                </label>
                <input {...register('email')} className="tc-input" type="email" placeholder="admin@acme.com" />
                {errors.email && <p style={{ fontSize: '12px', color: 'var(--red)', marginTop: '4px' }}>{errors.email.message}</p>}
              </div>

              {/* Password */}
              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '6px', letterSpacing: '0.08em', fontFamily: 'JetBrains Mono, monospace' }}>
                  PASSWORD
                </label>
                <div style={{ position: 'relative' }}>
                  <input {...register('password')} className="tc-input" type={showPassword ? 'text' : 'password'} placeholder="Min 8 chars, uppercase, number, symbol" style={{ paddingRight: '44px' }} />
                  <button type="button" onClick={() => setShowPassword(p => !p)} style={{
                    position: 'absolute', right: '12px', top: '50%', transform: 'translateY(-50%)',
                    background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: '0',
                  }}>
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
                {errors.password && <p style={{ fontSize: '12px', color: 'var(--red)', marginTop: '4px' }}>{errors.password.message}</p>}
              </div>

              {/* Tier */}
              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '8px', letterSpacing: '0.08em', fontFamily: 'JetBrains Mono, monospace' }}>
                  PLAN
                </label>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                  {tierOptions.map(({ value, label, rpm, quota, color }) => {
                    const selected = selectedTier === value;
                    return (
                      <button key={value} type="button" onClick={() => setValue('tier', value)} style={{
                        padding: '12px', borderRadius: '8px', cursor: 'pointer', textAlign: 'left',
                        background: selected ? `${color}18` : 'var(--bg-elevated)',
                        border: `1px solid ${selected ? `${color}44` : 'var(--border-default)'}`,
                        transition: 'all 0.15s',
                      }}>
                        <p style={{ fontFamily: 'Syne, sans-serif', fontWeight: 700, fontSize: '13px', color, marginBottom: '4px' }}>{label}</p>
                        <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '10px', color: 'var(--text-muted)' }}>{rpm}</p>
                        <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '10px', color: 'var(--text-muted)' }}>{quota}</p>
                      </button>
                    );
                  })}
                </div>
              </div>

              {error && (
                <div style={{
                  padding: '12px 16px', borderRadius: '8px',
                  background: 'var(--red-dim)', border: '1px solid rgba(255,69,96,0.2)',
                  fontSize: '13px', color: 'var(--red)',
                }}>
                  {error}
                </div>
              )}

              <button type="submit" disabled={isSubmitting} className="tc-btn-primary"
                style={{ width: '100%', fontSize: '14px', padding: '13px', marginTop: '4px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
                {isSubmitting ? 'Creating account...' : <>Create account <ArrowRight size={16} /></>}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
