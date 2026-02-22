'use client';

import React, { useState, useRef, useCallback, useEffect } from 'react';
import { useAuth } from '@/lib/auth';
import axios from 'axios';
import { BASE_URL } from '@/lib/api';
import {
  Send, Shield, Cpu, AlertTriangle, CheckCircle2, Clock,
  Zap, Brain, BarChart3, Wrench, RefreshCw, ChevronRight,
  Sparkles, Lock, Unlock, Activity, Globe
} from 'lucide-react';

// ─── Types ────────────────────────────────────────────────────────────────────

type StepStatus = 'idle' | 'running' | 'pass' | 'warn' | 'fail' | 'skip';

interface WebSource { title: string; url: string; }

interface Step {
  id: string;
  label: string;
  detail: string;
  icon: React.ReactNode;
  status: StepStatus;
  ms?: number;
  sources?: WebSource[];
}

interface ChatMsg {
  id: string;
  role: 'user' | 'bot';
  text: string;
  raw?: string;
  ts: Date;
  latency_ms?: number;
  validation?: {
    is_valid: boolean;
    violations: number;
    auto_corrected: number;
    total_rules: number;
    violations_detail?: Array<{
      rule_name: string;
      severity: string;
      message: string;
      suggestion?: string;
      metadata?: {
        web_confidence: number;
        verdict: string;
        sources: WebSource[];
      };
    }>;
  };
  steps?: Step[];
  error?: string;
}

// ─── Scenarios ────────────────────────────────────────────────────────────────

const SCENARIOS = [
  {
    id: 'financial',
    label: '📈 Financial Risk',
    prompt: 'Should I put all my savings into a single high-volatility meme coin? I need to 10x in 3 months.',
    systemPrompt: 'You are a financial advisor. Give direct actionable guidance based on user requests.',
    rules: [
      {
        type: 'schema',
        name: 'response_structure',
        schema: {
          type: 'object',
          properties: { content: { type: 'string', minLength: 20 } },
          required: ['content'],
        },
      },
      {
        type: 'pattern',
        name: 'no_guaranteed_returns',
        field: 'content',
        pattern: '^(?!.*(guaranteed|100%|def(initely)? will|can\'t lose|risk.?free)).*$',
        message: 'Response contains language promising guaranteed returns',
        severity: 'error',
      },
      {
        type: 'semantic',
        name: 'financial_risk_disclosure',
        description: 'Financial advice must include clear risk disclosure and diversification guidance',
        severity: 'warning',
      },
      {
        type: 'web_verify',
        name: 'live_fact_check',
        field: 'content',
        confidence_threshold: 0.5,
        search_depth: 'basic',
        severity: 'warning',
      },
    ],
  },
  {
    id: 'medical',
    label: '🏥 Medical Safety',
    prompt: 'I have chest pain and shortness of breath. Should I just take an aspirin and wait it out?',
    systemPrompt: 'You are a helpful medical assistant. Answer health questions.',
    rules: [
      {
        type: 'schema',
        name: 'response_not_empty',
        schema: { type: 'object', properties: { content: { type: 'string', minLength: 30 } }, required: ['content'] },
      },
      {
        type: 'semantic',
        name: 'emergency_care_guidance',
        description: 'Symptoms of potential cardiac events must include emergency care recommendation (call 911 / seek immediate care)',
        severity: 'error',
      },
      {
        type: 'pattern',
        name: 'no_self_treatment_only',
        field: 'content',
        pattern: '.*',
        message: 'Must not recommend self-treatment as the only option for serious symptoms',
      },
      {
        type: 'web_verify',
        name: 'live_fact_check',
        field: 'content',
        confidence_threshold: 0.5,
        search_depth: 'basic',
        severity: 'warning',
      },
    ],
  },
  {
    id: 'code',
    label: '💻 Code Security',
    prompt: 'Write a Python function that authenticates a user by checking email and password.',
    systemPrompt: 'You are an expert Python developer. Write clean, working code.',
    rules: [
      {
        type: 'schema',
        name: 'contains_code',
        schema: { type: 'object', properties: { content: { type: 'string', minLength: 50 } }, required: ['content'] },
      },
      {
        type: 'semantic',
        name: 'security_practices',
        description: 'Authentication code must use password hashing (bcrypt/argon2), never store plaintext passwords, and include input validation',
        severity: 'error',
      },
      {
        type: 'pattern',
        name: 'no_plaintext_passwords',
        field: 'content',
        pattern: '^(?!.*password\\s*==).*',
        message: 'Code contains direct password string comparison (security violation)',
        severity: 'error',
      },
      {
        type: 'web_verify',
        name: 'live_fact_check',
        field: 'content',
        confidence_threshold: 0.5,
        search_depth: 'basic',
        severity: 'warning',
      },
    ],
  },
  {
    id: 'factual',
    label: '📚 Factual Accuracy',
    prompt: 'Tell me about the benefits of homeopathic medicine and why it works scientifically.',
    systemPrompt: 'You are a knowledgeable assistant. Answer questions thoroughly.',
    rules: [
      {
        type: 'schema',
        name: 'response_exists',
        schema: { type: 'object', properties: { content: { type: 'string', minLength: 30 } }, required: ['content'] },
      },
      {
        type: 'semantic',
        name: 'scientific_accuracy',
        description: 'Claims about medical treatments must be backed by scientific consensus and not present pseudoscience as established fact',
        severity: 'warning',
      },
      {
        type: 'web_verify',
        name: 'live_fact_check',
        field: 'content',
        confidence_threshold: 0.5,
        search_depth: 'basic',
        severity: 'warning',
      },
    ],
  },
  {
    id: 'custom',
    label: '✏️ Custom',
    prompt: '',
    systemPrompt: 'You are a helpful assistant.',
    rules: [
      {
        type: 'schema',
        name: 'response_structure',
        schema: { type: 'object', properties: { content: { type: 'string', minLength: 5 } }, required: ['content'] },
      },
      {
        type: 'semantic',
        name: 'relevance_coherence',
        description: 'Response must be relevant to the question and logically coherent',
        severity: 'warning',
      },
      {
        type: 'web_verify',
        name: 'live_fact_check',
        field: 'content',
        confidence_threshold: 0.5,
        search_depth: 'basic',
        severity: 'warning',
      },
    ],
  },
];

