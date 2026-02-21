/**
 * TruthChain SDK — Main Client
 *
 * Usage (with API key):
 *   import { TruthChain } from "@truthchain/node";
 *   const client = new TruthChain({ apiKey: "tc_live_..." });
 *   const result = await client.validate({ hours: 8 }, [
 *     { type: "range", field: "hours", min: 0, max: 24, name: "hours_check" }
 *   ]);
 *   console.log(result.is_valid);
 *
 * Top-level helpers (no API key required):
 *   import { signup, login } from "@truthchain/node";
 *   const { api_key } = await signup("Acme Corp", "dev@acme.com", "s3cretPW!");
 */

import {
  APIKey,
  AnalyticsOverview,
  BillingPlan,
  CompleteRequest,
  LoginResult,
  ProxyResult,
  SignupResult,
  Subscription,
  ValidationResult,
  ValidationRule,
  ValidationStats,
} from "./types";

import {
  AuthenticationError,
  ConflictError,
  NotFoundError,
  PermissionError,
  QuotaExceededError,
  RateLimitError,
  ServerError,
  TruthChainError,
  ValidationError,
} from "./errors";

export const DEFAULT_BASE_URL = "http://localhost:8000";
export const DEFAULT_TIMEOUT_MS = 30_000;

// ── Internal helpers ──────────────────────────────────────────────────────────

async function raiseForStatus(response: Response): Promise<void> {
  if (response.ok) return;

  let detail: string;
  let body: Record<string, unknown> = {};
  try {
    body = (await response.json()) as Record<string, unknown>;
    detail = typeof body["detail"] === "string" ? body["detail"] : JSON.stringify(body);
  } catch {
    detail = await response.text();
  }

  const status = response.status;

  if (status === 401) throw new AuthenticationError(detail, status, body);
  if (status === 403) throw new PermissionError(detail, status, body);
  if (status === 404) throw new NotFoundError(detail, status, body);
  if (status === 422) throw new ValidationError(detail, status, body);
  if (status === 429) {
    const retryAfter = parseFloat(response.headers.get("Retry-After") ?? "0") || undefined;
    if (detail.toLowerCase().includes("quota")) {
      throw new QuotaExceededError(detail, status, body);
    }
    throw new RateLimitError(detail, retryAfter, status, body);
  }
  if (status === 400 || status === 409) throw new ConflictError(detail, status, body);
  if (status >= 500) throw new ServerError(detail, status, body);

  throw new TruthChainError(detail, status, body);
}

function buildHeaders(apiKey: string): HeadersInit {
  return {
    "X-API-Key": apiKey,
    "Content-Type": "application/json",
  };
}

async function fetchWithTimeout(
  url: string,
  init: RequestInit,
  timeoutMs: number,
): Promise<Response> {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } finally {
    clearTimeout(id);
  }
}

// ── Client config ─────────────────────────────────────────────────────────────

export interface TruthChainConfig {
  /** Your TruthChain API key (``tc_live_...``). */
  apiKey: string;
  /** Base URL of the TruthChain API. Defaults to ``http://localhost:8000``. */
  baseUrl?: string;
  /** Request timeout in milliseconds. Default: 30 000. */
  timeoutMs?: number;
}

// ── Main Client ───────────────────────────────────────────────────────────────

/**
 * TruthChain client.
 *
 * All methods are `async` and return the parsed API response.
 * On HTTP errors they throw typed error classes from `@truthchain/node/errors`.
 *
 * @example
 * ```ts
 * const client = new TruthChain({ apiKey: "tc_live_..." });
 *
 * const result = await client.validate(
 *   { fiqh_school: "Hanafy", sehri_time: "05:11 AM" },
 *   [
 *     { type: "enum", field: "fiqh_school", name: "school_enum",
 *       valid_options: ["Hanafi","Jafaria","Shafi","Maliki","Hanbali"] },
 *   ],
 *   { auto_correct: true }
 * );
 * console.log(result.is_valid, result.corrected_output);
 * ```
 */
export class TruthChain {
  private readonly apiKey: string;
  private readonly baseUrl: string;
  private readonly timeoutMs: number;

  constructor(config: TruthChainConfig) {
    this.apiKey = config.apiKey;
    this.baseUrl = (config.baseUrl ?? DEFAULT_BASE_URL).replace(/\/$/, "");
    this.timeoutMs = config.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  }

  // ── Internal ───────────────────────────────────────────────────────────────

