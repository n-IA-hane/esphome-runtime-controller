# Updating to Runtime Controller 2026.10.0

Use ESPHome **2026.9.0 or newer**. Update the firmware packages from the Intercom
repository together with Runtime Controller, then rebuild and upload the device.
This is a firmware dependency update, not a requirement to match the version of
the Home Assistant integration.

The easiest path is to start from an updated
[maintained device YAML](https://github.com/n-IA-hane/esphome-intercom/tree/main/yamls)
and reapply your GPIOs, board settings and customizations. The steps below are
for users keeping their own YAML.

## Check how each input reaches the controller

| Input | What to use | What to remove |
|---|---|---|
| VoIP state | `observe.voip_stack: phone` with the full profile, or a custom `voip:` mapping | Manual forwarding of the same call states |
| Media playback | `observe.media_player: speaker_media_player` | Callbacks that only send `media_playing`, `media_paused`, `media_idle` or `announcement_started` |
| Wi-Fi | `observe.wifi: true` | Duplicate forwarding of Wi-Fi connect/disconnect events |
| Mic/speaker mute | The corresponding `observe` switch binding | Duplicate runtime mute events, **not** the action that mutes the hardware |
| Voice Assistant | Shared Intercom voice callback packages | Unsupported `observe.voice_assistant`, if present |
| Micro Wake Word | Shared Intercom wake-word callback package | Unsupported `observe.micro_wake_word`, if present |
| HA API connection and timers | Shared Intercom callback packages | Only redundant copies of those same handlers |

The two unsupported observation keys previously accepted configuration without
registering a listener. They now fail validation. Removing their shared voice
callbacks would remove the real connection to the controller.

Keep user actions that do something else, such as updating a sensor or recording
a call. Only remove duplicate forwarding or competing output writers.

## Choose packages

These files are under `packages/runtime_controller/` in this repository. They
configure existing components and scripts; they do not create the hardware.

| Package | Adds | Required bindings or helpers |
|---|---|---|
| `base.yaml` | Controller `runtime`, base profile rules, initially empty feature selection | No audio or display components |
| `voice.yaml` | Voice rules and stop/start scripts | `va`, `speaker_media_player`, the Intercom voice/lifecycle globals and `ui_va_barge_start` / `ui_va_end` hooks |
| `media.yaml` | Media listener and ducking, which lowers music during higher-priority activity | `speaker_media_player`, `media_mixer_input`, `g_ducking_active` |
| `ringtone.yaml` | Call-state listener and ringtone actions | `phone`, `voip_start_ringtone`, `voip_stop_ringtone` |
| `timers.yaml` | Timer rules and alarm actions | `speaker_media_player`, `timer_alarm_loop`, `timer_alarm_auto_stop` |
| `display.yaml` | Map display decisions to the UI | `ui_state`, `render_ui_state`, the `ui_state_*` substitutions |
| `led_state.yaml` | Publish the numeric LED decision | `g_applied_led`; no physical LED required |
| `full_controller_base.yaml` | All adapters and Wi-Fi/mute/VoIP bindings | Their dependencies plus `mute` and `speaker_mute` |
| `full_controller.yaml` | Full base and physical LED output | Full-base dependencies plus `status_led`, or the overridden LED ID |
| `full_controller_no_led.yaml` | Full base without physical LED output | The full-base dependencies still apply |

Use the full presets with the complete Intercom profiles. For a smaller device,
include `base.yaml` and the adapters you actually need. Intercom's
[package guide](https://github.com/n-IA-hane/esphome-intercom/blob/main/packages/README.md)
explains where the supporting globals, callbacks and scripts come from.

For example, this fragment adds only the runtime's media binding to a device
that already supplies the player, mixer input and ducking global:

```yaml
packages:
  runtime_base: github://n-IA-hane/esphome-runtime-controller/packages/runtime_controller/base.yaml@main
  runtime_media: github://n-IA-hane/esphome-runtime-controller/packages/runtime_controller/media.yaml@main
```

Load the `runtime_controller` external component as shown in the
[installation instructions](README.md#start-with-a-maintained-device-profile).
Do not combine this fragment with a full runtime preset: the full preset already
includes these adapters.

### Rule selection is separate from hardware

The `features` setting selects built-in `voice_assistant`, `media_player` and
`timers` rules. `base.yaml` starts with `features: []`; feature packages add their
own selection. Enabling voice rules does not instantiate Voice Assistant.

When configuring `profile: full_voice_voip` directly, omitting `features`
selects all three rule sets and requires their named actions. If validation
reports a missing action, include the matching adapter or select only the
features you implement. For fully custom rules, omit `profile` and `features`.

## Review custom output callbacks

All bound output globals and the sequence counter are now written before policy
callbacks execute. For example, a display callback can read both the new display
mode and the new audio mode from the same update.

An event raised inside a callback is queued until that update finishes. If your
callback sends a second event and immediately reads its result, move that
follow-up work into the second event's `then:` or its policy callback.

Use one controller update when several facts must change together. Do not add
delays to try to make independently written globals line up.

## Check the result on the device

After upload, check the combinations your device supports:

1. Play media, then start and end a call. Check that the call indication clears
   and the remaining media state is shown correctly.
2. Pause music, ask the assistant a question, and wait for its reply. The
   responding indication should clear while the music remains paused.
3. Stop a voice response, then start another. Check that an earlier stop/restart
   operation does not unexpectedly restart the assistant.
4. If timers are configured, stop an alarm while another feature owns the
   announcement player. Check that the other sound is not stopped by timer cleanup.
5. Check reconnect and mute behavior without deleting hardware mute actions.

For a stuck indication, enable runtime debug and inspect the active activities
and resolved policies. The [diagnostic example](README.md#diagnosing-a-stuck-state)
shows how to expose a dump button. Test logs and successful compilation are
separate from confirming that sound and display output work on the device.
