'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Zap, ArrowRight, Eye, EyeOff, LogIn } from 'lucide-react';
import { publicApi, getApiError } from '@/lib/api';
import { useAuth } from '@/lib/auth';

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim() || !password.trim()) {
      setError('Please enter your email and password');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const res = await publicApi.login({ email: email.trim(), password });
      login(res.api_key, res.name, res.organization_id, res.tier);
      router.push('/dashboard');
    } catch (err) {
      setError(getApiError(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{
      minHeight: '100vh', background: 'var(--bg-void)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: '40px',
    }}>
      {/* Background orb */}
      <div style={{
        position: 'fixed', top: '30%', left: '50%', transform: 'translateX(-50%)',
        width: '600px', height: '400px', borderRadius: '50%',
        background: 'radial-gradient(circle, rgba(0,216,255,0.04) 0%, transparent 70%)',
        filter: 'blur(60px)', pointerEvents: 'none',
      }} />

      <div style={{ width: '100%', maxWidth: '420px', position: 'relative' }}>
        {/* Logo */}
        <Link href="/" style={{ textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '48px', justifyContent: 'center' }}>
          <div style={{
            width: '36px', height: '36px', borderRadius: '10px',
            background: 'linear-gradient(135deg, var(--cyan), #7B61FF)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 0 20px var(--cyan-glow)',
          }}>
            <Zap size={20} color="var(--bg-void)" strokeWidth={3} />
          </div>
          <span style={{ fontFamily: 'Syne, sans-serif', fontWeight: 800, fontSize: '18px', color: 'var(--text-primary)' }}>TruthChain</span>
        </Link>

        {/* Card */}
        <div className="glass-card fade-up" style={{ padding: '40px' }}>
          <div style={{ marginBottom: '32px', textAlign: 'center' }}>
            <div style={{
              width: '48px', height: '48px', borderRadius: '12px',
              background: 'var(--cyan-dim)', display: 'flex', alignItems: 'center', justifyContent: 'center',
              margin: '0 auto 16px', border: '1px solid rgba(0,216,255,0.2)',
            }}>
              <LogIn size={22} color="var(--cyan)" />
            </div>
            <h1 style={{ fontFamily: 'Syne, sans-serif', fontWeight: 800, fontSize: '24px', letterSpacing: '-0.03em', color: 'var(--text-primary)', marginBottom: '8px' }}>
              Sign in to TruthChain
            </h1>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
              Enter your email and password to access your dashboard
            </p>
          </div>

          <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {/* Email */}
            <div>
              <label style={{
                display: 'block', fontSize: '11px', fontWeight: 700,
                color: 'var(--text-muted)', marginBottom: '6px',
                letterSpacing: '0.1em', fontFamily: 'JetBrains Mono, monospace',
              }}>
                EMAIL
              </label>
              <input
                className="tc-input"
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="admin@acme.com"
                autoComplete="email"
              />
            </div>

            {/* Password */}
            <div>
              <label style={{
                display: 'block', fontSize: '11px', fontWeight: 700,
                color: 'var(--text-muted)', marginBottom: '6px',
                letterSpacing: '0.1em', fontFamily: 'JetBrains Mono, monospace',
              }}>
                PASSWORD
              </label>
              <div style={{ position: 'relative' }}>
                <input
                  className="tc-input"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••"
                  autoComplete="current-password"
                  style={{ paddingRight: '44px' }}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(p => !p)}
                  style={{
                    position: 'absolute', right: '12px', top: '50%', transform: 'translateY(-50%)',
                    background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: '0',
                  }}
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
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

            <button
              type="submit"
              disabled={loading}
              className="tc-btn-primary"
              style={{ width: '100%', padding: '13px', fontSize: '14px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', marginTop: '4px' }}
            >
              {loading ? 'Signing in...' : <>Sign in <ArrowRight size={16} /></>}
            </button>
          </form>

          <div style={{ marginTop: '24px', paddingTop: '24px', borderTop: '1px solid var(--border-subtle)', textAlign: 'center' }}>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
              Don&apos;t have an account?{' '}
              <Link href="/signup" style={{ color: 'var(--cyan)', textDecoration: 'none', fontWeight: 600 }}>Create one free</Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