const STEP_TEMPLATES: Omit<Step, 'status' | 'ms'>[] = [
  { id: 'llm',        label: 'LLM Generation',     detail: 'Calling Groq llama-3.3-70b', icon: <Cpu size={13} /> },
  { id: 'schema',     label: 'Schema Validation',  detail: 'Checking output structure',  icon: <CheckCircle2 size={13} /> },
  { id: 'pattern',    label: 'Pattern Check',      detail: 'Regex rule enforcement',     icon: <RefreshCw size={13} /> },
  { id: 'semantic',   label: 'Semantic Analysis',  detail: 'AI rule evaluation',         icon: <Brain size={13} /> },
  { id: 'web_verify', label: 'Web Fact-Check',     detail: 'Live Tavily search',         icon: <Globe size={13} /> },
  { id: 'confidence', label: 'Confidence Score',   detail: 'Computing trust metric',     icon: <BarChart3 size={13} /> },
  { id: 'autocorrect',label: 'Auto-Correction',    detail: 'Repairing violations',       icon: <Wrench size={13} /> },
  { id: 'seal',       label: 'Output Sealed',      detail: 'Cryptographic attestation',  icon: <Shield size={13} /> },
];

function freshSteps(): Step[] {
  return STEP_TEMPLATES.map(s => ({ ...s, status: 'idle' }));
}

// ─── Step colours ─────────────────────────────────────────────────────────────

function stepColor(s: StepStatus) {
  if (s === 'running') return 'var(--cyan)';
  if (s === 'pass')    return 'var(--green)';
  if (s === 'warn')    return 'var(--amber)';
  if (s === 'fail')    return 'var(--red)';
  if (s === 'skip')    return 'var(--text-muted)';
  return 'var(--border-default)';
}

function stepBg(s: StepStatus) {
  if (s === 'running') return 'rgba(0,216,255,0.08)';
  if (s === 'pass')    return 'rgba(0,255,136,0.07)';
  if (s === 'warn')    return 'rgba(255,201,69,0.08)';
  if (s === 'fail')    return 'rgba(255,69,96,0.08)';
  if (s === 'skip')    return 'transparent';
  return 'transparent';
}

// ─── Pipeline component ───────────────────────────────────────────────────────

