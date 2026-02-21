/**
 * @truthchain/node — Demo
 *
 * Demonstrates the SDK against a running TruthChain backend.
 * Themed around Dhaka Sehri / Ramadan 2026 data (Feb 22, 2026).
 *
 * Compile and run:
 *   npm run build
 *   node dist/demo.js
 */

import { TruthChain } from "./client";
import { TruthChainError, AuthenticationError } from "./errors";

const BASE_URL = process.env["TRUTHCHAIN_BASE_URL"] ?? "http://localhost:8000";
const API_KEY  = process.env["TRUTHCHAIN_API_KEY"]  ?? "tc_dev_key";

const sep  = "─".repeat(60);
const line = (t: string) => console.log(`  ${t}`);

function headline(title: string): void {
  console.log(`\n${sep}\n  ${title}\n${sep}`);
}

// ─────────────────────────────────────────────────────────────────────────────
// Demo 1 — Validate a Sehri/Fiqh record  (schema + range + enum rules)
// ─────────────────────────────────────────────────────────────────────────────

async function demoValidate(client: TruthChain): Promise<void> {
  headline("DEMO 1 — validate() — Sehri / Fiqh school record");

  const output = {
    fiqh_school: "Hanafy",          // typo — should be "Hanafi"
    sehri_duration_minutes: 30,
    timezone: "Asia/Dhaka",
    api_version: "v2",
  };

  const rules = [
    {
      type: "enum",
      name: "fiqh_school_check",
      field: "fiqh_school",
      valid_options: ["Hanafi", "Jafaria", "Shafi", "Maliki", "Hanbali"],
      severity: "error",
    },
    {
      type: "range",
      name: "duration_check",
      field: "sehri_duration_minutes",
      min: 0,
      max: 120,
      severity: "error",
    },
    {
      type: "schema",
      name: "timezone_required",
      required_fields: ["timezone"],
      severity: "error",
    },
  ];

  try {
    // First: without auto-correction
    const plain = await client.validate(output, rules);
    line(`Input             : ${JSON.stringify(output)}`);
    line(`is_valid          : ${plain.is_valid}`);
    line(`Status            : ${plain.status}`);
    if (plain.violations.length > 0) {
      line(`Violations (${plain.violations.length}):`);
      for (const v of plain.violations) {
        line(`  • [${v.severity.toUpperCase()}] ${v.field ?? "—"}: ${v.message}`);
      }
    }

    // Second: with auto-correction
    const corrected = await client.validate(output, rules, { auto_correct: true });
    if (corrected.auto_corrected) {
      line(`Auto-corrected    : ✓`);
      line(`Corrected output  : ${JSON.stringify(corrected.corrected_output)}`);
      for (const fix of corrected.corrections_applied) {
        line(`  ✎ ${fix}`);
      }
    }
  } catch (err) {
    if (err instanceof TruthChainError) {
      line(`✗ TruthChainError [${err.statusCode}]: ${err.message}`);
    } else {
      throw err;
    }
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Demo 2 — complete() LLM proxy with Aladhan validation
// ─────────────────────────────────────────────────────────────────────────────

async function demoLLMProxy(client: TruthChain): Promise<void> {
  headline("DEMO 2 — complete() — LLM proxy with Aladhan validation");

  try {
    const result = await client.complete({
      provider: "groq",
      messages: [
        {
          role: "system",
          content:
            'You are a helpful assistant. Reply ONLY with JSON: {"sehri_time": "HH:MM AM/PM"}. No extra text.',
        },
        {
          role: "user",
          content:
            "What is the Sehri (Fajr) time in Dhaka, Bangladesh on 22 February 2026?",
        },
      ],
      validation_rules: [
        {
          type: "external_ref",
          field: "sehri_time",
          connector: "aladhan_fajr_in_range",
          params: {
            city: "Dhaka",
            country: "Bangladesh",
            date: "22-02-2026",
            tolerance_minutes: 15,
          },
          severity: "error",
        },
      ],
      output_field: "sehri_time",
    });

    if (result.error) {
      line(`⚠  LLM error: ${result.error}`);
      line(`   (Set GROQ_API_KEY on the server to enable live LLM calls)`);
      return;
    }

    line(`Provider/model : ${result.provider} / ${result.model}`);
    line(`Latency        : ${result.latency_ms} ms`);
    line(`LLM content    : ${result.raw_content.slice(0, 120)}`);
    line(`Parsed output  : ${JSON.stringify(result.output)}`);

    if (result.validation) {
      const v = result.validation;
      const status = v.is_valid ? "✓ VALID" : `✗ INVALID (${v.violations} violation(s))`;
      line(`Validation     : ${status}`);
    }
  } catch (err) {
    if (err instanceof TruthChainError) {
      line(`✗ TruthChainError [${err.statusCode}]: ${err.message}`);
    } else {
      throw err;
    }
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Demo 3 — Error handling
// ─────────────────────────────────────────────────────────────────────────────

async function demoErrors(): Promise<void> {
  headline("DEMO 3 — Error handling (bad API key)");

  const badClient = new TruthChain({ apiKey: "invalid_key", baseUrl: BASE_URL });

  try {
    await badClient.validate({ x: 1 }, []);
    line("✗ Expected AuthenticationError but got success");
  } catch (err) {
    if (err instanceof AuthenticationError) {
      line(`✓ AuthenticationError caught: ${err.message} (HTTP ${err.statusCode})`);
    } else if (err instanceof TruthChainError) {
      line(`✓ TruthChainError caught (HTTP ${err.statusCode}): ${err.message}`);
    } else if (err instanceof Error && err.message.includes("fetch")) {
      line(`⚠  Server not reachable: ${err.message}`);
      line(`   To run the full demo, start the backend: uvicorn backend.api.main:app --reload`);
    } else {
      throw err;
    }
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Main
// ─────────────────────────────────────────────────────────────────────────────

async function main(): Promise<void> {
  console.log(`\n${"=".repeat(60)}`);
  console.log("  @truthchain/node — TypeScript SDK Demo");
  console.log(`  Backend : ${BASE_URL}`);
  console.log("=".repeat(60));

  const client = new TruthChain({ apiKey: API_KEY, baseUrl: BASE_URL });

  await demoValidate(client);
  await demoLLMProxy(client);
  await demoErrors();

  console.log(`\n${sep}`);
  console.log("  Demo complete.");
  console.log(sep);
}

main().catch((err) => {
  console.error("Fatal:", err);
  process.exit(1);
});
