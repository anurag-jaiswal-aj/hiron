# Security Policy

## 🛡️ Supported Versions

The table below indicates the versions of Hiron currently supported with security updates:

| Version   | Supported              |
| --------- | ---------------------- |
| `v1.0.x`  | :white_check_mark: Yes |
| `< 1.0.0` | :x: No                 |

---

## 🔒 Reporting Vulnerabilities

If you discover a security vulnerability within Hiron, please report it responsibly rather than opening a public issue on GitHub.

**How to report:**

- **GitHub Private Vulnerability Reporting**: Use the "Report a vulnerability" button under the **Security** tab of the repository to submit a private disclosure directly to the maintainers.
- **Maintainer Contact**: If private vulnerability reporting is not enabled, please reach out to the project maintainers privately via GitHub or open a private repository discussion.
- **Dedicated Security Email**: A dedicated security contact email address may be provided in a future release.

**Reporting Details:**
Please include:

- Description of the vulnerability and potential impact
- Step-by-step proof of concept (PoC) or reproduction steps
- Any suggested mitigations or patches

---

## 🤝 Responsible Disclosure

We ask that security researchers:

- Give us reasonable time to investigate, address, and patch reported vulnerabilities before public disclosure.
- Make a good-faith effort to avoid privacy violations, data destruction, or disruption of production systems.
- Refrain from disclosing vulnerability details publicly until a fix is released.

---

## 🔑 Secrets Management

- **No Hardcoded Secrets**: Production passwords, private RSA key material, database credentials, and OpenAI API keys must **never** be committed to version control.
- **Environment Variables**: Use `.env.local` for local development and AWS Secrets Manager or Systems Manager Parameter Store for production deployments.
- **RSA JWT Keys**: RS256 JWT private keys should be mounted dynamically into container environments at runtime.

---

## 📦 Dependency Updates

- **Automated Scans**: Dependabot is configured (`.github/dependabot.yml`) to scan for Python (`uv.lock`) and Node (`pnpm-lock.yaml`) package vulnerability advisories.
- **Patch Management**: Security patches and critical dependency updates are applied promptly via security release pull requests.

---

## 🛡️ Security Best Practices in Hiron

- **Asymmetric JWT Signing**: RS256 algorithm with 4096-bit RSA keys and short-lived access tokens (15 minutes).
- **Password Hashing**: Argon2id hashing algorithm with custom iteration parameters and high-memory cost bounds.
- **Header Hardening**: `SecurityHeadersMiddleware` enforces HTTP Strict Transport Security (HSTS), frame protection (`X-Frame-Options: DENY`), MIME sniffing protection (`nosniff`), and Content Security Policy (CSP).
- **Payload Limits**: `RequestSizeLimitMiddleware` limits incoming HTTP body size to 10 MB.
- **Multi-Tenant Isolation**: Header-enforced tenant context (`TenantIsolationMiddleware`) and database Row Level Security (RLS) policies.
