# Changelog

All notable changes to `scitex-notification` are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.2.12]

First published release of the 0.2.10 / 0.2.11 work below: both tags exist
but neither reached PyPI. The release pipeline's SIF scripts were stale
(copied from another package; they required a Spartan-only apptainer shim
and wrote to `/data`), so every test leg failed before building.

### Fixed
- Release pipeline: port the host-agnostic SIF scripts used by
  scitex-logging (apptainer from the shim or PATH, job-owned RUNNER_TEMP
  scratch, digest-verified image via `SCITEX_CI_SIF_SHA256`).

## [0.2.11]

Tagged, never published (see 0.2.12). Contents below.

### Security
- STARTTLS now verifies the SMTP server certificate and host name
  (`ssl.create_default_context()`). Before, `starttls()` ran without a
  context, so an interceptor could present any certificate and receive the
  SMTP password. `send_email` / `send_with_profile` accept `ssl_context=`
  for a private CA. A relay with an untrusted certificate now fails with
  `ssl.SSLCertVerificationError` instead of sending.

### Added
- Message templates: `render_template(name, data) -> (subject, body)`,
  `validate_message(name, subject, body, **context)`,
  `register_template(name, render, validate)`, `list_templates()`,
  `load_message_data()` (dict / JSON / YAML) and `MessageFormatError`
  (lists every violation). Built-in `notice` template: subject
  `[SciTeX][<agent>] <KIND>: <title>` (NEEDS-YOU / DONE / STOPPED / FYI),
  sections NEEDS YOU / DONE / RUNNING (no action needed) in order, numbered
  questions with `-> recommend:` and `reply: "N X"`, footer
  `agent: | host: | card/PR:`, at most 20 lines, credential-shaped text
  refused.
- Email profiles: `get_profile(name)` reads
  `SCITEX_NOTIFICATION_PROFILE_<NAME>_{FROM,FROM_NAME,TO,SMTP_HOST,SMTP_PORT,PASSWORD,PASSWORD_FILE}`
  (password file must be owner-only); `send_with_profile(profile, subject,
  body, *, message_id, dedupe_key, dedupe_window_s, dry_run, template)`
  validates, de-duplicates, then sends. A profile never borrows the generic
  `SCITEX_NOTIFICATION_EMAIL_*` credential chain.
- `RateLimiter(window_s, state_dir=None, max_events=1)` with `allow` /
  `peek` / `hold` / `suppressed_count`: per-key repeat suppression in
  owner-only files under `flock`, shared across processes.
- `send_email(..., from_name="Display Name")`: the From header becomes
  `"Display Name" <from_addr>` (RFC 2047 for non-ASCII; CR/LF rejected).
  SMTP login and envelope sender stay the bare address.
- CLI: `list-templates`, `render-message`, `validate-message`,
  `show-profile`, `send-email` (exit 2 on invalid input). MCP:
  `notification_render_message`, `notification_validate_message`.
- `send_email(..., message_id="<local@domain>")`: an optional caller-chosen
  `Message-ID` header, so a sender can later match replies by their
  `In-Reply-To` / `References` headers. Malformed values (including any
  CR/LF) raise `ValueError`. Omitted, the submission server assigns one as
  before.

## [0.2.9]

### Added
- Public `send_email(to, subject, body, *, from_addr=, password=, smtp_host=, smtp_port=)`
  at the package top level — a side-channel-free SMTP send that takes an
  explicit, coherent credential set. Unlike the env-driven `EmailBackend`
  (whose independent `from`/`password` fallback chains can pair a sender from
  one identity with a password from another), the caller supplies all fields,
  so the SMTP login is always coherent. Used by scitex-agent-container's OAuth
  login-relay to email the auth URL from `agent@scitex.ai`.

## [0.2.5]

- Initial CHANGELOG entry — see git log for prior history.
