# Security Policy

## Reporting a vulnerability

Please **do not open a public issue** for security problems. Report them privately through
[GitHub Security Advisories](https://github.com/rotemweiss57/gpt-newspaper/security/advisories/new)
or by email to rotem5707@gmail.com. We aim to acknowledge reports within 3 business days.

## How GPT Newspaper handles your data

- **API keys entered in the web UI** are stored only in your browser (and only if you tick
  "Remember keys"). They are sent to *your* GPT Newspaper server with each request, used for that
  edition only, and never written to disk or logs. Validation errors never echo submitted values.
- **Generated pages** escape all model output and web content (Jinja2 autoescaping). Only `http(s)`
  links from search results are rendered, and inline citations are linked only after escaping.
- **Prompt injection**: search results are untrusted. Agents are instructed to treat them as material to
  report on, never as instructions, and agents have no tools beyond the fixed pipeline.
- **HTTP hardening**: a strict Content-Security-Policy (`script-src 'self'` for the app), `nosniff`,
  `X-Frame-Options: DENY`, a restrictive `Permissions-Policy` and `Referrer-Policy`.
- **Docker** images run as an unprivileged user, and `.env` is excluded from the build context.

## Running a public instance

GPT Newspaper is designed to run locally or for a trusted group. If you expose it to the internet:

- Anyone who can reach it can spend **your** server-side API keys. Prefer leaving server keys unset so
  visitors bring their own, or put the app behind authentication.
- Set `ALLOW_MODEL_OVERRIDE=false` to pin the model, and tune `MAX_CONCURRENT_EDITIONS`.
- Serve it over HTTPS (keys travel in request bodies).
- Generated editions in `outputs/` are public to anyone with the link and are not cleaned up automatically.

## Supported versions

Security fixes are made on the latest release.
