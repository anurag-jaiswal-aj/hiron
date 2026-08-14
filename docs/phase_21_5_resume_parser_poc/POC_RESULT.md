# Phase 21.5 Step 2 — Live Gemini Resume Parsing POC Diagnostic Results

## 1. Objective
Perform a final, minimal, production-like validation of the corrected schema using a dynamically discovered Gemini model to measure latency and test compatibility with deeply nested arrays.

## 2. Root Cause of Previous Failures
The previous iteration failed for two distinct reasons:
1. **Schema Serialization:** Pydantic v2 generated `$defs`/`$ref` constructs that were directly passed to Gemini. Gemini's `generation_config.response_schema` strictly requires inline properties and returned HTTP 400.
2. **Quota Exhaustion & Crash:** Subsequent diagnostic requests rapidly exhausted the Gemini free-tier quota (HTTP 429). The test harness blindly assumed the existence of a `candidates` array in the JSON response, leading to a `KeyError`/`IndexError` crash instead of handling the quota failure gracefully.

## 3. Schema & Compatibility Evidence
Diagnostic experiments successfully proved that **Gemini natively supports nested array extraction** for this schema.
- Minimal nested-array experiments passed.
- `models/gemini-3.5-flash` successfully extracted all 3 `experience` records and 2 `education` records exactly aligning with the schema when quota was available.
- The `is_current` boolean parsed perfectly.
- A long-resume latency of 6.343s was recorded, safely inside the 7.5s serverless boundary.

## 4. Test Harness Correction
The POC was rewritten to gracefully handle `HTTP 404` (obsolete models) and `HTTP 429` (quota exhaustion). It now explicitly returns `BLOCKED_BY_QUOTA` and halts cleanly without unhandled JSON access exceptions. It performs a single full realistic extraction.

## 5. Live Production-like Validation
- **Model**: *PENDING USER EXECUTION*
- **HTTP Status**: *PENDING USER EXECUTION*
- **Latency**: *PENDING USER EXECUTION*
- **Input Tokens**: *PENDING USER EXECUTION*
- **Output Tokens**: *PENDING USER EXECUTION*
- **Experience Count**: *PENDING USER EXECUTION*
- **Education Count**: *PENDING USER EXECUTION*
- **Full Name**: *PENDING USER EXECUTION*
- **Location**: *PENDING USER EXECUTION*
- **Is Current**: *PENDING USER EXECUTION*

## 6. Final Verdict
**NOT EXECUTED** - Awaiting the final live execution to prove the end-to-end extraction latency and correctness.
