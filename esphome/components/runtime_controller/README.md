# Runtime Controller YAML reference

Start with the [practical guide](../../../README.md) for an introduction and a
working button-driven example. This reference explains configuration fragments
that you merge into a device YAML. IDs such as `phone`, `speaker_media_player`
and `status_led` refer to components you must supply.

Requires ESPHome 2026.9.0 or newer for the maintained packages.

## Controller options

| Option | Default | Meaning |
|---|---|---|
| `id` | Generated | Use an explicit ID, such as `runtime`, when sending actions. |
| `debug` | `false` | Compile detailed event and state logging. Required for detailed dumps. |
| `storage_in_psram` | `false` | Put the controller's fixed tables and queues in PSRAM. Requires `psram:`. |
| `profile` | None | `full_voice_voip` supplies rules for the maintained voice/intercom devices. |
| `features` | All three when omitted with the profile | Select `voice_assistant`, `media_player`, `timers`, or `[]`. Valid only with `full_voice_voip`. |
| `activities` | `{}` | Facts, priorities and desired policy values. |
| `groups` | `{}` | Lists of activities that cannot be active together. |
| `derived_activities` | `[]` | Activities calculated from other activities. |
| `events` | `{}` | Named inputs and the changes they make. |
| `auto_events` | `true` | Add an activation event with the same name as each declared activity. It does not add a matching stop event. |
| `actions` | `{}` | Named ESPHome automations requested by events. |
| `policies` | `{}` | Map resolved policy values to globals and automations. |
| `observe` | `{}` | Connect existing components to the controller. See below. |
| `voip` | None | Custom mapping from SIP call states to activities, instead of the profile's mapping. |
| `outputs.led` | None | Render the `led_status` policy on a light. |
| `output_script` | None | Run an existing parameterless script after a committed change. |
| `state_outputs` | `{}` | Expose the activity bitmask and sequence number through globals. |

