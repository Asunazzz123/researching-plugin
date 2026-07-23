# Anonymous discovery architecture

## Contents

1. Package boundaries
2. Access-state semantics
3. Provider and resolver policy
4. Adding an adapter
5. Authentication handoff

## Package boundaries

Keep business concepts out of a generic `utils` package.

| Package | Responsibility |
|---|---|
| `domain/` | Canonical `PaperRecord` and `AccessStatus` values |
| `application/` | Discovery orchestration, queue partitioning, manifests, login notices |
| `providers/` | Crossref, OpenAlex, and future metadata-index adapters |
| `resolvers/` | Unpaywall and future authorized full-text location resolvers |
| `infrastructure/` | Replaceable HTTP and external-system implementations |
| `utils/` | Stateless DOI, title, markup, and redaction functions only |
| `certification/` | OS-native secrets, encrypted browser state, and known-form autofill |

Depend inward: adapters may import domain objects, but domain objects must not import
providers, HTTP clients, browser clients, or credential stores.

## Access-state semantics

- `metadata_only`: Retain metadata when access has not been checked.
- `open_access`: Require a known legal OA location.
- `authentication_required`: Treat the paper as a subscription candidate that needs
  post-login entitlement checking. Do not claim that the institution subscribes.
- `unresolved`: Preserve the paper when neither OA nor a reliable subscription
  candidate can be established.

Never collapse `metadata_only` or `unresolved` into a negative boolean. Public indexes
are incomplete and provider outages must remain distinguishable from closed access.

## Provider and resolver policy

- Use Crossref as the no-key baseline. Include `mailto` for polite access when available.
- Add OpenAlex only when a free API key is available. Store the key in the OS credential
  store rather than CLI arguments or repository configuration.
- Run Unpaywall after DOI normalization. Treat `is_oa=false` as an authentication
  candidate, not proof of institutional entitlement.
- Prefer official APIs over publisher-page scraping. Use visible browser interaction
  only when an API cannot supply the user-requested information.
- Preserve partial success. Return `DiscoveryIssue` entries when one source fails while
  other sources succeed.
- Cache public metadata separately from encrypted authentication state.

## Adding an adapter

1. Implement `MetadataProvider` or `AccessResolver`.
2. Inject `JsonHttpClient`; do not hard-wire test network calls.
3. Return canonical `PaperRecord` objects and normalized DOI values.
4. Mark provider-specific fields as nullable.
5. Redact API keys, tokens, email parameters, and authorization headers from errors.
6. Add fixture-based parser tests and failure tests without calling the live service.
7. Add the adapter to the factory only when its credentials are explicitly configured.

For CNKI or publisher-specific adapters, use an official API when available. Otherwise,
limit browser work to visible metadata and user-authorized downloads; do not bypass
CAPTCHA, access controls, robot limits, or subscription checks.

## Authentication handoff

Build a login notice only for the `authentication_required` partition. After the user
logs in:

1. Recheck entitlement for each candidate.
2. Separate downloadable, unavailable, and expired-session records.
3. Present the exact download manifest.
4. Download only user-selected records with conservative concurrency.
5. Return to visible login for MFA, CAPTCHA, consent, or expired sessions.
