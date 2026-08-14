# Phase 21.6.12 — Resume Worker Step 10: Railway Network Root Cause Report

## A. Exact Traceback
The Railway worker logs produce the following traceback upon receiving the QStash webhook:
```
2026-08-14 08:22:41 [error    ] Error in parse_resume_webhook  error='[Errno 101] Network is unreachable'
INFO:     100.64.0.9:37136 - "POST /api/v1/webhooks/qstash/resumes/parse HTTP/1.1" 500 Internal Server Error
  File "/app/apps/worker/src/main.py", line 39, in parse_resume_webhook
    await parse_resume_pipeline(
  File "/app/apps/worker/src/pipeline.py", line 106, in parse_resume_pipeline
```

## B. Exact Failing Function
The crash occurs at `apps/worker/src/pipeline.py`, line 106:
```python
    resume = await resume_repo.get_resume_by_id(
        session=session,
        tenant_id=tenant_id,
        resume_id=resume_id,
    )
```
This function executes a SQLAlchemy `select(Resume)` statement, which triggers `asyncpg` to negotiate the very first physical connection to the database. The underlying `asyncio.create_connection` socket layer fails to establish a TCP connection.

## C. Exact Network Destination
The exact network destination is the PostgreSQL database host configured on the Railway instance:
`db.bpizcvzqehvbzwkuscfe.supabase.co:5432`

## D. Relevant Environment Variable NAME Only
The variable causing the issue is `DATABASE_URL` configured in the Railway environment.

## E. IPv4/IPv6 Resolution Evidence
Performing a DNS lookup on the database host reveals that it is an IPv6-only endpoint:
```bash
$ host db.bpizcvzqehvbzwkuscfe.supabase.co
db.bpizcvzqehvbzwkuscfe.supabase.co has IPv6 address 2406:da1a:314:7100:8e80:e36e:bbcf:d910
```
Because Railway outbound networking lacks native support for routing to external IPv6-only addresses in this setup, the socket immediately returns `[Errno 101] Network is unreachable`.

## F. Relation to Previous Issues
**Yes**, this is the exact same class of problem that was previously diagnosed and fixed on the Vercel API deployment. The Vercel API was remediated by switching its `DATABASE_URL` to use the Supavisor connection pooler (`aws-0-ap-south-1.pooler.supabase.com:5432`), which supports IPv4. The Railway worker was overlooked during that migration and is still configured with the old, IPv6-only direct connection URL.

## G. Exact ONE Next Remediation Action
**Action:** Update the `DATABASE_URL` environment variable in the Railway project dashboard/CLI to use the Supavisor IPv4 connection pooler endpoint (i.e., replacing `db.bpizcvzqehvbzwkuscfe.supabase.co` with `aws-0-ap-south-1.pooler.supabase.com`) instead of the direct endpoint.

## H. Explicitly State What Must NOT Be Changed
- Do **NOT** modify any source code in `apps/worker` or `apps/api`.
- Do **NOT** modify the Vercel environment or deployment.
- Do **NOT** modify QStash configuration.
- Do **NOT** modify Supabase infrastructure or database records.
