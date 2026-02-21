/**
 * TruthChain SDK — Type Definitions
 *
 * Mirrors the Python SDK dataclasses and backend Pydantic models.
 * All interfaces match the exact field names returned by the TruthChain REST API.
 */

// ── Auth ──────────────────────────────────────────────────────────────────────

export interface SignupResult {
  /** Unique identifier for the newly-created organization. */
  organization_id: string;
  name: string;
  email: string;
  tier: "free" | "startup" | "business" | "enterprise";
  /** Full API key — shown **only once**, save immediately. */
  api_key: string;
  monthly_quota: number;
}

export interface LoginResult {
  organization_id: string;
  name: string;
  email: string;
  tier: "free" | "startup" | "business" | "enterprise";
  /** Fresh API key issued on login. */
  api_key: string;
  monthly_quota: number;
}

export interface APIKey {
  id: string;
  name: string;
  is_active: boolean;
  created_at: string;
  /** Full key value — only present immediately after creation. */
  key?: string;
  /** First 20 characters, safe to display in logs. */
  key_prefix?: string;
  last_used_at?: string;
}

// ── Validation ────────────────────────────────────────────────────────────────

/** Shape of a single validation rule. Field names depend on rule `type`. */
export type ValidationRule = Record<string, unknown>;

/** A single violated rule. */
export interface Violation {
  rule_name: string;
  violation_type: string;
  message: string;
  severity: "error" | "warning" | "info";
  /** The field in ``output`` that triggered the violation (if applicable). */
  field?: string;
  expected?: unknown;
  actual?: unknown;
}

/** Full result returned by ``POST /v1/validate``. */
export interface ValidationResult {
  validation_id: string;
  status: "passed" | "failed" | "warning";
  is_valid: boolean;
  violations: Violation[];
  /** Present when auto-correction rewrote some fields. */
  corrected_output?: Record<string, unknown>;
  auto_corrected: boolean;
  corrections_applied: string[];
  confidence_score?: number;
  latency_ms?: number;
  metadata: Record<string, unknown>;
}

// ── Analytics ─────────────────────────────────────────────────────────────────

export interface ValidationStats {
  total_validations: number;
  passed: number;
  failed: number;
  warnings: number;
  success_rate: number;
  avg_latency_ms: number;
  auto_corrections: number;
  auto_correction_rate: number;
}

export interface DailyBreakdown {
  date: string;
  total: number;
  passed: number;
  failed: number;
}

export interface TopViolation {
  rule_name: string;
  count: number;
  percentage: number;
}

export interface AnalyticsOverview {
  stats: ValidationStats;
  daily_breakdown: DailyBreakdown[];
  top_violations: TopViolation[];
  period_days: number;
}

// ── Billing ───────────────────────────────────────────────────────────────────

export interface BillingPlan {
  tier: string;
  name: string;
  price_usd: number;
  monthly_quota: number;
  features: string[];
}

export interface Subscription {
  organization_id: string;
  tier: string;
  monthly_quota: number;
  used_this_month: number;
  remaining_quota: number;
  plan: BillingPlan;
}

// ── LLM Proxy (GAP 6) ─────────────────────────────────────────────────────────

export interface MessageItem {
  role: "system" | "user" | "assistant";
  content: string;
}

/** Request body for ``POST /v1/complete``. */
export interface CompleteRequest {
  /** LLM provider — ``"groq"`` (default, free), ``"openai"``, or ``"custom"``. */
  provider?: "openai" | "groq" | "custom";
  /** Model name. Defaults to provider's default (e.g. ``"llama-3.1-8b-instant"`` for Groq). */
  model?: string;
  messages: MessageItem[];
  validation_rules?: ValidationRule[];
  /** Top-level JSON key expected in LLM response (used as fallback wrap key). */
  output_field?: string;
  /** Apply AutoCorrector strategies to violations before returning. */
  auto_correct?: boolean;
  /** Per-request API key override (takes precedence over server-side config). */
  provider_api_key?: string;
  /** Required when ``provider = "custom"``. */
  base_url?: string;
  extra_params?: Record<string, unknown>;
}

export interface ValidationSummary {
  is_valid: boolean;
  total_rules: number;
  violations: number;
  auto_corrected: number;
}

/** Full result returned by ``POST /v1/complete``. */
export interface ProxyResult {
  /** Final content string (auto-corrected if applicable). */
  content: string;
  /** Original LLM response before any correction. */
  raw_content: string;
  /** Parsed dict form of the LLM response. */
  output: Record<string, unknown>;
  provider: string;
  model: string;
  usage: Record<string, number>;
  latency_ms: number;
  /** Non-empty if the LLM call itself failed. */
  error: string;
  validation?: ValidationSummary;
}
