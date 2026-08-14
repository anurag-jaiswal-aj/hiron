# Phase 21.6.12 — Resume Worker Step 10: Login 500 Root Cause Report

## A. Production Login Reproduction
- **Endpoint**: `POST https://hiron-api.vercel.app/api/v1/auth/login`
- **Email**: `e2e-test@hiron.dev`
- **Account State**: Password correctly verified locally against production database.

## B. Exact HTTP Status
**HTTP 500 Internal Server Error**

## C. Sanitized Runtime Exception
Extracted from Vercel Production Runtime Logs:
```json
{
  "error": "[Errno 99] Cannot assign requested address",
  "exc_info": "OSError(99, 'Cannot assign requested address')",
  "event": "Unhandled server exception",
  "logger": "hiron.api.exceptions",
  "level": "error"
}
```

## D. Relevant Stack Trace / Function
The `OSError(99)` (`EADDRNOTAVAIL`) occurs inside `asyncpg` when establishing the underlying TCP socket connection to PostgreSQL during the `user = await auth_service.authenticate_user(...)` execution sequence. 

## E. Root Cause
The production `DATABASE_URL` configured on Vercel is set to the Supabase **direct connection endpoint**:
`db.bpizcvzqehvbzwkuscfe.supabase.co:5432`

This endpoint only resolves to an IPv6 address. Standard Vercel Serverless Functions running on AWS Lambda environments operate on an IPv4 network stack. When Vercel attempts to establish a socket connection to an IPv6-only destination, the OS natively rejects it with `Errno 99 Cannot assign requested address`.

## F. Evidence Supporting the Root Cause
1. **Log Analysis**: The exact exception `OSError(99, 'Cannot assign requested address')` during an external DB request is the hallmark signature of an IPv4-to-IPv6 routing failure in serverless environments.
2. **DNS Resolution Check**: A safe internal execution script confirmed that `db.bpizcvzqehvbzwkuscfe.supabase.co` resolves exclusively to IPv6 records (`AAAA`), with 0 IPv4 records available.
3. **Local Discrepancy**: The login script worked locally because macOS/Linux local environments have native dual-stack IPv4/IPv6 support, completely masking the network limitation of the Vercel execution environment.

## G. JWT / Config Structural Findings
Structural checks were performed on `JWT_PRIVATE_KEY_CONTENT` and `JWT_PUBLIC_KEY_CONTENT`:
- Both variables exist on Vercel.
- Both begin with the expected `-----BEGIN` header.
- Both properly contain newline (`\n`) characters required for PEM parsing.
- *Conclusion: JWT configuration is structurally sound and is not the cause of the 500 error.*

## H. Whether Source Code is Affected
**No.** The application source code handles database connections properly. This is entirely an infrastructure configuration defect.

## I. Whether Production Environment Variables Require Modification
**Yes.** The `DATABASE_URL` environment variable on Vercel must be modified.

## J. Exact Remediation Proposal
Update the Vercel `DATABASE_URL` environment variable to use the Supabase **Connection Pooler (Supavisor)** endpoint instead of the Direct Connection endpoint. The Supabase connection pooler domain (e.g., `aws-0-[region].pooler.supabase.com`) resolves to IPv4 addresses, which Vercel Serverless Functions can reach natively.

1. Locate the correct Supabase Connection Pooler string (Port 6543 for transaction pooling).
2. Use the Vercel CLI to update the variable:
   `vercel env rm DATABASE_URL production`
   `vercel env add DATABASE_URL production` (using the pooler URL)
3. Trigger a redeployment of the API on Vercel to inject the new environment variable into the runtime.

## K. Risk Assessment
- **Risk Level**: **Low.** 
- **Impact**: Changing to the connection pooler is the industry standard practice for serverless deployments (especially Vercel) connecting to Supabase. It strictly improves connection management, scalability, and network compatibility without modifying application behavior.
