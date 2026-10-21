# ESPHome Runtime Controller

*Developed and maintained by n-IA-hane, with community contributions and support. [❤️ Sponsor the project](https://github.com/sponsors/n-IA-hane)*

[Development preview 2026.10.0-dev](https://github.com/n-IA-hane/esphome-runtime-controller/releases/tag/v2026.10.0-dev) uses the coordinated `dev` sources.

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

Stable release: [2026.10.1](https://github.com/n-IA-hane/esphome-runtime-controller/releases/tag/v2026.10.1).
Requires ESPHome **2026.10.0 or newer**. See the
[changes since 2026.9.2](CHANGELOG.md) and [migration guide](MIGRATION.md).

## Choose how far you need to go

| Your situation | Read next | What you change |
| --- | --- | --- |
| You want a working voice/intercom device | [Maintained profiles](#start-with-a-maintained-device-profile) | The board's feature list; its runtime rules are already supplied |
| You want to understand the reducer | [Music interrupted by a call](#what-happens-when-a-call-interrupts-music), then [the button exercise](#a-small-example-you-can-try) | On a separate test configuration, simulate events and observe which activity wins |
| You already have a player and LED | [Connect an existing player](#connect-an-existing-media-player-without-forwarding-callbacks) | Observe real inputs and connect one output |
| You are composing a custom voice/call device | [Feature and adapter selection](#choosing-only-the-features-you-need) | Choose rules, provide their components and attach each adapter once |
| You need different priorities or custom output behavior | [The YAML reference](esphome/components/runtime_controller/README.md) | Change a policy or event and check the resulting activity sequence |

The small examples teach coordination. They are alternatives to a maintained
controller configuration, not blocks to paste alongside its existing controller.
You can use the maintained firmware without learning the reducer implementation.
VoIP-only device profiles keep their direct VoIP Stack callbacks and do not
instantiate Runtime Controller.

## Start with a maintained device profile

For a complete intercom or voice device, start from an
[Intercom YAML profile](https://github.com/n-IA-hane/esphome-intercom/tree/main/yamls).
It supplies the microphone, speaker, runtime packages and board-specific wiring.

For your own controller, load the component below. A maintained device package
already loads it; do not add a duplicate source or controller there.

```yaml
external_components:
  - source: github://n-IA-hane/esphome-runtime-controller@dev
    components: [runtime_controller]
```

For a maintained Intercom device, edit the existing `firmware_features` list in
its YAML. Its device package selects the required runtime bindings together with
the components and controls. You do not need to write activities, priorities or
voice stop/restart scripts yourself.

```yaml
substitutions:
  firmware_features: [voice, wake_word, voip, music, timers, status_led]
```

Keep the other substitutions and the device package from that board's YAML.
Removing `voip` also removes the phone input, phone controls and its UI bindings.
Removing `music` leaves announcement playback available for voice replies and
ringtones. The [Intercom package guide](https://github.com/n-IA-hane/esphome-intercom/blob/dev/packages/README.md)
contains the complete selection table.

The feature-list layout is available in the coordinated Intercom development
preview. Use its matching `dev` sources; older stable device YAMLs can still use
the previous composition. The
[device migration checklist](https://github.com/n-IA-hane/esphome-intercom/blob/dev/docs/BREAKING_CHANGES.md#development-firmware-new-device-packages)
explains what to carry over from an existing installation.

The older `packages/runtime_controller/full_controller.yaml` and individual
adapter paths remain compatibility entrypoints. Their application bindings now
have one implementation in Intercom. They still require the component IDs and
helpers documented in the [migration guide](MIGRATION.md#choose-packages).
Do not add a legacy full preset on top of a new device package.

## What happens when a call interrupts music

| Moment | Facts kept by the controller | Result |
| --- | --- | --- |
| Music starts | Music is active | Media indication, normal music level |
| A call arrives | Music is still active; the phone is ringing | Call indication and ringtone, music is attenuated |
| The call is answered | Music is still active; the phone is in a call | Call indication, no ringtone, music remains attenuated |
| The call ends | Music remains active | Media indication and normal music level return |

The controller does not receive RTP or decode audio. It selects the requested
outputs and invokes the existing component actions. The media player owns its
streams; VoIP Stack owns the call. A higher-priority indication does not erase
background activity.

Most of a display YAML describes pins, fonts, pictures and geometry. A reducer
cannot remove those definitions. The device packages remove repeated wiring from
the user-facing YAML, while the coordinator removes conflicting decisions from
callbacks. These solve different parts of the original complexity.

## Automatic VoIP binding in shared packages

From 2026.10.1, the full controller and ringtone packages use the single VoIP
component without requiring `id: phone`. You can choose a different ID or omit
it when no lambda needs to refer to the component by name.

For a custom observer, `voip_stack: {}` under `observe:` selects that same
instance. Supplying an explicit ID remains supported. This selects an existing
VoIP component; it does not create another phone.

## Which components are observed directly?

Input adapters use the component's existing notifications or compose into its
official automation chain. Publicly readable state is acquired at setup; an
unobservable detailed phase or past wake-word detection is not invented.

| Input | Connection to the controller |
|---|---|
| VoIP call state | `observe.voip_stack` with a built-in profile (empty selects the single phone), or a custom `voip:` mapping |
| Media player | `observe.media_player` |
| Wi-Fi connection | `observe.wifi: true` |
| Microphone mute switch | `observe.microphone_mute` |
| Speaker mute switch | `observe.speaker_mute` |
| Voice Assistant | `observe.voice_assistant: va` |
| Micro Wake Word | `observe.micro_wake_word: mww` |
| HA API connection | `observe.api: true`, diagnostic clients filtered and 250 ms reconnect grace |
| Assist timers | `observe.timers: va`, reading the existing VA timer collection |

When you enable a native listener, remove YAML callbacks that only forward the
same event. Keep your other automations. Observing a mute switch does not mute
hardware by itself: the switch's hardware mute action must remain.

The media observer replays the initial state, then emits only changes between
playing, paused, announcing and idle. Volume or metadata updates that republish
the same state do not retrigger controller actions. Existing player callbacks
and explicit `runtime_controller.event` actions keep their usual behavior.

Voice, wake-word, timer and API bindings preserve the source's existing user
actions and delays in one automation chain. Remove only duplicate state
forwarding when opting into an observer. See the
[exact listener events](esphome/components/runtime_controller/README.md#component-observation)
when building custom rules.

## Connect an existing media player without forwarding callbacks

These shorthand triggers are available in the coordinated development sources.
Use `@dev` for this example. Existing explicit activity/policy configurations stay
supported, including `outputs.led` presets.

Suppose your player is `speaker_media_player` and your light is `status_led`,
with the ordinary ESPHome `Pulse` effect already declared on that light:

```yaml
runtime_controller:
  id: runtime
  observe:
    media_player: speaker_media_player
  on_music:
    then:
      - light.turn_on:
          id: status_led
          effect: Pulse
  on_announcement:
    then:
      - light.turn_on:
          id: status_led
          effect: None
          brightness: 100%
  on_idle:
    then:
      - light.turn_off: status_led
```

No manual activity table, event forwarding or numeric state mapping is needed.
`on_music` means music became the **selected presentation**. It runs again when
an interruption ends and music remains active, without another player `on_play`.
Repeated notifications of an unchanged presentation do not restart the action.
The light component owns and runs the effect; the controller chooses when to
request it. It does not render animation frames or download effects.

The inferred `presentation` profile observes only. It does not start Assist,
stop calls or change music volume. Your components retain those responsibilities;
the maintained Full profile supplies its existing coordination actions.

## Add sources and customize presentation

Add the existing component IDs under `observe`:

```yaml
runtime_controller:
  observe:
    media_player: speaker_media_player
    voice_assistant: va
    micro_wake_word: mww
    timers: va
    voip_stack: phone
    wifi: true
    api: true
  presentation:
    priorities:
      music: 50
  on_ringing:
    then:
      - light.turn_on:
          id: status_led
          effect: Pulse
  on_call:
    then:
      - light.turn_on:
          id: status_led
          effect: None
  on_listening:
    then:
      - logger.log: Assistant is listening
```

Use this as an extension of the same controller, not a second instance.
`on_ringing` is an incoming ringing call; `on_call` is an established call.
Outgoing setup and remote ringing have `on_calling` and `on_remote_ringing`.
Keep an `on_idle` action if your output should be cleared when no activity wins.

Omitted priorities retain the existing profile defaults. Overrides affect the
presentation, LED and display policies only, never call control or ducking.
`on_state_change` provides the string arguments `previous` and `current` for
custom displays. Native light effects need no animation loop in your YAML.
Long-running custom scripts retain normal ESPHome semantics: explicitly stop
such scripts from another trigger when that is what your application requires.

Source events and selected presentation are different. For raw notifications,
advanced configurations can still use `events.<event>.then`. A player's
`ANNOUNCING` state is its reported lifecycle state, not a measurement that sound
has physically reached the speaker.

## Choosing only the features you need

For a maintained Intercom device, choose the application in `firmware_features`.
The device package selects its runtime bindings for you. To remove telephone
functionality, remove `voip` there; changing an internal runtime rule alone does
not remove the SIP component.

For a custom or legacy composition, runtime packages are split into controller,
voice, media, timer, ringtone, display and LED configuration. For example, a
voice-only device does not need the ringtone adapter. These low-level adapters
refer to existing component IDs and scripts; they do not create all dependencies.

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
other YAML components only when the device uses them. In a maintained device,
removing `display` from `firmware_features` removes its presentation bindings.
In a custom composition, leave out the `display.yaml` adapter when there is no
display script to call. Legacy full presets deliberately include all their
adapters; custom builds can use `base.yaml` plus selected adapters instead.

The generic reducer still needs its common rule tables and queues. Their
capacity is fixed; selecting fewer profile rules does not resize every common
table. The exclusions above remove feature-specific code and storage, rather
than promising that the entire controller has zero overhead. Build flags apply
to the whole firmware: a feature needed by one controller instance is compiled
for that firmware.

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

The log lists active activities and, for each policy, its value and the activity
that selected it (`source=...`). This source is recorded by the existing resolver,
not recomputed by a second diagnostic state machine. If the
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
