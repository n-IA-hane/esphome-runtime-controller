# Changelog

## 2026.9.0, 2026-08-29

Existing runtime-controller YAML remains compatible. No migration is required.

### Added

- `storage_in_psram` can place persistent reducer state in PSRAM on large voice
  and display profiles. The option is disabled by default and requires the
  ESPHome `psram` component when enabled.

### Changed

- Activity matching and policy resolution share one implementation, removing
  duplicate state checks from individual runtime features.
- The component schema and tests are aligned with current ESPHome validation
  and code-generation contracts.