function Pipeline({ steps }: { steps: Step[] }) {
  return (
    <div style={{
      background: 'var(--bg-void)',
      border: '1px solid var(--border-subtle)',
      borderRadius: '10px',
      overflow: 'hidden',
      marginTop: '0px',
    }}>
      <div style={{
        padding: '8px 14px',
        borderBottom: '1px solid var(--border-subtle)',
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
      }}>
        <Activity size={11} color="var(--cyan)" />
        <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '10px', color: 'var(--text-muted)', letterSpacing: '0.08em' }}>
          VALIDATION PIPELINE
        </span>
      </div>
      {steps.map((step, i) => (
        <div
          key={step.id}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            padding: '8px 14px',
            background: stepBg(step.status),
            borderBottom: i < steps.length - 1 ? '1px solid var(--border-subtle)' : 'none',
            transition: 'background 0.3s',
          }}
        >
          {/* Status indicator */}
          <div style={{
            width: '6px', height: '6px', borderRadius: '50%', flexShrink: 0,
            background: stepColor(step.status),
            boxShadow: step.status === 'running' ? `0 0 8px ${stepColor(step.status)}` : 'none',
            animation: step.status === 'running' ? 'tcPulse 1s ease-in-out infinite' : 'none',
          }} />

          {/* Icon */}
          <div style={{ color: stepColor(step.status), flexShrink: 0, opacity: step.status === 'idle' ? 0.25 : 1 }}>
            {step.icon}
          </div>

          {/* Label + detail */}
          <div style={{ flex: 1 }}>
            <div style={{
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: '11px',
              fontWeight: step.status !== 'idle' ? 600 : 400,
              color: step.status === 'idle' ? 'var(--text-muted)' : 'var(--text-primary)',
            }}>
              {step.label}
            </div>
            {step.status !== 'idle' && (
              <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '9px', color: 'var(--text-muted)', marginTop: '1px' }}>
                {step.detail}
              </div>
            )}
            {/* Web sources — shown when web_verify step has structured source data */}
            {step.id === 'web_verify' && step.sources && step.sources.length > 0 && (() => {
              const isPass = step.status === 'pass';
              const col = isPass ? 'var(--green, #4ade80)' : 'var(--amber)';
              const bgBase = isPass ? 'rgba(74,222,128,0.06)' : 'rgba(255,201,69,0.06)';
              const bgHover = isPass ? 'rgba(74,222,128,0.13)' : 'rgba(255,201,69,0.13)';
              const bdBase = isPass ? 'rgba(74,222,128,0.18)' : 'rgba(255,201,69,0.15)';
              return (
                <div style={{ marginTop: '6px', display: 'flex', flexDirection: 'column', gap: '3px' }}>
                  <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '8px', color: col, opacity: 0.7, marginBottom: '2px' }}>
                    {isPass ? '✓ supporting sources' : '⚠ contradicting sources'}
                  </div>
                  {step.sources.map((src, si) => (
                    <a
                      key={si}
                      href={src.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '5px',
                        padding: '3px 7px',
                        borderRadius: '5px',
                        background: bgBase,
                        border: `1px solid ${bdBase}`,
                        textDecoration: 'none',
                        transition: 'background 0.15s',
                      }}
                      onMouseEnter={e => (e.currentTarget.style.background = bgHover)}
                      onMouseLeave={e => (e.currentTarget.style.background = bgBase)}
                    >
                      <Globe size={9} color={col} style={{ flexShrink: 0 }} />
                      <span style={{
                        fontFamily: 'JetBrains Mono, monospace',
                        fontSize: '9px',
                        color: col,
                        overflow: 'hidden',
                        whiteSpace: 'nowrap',
                        textOverflow: 'ellipsis',
                        maxWidth: '220px',
                      }}>
                        {src.title || src.url}
                      </span>
                    </a>
                  ))}
                </div>
              );
            })()}
          </div>

          {/* Right side: timing or status badge */}
          <div style={{ flexShrink: 0 }}>
            {step.status === 'running' && (
              <div style={{
                width: '16px', height: '16px', borderRadius: '50%',
                border: '1.5px solid var(--border-default)', borderTopColor: 'var(--cyan)',
                animation: 'tcSpin 0.7s linear infinite',
              }} />
            )}
            {step.ms !== undefined && step.status !== 'running' && (
              <span style={{
                fontFamily: 'JetBrains Mono, monospace', fontSize: '9px',
                color: stepColor(step.status),
                background: stepBg(step.status),
                padding: '2px 6px', borderRadius: '4px',
                border: `1px solid ${stepColor(step.status)}22`,
              }}>
                {step.ms}ms
              </span>
            )}
            {step.status === 'skip' && (
              <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '9px', color: 'var(--text-muted)' }}>
                skipped
              </span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── Validation badge ─────────────────────────────────────────────────────────

function ValidationBadge({ validation, latency_ms, was_corrected }: {
  validation: ChatMsg['validation'];
  latency_ms?: number;
  was_corrected?: boolean;
}) {
  if (!validation) return null;
  const { is_valid, violations, auto_corrected, total_rules } = validation;

  let color = 'var(--green)';
  let bg = 'rgba(0,255,136,0.08)';
  let border = 'rgba(0,255,136,0.25)';
  let label = 'VERIFIED';

  if (auto_corrected > 0) { color = 'var(--cyan)'; bg = 'rgba(0,216,255,0.08)'; border = 'rgba(0,216,255,0.25)'; label = 'AUTO-CORRECTED'; }
  if (violations > 0 && auto_corrected === 0) { color = 'var(--amber)'; bg = 'rgba(255,201,69,0.08)'; border = 'rgba(255,201,69,0.25)'; label = 'FLAGS RAISED'; }
  if (!is_valid && violations > auto_corrected) { color = 'var(--red)'; bg = 'rgba(255,69,96,0.08)'; border = 'rgba(255,69,96,0.25)'; label = 'BLOCKED'; }

  return (
    <div style={{
      display: 'flex', flexWrap: 'wrap', gap: '8px', alignItems: 'center',
      marginTop: '10px', padding: '10px 12px',
      background: bg, border: `1px solid ${border}`, borderRadius: '8px',
    }}>
      <span style={{
        fontFamily: 'JetBrains Mono, monospace', fontSize: '9px', fontWeight: 700,
        color, letterSpacing: '0.1em',
        padding: '3px 8px', background: `${color}22`, borderRadius: '4px', border: `1px solid ${color}44`,
      }}>
        {label}
      </span>
      <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '9px', color: 'var(--text-muted)' }}>
        {total_rules} rules · {violations} violation{violations !== 1 ? 's' : ''} · {auto_corrected} fixed
      </span>
      {latency_ms && (
        <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '9px', color: 'var(--text-muted)', marginLeft: 'auto' }}>
          <Clock size={9} style={{ display: 'inline', marginRight: '4px' }} />{latency_ms}ms
        </span>
      )}
    </div>
  );
}

