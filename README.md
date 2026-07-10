# ESPHome Runtime Controller

Deterministic state arbitration for composite ESPHome devices: one reducer that
turns overlapping events from Voice Assistant, media, VoIP, timers, mute and
connectivity into a single coherent set of outputs.

`runtime_controller` is a small fixed-capacity reducer component. Feature
callbacks stop writing to LEDs, displays and mixers directly; they report facts
such as "media is playing", "a call is ringing", or "the mic is muted". The
controller keeps the active facts, resolves them by priority into one snapshot,
and drives outputs from that snapshot alone.

```text
feature callbacks
  media_playing
  va_responding
  voip:ringing
  mic_muted
        |
        v
runtime_controller reducer
        |
        v
resolved snapshot
  led_status: va_responding
  display_status: va_responding
  audio_policy: duck
  ringtone: stop
```

## 1. What This Is

Composite ESPHome devices are event-driven, and that is fine until events
overlap. Media playback sets the LED; TTS sets the same LED; a call sets it
again; a timer wants a ringtone and display overlay; mute switches and
HA-disconnect banners also claim priority.

Wired as plain callbacks, the last writer wins. The symptoms are familiar:
brief wrong flashes, LEDs stuck on stale states, ducking released mid-TTS,
display pages that do not match the device, and hand-rolled previous-state
variables everywhere.

The structural fix is to separate facts from rendering:

- an **activity** is a named boolean fact with a priority and policies;
- an **event** is a named input that activates or deactivates activities;
- a **policy** is an output channel whose value is chosen by priority;
- an **action** is a named one-shot automation requested by an event.

Because multiple facts stay active at once, "return to the previous state" is
not a feature to implement. It is what naturally happens when a higher-priority
fact deactivates. Media stays active while TTS runs on top; when TTS ends,
media is still the highest bidder and the device falls back to it.

## 2. What It Gives You

- **Per-policy priority resolution.** Each output channel is resolved
  independently. Activities that do not define a channel are transparent for
  that channel.
- **Declarative event rules with guarded cases.** Events can have default
  activate/deactivate lists plus ordered cases guarded by `any`, `all` and
  `none` conditions over active activities.
- **Derived activities.** Facts computed from other facts. The acyclic
  dependency graph resolves to a fixed point after every update, independent of
  YAML declaration order; validation rejects cycles.
- **Groups.** Activities in the same group are mutually exclusive.
- **A batteries-included profile.** `profile: full_voice_voip` ships the
  complete activity table and event vocabulary for Voice Assistant, Micro Wake
  Word, media, announcement, timer, mute, connectivity and VoIP devices.
- **A native VoIP bridge.** Given a `voip_stack` id, the controller subscribes
  to call-state changes and maintains `voip:<state>` activities automatically.
- **Multiple output styles.** Built-in LED renderer, policy value automations,
  integer globals, per-policy `on_change`, optional snapshot script, activity
  mask and sequence globals.
- **Deterministic reducer state and re-entrancy safety.** Runtime tables and
  queues have fixed capacity; the resolution hot path uses no dynamically
  growing containers. ESPHome templatable string actions can still create
  temporary `std::string` values. Work raised during dispatch is queued and
  drained in bounded batches.
- **Introspection.** Debug logs, dump action, activity mask and sequence counter
  make state bugs inspectable from one table.

## 3. When To Use It

Use `runtime_controller` when one device combines several of:

- Voice Assistant and Micro Wake Word;
- media, announcements or TTS;
- VoIP or intercom calls;
- LVGL pages;
- status LEDs or LED rings;
- timer alarms and ringtones;
- mute switches;
- Wi-Fi, API or HA connectivity status.

Do not use it where one callback controls one output. A button toggling a relay
does not need a reducer.

## 4. Core Concepts

**Activity.** A named boolean with priority, optional `initial: true`, optional
group, and policy values. Active activities are the current facts.

**Event.** A named input delivered by `runtime_controller.event`. It can define
default `activate`, `deactivate`, `action`, ordered `cases`, and an inline
`then` automation. The inline `then` runs after the matching case/default has
updated activities and outputs, so it observes the resolved state. Event
`then` names must not collide with top-level named `actions:`.

**Case.** A guarded branch with `any`, `all`, `none`, and its own effects. Cases
are evaluated in order; the first match wins. Defaults are the fallback.

**Policy.** An output channel. On every change the reducer walks active
activities and picks the value from the highest-priority activity defining that
channel. On equal priority, later declaration wins.

**Action.** A named one-shot automation in the top-level `actions:` map. Events
reference actions by name. Actions are the escape hatch into imperative
ESPHome automations; state stays in activities.

**Derived activity.** A fact computed from other facts via `when:
{any_active, all_active, none_active}`. Derived dependencies may be declared in
any order: the reducer iterates the validated acyclic graph to a fixed point.

**Group.** Mutual exclusion. Activating one activity deactivates active peers in
the same group.

## 5. Installation

