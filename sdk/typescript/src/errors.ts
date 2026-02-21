/**
 * TruthChain SDK — Error Classes
 *
 * Mirrors the Python SDK exception hierarchy.
 * All errors extend `TruthChainError` for easy `instanceof` checks.
 */

export class TruthChainError extends Error {
  readonly statusCode?: number;
  readonly response: Record<string, unknown>;

  constructor(
    message: string,
    statusCode?: number,
    response?: Record<string, unknown>,
  ) {
    super(message);
    this.name = "TruthChainError";
    this.statusCode = statusCode;
    this.response = response ?? {};
    // Fix prototype chain so `instanceof` works after TypeScript compilation
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

/** Raised when the API key is missing, invalid, or revoked (HTTP 401). */
export class AuthenticationError extends TruthChainError {
  constructor(message: string, statusCode?: number, response?: Record<string, unknown>) {
    super(message, statusCode, response);
    this.name = "AuthenticationError";
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

/** Raised when the API key lacks permission for the action (HTTP 403). */
export class PermissionError extends TruthChainError {
  constructor(message: string, statusCode?: number, response?: Record<string, unknown>) {
    super(message, statusCode, response);
    this.name = "PermissionError";
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

/** Raised when the monthly validation quota is exhausted (HTTP 429 quota). */
export class QuotaExceededError extends TruthChainError {
  constructor(message: string, statusCode?: number, response?: Record<string, unknown>) {
    super(message, statusCode, response);
    this.name = "QuotaExceededError";
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

/** Raised when requests-per-minute limit is hit (HTTP 429 rate-limit). */
export class RateLimitError extends TruthChainError {
  readonly retryAfter?: number;

  constructor(
    message: string,
    retryAfter?: number,
    statusCode?: number,
    response?: Record<string, unknown>,
  ) {
    super(message, statusCode, response);
    this.name = "RateLimitError";
    this.retryAfter = retryAfter;
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

/** Raised when a requested resource does not exist (HTTP 404). */
export class NotFoundError extends TruthChainError {
  constructor(message: string, statusCode?: number, response?: Record<string, unknown>) {
    super(message, statusCode, response);
    this.name = "NotFoundError";
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

/** Raised when the request payload is invalid (HTTP 422). */
export class ValidationError extends TruthChainError {
  constructor(message: string, statusCode?: number, response?: Record<string, unknown>) {
    super(message, statusCode, response);
    this.name = "ValidationError";
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

/** Raised on unexpected server-side errors (HTTP 5xx). */
export class ServerError extends TruthChainError {
  constructor(message: string, statusCode?: number, response?: Record<string, unknown>) {
    super(message, statusCode, response);
    this.name = "ServerError";
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

/** Raised on a conflict, e.g. duplicate email (HTTP 400 / 409). */
export class ConflictError extends TruthChainError {
  constructor(message: string, statusCode?: number, response?: Record<string, unknown>) {
    super(message, statusCode, response);
    this.name = "ConflictError";
    Object.setPrototypeOf(this, new.target.prototype);
  }
}
