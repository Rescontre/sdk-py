# Changelog

## 0.1.1 - 2026-04-28

- **BREAKING:** `Client(...)` now requires an API key, sourced from the
  `api_key=` constructor argument or the `RESCONTRE_API_KEY` environment
  variable. Construction raises `RescontreConfigurationError` if neither is
  set. The facilitator began enforcing `X-API-Key` on `/verify` and `/settle`
  in commit `1ea7b3b` (2026-04-28).
- The SDK now sends `X-API-Key: <key>` on every `verify` and `settle`
  request. Other endpoints (`/health`, `/agents`, `/servers`, `/agreements`,
  `/settlement`) are unchanged.
- Added `AuthenticationError` (subclass of `RescontreAPIError`), raised
  without retry when the facilitator returns HTTP 401 from `verify` or
  `settle`.

## 0.1.0 - 2026-04-25

- Initial release.