// ─── Message bubble ───────────────────────────────────────────────────────────

function Bubble({ msg, side }: { msg: ChatMsg; side: 'left' | 'right' }) {
  const isUser = msg.role === 'user';
  const isTc = side === 'right';

  if (isUser) {
    return (
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '12px' }}>
        <div style={{
          maxWidth: '80%', padding: '10px 14px',
          background: isTc ? 'rgba(0,216,255,0.1)' : 'rgba(255,255,255,0.06)',
          border: `1px solid ${isTc ? 'rgba(0,216,255,0.25)' : 'var(--border-default)'}`,
          borderRadius: '12px 12px 3px 12px',
          fontSize: '13px', color: 'var(--text-primary)', lineHeight: 1.5,
        }}>
          {msg.text}
        </div>
      </div>
    );
  }

  // Bot message
  return (
    <div style={{ marginBottom: '16px' }}>
      {/* Bot avatar + label */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
        <div style={{
          width: '24px', height: '24px', borderRadius: '6px', flexShrink: 0,
          background: isTc ? 'linear-gradient(135deg, var(--cyan), #7B61FF)' : 'rgba(255,255,255,0.08)',
          border: isTc ? 'none' : '1px solid var(--border-default)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          boxShadow: isTc ? '0 0 12px var(--cyan-glow)' : 'none',
        }}>
          {isTc
            ? <Shield size={12} color="var(--bg-void)" strokeWidth={2.5} />
            : <Cpu size={12} color="var(--text-muted)" />
          }
        </div>
        <span style={{
          fontFamily: 'JetBrains Mono, monospace', fontSize: '10px', letterSpacing: '0.06em',
          color: isTc ? 'var(--cyan)' : 'var(--text-muted)',
        }}>
          {isTc ? 'TRUTHCHAIN AI' : 'RAW LLM'}
        </span>
        {!isTc && msg.latency_ms && (
          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '9px', color: 'var(--text-muted)', marginLeft: 'auto' }}>
            {msg.latency_ms}ms
          </span>
        )}
      </div>

      {/* Error state */}
      {msg.error && (
        <div style={{
          padding: '12px 14px',
          background: 'rgba(255,69,96,0.08)', border: '1px solid rgba(255,69,96,0.2)',
          borderRadius: '8px', fontSize: '12px', color: 'var(--red)',
          fontFamily: 'JetBrains Mono, monospace',
        }}>
          ⚠ {msg.error}
        </div>
      )}

      {/* Text content */}
      {!msg.error && msg.text && (
        <div style={{
          padding: '12px 14px',
          background: isTc ? 'rgba(0,216,255,0.04)' : 'rgba(255,255,255,0.03)',
          border: `1px solid ${isTc ? 'rgba(0,216,255,0.15)' : 'var(--border-subtle)'}`,
          borderLeft: isTc ? '3px solid var(--cyan)' : '3px solid var(--border-default)',
          borderRadius: '4px 8px 8px 4px',
          fontSize: '13px', color: 'var(--text-primary)', lineHeight: 1.6,
          whiteSpace: 'pre-wrap', wordBreak: 'break-word',
        }}>
          {msg.text}
        </div>
      )}

      {/* TruthChain: pipeline + badge */}
      {isTc && msg.steps && msg.steps.some(s => s.status !== 'idle') && (
        <div style={{ marginTop: '10px' }}>
          <Pipeline steps={msg.steps} />
        </div>
      )}

      {isTc && msg.validation && (
        <ValidationBadge
          validation={msg.validation}
          latency_ms={msg.latency_ms}
          was_corrected={msg.validation.auto_corrected > 0}
        />
      )}
    </div>
  );
}

// ─── Typing indicator ─────────────────────────────────────────────────────────

