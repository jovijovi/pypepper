# Security Policy

## Supported versions

Security fixes are applied to the latest released version on PyPI and to `main`.
Older releases may not receive backports.

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security-sensitive reports.

Prefer one of:

1. [GitHub Security Advisories](https://github.com/jovijovi/pypepper/security/advisories/new)
   (private vulnerability reporting), or
2. Contact the maintainers via the email listed on the
   [GitHub profile](https://github.com/jovijovi) / PyPI project page if advisories
   are unavailable.

Include:

- Affected version / commit
- Impact and attack scenario
- Minimal reproduction steps (if possible)

## What to expect

- Acknowledgement when practical
- A fix or mitigation timeline communicated privately when possible
- Credit in the advisory / CHANGELOG when you want it

## Non-vulnerabilities

Misconfiguration of optional features (for example leaving
`sse.authentication.enabled: false` in production) is documented as an operator
footgun, not a library vulnerability. See the [SSE guide](https://jovijovi.github.io/pypepper/guides/network-sse/).