  private async request<T>(method: string, path: string, body?: unknown): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const init: RequestInit = {
      method,
      headers: buildHeaders(this.apiKey),
    };
    if (body !== undefined) {
      init.body = JSON.stringify(body);
    }
    const resp = await fetchWithTimeout(url, init, this.timeoutMs);
    await raiseForStatus(resp);
    if (resp.status === 204) return undefined as T;
    return (await resp.json()) as T;
  }

  // ── Validation ─────────────────────────────────────────────────────────────

  /**
   * Validate AI output against a set of rules.
   *
   * @param output    The JSON object produced by your AI / LLM.
   * @param rules     List of validation rule objects.
   * @param context   Optional extra context, e.g. `{ auto_correct: true }`.
   *
   * @example
   * ```ts
   * const result = await client.validate(
   *   { hours: 25 },
   *   [{ type: "range", field: "hours", name: "hours_check", min: 0, max: 24 }]
   * );
   * // result.is_valid === false
   * // result.violations[0].message === "hours must be between 0 and 24"
   * ```
   */
  async validate(
    output: Record<string, unknown>,
    rules: ValidationRule[],
    context?: Record<string, unknown>,
  ): Promise<ValidationResult> {
    const payload: Record<string, unknown> = { output, rules };
    if (context) payload["context"] = context;
    return this.request<ValidationResult>("POST", "/v1/validate", payload);
  }

  // ── LLM Proxy (GAP 6) ──────────────────────────────────────────────────────

  /**
   * Proxy an LLM call through TruthChain validation.
   *
   * The server forwards `messages` to the chosen LLM provider, validates the
   * response with `validation_rules`, optionally auto-corrects violations, and
   * returns the full result including validation metadata.
   *
   * @example
   * ```ts
   * const result = await client.complete({
   *   provider: "groq",
   *   messages: [
   *     { role: "system", content: "Reply only with JSON {\"sehri_time\": \"HH:MM AM/PM\"}" },
   *     { role: "user",   content: "What is the Sehri time in Dhaka on 22 Feb 2026?" }
   *   ],
   *   validation_rules: [{
   *     type: "external_ref", field: "sehri_time",
   *     connector: "aladhan_fajr_in_range",
   *     params: { city: "Dhaka", country: "Bangladesh", tolerance_minutes: 15 }
   *   }],
   *   output_field: "sehri_time"
   * });
   * console.log(result.validation?.is_valid);
   * ```
   */
  async complete(request: CompleteRequest): Promise<ProxyResult> {
    return this.request<ProxyResult>("POST", "/v1/complete", request);
  }

  // ── Analytics ──────────────────────────────────────────────────────────────

  /** Fetch a full analytics overview (stats, daily breakdown, top violations). */
  async getAnalytics(): Promise<AnalyticsOverview> {
    return this.request<AnalyticsOverview>("GET", "/v1/analytics/overview");
  }

  /** Fetch aggregated validation statistics for your organization. */
  async getValidationStats(): Promise<ValidationStats> {
    return this.request<ValidationStats>("GET", "/v1/analytics/validation-stats");
  }

  // ── Billing ────────────────────────────────────────────────────────────────

  /** Fetch the current subscription details for your organization. */
  async getSubscription(): Promise<Subscription> {
    return this.request<Subscription>("GET", "/v1/billing/subscription");
  }

  /** List all available billing plans. */
  async getPlans(): Promise<BillingPlan[]> {
    return this.request<BillingPlan[]>("GET", "/v1/billing/plans");
  }

  /**
   * Upgrade or downgrade the subscription tier.
   *
   * @param tier  One of `"free"`, `"startup"`, `"business"`, `"enterprise"`.
   */
  async upgrade(tier: string): Promise<Subscription> {
    return this.request<Subscription>("POST", "/v1/billing/upgrade", { tier });
  }

  // ── API Key Management ─────────────────────────────────────────────────────

  /** List all API keys for your organization. */
  async listApiKeys(): Promise<APIKey[]> {
    return this.request<APIKey[]>("GET", "/v1/auth/api-keys");
  }

  /**
   * Create a new API key.
   *
   * > **Warning:** Save the returned `key` immediately — it is shown **only once**.
   *
   * @param name  Human-readable label for the key.
   */
  async createApiKey(name = "API Key"): Promise<APIKey> {
    return this.request<APIKey>(
      "POST",
      `/v1/auth/api-keys?name=${encodeURIComponent(name)}`,
    );
  }

  /**
   * Rotate an existing API key (old key revoked, new one issued).
   *
   * @param keyId  The `id` of the key to rotate.
   */
  async rotateApiKey(keyId: string): Promise<APIKey> {
    return this.request<APIKey>("POST", `/v1/auth/api-keys/${keyId}/rotate`);
  }

  /**
   * Revoke (deactivate) an API key.
   *
   * @param keyId  The `id` of the key to revoke.
   */
  async revokeApiKey(keyId: string): Promise<void> {
    return this.request<void>("DELETE", `/v1/auth/api-keys/${keyId}`);
  }
}

// ── Top-level auth helpers (no API key required) ──────────────────────────────

/**
 * Register a new organization and receive an API key.
 *
 * > **Warning:** Save the returned `api_key` immediately — shown **only once**.
 *
 * @example
 * ```ts
 * import { signup } from "@truthchain/node";
 * const result = await signup("Acme Corp", "dev@acme.com", "s3cretPW!");
 * console.log(result.api_key);   // tc_live_...  ← save this!
 * ```
 */
export async function signup(
  name: string,
  email: string,
  password: string,
  tier: "free" | "startup" | "business" | "enterprise" = "free",
  baseUrl = DEFAULT_BASE_URL,
  timeoutMs = DEFAULT_TIMEOUT_MS,
): Promise<SignupResult> {
  const url = `${baseUrl.replace(/\/$/, "")}/v1/auth/signup`;
  const resp = await fetchWithTimeout(
    url,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, email, password, tier }),
    },
    timeoutMs,
  );
  await raiseForStatus(resp);
  return (await resp.json()) as SignupResult;
}

/**
 * Login with email and password to receive a fresh API key.
 *
 * @example
 * ```ts
 * import { login, TruthChain } from "@truthchain/node";
 * const { api_key } = await login("dev@acme.com", "s3cretPW!");
 * const client = new TruthChain({ apiKey: api_key });
 * ```
 */
export async function login(
  email: string,
  password: string,
  baseUrl = DEFAULT_BASE_URL,
  timeoutMs = DEFAULT_TIMEOUT_MS,
): Promise<LoginResult> {
  const url = `${baseUrl.replace(/\/$/, "")}/v1/auth/login`;
  const resp = await fetchWithTimeout(
    url,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    },
    timeoutMs,
  );
  await raiseForStatus(resp);
  return (await resp.json()) as LoginResult;
}
