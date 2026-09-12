# Changelog

## ESPHome Runtime Controller 2026.9.2

This release identifies the Runtime Controller used by ESPHome Intercom 2026.9.2.

The runtime implementation is unchanged from 2026.9.1. Existing activities, priorities and policies remain compatible; no configuration migration is needed.

---

## ESPHome Runtime Controller 2026.9.1

This release marks the Runtime Controller used by the stable ESPHome Intercom 2026.9.1 platform.

The component source is unchanged from v2026.9.0. Existing activity rules, priorities, runtime policies and YAML configuration remain compatible; no migration is required.

The version number is aligned with the coordinated platform release so users can identify the matching component set.

[Platform release notes and update instructions](https://github.com/n-IA-hane/esphome-intercom/releases/tag/v2026.9.1)


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
