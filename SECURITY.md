# Security Policy

## Reporting a vulnerability

If you discover a security issue, please **do not** open a public GitHub issue with exploit details.

Open a private security advisory on GitHub (Repository → Security → Advisories) or contact the maintainers directly.

## Secrets and API keys

- Never commit `.env` or API keys to the repository.
- `config.py` reads credentials from environment variables only.
- If a key was exposed, rotate it immediately at [OpenRouter](https://openrouter.ai) and update your local `.env`.

## Local data

`kanoonvault.db`, `uploads/`, and `chroma_db/` contain case documents and are gitignored by default. Do not publish user data when pushing to a public repo.
