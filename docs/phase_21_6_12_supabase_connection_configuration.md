# Phase 21.6.12: Supabase Connection Configuration

## 1. Exact DATABASE_URL Format
The Hiron backend uses SQLAlchemy 2.0 with the `asyncpg` dialect. The exact required format for the Supabase Direct Connection is:
`postgresql+asyncpg://postgres:<PASSWORD>@db.bpizcvzqehvbzwkuscfe.supabase.co:5432/postgres`

*(Note: The database name must be `postgres`, not the project name).*

## 2. How Alembic Reads the DATABASE_URL
1. When `alembic upgrade head` is executed, it loads `apps/api/alembic/env.py`.
2. `env.py` imports `get_settings()` from `apps/api/hiron/core/config.py`.
3. `config.py` relies on Pydantic `BaseSettings`, which prioritizes standard OS environment variables. If `DATABASE_URL` is set in the environment, it completely overrides the default local configuration.
4. `env.py` then calls `config.set_main_option("sqlalchemy.url", settings.database_url)`, passing the connection string to SQLAlchemy.

## 3. SSL Configuration (asyncpg)
- **Current Setup:** `apps/api/alembic/env.py` and `apps/api/hiron/core/config.py` do **not** inject manual `connect_args` for SSL.
- **Behavior:** The `asyncpg` dialect in SQLAlchemy natively parses the query string. In most cases, `asyncpg` automatically negotiates SSL with Supabase when connecting to port 5432.
- **Action:** If the migration fails with an SSL requirement error, you can simply append `?ssl=require` directly to the `DATABASE_URL`. SQLAlchemy will pass this correctly to `asyncpg`. No code modifications are needed.

## 4. Supabase Endpoint Reachability
**VERIFIED.** Tested using `nc -zv db.bpizcvzqehvbzwkuscfe.supabase.co 5432`. The direct PostgreSQL port is open and fully reachable from this machine.

## 5. Safe Password Provisioning Method
Since the password must remain completely out of logs, `.env.local`, and source control, the safest automated method for running the migration is to temporarily export the URL without writing it to disk or exposing it to shell history.

When you are ready to authorize the migration in the next step, you can safely inject the password into my isolated execution context by running:

```bash
export SUPABASE_DB_PASSWORD="your_actual_password"
```

In the next step, I can programmatically read `$SUPABASE_DB_PASSWORD` using Python (`os.getenv`), construct the `DATABASE_URL` internally without printing it, and securely execute `alembic upgrade head` using a subprocess with the updated environment. This guarantees the password never enters `.env.local`, log files, or terminal stdout.

---

**CONNECTION CONFIGURATION READY**
