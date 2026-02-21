/**
 * @truthchain/node — TypeScript/JavaScript SDK for the TruthChain AI-validation API
 *
 * @example
 * ```ts
 * import { TruthChain, signup, login } from "@truthchain/node";
 * import type { ValidationResult, ProxyResult } from "@truthchain/node";
 * ```
 */

export { TruthChain, signup, login, DEFAULT_BASE_URL, DEFAULT_TIMEOUT_MS } from "./client";
export type { TruthChainConfig } from "./client";

export type {
  // Auth
  SignupResult,
  LoginResult,
  APIKey,
  // Validation
  ValidationRule,
  Violation,
  ValidationResult,
  // Analytics
  ValidationStats,
  DailyBreakdown,
  TopViolation,
  AnalyticsOverview,
  // Billing
  BillingPlan,
  Subscription,
  // LLM proxy
  MessageItem,
  CompleteRequest,
  ValidationSummary,
  ProxyResult,
} from "./types";

export {
  TruthChainError,
  AuthenticationError,
  PermissionError,
  QuotaExceededError,
  RateLimitError,
  NotFoundError,
  ValidationError,
  ServerError,
  ConflictError,
} from "./errors";
