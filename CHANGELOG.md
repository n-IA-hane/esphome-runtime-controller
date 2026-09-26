# Changelog

## 2026.10.0: voice completion fixes and modular runtime packages

Release candidate. Changes since stable **2026.9.2**.

### Voice Assistant returns to the correct state

- Fix the device remaining in the responding state after its spoken reply ends
  when music was already paused. Completion now handles paused, playing and idle
  media, whether the pipeline or audio playback finishes first.
- Explicit voice stop waits for the stop acknowledgement. A stop timeout is
  reported as a timeout instead of being treated as successful completion.
- A newer voice command replaces a pending stop/restart operation, preventing an
  older continuation from restarting the assistant after a later stop.
- Disconnecting the Voice Assistant client clears the interrupted voice phase
  before reconnecting.

### Consistent updates when events overlap

The controller now publishes all bound state values and the sequence number
before running output callbacks. A callback therefore sees the complete new
state, rather than a mixture of old and new values.

Events raised by callbacks wait until the current event finishes. Queued VoIP
observations retain the call state captured when they arrived, so rapid call
transitions are processed in order. If that queue overflows, the controller
reconciles with the latest call state after draining it.

Stopping a timer alarm no longer unconditionally stops the shared announcement
player. The timer adapter preserves an active call ringtone or Voice Assistant
response instead of interrupting it.

### Direct state listeners and optional packages

- Add native listeners for Wi-Fi connectivity, media-player state and microphone
  and speaker mute switches. These bindings also read the current state at setup,
  reducing manual YAML event forwarding.
- Split the full runtime packages into selectable voice, media, timer, ringtone,
  display and LED adapters. The no-LED preset now composes shared packages instead
  of duplicating the full controller configuration.
- Add `features` selection for the built-in profile, so configurations can include
  only the voice, media and timer rules they need.
- Compile LED and output-script support only when those outputs are configured.

### Upgrading your YAML

Use **ESPHome 2026.9.0 or newer** and update Intercom and Runtime Controller
together when adopting these package changes.

Start from one of our updated
[maintained YAML profiles](https://github.com/n-IA-hane/esphome-intercom/tree/main/yamls)
and reapply your board settings and customizations. These profiles already
include the migration changes.

**Alternatively, migrate your existing YAML:**

- Remove `observe.voice_assistant` and `observe.micro_wake_word` if present. They
  previously accepted configuration without establishing an observation; they
  now produce a validation error. Keep the shared Voice Assistant and wake-word
  callback packages.
- Remove duplicate Wi-Fi, media and mute event forwarding where you enable the
  corresponding native listener. Keep hardware mute actions and your own
  automations.
- For a custom composition, select the adapters needed by your hardware as
  described in the migration guide. Update custom callbacks that relied on
  partially updated globals or immediate nested event execution.

Rebuild and upload the firmware after updating the packages.

[Runtime migration guide](https://github.com/n-IA-hane/esphome-runtime-controller/blob/main/MIGRATION.md)
| [Intercom package guide](https://github.com/n-IA-hane/esphome-intercom/blob/main/packages/README.md)

### Configuration checks and regression coverage

- Reject conflicting initial members and derived members of exclusive activity
  groups, unsupported observation keys and incomplete feature bindings.
- Stop configuration safely after a runtime-storage allocation failure, rather
  than continuing with partially initialized state.
- Add executable tests for event ordering, complete state publication, queue
  limits, VoIP observations, allocation failures, native listeners and voice
  completion with idle, playing or paused music.

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
