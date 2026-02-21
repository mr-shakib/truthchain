'use client';

import { useEffect, useState, useCallback } from 'react';
import { useAuth } from '@/lib/auth';
import { createAuthApi, getApiError } from '@/lib/api';
import type { ApiKey, CreateApiKeyResponse } from '@/lib/types';
import { formatDateTime } from '@/lib/utils';
import { Plus, Copy, RefreshCw, Trash2, KeyRound, Eye, EyeOff, CheckCircle2, AlertTriangle } from 'lucide-react';

export default function ApiKeysPage() {
  const { apiKey } = useAuth();
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [newKeyName, setNewKeyName] = useState('');
  const [creating, setCreating] = useState(false);
  const [newlyCreated, setNewlyCreated] = useState<CreateApiKeyResponse | null>(null);
  const [showNewKey, setShowNewKey] = useState(false);
  const [copied, setCopied] = useState('');
  const [rotatingId, setRotatingId] = useState('');
  const [deletingId, setDeletingId] = useState('');
  const [showPrefix, setShowPrefix] = useState<Record<string, boolean>>({});

  const fetchKeys = useCallback(async () => {
    if (!apiKey) return;
    setError('');
    try {
      const api = createAuthApi(apiKey);
      const data = await api.listApiKeys();
      setKeys(data);
    } catch (err) {
      setError(getApiError(err));
    } finally {
      setLoading(false);
    }
  }, [apiKey]);

  useEffect(() => { fetchKeys(); }, [fetchKeys]);

  async function handleCreate() {
    if (!apiKey) return;
    setCreating(true);
    setError('');
    try {
      const api = createAuthApi(apiKey);
      const created = await api.createApiKey({ name: newKeyName || undefined });
      setNewlyCreated(created);
      setNewKeyName('');
      setShowNewKey(true);
      await fetchKeys();
    } catch (err) {
      setError(getApiError(err));
    } finally {
      setCreating(false);
    }
  }

  async function handleRotate(id: string) {
    if (!apiKey) return;
    setRotatingId(id);
    setError('');
    try {
      const api = createAuthApi(apiKey);
      const res = await api.rotateApiKey(id);
      // res is directly a CreateApiKeyResponse (flat APIKeyResponse from backend)
      setNewlyCreated(res);
      setShowNewKey(true);
      await fetchKeys();
    } catch (err) {
      setError(getApiError(err));
    } finally {
      setRotatingId('');
    }
  }

  async function handleRevoke(id: string) {
    if (!apiKey) return;
    setDeletingId(id);
    setError('');
    try {
      const api = createAuthApi(apiKey);
      await api.revokeApiKey(id);
      await fetchKeys();
    } catch (err) {
      setError(getApiError(err));
    } finally {
      setDeletingId('');
    }
  }

  function copyToClipboard(text: string, id: string) {
    navigator.clipboard.writeText(text);
    setCopied(id);
    setTimeout(() => setCopied(''), 2000);
  }

  return (
    <div style={{ padding: '40px', maxWidth: '900px' }}>
      {/* Header */}
      <div className="fade-up" style={{ marginBottom: '32px' }}>
        <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--text-muted)', letterSpacing: '0.1em', marginBottom: '6px' }}>
          AUTHENTICATION
        </p>
        <h1 style={{ fontFamily: 'Syne, sans-serif', fontWeight: 800, fontSize: '28px', letterSpacing: '-0.02em', color: 'var(--text-primary)', marginBottom: '8px' }}>
          API Keys
        </h1>
        <p style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>
          Manage API keys for your organization. Keys grant full access — keep them secure.
        </p>
      </div>

      {/* Newly created key reveal */}
      {newlyCreated && showNewKey && (
        <div className="fade-up glass-card" style={{
          padding: '20px', marginBottom: '24px',
          border: '1px solid rgba(0,255,136,0.3)',
          boxShadow: '0 0 20px rgba(0,255,136,0.08)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
            <CheckCircle2 size={16} color="var(--green)" />
            <p style={{ fontFamily: 'Syne, sans-serif', fontWeight: 700, fontSize: '14px', color: 'var(--green)' }}>
              New API key created — copy it now, it won&apos;t be shown again!
            </p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{
              flex: 1, fontFamily: 'JetBrains Mono, monospace', fontSize: '13px',
              background: 'var(--bg-void)', border: '1px solid var(--border-subtle)',
              borderRadius: '8px', padding: '10px 14px', color: 'var(--text-primary)',
              overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
            }}>
              {showNewKey ? newlyCreated.key : '•'.repeat(40)}
            </div>
            <button onClick={() => setShowNewKey(!showNewKey)} className="tc-btn-ghost" style={{ padding: '10px', flexShrink: 0 }}>
              {showNewKey ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
            <button
              onClick={() => copyToClipboard(newlyCreated.key, 'new')}
              className="tc-btn-primary"
              style={{ padding: '10px 16px', flexShrink: 0, display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px' }}
            >
              {copied === 'new' ? <><CheckCircle2 size={14} /> Copied!</> : <><Copy size={14} /> Copy</>}
            </button>
          </div>
          <button
            onClick={() => setNewlyCreated(null)}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', fontSize: '12px', marginTop: '8px', fontFamily: 'Syne, sans-serif' }}
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Create new key */}
      <div className="glass-card fade-up-1" style={{ padding: '20px', marginBottom: '24px' }}>
        <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--text-muted)', letterSpacing: '0.08em', marginBottom: '12px' }}>
          CREATE NEW KEY
        </p>
        <div style={{ display: 'flex', gap: '12px' }}>
          <input
            className="tc-input"
            value={newKeyName}
            onChange={e => setNewKeyName(e.target.value)}
            placeholder="Key name (optional)"
            onKeyDown={e => e.key === 'Enter' && handleCreate()}
            style={{ flex: 1 }}
          />
          <button
            onClick={handleCreate}
            disabled={creating}
            className="tc-btn-primary"
            style={{ display: 'flex', alignItems: 'center', gap: '6px', flexShrink: 0, fontSize: '13px', padding: '10px 20px' }}
          >
            <Plus size={15} />
            {creating ? 'Creating...' : 'Create Key'}
          </button>
        </div>
      </div>

      {error && (
        <div style={{ padding: '12px 16px', borderRadius: '8px', background: 'var(--red-dim)', border: '1px solid rgba(255,69,96,0.2)', marginBottom: '16px' }}>
          <p style={{ color: 'var(--red)', fontSize: '13px' }}>⚠ {error}</p>
        </div>
      )}

      {/* Keys list */}
      <div className="glass-card fade-up-2" style={{ overflow: 'hidden' }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <KeyRound size={14} color="var(--cyan)" />
          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--text-muted)', letterSpacing: '0.08em' }}>
            ALL KEYS ({keys.filter(k => k.is_active).length} active)
          </span>
        </div>

        {loading ? (
          <div style={{ padding: '40px', textAlign: 'center' }}>
            <RefreshCw size={20} color="var(--text-muted)" style={{ animation: 'spin 0.8s linear infinite', margin: '0 auto' }} />
          </div>
        ) : keys.length === 0 ? (
          <div style={{ padding: '40px', textAlign: 'center' }}>
            <KeyRound size={28} color="var(--text-muted)" style={{ margin: '0 auto 12px', opacity: 0.3 }} />
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '12px', color: 'var(--text-muted)' }}>No API keys found</p>
          </div>
        ) : (
          <div>
            {keys.map((key, i) => (
              <div key={key.id} style={{
                padding: '16px 20px',
                borderBottom: i < keys.length - 1 ? '1px solid var(--border-subtle)' : 'none',
                display: 'flex', alignItems: 'center', gap: '16px',
                opacity: key.is_active ? 1 : 0.5,
              }}>
                {/* Active indicator */}
                <div style={{
                  width: '8px', height: '8px', borderRadius: '50%', flexShrink: 0,
                  background: key.is_active ? 'var(--green)' : 'var(--text-muted)',
                  boxShadow: key.is_active ? '0 0 8px rgba(0,255,136,0.4)' : 'none',
                }} />

                {/* Key info */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                    <span style={{ fontFamily: 'Syne, sans-serif', fontWeight: 700, fontSize: '13px', color: 'var(--text-primary)' }}>
                      {key.name || 'Unnamed key'}
                    </span>
                    {!key.is_active && (
                      <span style={{
                        fontFamily: 'JetBrains Mono, monospace', fontSize: '9px', color: 'var(--red)',
                        background: 'var(--red-dim)', border: '1px solid rgba(255,69,96,0.2)',
                        padding: '2px 6px', borderRadius: '4px', letterSpacing: '0.1em',
                      }}>REVOKED</span>
                    )}
                  </div>
                  <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
                    <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--cyan)' }}>
                      {key.key_prefix
                        ? (showPrefix[key.id]
                            ? key.key_prefix
                            : `${key.key_prefix.slice(0, 12)}•••`)
                        : 'tc_live_•••••••••••• (rotate to reveal prefix)'}
                    </span>
                    <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '10px', color: 'var(--text-muted)' }}>
                      Created {formatDateTime(key.created_at)}
                    </span>
                    {key.last_used_at && (
                      <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '10px', color: 'var(--text-muted)' }}>
                        Last used {formatDateTime(key.last_used_at)}
                      </span>
                    )}
                  </div>
                </div>

                {/* Actions */}
                {key.is_active && (
                  <div style={{ display: 'flex', gap: '8px', flexShrink: 0 }}>
                    <button
                      onClick={() => key.key_prefix && copyToClipboard(key.key_prefix, key.id)}
                      className="tc-btn-ghost"
                      style={{ padding: '7px 12px', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '5px', opacity: key.key_prefix ? 1 : 0.4, cursor: key.key_prefix ? 'pointer' : 'not-allowed' }}
                      title={key.key_prefix ? `Copy: ${key.key_prefix}` : 'Rotate this key to get a copyable prefix'}
                    >
                      {copied === key.id ? <CheckCircle2 size={13} color="var(--green)" /> : <Copy size={13} />}
                    </button>
                    <button
                      onClick={() => handleRotate(key.id)}
                      disabled={rotatingId === key.id}
                      className="tc-btn-ghost"
                      style={{ padding: '7px 12px', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '5px' }}
                      title="Rotate key"
                    >
                      <RefreshCw size={13} style={rotatingId === key.id ? { animation: 'spin 0.8s linear infinite' } : {}} />
                      Rotate
                    </button>
                    <button
                      onClick={() => handleRevoke(key.id)}
                      disabled={deletingId === key.id}
                      className="tc-btn-danger"
                      style={{ display: 'flex', alignItems: 'center', gap: '5px' }}
                      title="Revoke key"
                    >
                      <Trash2 size={13} />
                      Revoke
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Security note */}
      <div style={{
        marginTop: '16px', padding: '14px 16px', borderRadius: '8px',
        background: 'var(--amber-dim)', border: '1px solid rgba(255,201,69,0.2)',
        display: 'flex', gap: '10px', alignItems: 'flex-start',
      }}>
        <AlertTriangle size={14} color="var(--amber)" style={{ flexShrink: 0, marginTop: '2px' }} />
        <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--amber)', lineHeight: 1.6 }}>
          Never expose API keys in client-side code or public repositories. Use environment variables in production.
        </p>
      </div>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
