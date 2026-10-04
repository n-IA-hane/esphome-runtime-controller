# Changelog

## 2026.10.1

Changes since stable **2026.10.0**.

### 🧩 Your phone no longer needs to be named `phone`

The shared runtime packages now resolve the VoIP component automatically instead
of requiring its declaration to use `id: phone`.

This removes unnecessary coupling between the packages and the name chosen in a
firmware YAML. Explicit IDs remain available for custom configurations, and
lambdas that address a component by name still need that declared ID.

The change covers the full controller's VoIP observer and the shared ringtone
package. It builds on the component's existing automatic binding.

### 📦 Updating

Refresh the Runtime Controller component and packages from `main`, then rebuild
your firmware. The coordinated reference profiles use Runtime Controller
**2026.10.1**, ESP VoIP Stack **2026.10.1**, and Audio Stack **2026.10.2**.

Requires ESPHome **2026.9.0 or newer**.

[Configuration guide](https://github.com/n-IA-hane/esphome-runtime-controller/blob/main/README.md)

## 2026.10.0: more reliable voice controls and simpler YAML packages

Changes since stable **2026.9.2**.

### Voice responses, stop commands and timers

- **Paused music no longer leaves the assistant stuck in "responding".** If you
  pause music, speak to the assistant and wait for its reply, the device returns
  to idle when the reply finishes. The music stays paused.
- **Stopping the assistant cancels pending restarts.** An older request to restart
  listening can no longer take effect after a newer stop command. The controller
  waits for confirmation that Voice Assistant has stopped; if it takes too long,
  it reports a timeout instead of treating the stop as complete.
- **Reconnecting starts from a clean voice state.** Losing the connection to the
  Voice Assistant client clears the interrupted listening or responding state.
- **Stopping a timer alarm no longer cuts off another sound.** The timer cleanup
  checks whether an incoming-call ringtone or assistant response is using the
  announcement player before stopping it.

### More reliable handling of overlapping events

A call can start while music is playing, or end while the display is being
updated. The controller now completes each state update before handling events
raised by that update. LED, display and other output callbacks read the complete
new state, rather than a mixture of old and new values.

Rapid VoIP state changes are also kept in order. For example, a queued ringing
notification retains its ringing state even if the call has already been
answered by the time that notification is processed.

### Less manual wiring in custom YAMLs

New `observe` bindings let the controller read Wi-Fi connectivity, media-player
state and microphone/speaker mute switches directly. You can remove the YAML
callbacks that only forward those same state changes to the controller. The
bindings also read the current state at startup.

Voice, media, timers, ringtone, display and LED configuration are now split into
separate packages. A custom device can include the parts it needs. The no-LED
preset uses these shared packages instead of maintaining a second copy of the
full configuration.

The new `features` setting selects which built-in voice, media and timer rules
to include. Unused VoIP, LED and output-script connections now exclude their stored state
as well as their code. LED-free builds omit the LED mapping table. Wi-Fi, media
and each mute observer are also compiled only when selected.

### Updating an existing device

Use **ESPHome 2026.9.0 or newer**. Update the firmware packages from the Intercom
repository together with Runtime Controller. The Home Assistant integration does
not need the same version number as the ESP firmware.

The easiest option is to start from one of our updated
[maintained YAML profiles](https://github.com/n-IA-hane/esphome-intercom/tree/main/yamls)
and reapply your board settings and customizations.

**Alternatively, update your existing YAML:**

- Remove `observe.voice_assistant` and `observe.micro_wake_word` if present.
  These settings previously accepted configuration but did nothing; they now
  cause a validation error. **Keep the shared Voice Assistant and wake-word
  callback packages**, which provide the actual connection to the controller.
- Where you enable native Wi-Fi, media or mute observation, remove callbacks
  that send duplicate state updates. Keep your hardware mute actions and other
  user automations.
- Follow the guides below to select individual packages or adapt custom
  controller callbacks.

Rebuild and upload the firmware to apply these changes.

[Runtime migration guide](https://github.com/n-IA-hane/esphome-runtime-controller/blob/main/MIGRATION.md)
| [Intercom package guide](https://github.com/n-IA-hane/esphome-intercom/blob/main/packages/README.md)

### Earlier error detection and additional tests

Configuration validation now rejects more invalid combinations, such as two
mutually exclusive states both being active at startup. If memory allocation
for controller state fails, setup stops instead of continuing with incomplete
configuration.

New automated tests exercise overlapping events, rapid call-state changes,
full event queues, allocation failures and assistant replies with music idle,
playing or paused.

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