```yaml
external_components:
  - source: github://n-IA-hane/esphome-runtime-controller@main
    components: [runtime_controller]
```

Ready package with the full voice + VoIP profile:

```yaml
packages:
  runtime_controller: github://n-IA-hane/esphome-runtime-controller/packages/runtime_controller/full_controller.yaml@main
```

No-LED package for devices where custom YAML or LVGL owns LED rendering:

```yaml
packages:
  runtime_controller: github://n-IA-hane/esphome-runtime-controller/packages/runtime_controller/full_controller_no_led.yaml@main
```

The component has no hardware requirements. The optional VoIP bridge requires
the `voip_stack` component from
[`n-IA-hane/esphome-intercom`](https://github.com/n-IA-hane/esphome-intercom).

## 6. Minimal Custom Controller

This is a small reducer with two facts and one output channel:

```yaml
globals:
  - id: g_led_status
    type: int
    restore_value: no
    initial_value: "0"

runtime_controller:
  id: runtime

  policies:
    led_status:
      output: g_led_status
      values:
        idle: 0
        media: 1
        responding: 2

  activities:
    idle:
      priority: 0
      initial: true
      policies:
        led_status: idle
    media:
      priority: 100
      policies:
        led_status: media
    va_responding:
      priority: 840
      policies:
        led_status: responding

  events:
    media_playing:
      activate: media
    media_idle:
      deactivate: media
    tts_started:
      activate: va_responding
    tts_finished:
      deactivate: va_responding
```

Play music: LED goes media. TTS starts on top: LED goes responding while media
stays active underneath. TTS ends: LED returns to media by resolution, not by
anyone remembering it should.

## 7. The `full_voice_voip` Profile

```yaml
runtime_controller:
  id: runtime
  profile: full_voice_voip
  observe:
    voip_stack: phone
```

The profile installs a complete arbitration model. You keep emitting the
standard event vocabulary from callbacks; anything you declare in `activities:`,
`events:` or `policies:` merges over the profile.

### 7.1 Activity Table

| Activity | Priority | Notes |
|---|---:|---|
| `boot` | 1000 | Boot overlay beats everything. |
| `no_wifi` / `no_ha` / `no_va` | 990 / 980 / 970 | Connectivity problems in causal order. |
| `voip:ringing` / `voip:calling` | 975 / 974 | Incoming ring outranks outgoing dialing. |
| `timer_ringing` | 900 | Alarm overlay and timer alarm playback. |
| `va_responding` / `va_thinking` / `va_barging` / `va_listening` | 840 / 830 / 825 / 820 | Voice Assistant phase chain. |
| `va_start_requested` / `va_starting` | 810 | Wake acknowledged and pipeline starting. |
| `voip:in_call` | 700 | Persistent call base state; transient VA can show through and then fall back to call. |
| `both_muted` / `mic_muted` / `speaker_muted` | 660 / 650 / 640 | `both_muted` is derived. |
| `announcement` | 200 | TTS/announcement overlay over media. |
| `media` | 100 | Base media state. |
| `idle` | 0 | Initial baseline. |

Policy channels used by the profile: `led_status`, `display_status`,
`va_state`, `va_response`, `audio_policy`, `ringtone`, `timer_alarm`.

### 7.2 Event Vocabulary

Connectivity and lifecycle:

```text
boot_start, boot_ready,
wifi_connected, wifi_disconnected,
ha_connected, ha_disconnected,
va_client_connected, va_client_disconnected
```

Mute:

```text
mic_muted, mic_unmuted, speaker_muted, speaker_unmuted
```

Timers, media and voice:

```text
timer_started, timer_finished, timer_stopped,
media_playing, media_paused, media_idle, announcement_started,
wake_word and the Voice Assistant phase events
```

The important part is not the list but the guarded cases attached to media,
announcement and wake-word events. They encode the interleavings that break
naive wiring: response drain while media resumes, barge-in during response,
wake word during announcement, and media underneath a drained response.

### 7.3 VoIP Bridge

Profile mode:

```yaml
runtime_controller:
  id: runtime
  profile: full_voice_voip
  observe:
    voip_stack: phone
```

Standalone bridge:

```yaml
runtime_controller:
  id: runtime
  voip:
    id: phone
    activity_prefix: "voip:"
    states:
      ringing:
        priority: 975
        policies:
          led_status: voip_ringing
          ringtone: play
      in_call:
        priority: 700
        policies:
          led_status: voip_in_call
          audio_policy: duck
```

The controller registers a call-state callback on `voip_stack` and synchronizes
one `voip:<state>` activity with it.

## 8. Outputs

### 8.1 LED Preset Renderer

```yaml
runtime_controller:
  id: runtime
  outputs:
    led:
      id: status_led
      preset: ws2812_ring
      states:
        media:
          color: "#0060ff"
          effect: none
          brightness: 55%
        voip_in_call:
          color: "#00ff40"
          effect: none
          brightness: 70%
```

The renderer maps `led_status` values to light calls. The preset supplies
defaults; `states:` overrides color, effect and brightness per state.

### 8.2 Policy Automations, Globals and Triggers

```yaml
globals:
  - id: g_display_status
    type: int
    restore_value: no
    initial_value: "0"

runtime_controller:
  id: runtime
  policies:
    display_status:
      output: g_display_status
      values:
        idle: 0
        media: 1
        voip: 2
      on_change:
        then:
          - script.execute: render_display
```

Globals are the cheap consumption path for LVGL pages and lambdas that only
need the current decision.

### 8.3 Snapshot Outputs

```yaml
runtime_controller:
  id: runtime
  output_script: render_runtime_snapshot
  state_outputs:
    activity_mask: g_runtime_activity_mask
    sequence: g_runtime_sequence
```

`output_script` is the single choke point for devices that prefer rendering in
one script. The mask and sequence globals serve external observers and debug
dashboards.

## 9. Actions and Conditions

| Item | Parameters | Meaning |
|---|---|---|
| `runtime_controller.event` | `event`, `reason`, `dump` | Deliver an event. With `dump: true`, log full state after processing. |
| `runtime_controller.set_activity` | `activity`, `active` | Set one fact directly. |
| `runtime_controller.set_activities` | `set:` map | Set several facts atomically. |
| `runtime_controller.request_action` | `action` | Run a top-level named action. |
| `runtime_controller.dump` | `reason` | Log active activities and resolved policies. |
| `runtime_controller.is_active` | `activity` | Condition true when a fact is active. |

Prefer events over direct `set_activity` in feature callbacks: events go
through the rule layer, where the interleaving knowledge lives.

## 10. Configuration Reference

| Option | Default | Meaning |
|---|---|---|
| `debug` | `false` | Log every event with sequence and activity mask. |
| `profile` | none | `full_voice_voip` installs the built-in model. |
| `observe.voip_stack` | none | `voip_stack` id for automatic bridge in profile mode. |
| `voip.id` / `voip.activity_prefix` / `voip.states` | none / `voip:` / `{}` | Standalone VoIP bridge. |
| `activities` | `{}` | Map of name to priority, initial, group and policies. |
| `groups` | `{}` | Mutually exclusive activity groups. |
| `derived_activities` | `[]` | Computed facts. |
| `events` | `{}` | Event rules, cases and optional post-reducer `then`. |
| `actions` | `{}` | Named automations. |
| `policies` | `{}` | Output channels, values and triggers. |
| `auto_events` | `true` | Create an implicit same-name activation event for each explicitly declared activity. Set false when every accepted event must be declared under `events:`. |
| `outputs.led` | none | Built-in LED renderer config. |
| `output_script` | none | Script executed after each committed change. |
| `state_outputs.activity_mask` / `state_outputs.sequence` | none | Globals receiving active bitmask and change counter. |

## 11. Design Rules and Limits

The component is intentionally a reducer and nothing else:

- callbacks report facts, they do not render;
- all rendering flows from the resolved snapshot;
- state lives in activities;
- named actions are one-shot side effects;
- priorities are data, so behavior changes are YAML edits.

The reducer core uses fixed storage. Current schema/runtime limits are:

- 32 activities and 16 derived-activity definitions;
- 8 resolved policy channels and 8 policy entries per activity;
- 64 event rules, 64 direct event-update slots (implicit auto-events currently
  use at most one per declared activity), 16 named actions and 16 event-level
  `then` triggers;
- per rule: 8 entries in each `any`/`all`/`none` list and 16 activity updates;
- 64 policy value outputs, 32 policy value actions and 32 LED states;
- 16 queued reentrant events/atomic update batches and 16 queued named actions.

Exceeding a schema limit is an explicit configuration error. Reentrant work is
queued after the current commit. A drain processes only the batch present when
it starts; events/actions created by that batch remain for the next main-loop
turn, bounding self-referential automations without sleeps or busy loops.
Unknown events and activities produce warnings, never silent drops.

## 12. Debugging

- `debug: true` logs the event stream with sequence numbers and masks.
- `dump: true` on `runtime_controller.event` prints the active set and
  per-channel winners after that event.
- `runtime_controller.dump` can be called from any automation or HA service.
- The `sequence` global helps detect missed transitions from outside.
- `reason` strings label who sent what when reading logs.

The usual debugging loop is: reproduce, dump, read which activity won each
channel. Because rendering is centralized, the answer is in one table instead
of scattered across callbacks.

## 13. Provenance And License

Extracted from the maintained
[`n-IA-hane/esphome-intercom`](https://github.com/n-IA-hane/esphome-intercom)
codebase, where this reducer arbitrates Voice Assistant, Micro Wake Word,
media, announcements, timers, mute, connectivity and SIP call state on real
voice/intercom devices. `SOURCE.md` records the extraction origin and scope;
subsequent changes are tracked by this repository's own commit history.

The `packages/runtime_controller/` directory ships ready-to-include YAML
packages: `full_controller.yaml` and `full_controller_no_led.yaml`.

MIT license.
