# Modular runtime packages

Requires ESPHome 2026.9.0 or newer. Update the matching Intercom and Runtime
Controller components together when adopting these package changes.

## Component observation

The native `observe` bindings are `voip_stack`, `media_player`, `wifi`,
`microphone_mute` and `speaker_mute`. Voice Assistant and Micro Wake Word continue
to use official callbacks in shared Intercom packages. No new producer fork or
private callback API is required.

Remove `observe.voice_assistant` and `observe.micro_wake_word` from custom YAML.
Previously they were accepted without establishing an observation. The schema now
rejects unsupported keys. Keep the shared voice and wake-word callback packages.
Remove duplicate media, Wi-Fi and mute forwarding only when their native listener
is selected; keep user automations and hardware mute actions.

## Package selection

`base.yaml` supplies only the controller. Add `voice.yaml`, `media.yaml`,
`ringtone.yaml`, `timers.yaml`, `display.yaml` and `led_state.yaml` according to the
components you actually have. The complete presets compose these same adapters;
there is no second implementation for the no-LED variant.

For the built-in profile, `features` selects `voice_assistant`, `media_player`
and `timers`. The base package starts with an empty list, and each feature adapter
adds its rule set. Selecting a rule set does not instantiate its components.
Omitting the field when directly configuring the full profile selects the complete
rule set. Custom activities/events remain supported without the built-in profile.

## Observable behavior

- All bound globals and the sequence are published before policy effects run.
- Reentrant events are queued until the current event and its callbacks finish.
- Voice completion handles music paused, playing or idle in either completion order.
- Losing the VA client clears the interrupted voice phase before reconnect.
- A stop timeout is not reported as a successful physical stop.
- A new voice command replaces a pending stop/restart continuation.
- LED and output-script code is included only when those bindings are selected.

Update custom event handlers that relied on partially published globals or nested
execution. Such intermediate states are no longer observable.