The profile is a set of rules, not a hardware preset. Enabling voice rules does
not create Voice Assistant, its microphone or its action scripts. The
[package guide](../../../MIGRATION.md#choose-packages) lists those requirements.

## Activities and priorities

```yaml
runtime_controller:
  id: runtime
  activities:
    idle:
      initial: true
      priority: 0
      policies:
        status: idle
        ringtone: stop
    ringing:
      priority: 700
      policies:
        status: ringing
        ringtone: play
```

An activity has `priority` (default `0`, range -32768 to 32767), `initial`
(default `false`) and a `policies` map. Each policy independently chooses the
value from the highest-priority active activity that defines it. Equal priority
is resolved in favor of the activity declared later.

Keep an idle activity with explicit stop/normal values for outputs that must
be reset. If the last activity requesting `ringtone: play` disappears and no
activity requests `ringtone: stop`, no stop-value automation can run.

### Mutually exclusive activities

Use a top-level `groups` map. Activating one member deactivates the other members:

```yaml
runtime_controller:
  groups:
    call_phase: [ringing, talking]
```

Declare both activities under `activities`. A member can belong to only one
group, and a group can have at most one initially active member. Derived
activities cannot be group members. Music and a call usually belong outside
such a group because both can be active together.

### Calculated activities

A derived activity is calculated from other facts, for example both mute
switches being on:

```yaml
runtime_controller:
  activities:
    mic_muted: {}
    speaker_muted: {}
    both_muted:
      priority: 660
      policies:
        status: muted
  derived_activities:
    - name: both_muted
      when:
        all_active: [mic_muted, speaker_muted]
```

`when` accepts `any_active`, `all_active` and `none_active`. These conditions
are combined: at least one `any_active` item, every `all_active` item, and no
`none_active` item must be active. Empty condition lists add no restriction.
Dependencies may be declared in any order. Cycles are rejected during validation.

## Events and named actions

An event can activate and deactivate activities together, then request an action:

```yaml
runtime_controller:
  events:
    answer:
      deactivate: ringing
      activate: talking
      action: accept_call
  actions:
    accept_call:
      - logger.log: "Run the configured answer action here"
```

This is a generic example: replace the log with the action for your component.
The built-in VoIP observer already receives real call states from `voip_stack`.

### Conditional events

Cases are checked from top to bottom. Only the first matching case is applied;
the event's outer effects are the fallback, not extra effects added to a case.

```yaml
runtime_controller:
  events:
    button_pressed:
      cases:
        - all: [ringing]
          deactivate: ringing
          activate: talking
        - all: [talking]
          deactivate: talking
      activate: ringing
```

`any`, `all` and `none` accept one activity name or a list. Together they mean
"at least one of these, all of these, and none of these". Every referenced
activity and named action must exist.

An event may also have `then:`. This runs after its state changes and output
callbacks, including when no policy changed. A top-level named action is queued
for the main loop. Do not use the same name for an event with `then:` and a named
action.

Events raised while another event is being processed are queued. This prevents
a callback from changing half of the current state while another callback is
still reading it. Queue draining processes a bounded batch; new work generated
by that batch waits for a later loop turn.

## Policy outputs

Policy values are strings such as `idle` or `ringing`. Map them to integers for
globals or to actions for hardware:

```yaml
globals:
  - id: display_mode
    type: int
    restore_value: false
    initial_value: "0"

runtime_controller:
  policies:
    status:
      output: display_mode
      values:
        idle: 0
        ringing:
          value: 1
          then:
            - logger.log: "Show incoming call"
        talking: 2
      on_change:
        - logger.log:
            format: "Display mode: %d"
            args: [value]
```

`output` receives the mapped integer. `on_change` receives that integer as
`value`. A value's `then` automation runs when the policy changes to that string.
Policy callbacks run only when the resolved string changes. All bound globals
and the sequence number are updated before these callbacks run. A missing
integer mapping resolves to `0`; provide explicit mappings when the distinction
matters.

### LED output

```yaml
runtime_controller:
  outputs:
    led:
      id: status_led
      preset: rgb_single
      states:
        voip_in_call:
          color: [0%, 100%, 0%]
          brightness: 30%
          effect: None
```

The renderer consumes the `led_status` policy. Presets are `ws2812_ring`,
`rgb_single` and `spotpear_rgb`. State overrides accept a supported color name
or three RGB percentages, a brightness percentage, and an effect name available
on the target light. Hexadecimal color strings are not accepted. The renderer
does not define light effects for you.

### Shared display script and diagnostic globals

```yaml
globals:
  - id: runtime_mask
    type: uint32_t
    restore_value: false
    initial_value: "0"
  - id: runtime_sequence
    type: uint32_t
    restore_value: false
    initial_value: "0"

script:
  - id: render_runtime
    then:
      - logger.log: "Read the resolved globals and update the display here"

runtime_controller:
  output_script: render_runtime
  state_outputs:
    activity_mask: runtime_mask
    sequence: runtime_sequence
```

The bitmask shows which activity slots are active; the sequence counts committed
changes. Slot numbers follow configuration order and are not permanent IDs.
`output_script` has no parameters and runs after a committed change. LED and
output-script code are included only when their bindings are configured.

## Component observation

For a device using the full profile and its supporting packages:

```yaml
runtime_controller:
  id: runtime
  profile: full_voice_voip
  observe:
    voip_stack: phone
    media_player: speaker_media_player
    wifi: true
    microphone_mute: mute
    speaker_mute: speaker_mute
```

The `observe.voip_stack` value can be left empty to select the single configured
VoIP stack automatically. An explicit ID remains valid. To disable this observer,
omit its key entirely; an empty value enables automatic binding.

| Binding | Notifications delivered |
|---|---|
| `wifi` | `wifi_connected`, `wifi_disconnected` |
| `media_player` | `media_playing`, `media_paused`, `announcement_started`, `media_idle` |
| `microphone_mute` | `mic_muted`, `mic_unmuted` |
| `speaker_mute` | `speaker_muted`, `speaker_unmuted` |
| `voip_stack` | Synchronizes the profile's `voip:<state>` activities |

Media states `NONE`, `IDLE`, `OFF` and `ON` map to `media_idle`. Switch on means
muted. These listeners read the initial state and preserve other component
callbacks. They do not execute hardware mute operations.

The full profile provides the corresponding event rules. If you use Wi-Fi,
media or mute observation in a custom controller, define those event names
under `events:` yourself. Unknown events produce warnings.

Voice Assistant and Micro Wake Word use their official ESPHome callbacks via
shared Intercom packages. Neither `observe.voice_assistant` nor
`observe.micro_wake_word` is supported. HA API presence also uses the shared
Intercom callbacks; Wi-Fi connection alone does not mean HA is connected.

### Custom VoIP state mapping

Use `voip:` instead of `observe.voip_stack` for a controller without the built-in
profile:

```yaml
runtime_controller:
  id: runtime
  voip:
    id: phone
    activity_prefix: "voip:"
    states:
      ringing:
        priority: 700
        policies:
          status: ringing
      in_call:
        priority: 600
        policies:
          status: talking
```

This creates `voip:ringing` and `voip:in_call` activities and follows the phone's
state callbacks. Supply your idle policy and output mappings separately.
Do not configure this block and `observe.voip_stack` together.

## Built-in voice and intercom rules

`profile: full_voice_voip` supplies rules for calls, voice, media, connectivity,
mute and timers. `features` selects the `voice_assistant`, `media_player` and
`timers` portions. Omit `features` to select all three; use `[]` for the base
rules alone. This setting requires the built-in profile.

The modular base package explicitly starts with `features: []`. Each optional
feature package contributes its selection and the actions required by its rules.
Your `activities`, `events` and `policies` declarations override profile entries
with the same names. Review the complete resulting rule when overriding an event.

The main policy channels are `led_status`, `display_status`, `va_state`,
`va_response`, `audio_policy`, `ringtone` and `timer_alarm`. Voice response
completion waits for both the assistant run and playback to finish. This is why
an `on_end` notification alone must not be used to force the device back to idle.

The main default priorities are:

| Activity | Priority |
|---|---:|
| Boot | 1000 |
| Wi-Fi / HA / Voice Assistant client unavailable | 990 / 980 / 970 |
| Incoming call ringing | 975 |
| Outgoing call, including remote ringing | 974 |
| Timer alarm | 900 |
| Assistant responding / thinking / listening | 840 / 830 / 820 |
| Established call | 700 |
| Announcement | 200 |
| Music | 100 |
| Idle | 0 |

These priorities apply only to the policies each activity defines. For example,
a voice phase can temporarily take over the display during an established call;
it does not terminate the call. Custom priorities should be chosen per output,
with explicit idle/stop values for ongoing effects.

Use the maintained callback packages to deliver voice, timer and HA connection
events. The complete built-in event definitions are in
[`__init__.py`](__init__.py), under `FULL_VOICE_VOIP_EVENTS`; the package
[selection guide](../../../MIGRATION.md#choose-packages) explains how to connect
them to components.

## Actions and conditions

Each action below identifies the controller with `id: runtime`.

| Action | Other fields | Behavior |
|---|---|---|
| `runtime_controller.event` | `event`, optional `reason` and `dump` | Apply a named event. `dump: true` requests debug output after processing. |
| `runtime_controller.set_activity` | `activity`, `active` | Set one activity directly. |
| `runtime_controller.set_activities` | `set` map | Change several activities in one update. |
| `runtime_controller.request_action` | `action` | Queue a configured named action. |
| `runtime_controller.dump` | Optional `reason`, default `manual` | Request a debug snapshot. Requires debug-enabled firmware for detailed output. |

Use events for normal component input so the rules decide what to change.
Direct setters are useful for a custom aggregate input, for example:

```yaml
- runtime_controller.set_activities:
    id: runtime
    set:
      ringing: false
      talking: true
```

The `set` map uses fixed names and booleans. The singular `set_activity` supports
templated `activity` and `active` values. `event`, `reason` and requested `action`
names can also be templated.

The condition checks one current activity:

```yaml
- if:
    condition:
      runtime_controller.is_active:
        id: runtime
        activity: talking
    then:
      - logger.log: "A call is active"
```

In lambdas, `id(runtime).is_activity_active("talking")` checks a fact;
`id(runtime).get_policy("status", "idle")` returns the resolved string or the
fallback. `get_sequence()` and `get_activity_mask()` expose diagnostic counters.

## Debugging and limits

Set `debug: true` and rebuild to enable detailed event and snapshot logging.
For maintained presets, use `runtime_controller_debug: "true"` in substitutions.
The dump action is an ESPHome automation action; it is not automatically a Home
Assistant service. Expose it through a template button or an API action if needed.
See the [button example](../../../README.md#diagnosing-a-stuck-state).

If the runtime says `responding`, examine which voice/announcement activities
are still active. If the runtime says idle but a display still shows responding,
examine the display binding. This separates missing completion events from
rendering problems.

| Fixed capacity | Limit |
|---|---:|
| Activities | 32 |
| Resolved policies / policies per activity | 8 / 8 |
| Derived activities | 16 |
| Conditions in each condition list | 8 |
| Activity updates per event rule | 16 |
| Direct event updates / event rules | 64 / 64 |
| Named actions / event `then` triggers | 16 / 16 |
| Policy integer mappings / value actions | 64 / 32 |
| LED state mappings | 32 |
| Queued events or update batches / named actions | 16 / 16 |

Event names must fit in 47 UTF-8 bytes. Generated VoIP activity names, including
the prefix, must fit in 63 bytes. Invalid references, cyclic derived rules and
schema capacity violations are rejected before compilation.

The core allocates fixed tables and queues, using internal memory by default.
`storage_in_psram: true` moves these tables and queues to PSRAM; it does not move
audio buffers or task stacks. Templated action parameters may allocate temporary
strings. A failed state allocation stops configuration rather than leaving a
partially configured controller.

Optional VoIP, LED and output-script fields are removed when their build flags
are absent. Wi-Fi, media and each mute listener have independent gates. No
observer object is generated when none is selected. See the
[feature cost table](../../../README.md#what-an-unused-feature-costs) for the
difference between feature-specific memory and the fixed common rule tables.

An overflow is logged. A VoIP observation lost because the queue is full is
followed by reconciliation with the latest call state after queued work drains;
this does not recover every intermediate transition. Review event loops and
callback ownership if overflows occur.

## Running the tests

From the repository root, with Python, ESPHome, pytest and a C++17-capable `g++`
installed:

```bash
python -m pytest -q
```

The CI versions are recorded in [ci.yml](../../../.github/workflows/ci.yml).
The suite executes the production C++ controller with host adapters, tests the
built-in voice rules and checks schema/listener behavior. It covers nested
events, complete output publication, queue bounds, allocation failure and voice
completion in different media states. Real audio, radio behavior and physical
LED/display output still require device tests.
