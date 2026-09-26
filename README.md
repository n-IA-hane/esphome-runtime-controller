# ESPHome Runtime Controller

Runtime Controller coordinates the visible state and shared controls of an
ESPHome device that combines music, Voice Assistant, calls and timers.

For example, music is playing when a call arrives. The LED should show the call,
but the device must still remember that music is playing. When the call ends,
the LED should return to the music indication. A callback from the music player
must not overwrite the call indication halfway through the call.

The controller makes that decision in one place. Components report what is
happening; priorities decide what the LED, display, ringtone and audio controls
should do. The audio components still own playback and the VoIP component still
owns calls.

**2026.10.0 release candidate:** requires ESPHome **2026.9.0 or newer**.
See the [changes since 2026.9.2](CHANGELOG.md) and [migration guide](MIGRATION.md).
The stable release is [2026.9.2](https://github.com/n-IA-hane/esphome-runtime-controller/releases/tag/v2026.9.2)
until the candidate is published.

## Start with a maintained device profile

For a complete intercom or voice device, start from an
[Intercom YAML profile](https://github.com/n-IA-hane/esphome-intercom/tree/main/yamls).
It supplies the microphone, speaker, runtime packages and board-specific wiring.

For your own controller, load the component:

```yaml
external_components:
  - source: github://n-IA-hane/esphome-runtime-controller@main
    components: [runtime_controller]
```

The full runtime preset is available as a package:

```yaml
packages:
  runtime_controller: github://n-IA-hane/esphome-runtime-controller/packages/runtime_controller/full_controller.yaml@main
```

That package expects the component IDs and supporting scripts used by the
Intercom full profiles. It does not create a microphone, speaker, media player
or phone. For a custom device, read [package requirements](MIGRATION.md#choose-packages)
before including it. Use `full_controller_no_led.yaml` when there is no physical
status LED; its other dependencies are the same.

## Four terms used in the YAML

| Term | Meaning | Example |
|---|---|---|
| Activity | A fact that is currently true | Music is playing. |
| Event | A notification that changes facts | The call ended. |
| Policy | A decision for one output | The status indicator should show a call. |
| Action | An ESPHome automation requested by an event | Start Voice Assistant. |

The **reducer** is the code that applies an event to the current activities and
calculates the new decisions. Several activities may be active together. Unlike
a single list of mutually exclusive device states, this preserves background
work while a higher-priority activity is visible.

Each policy is resolved separately: an activity can change the display without
changing the audio policy. Higher priority wins. If priorities are equal, the
activity declared later wins; use different priorities when precedence matters.

## A small example you can try

Add this to a device with the component loaded and `logger:` enabled. It uses
buttons to simulate music and calls, so no audio hardware is needed. The output
is a number in the log: `0` for idle, `1` for music and `2` for a call.

```yaml
runtime_controller:
  id: runtime
  auto_events: false
  activities:
    idle:
      initial: true
      priority: 0
      policies:
        status: idle
    music:
      priority: 100
      policies:
        status: music
    call:
      priority: 700
      policies:
        status: call
  events:
    music_started:
      activate: music
    music_stopped:
      deactivate: music
    call_started:
      activate: call
    call_ended:
      deactivate: call
  policies:
    status:
      values:
        idle: 0
        music: 1
        call: 2
      on_change:
        - logger.log:
            format: "Resolved status: %d"
            args: [value]

button:
  - platform: template
    name: Simulate music start
    on_press:
      - runtime_controller.event:
          id: runtime
          event: music_started
  - platform: template
    name: Simulate call start
    on_press:
      - runtime_controller.event:
          id: runtime
          event: call_started
  - platform: template
    name: Simulate call end
    on_press:
      - runtime_controller.event:
          id: runtime
          event: call_ended
  - platform: template
    name: Simulate music stop
    on_press:
      - runtime_controller.event:
          id: runtime
          event: music_stopped
```

Press the buttons in the order shown:

| Input | Active activities | Resolved status |
|---|---|---|
| Music starts | idle, music | music |
| Call starts | idle, music, call | call |
| Call ends | idle, music | music |
| Music stops | idle | idle |

There is no saved "previous status" to restore. Ending the call removes only the
call activity, and the remaining activities determine the output.

To drive real hardware, replace the log action with your display or LED action.
Keep that output under the controller's control: a second automation writing to
the same LED can still overwrite the result.

## Which components are observed directly?

A native listener subscribes to the component's existing state notifications.
It also reads the current state during setup, so the controller does not have
to wait for the next change.

| Input | Connection to the controller |
|---|---|
| VoIP call state | `observe.voip_stack` with the built-in profile, or a custom `voip:` mapping |
| Media player | `observe.media_player` |
| Wi-Fi connection | `observe.wifi: true` |
| Microphone mute switch | `observe.microphone_mute` |
| Speaker mute switch | `observe.speaker_mute` |
| Voice Assistant | Shared Intercom packages forward the official ESPHome callbacks |
| Micro Wake Word | Shared Intercom package forwards `on_wake_word_detected` |
| HA API connection and timer events | Shared Intercom callback packages |

When you enable a native listener, remove YAML callbacks that only forward the
same event. Keep your other automations. Observing a mute switch does not mute
hardware by itself: the switch's hardware mute action must remain.

`observe.voice_assistant` and `observe.micro_wake_word` are unsupported. Use the
shared callback packages for those components. See the
[exact listener events](esphome/components/runtime_controller/README.md#component-observation)
when building custom rules.

## Connect an existing media player without forwarding callbacks

Suppose your device already has Wi-Fi, a media player named
`speaker_media_player`, and a light named `status_led`. You want the light to
show music, a higher-priority announcement, or a Wi-Fi outage.

Start a separate custom controller with the fragment below. It replaces the
button-driven example above; do not add a second controller with the same ID.
The state listener supplies the events, so you do not need to add `on_play`,
`on_pause` and `on_idle` callbacks to the media player.

```yaml
runtime_controller:
  id: runtime
  auto_events: false
  observe:
    media_player: speaker_media_player
    wifi: true
  activities:
    idle:
      initial: true
      priority: 0
      policies:
        led_status: idle
    music:
      priority: 100
      policies:
        led_status: media
    announcement:
      priority: 200
      policies:
        led_status: responding
    disconnected:
      priority: 900
      policies:
        led_status: no_wifi
  events:
    media_playing:
      activate: music
      deactivate: announcement
    media_paused:
      deactivate: [music, announcement]
    media_idle:
      deactivate: [music, announcement]
    announcement_started:
      activate: announcement
    wifi_connected:
      deactivate: disconnected
    wifi_disconnected:
      activate: disconnected
  outputs:
    led:
      id: status_led
      preset: rgb_single
```

The three design steps are visible in this example:

1. **Observe the inputs:** `observe` connects the existing player and Wi-Fi.
2. **Decide precedence:** the announcement outranks music; disconnection outranks
   both. Each event changes only the facts it owns.
3. **Connect the output once:** `outputs.led` renders the winning `led_status`.

When the player returns from an announcement to playing or paused, its native
state notification selects the corresponding result. To change precedence,
edit the priorities. To change colors, override the LED states as shown in the
[YAML reference](esphome/components/runtime_controller/README.md#led-output).

This example coordinates status only. It does not pause music, adjust volume or
implement Voice Assistant. For those behaviors, use the corresponding adapters
and the maintained voice/intercom rules below.

## Choosing only the features you need

The runtime packages are split into controller, voice, media, timer, ringtone,
display and LED configuration. For example, a voice-only device does not need the
ringtone adapter, and a device without a display does not need the display
adapter. The packages refer to existing component IDs and scripts; they do not
create all of their dependencies automatically.

The built-in `full_voice_voip` profile supplies the activity rules. Its `features`
setting selects the voice, media and timer rule sets. Selecting a rule set and
including the hardware that carries it out are separate steps.

For a device with Voice Assistant but no phone, Intercom also provides a
[voice-only runtime preset](https://github.com/n-IA-hane/esphome-intercom/blob/main/packages/presets/voice_runtime.yaml).
Supply its microphone, media player and mixer bindings as described in that
package. Add wake-word hardware and callbacks separately if needed.

See the [package table and migration examples](MIGRATION.md#choose-packages).
For custom priorities, event cases, grouped activities and output configuration,
use the [YAML reference](esphome/components/runtime_controller/README.md).

## What an unused feature costs

The firmware only includes the optional connections selected in its YAML:

| Omitted configuration | Excluded from the runtime controller |
|---|---|
| Both VoIP observation forms | VoIP callbacks, call-state tracking fields and VoIP queue handling |
| `outputs.led` | Light renderer, light pointer and the 32-entry LED mapping table |
| `output_script` | The script connection and its stored pointer |
| `observe.wifi` | Wi-Fi listener and its stored pointer |
| `observe.media_player` | Media listener and its stored pointer |
| Either mute observation | That switch's callback and pointer, independently of the other switch |
| All Wi-Fi/media/mute observations | The observer component itself |

The controller does not import LVGL or a display driver. Those are supplied by
other YAML components only when the device uses them. A `display.yaml` adapter
connects decisions to your existing display script; leave it out on a device
without that UI. The full preset deliberately includes all its adapters, so use
`base.yaml` plus selected adapters for a smaller device.

The generic reducer still needs its common rule tables and queues. Their
capacity is fixed; selecting fewer profile rules does not resize every common
table. The exclusions above remove feature-specific code and storage, rather
than promising that the entire controller has zero overhead. Build flags apply
to the whole firmware: a feature needed by one controller instance is compiled
for that firmware.

## How overlapping events are handled

The controller finishes one state update before processing events raised by
that update. All bound globals are written before output callbacks run. A
callback can therefore read the new display and audio decisions together.

Named actions are queued for execution from the main loop. Events arriving
inside a callback are also queued. These queues are bounded: a self-triggering
automation cannot grow them indefinitely. Queue overflow is logged; it must be
investigated rather than treated as successful delivery of every event.

For voice replies, the full profile tracks both the assistant run and the end
of playback. The run may finish while reply audio is still playing. Once both
have finished, the responding state clears. Music that was paused stays paused;
playing music can become the visible state again.

The controller also waits for Voice Assistant to stop before completing a
stop/restart operation. A timeout does not count as confirmation that it stopped.

## Diagnosing a stuck state

Enable runtime debug when building the firmware:

```yaml
runtime_controller:
  id: runtime
  debug: true
```

With the maintained full packages, set the `runtime_controller_debug`
substitution to `"true"` instead. Add an optional diagnostic button:

```yaml
button:
  - platform: template
    name: Runtime snapshot
    entity_category: diagnostic
    on_press:
      - runtime_controller.dump:
          id: runtime
          reason: manual_check
```

The log lists active activities and the winning value for each policy. If the
LED stays in a call state, first check whether the call activity is still active.
If the resolved policy is already idle, inspect the LED automation instead.
For a stuck response, check the voice completion and media events together.

**Detailed runtime dumps require `debug: true` at compile time.** Merely adding
the dump button does not enable them. Use this setting for investigation because
it adds event logging. It is separate from the Audio Stack and VoIP on-demand
diagnostic actions. See the [debug reference](esphome/components/runtime_controller/README.md#debugging-and-limits)
for queue limits and error reporting.

## Development, license and support

The controller was extracted from the
[Intercom project](https://github.com/n-IA-hane/esphome-intercom).
[SOURCE.md](SOURCE.md) records its origin. License: MIT.

The [test instructions](esphome/components/runtime_controller/README.md#running-the-tests)
cover host-side C++ execution and schema validation. Passing those tests does
not by itself verify audio playback, wake-word recognition or a physical display.

If this component helps your project,
[consider sponsoring development](https://github.com/sponsors/n-IA-hane).
Contributions support development tools, services and test hardware.