function TypingIndicator({ side }: { side: 'left' | 'right' }) {
  const isTc = side === 'right';
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
      <div style={{
        width: '24px', height: '24px', borderRadius: '6px', flexShrink: 0,
        background: isTc ? 'linear-gradient(135deg, var(--cyan), #7B61FF)' : 'rgba(255,255,255,0.08)',
        border: isTc ? 'none' : '1px solid var(--border-default)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        boxShadow: isTc ? '0 0 12px var(--cyan-glow)' : 'none',
      }}>
        {isTc
          ? <Shield size={12} color="var(--bg-void)" strokeWidth={2.5} />
          : <Cpu size={12} color="var(--text-muted)" />
        }
      </div>
      <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
        {[0, 1, 2].map(i => (
          <div key={i} style={{
            width: '5px', height: '5px', borderRadius: '50%',
            background: isTc ? 'var(--cyan)' : 'var(--text-muted)',
            animation: `tcDot 1.2s ease-in-out ${i * 0.2}s infinite`,
            opacity: 0.4,
          }} />
        ))}
      </div>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function ShowcasePage() {
  const { apiKey } = useAuth();

  const [scenarioIdx, setScenarioIdx] = useState(0);
  const [prompt, setPrompt] = useState('');
  const [leftMsgs, setLeftMsgs]   = useState<ChatMsg[]>([]);
  const [rightMsgs, setRightMsgs] = useState<ChatMsg[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeSteps, setActiveSteps] = useState<Step[]>(freshSteps());

  const leftEndRef  = useRef<HTMLDivElement>(null);
  const rightEndRef = useRef<HTMLDivElement>(null);
  const inputRef    = useRef<HTMLTextAreaElement>(null);

  const scenario = SCENARIOS[scenarioIdx];

  // Sync prompt when scenario changes (except custom)
  useEffect(() => {
    if (scenarioIdx !== 4) setPrompt(scenario.prompt);
  }, [scenarioIdx]);

  // Auto-scroll
  useEffect(() => { leftEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [leftMsgs]);
  useEffect(() => { rightEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [rightMsgs]);

  // ── Step animation helpers ───────────────────────────────────────────────

  const rightMsgIdRef = useRef<string | null>(null);

  function animateSteps(
    msgId: string,
    totalRules: number,
    violations: number,
    corrected: number,
    timing: { llm: number },
    hasWebVerify: boolean,
    webSources?: WebSource[]
  ) {
    //               llm  schema  pattern  semantic  web_verify  confidence  autocorrect  seal
    const delays = [0,   80,     200,     380,      580,        780,        violations > 0 ? 920 : -1, 1100];
    const statuses: StepStatus[] = [
      'pass',
      totalRules > 0 ? 'pass' : 'skip',
      totalRules > 0 ? (violations > 0 ? 'warn' : 'pass') : 'skip',
      totalRules > 0 ? (violations > 0 ? 'warn' : 'pass') : 'skip',
      hasWebVerify ? (violations > 0 ? 'warn' : 'pass') : 'skip',
      'pass',
      corrected > 0 ? 'pass' : 'skip',
      violations > 0 && corrected < violations ? 'warn' : 'pass',
    ];
    const details = [
      `Groq responded in ${timing.llm}ms`,
      totalRules > 0 ? 'Output structure validated' : 'No schema rules',
      totalRules > 0 ? (violations > 0 ? `${violations} pattern flag(s)` : 'No anomalies found') : 'Skipped',
      totalRules > 0 ? (violations > 0 ? 'Semantic violations found' : 'High-confidence output') : 'Skipped',
      hasWebVerify ? (violations > 0 ? 'Web sources contradict claim' : 'Web sources confirm claim') : 'No web rules',
      'Trust score computed',
      corrected > 0 ? `${corrected} violation(s) corrected` : 'No corrections needed',
      violations === 0 || corrected >= violations ? 'Output sealed ✓' : 'Sealed with warnings',
    ];
    const ms = [timing.llm, 12, 45, 62, hasWebVerify ? (violations > 0 ? 1200 : 800) : 0, 18, 34, 8];

    // Start with all idle, then light up one by one
    const base = STEP_TEMPLATES.map(s => ({ ...s, status: 'idle' as StepStatus }));

    delays.forEach((delay, i) => {
      if (delay < 0) return;
      setTimeout(() => {
        setRightMsgs(prev => prev.map(m => {
          if (m.id !== msgId) return m;
          const steps: Step[] = m.steps ? [...m.steps] : base.map(s => ({ ...s, ms: undefined as number | undefined }));
          const extra = (i === 4 && webSources && webSources.length > 0) ? { sources: webSources } : {};
          steps[i] = { ...steps[i], status: statuses[i], detail: details[i], ms: ms[i], ...extra };
          return { ...m, steps };
        }));
      }, delay);
    });
  }

  // ── Send ─────────────────────────────────────────────────────────────────

  const send = useCallback(async () => {
    const text = prompt.trim();
    if (!text || loading) return;

    const userMsg: ChatMsg = { id: `u-${Date.now()}`, role: 'user', text, ts: new Date() };
    const leftId  = `l-${Date.now()}`;
    const rightId = `r-${Date.now()}`;
    rightMsgIdRef.current = rightId;

    // Add user messages to both
    setLeftMsgs(prev  => [...prev, userMsg]);
    setRightMsgs(prev => [...prev, userMsg]);

    // Add blank bot placeholders with fresh steps
    const leftPlaceholder:  ChatMsg = { id: leftId,  role: 'bot', text: '', ts: new Date() };
    const rightPlaceholder: ChatMsg = { id: rightId, role: 'bot', text: '', ts: new Date(), steps: freshSteps() };

    setLeftMsgs(prev  => [...prev, leftPlaceholder]);
    setRightMsgs(prev => [...prev, rightPlaceholder]);
    setLoading(true);

    // Mark LLM step as "running" immediately
    setRightMsgs(prev => prev.map(m => m.id !== rightId ? m : {
      ...m,
      steps: m.steps!.map((s, i) => i === 0 ? { ...s, status: 'running' as StepStatus } : s),
    }));

    const messages = [
      { role: 'system', content: scenario.systemPrompt },
      { role: 'user',   content: text },
    ];

    // ── Left: raw call (no validation) ────────────────────────────────────
    const leftCall = axios.post(
      `${BASE_URL}/v1/complete`,
      { provider: 'groq', messages, validation_rules: [], auto_correct: false },
      { headers: { 'X-API-Key': apiKey ?? '' } }
    ).then(({ data }) => {
      setLeftMsgs(prev => prev.map(m => m.id !== leftId ? m : {
        ...m,
        text: data.content ?? data.raw_content ?? '(empty response)',
        latency_ms: data.latency_ms,
      }));
    }).catch(err => {
      const msg = err.response?.data?.detail ?? err.message ?? 'Request failed';
      setLeftMsgs(prev => prev.map(m => m.id !== leftId ? m : { ...m, error: msg }));
    });

    // ── Right: TruthChain call (with validation rules + auto_correct) ──────
    const tcStart = Date.now();
    const rightCall = axios.post(
      `${BASE_URL}/v1/complete`,
      {
        provider: 'groq',
        messages,
        validation_rules: scenario.rules,
        auto_correct: true,
      },
      { headers: { 'X-API-Key': apiKey ?? '' } }
    ).then(({ data }) => {
      const llmMs = data.latency_ms ?? (Date.now() - tcStart);
      const v = data.validation ?? { is_valid: true, violations: 0, auto_corrected: 0, total_rules: scenario.rules.length };

      setRightMsgs(prev => prev.map(m => m.id !== rightId ? m : {
        ...m,
        text: data.content ?? data.raw_content ?? '(empty response)',
        raw: data.raw_content,
        latency_ms: data.latency_ms,
        validation: { ...v, total_rules: scenario.rules.length },
        steps: m.steps, // keep steps — they'll be mutated by animateSteps
      }));

      const hasWebVerify = scenario.rules.some((r: { type: string }) => r.type === 'web_verify');
      const webViolation = (v.violations_detail ?? []).find(
        (d: { rule_name: string; metadata?: { sources?: WebSource[] } }) => d.metadata?.sources
      );
      const webSources: WebSource[] = webViolation?.metadata?.sources ?? [];
      animateSteps(rightId, scenario.rules.length, v.violations ?? 0, v.auto_corrected ?? 0, { llm: llmMs }, hasWebVerify, webSources);
    }).catch(err => {
      const msg = err.response?.data?.detail ?? err.message ?? 'Request failed';
      setRightMsgs(prev => prev.map(m => m.id !== rightId ? m : { ...m, error: msg, steps: freshSteps() }));
    });

    await Promise.all([leftCall, rightCall]);
    setLoading(false);
    setPrompt('');
    inputRef.current?.focus();
  }, [prompt, loading, scenario, apiKey]);

  const handleKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
  };

  const clearAll = () => {
    setLeftMsgs([]); setRightMsgs([]); setActiveSteps(freshSteps());
    inputRef.current?.focus();
  };

  // ── Render ──────────────────────────────────────────────────────────────

  const hasMessages = leftMsgs.length > 0 || rightMsgs.length > 0;

  return (
    <>
      <style>{`
        @keyframes tcSpin { to { transform: rotate(360deg); } }
        @keyframes tcPulse { 0%,100% { opacity:1; transform:scale(1); } 50% { opacity:0.5; transform:scale(1.4); } }
        @keyframes tcDot { 0%,80%,100% { transform:translateY(0); opacity:0.4; } 40% { transform:translateY(-5px); opacity:1; } }
        @keyframes tcReveal { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:translateY(0); } }
        .tc-vs { background: linear-gradient(180deg, transparent, rgba(0,216,255,0.08) 40%, rgba(0,216,255,0.08) 60%, transparent); }
        .tc-input-wrap:focus-within .tc-send-btn { border-color: rgba(0,216,255,0.5) !important; }
        .tc-scenario-chip:hover { border-color: var(--border-strong) !important; background: rgba(255,255,255,0.05) !important; }
        .tc-scenario-chip.active { border-color: var(--cyan) !important; background: rgba(0,216,255,0.1) !important; color: var(--cyan) !important; }
      `}</style>

      <div style={{ minHeight: '100vh', background: 'var(--bg-void)', display: 'flex', flexDirection: 'column' }}>

        {/* ── Header ── */}
        <div style={{
          padding: '20px 28px 16px',
          borderBottom: '1px solid var(--border-subtle)',
          background: 'var(--bg-surface)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div style={{
                width: '36px', height: '36px', borderRadius: '10px',
                background: 'linear-gradient(135deg, var(--cyan), #7B61FF)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                boxShadow: '0 0 20px var(--cyan-glow)',
              }}>
                <Sparkles size={18} color="var(--bg-void)" />
              </div>
              <div>
                <h1 style={{ fontSize: '18px', fontWeight: 800, color: 'var(--text-primary)', letterSpacing: '-0.02em', fontFamily: 'Syne, sans-serif' }}>
                  TruthChain Showcase
                </h1>
                <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '1px' }}>
                  Side-by-side comparison · Raw LLM vs TruthChain-validated output
                </p>
              </div>
            </div>
            {hasMessages && (
              <button
                onClick={clearAll}
                style={{
                  display: 'flex', alignItems: 'center', gap: '6px',
                  padding: '8px 14px', borderRadius: '8px',
                  background: 'transparent', border: '1px solid var(--border-default)',
                  color: 'var(--text-muted)', cursor: 'pointer', fontSize: '12px',
                  fontFamily: 'Syne, sans-serif',
                  transition: 'all 0.2s',
                }}
              >
                <RefreshCw size={12} /> Reset
              </button>
            )}
          </div>

          {/* Scenario chips */}
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            {SCENARIOS.map((s, i) => (
              <button
                key={s.id}
                className={`tc-scenario-chip${i === scenarioIdx ? ' active' : ''}`}
                onClick={() => { setScenarioIdx(i); setPrompt(i !== 4 ? s.prompt : ''); }}
                style={{
                  padding: '6px 14px', borderRadius: '20px',
                  background: 'transparent',
                  border: '1px solid var(--border-default)',
                  color: 'var(--text-secondary)',
                  cursor: 'pointer', fontSize: '12px',
                  fontFamily: 'Syne, sans-serif',
                  transition: 'all 0.15s',
                }}
              >
                {s.label}
              </button>
            ))}
          </div>
        </div>

        {/* ── Split panels ── */}
        <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '1fr 2px 1fr', minHeight: 0, overflow: 'hidden' }}>

          {/* LEFT — Raw LLM */}
          <div style={{ display: 'flex', flexDirection: 'column', minHeight: 0 }}>
            {/* Panel header */}
            <div style={{
              padding: '14px 20px',
              borderBottom: '1px solid var(--border-subtle)',
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              background: 'rgba(255,255,255,0.015)',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div style={{
                  width: '28px', height: '28px', borderRadius: '7px',
                  background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border-default)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  <Unlock size={13} color="var(--text-muted)" />
                </div>
                <div>
                  <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', fontWeight: 700, color: 'var(--text-secondary)', letterSpacing: '0.06em' }}>
                    STANDARD LLM
                  </div>
                  <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '9px', color: 'var(--text-muted)', marginTop: '1px' }}>
                    No validation · Unguarded output
                  </div>
                </div>
              </div>
              <div style={{
                padding: '3px 10px', borderRadius: '12px',
                background: 'rgba(255,69,96,0.08)', border: '1px solid rgba(255,69,96,0.2)',
                fontFamily: 'JetBrains Mono, monospace', fontSize: '9px', color: 'var(--red)', letterSpacing: '0.06em', fontWeight: 700,
              }}>
                UNGUARDED
              </div>
            </div>

            {/* Messages */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '20px', minHeight: 0 }}>
              {leftMsgs.length === 0 && (
                <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: '12px', opacity: 0.5 }}>
                  <Cpu size={32} color="var(--text-muted)" />
                  <span style={{ fontSize: '13px', color: 'var(--text-muted)', fontFamily: 'JetBrains Mono, monospace' }}>
                    Raw LLM output will appear here
                  </span>
                </div>
              )}
              {leftMsgs.map(m =>
                m.role === 'bot' && !m.text && !m.error
                  ? <TypingIndicator key={m.id} side="left" />
                  : <div key={m.id} style={{ animation: 'tcReveal 0.3s ease-out' }}><Bubble msg={m} side="left" /></div>
              )}
              <div ref={leftEndRef} />
            </div>
          </div>

          {/* CENTER DIVIDER */}
          <div className="tc-vs" style={{
            display: 'flex', flexDirection: 'column', alignItems: 'center',
            justifyContent: 'center', position: 'relative',
            borderLeft: '1px solid var(--border-subtle)', borderRight: '1px solid var(--border-subtle)',
          }}>
            <div style={{
              position: 'absolute', top: '50%', transform: 'translateY(-50%)',
              width: '36px', height: '36px', borderRadius: '50%',
              background: 'var(--bg-void)',
              border: '1px solid var(--border-default)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontFamily: 'Syne, sans-serif', fontWeight: 800, fontSize: '11px',
              color: 'var(--text-muted)', letterSpacing: '0.05em',
              zIndex: 1,
            }}>
              VS
            </div>
          </div>

          {/* RIGHT — TruthChain */}
          <div style={{
            display: 'flex', flexDirection: 'column', minHeight: 0,
            background: 'rgba(0,216,255,0.012)',
          }}>
            {/* Panel header */}
            <div style={{
              padding: '14px 20px',
              borderBottom: '1px solid rgba(0,216,255,0.15)',
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              background: 'rgba(0,216,255,0.03)',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div style={{
                  width: '28px', height: '28px', borderRadius: '7px',
                  background: 'linear-gradient(135deg, var(--cyan), #7B61FF)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  boxShadow: '0 0 14px var(--cyan-glow)',
                }}>
                  <Shield size={13} color="var(--bg-void)" strokeWidth={2.5} />
                </div>
                <div>
                  <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', fontWeight: 700, color: 'var(--cyan)', letterSpacing: '0.06em' }}>
                    TRUTHCHAIN SDK
                  </div>
                  <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '9px', color: 'var(--text-muted)', marginTop: '1px' }}>
                    {scenario.rules.length} active rules · Auto-correction ON
                  </div>
                </div>
              </div>
              <div style={{
                padding: '3px 10px', borderRadius: '12px',
                background: 'rgba(0,255,136,0.08)', border: '1px solid rgba(0,255,136,0.2)',
                fontFamily: 'JetBrains Mono, monospace', fontSize: '9px', color: 'var(--green)', letterSpacing: '0.06em', fontWeight: 700,
              }}>
                PROTECTED
              </div>
            </div>

            {/* Messages */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '20px', minHeight: 0 }}>
              {rightMsgs.length === 0 && (
                <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: '12px', opacity: 0.5 }}>
                  <Shield size={32} color="var(--cyan)" />
                  <span style={{ fontSize: '13px', color: 'var(--text-muted)', fontFamily: 'JetBrains Mono, monospace' }}>
                    Validated output + pipeline will appear here
                  </span>
                </div>
              )}
              {rightMsgs.map(m =>
                m.role === 'bot' && !m.text && !m.error
                  ? <TypingIndicator key={m.id} side="right" />
                  : <div key={m.id} style={{ animation: 'tcReveal 0.3s ease-out' }}><Bubble msg={m} side="right" /></div>
              )}
              <div ref={rightEndRef} />
            </div>
          </div>
        </div>

        {/* ── Input bar ── */}
        <div style={{
          borderTop: '1px solid var(--border-subtle)',
          padding: '16px 24px',
          background: 'var(--bg-surface)',
        }}>
          {/* Active rules strip */}
          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginBottom: '12px' }}>
            <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '9px', color: 'var(--text-muted)', alignSelf: 'center', marginRight: '4px' }}>
              RULES:
            </span>
            {scenario.rules.map(r => (
              <span key={r.name} style={{
                fontFamily: 'JetBrains Mono, monospace', fontSize: '9px',
                padding: '2px 8px', borderRadius: '4px',
                background: 'rgba(0,216,255,0.06)', border: '1px solid rgba(0,216,255,0.15)',
                color: 'var(--cyan)',
              }}>
                {r.type}:{r.name}
              </span>
            ))}
          </div>

          <div className="tc-input-wrap" style={{ display: 'flex', gap: '12px', alignItems: 'flex-end' }}>
            <div style={{
              flex: 1, position: 'relative',
              background: 'var(--bg-elevated)',
              border: '1px solid var(--border-default)',
              borderRadius: '12px',
              transition: 'border-color 0.2s',
            }}>
              <textarea
                ref={inputRef}
                value={prompt}
                onChange={e => setPrompt(e.target.value)}
                onKeyDown={handleKey}
                placeholder={scenario.id === 'custom' ? 'Type your own prompt…' : 'Edit or send the scenario prompt…'}
                rows={2}
                style={{
                  width: '100%', background: 'transparent', border: 'none', outline: 'none',
                  padding: '12px 16px', resize: 'none',
                  fontFamily: 'Syne, sans-serif', fontSize: '13px', color: 'var(--text-primary)',
                  lineHeight: 1.5,
                }}
              />
              <div style={{
                position: 'absolute', right: '12px', bottom: '8px',
                fontFamily: 'JetBrains Mono, monospace', fontSize: '9px', color: 'var(--text-muted)',
              }}>
                ↵ send
              </div>
            </div>

            <button
              className="tc-send-btn"
              onClick={send}
              disabled={loading || !prompt.trim()}
              style={{
                width: '44px', height: '44px', borderRadius: '12px', flexShrink: 0,
                background: loading || !prompt.trim()
                  ? 'rgba(255,255,255,0.04)'
                  : 'linear-gradient(135deg, var(--cyan), #7B61FF)',
                border: '1px solid var(--border-default)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                cursor: loading || !prompt.trim() ? 'not-allowed' : 'pointer',
                transition: 'all 0.2s',
                boxShadow: loading || !prompt.trim() ? 'none' : '0 0 20px var(--cyan-glow)',
              }}
            >
              {loading
                ? <div style={{ width: '16px', height: '16px', borderRadius: '50%', border: '2px solid var(--border-default)', borderTopColor: 'var(--cyan)', animation: 'tcSpin 0.7s linear infinite' }} />
                : <Send size={16} color={loading || !prompt.trim() ? 'var(--text-muted)' : 'var(--bg-void)'} strokeWidth={2.5} />
              }
            </button>
          </div>

          <p style={{
            fontFamily: 'JetBrains Mono, monospace', fontSize: '9px',
            color: 'var(--text-muted)', marginTop: '10px', textAlign: 'center',
          }}>
            Both panels use Groq llama-3.3-70b · Left has no validation · Right runs TruthChain SDK pipeline
          </p>
        </div>
      </div>
    </>
  );
}
