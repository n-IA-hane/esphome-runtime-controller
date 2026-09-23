# Changelog

## 2026.10.0-dev: reliable full profiles and optional features

This development preview requires ESPHome 2026.9.0 or newer. Update Intercom and Runtime Controller together.

- Voice Assistant returns to idle after speaking even when music was paused beforehand.
- Overlapping voice, call, timer and media events update the device state consistently.
- Stopping one timer does not dismiss another alarm or interrupt an incoming call.
- Wi-Fi, media-player and mute state use existing native callbacks. Voice Assistant and wake-word wiring uses shared standard ESPHome callbacks.
- Packages can select voice, media, timers, ringtone, display and LED features separately. The full preset still includes the complete experience.
- LED and script dependencies are included only when configured.

Custom YAMLs may need changes: see the [migration guide](https://github.com/n-IA-hane/esphome-runtime-controller/blob/dev/MIGRATION.md) and [Intercom package guide](https://github.com/n-IA-hane/esphome-intercom/blob/dev/packages/README.md).

Rebuild and upload your firmware. Installing the Home Assistant integration alone does not update the device.

Thanks to everyone who donated to support the project.

---

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
