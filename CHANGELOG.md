# Changelog

All notable changes to `scitex-notification` are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
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
