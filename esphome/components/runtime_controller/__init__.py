from esphome import automation
import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import globals as globals_component, light, script
from esphome.const import CONF_ID, CONF_NAME, CONF_THEN

CODEOWNERS = ["@n-IA-hane"]
DEPENDENCIES = []

runtime_controller_ns = cg.esphome_ns.namespace("runtime_controller")
RuntimeController = runtime_controller_ns.class_("RuntimeController", cg.Component)
VoipStack = cg.esphome_ns.namespace("voip_stack").class_("VoipStack", cg.Component)
EventAction = runtime_controller_ns.class_(
    "EventAction", automation.Action, cg.Parented.template(RuntimeController)
)
SetActivityAction = runtime_controller_ns.class_(
    "SetActivityAction", automation.Action, cg.Parented.template(RuntimeController)
)
SetActivitiesAction = runtime_controller_ns.class_(
    "SetActivitiesAction", automation.Action, cg.Parented.template(RuntimeController)
)
RequestActionAction = runtime_controller_ns.class_(
    "RequestActionAction", automation.Action, cg.Parented.template(RuntimeController)
)
DumpAction = runtime_controller_ns.class_(
    "DumpAction", automation.Action, cg.Parented.template(RuntimeController)
)
IsActiveCondition = runtime_controller_ns.class_(
    "IsActiveCondition", automation.Condition, cg.Parented.template(RuntimeController)
)

CONF_DEBUG = "debug"
CONF_OUTPUT_SCRIPT = "output_script"
CONF_STATE_OUTPUTS = "state_outputs"
CONF_ACTIVITY_MASK = "activity_mask"
CONF_SEQUENCE = "sequence"
CONF_VOIP_ID = "voip_id"
CONF_VOIP = "voip"
CONF_ACTIVITY_PREFIX = "activity_prefix"
CONF_ACTIVITIES = "activities"
CONF_GROUPS = "groups"
CONF_AUTO_EVENTS = "auto_events"
CONF_DERIVED_ACTIVITIES = "derived_activities"
CONF_EVENTS = "events"
CONF_SET = "set"
CONF_POLICIES = "policies"
CONF_GROUP = "group"
CONF_PRIORITY = "priority"
CONF_INITIAL = "initial"
CONF_ACTIONS = "actions"
CONF_VALUES = "values"
CONF_OUTPUT = "output"
CONF_ON_CHANGE = "on_change"
CONF_VALUE = "value"
CONF_EVENT = "event"
CONF_ACTIVITY = "activity"
CONF_ACTIVE = "active"
CONF_ACTION = "action"
CONF_REASON = "reason"
CONF_DUMP = "dump"
CONF_RULES = "rules"
CONF_WHEN = "when"
CONF_ANY_ACTIVE = "any_active"
CONF_ALL_ACTIVE = "all_active"
CONF_NONE_ACTIVE = "none_active"
CONF_ACTIVATE = "activate"
CONF_DEACTIVATE = "deactivate"
CONF_CASES = "cases"
CONF_ANY = "any"
CONF_ALL = "all"
CONF_NONE = "none"
CONF_STATES = "states"
CONF_PROFILE = "profile"
CONF_OBSERVE = "observe"
CONF_OUTPUTS = "outputs"
CONF_LED = "led"
CONF_VOICE_ASSISTANT = "voice_assistant"
CONF_MICRO_WAKE_WORD = "micro_wake_word"
CONF_MEDIA_PLAYER = "media_player"
CONF_VOIP_STACK = "voip_stack"
CONF_PRESET = "preset"
CONF_COLOR = "color"
CONF_EFFECT = "effect"
CONF_BRIGHTNESS = "brightness"

PROFILE_FULL_VOICE_VOIP = "full_voice_voip"

LED_POLICY = "led_status"

COLOR_NAMES = {
    "off": (0.0, 0.0, 0.0),
    "black": (0.0, 0.0, 0.0),
    "red": (1.0, 0.0, 0.0),
    "orange": (1.0, 0.5, 0.0),
    "yellow": (1.0, 1.0, 0.0),
    "green": (0.0, 1.0, 0.0),
    "blue": (0.0, 0.0, 1.0),
    "violet": (0.55, 0.15, 1.0),
}

LED_PRESETS = {
    "ws2812_ring": {
        "idle": {"color": "off", "effect": "None", "brightness": 0.0},
        "muted": {"color": "red", "effect": "Slow Pulse", "brightness": 0.4},
        "mic_muted": {"color": "red", "effect": "None", "brightness": 0.3},
        "speaker_muted": {"color": "orange", "effect": "None", "brightness": 0.3},
        "wake": {"color": "red", "effect": "Spin", "brightness": 0.7},
        "listening": {"color": "red", "effect": "Spin", "brightness": 0.7},
        "thinking": {"color": "yellow", "effect": "Spin", "brightness": 0.7},
        "responding": {"color": "blue", "effect": "None", "brightness": 1.0},
        "voip_ringing": {"color": "red", "effect": "Ringing", "brightness": 1.0},
        "voip_calling": {"color": "orange", "effect": "Calling", "brightness": 1.0},
        "voip_in_call": {"color": [0.3, 0.69, 0.31], "effect": "None", "brightness": 1.0},
        "error": {"color": "red", "effect": "None", "brightness": 0.7},
        "media": {"color": "green", "effect": "Spin", "brightness": 1.0},
        "boot": {"color": "red", "effect": "None", "brightness": 0.6},
        "no_wifi": {"color": "orange", "effect": "Blink", "brightness": 0.7},
        "no_ha": {"color": "blue", "effect": "Blink", "brightness": 0.6},
        "no_va": {"color": "violet", "effect": "Blink", "brightness": 0.6},
        "timer_ringing": {"color": "yellow", "effect": "Fast Pulse", "brightness": 1.0},
    },
    "rgb_single": {
        "idle": {"color": "off", "effect": "None", "brightness": 0.0},
        "muted": {"color": "red", "effect": "Slow Pulse", "brightness": 0.4},
        "mic_muted": {"color": "red", "effect": "None", "brightness": 0.3},
        "speaker_muted": {"color": "orange", "effect": "None", "brightness": 0.3},
        "wake": {"color": "red", "effect": "None", "brightness": 0.7},
        "listening": {"color": "red", "effect": "None", "brightness": 0.7},
        "thinking": {"color": "yellow", "effect": "Fast Pulse", "brightness": 1.0},
        "responding": {"color": [0.3, 0.3, 0.7], "effect": "None", "brightness": 0.6},
        "voip_ringing": {"color": "red", "effect": "Ringing", "brightness": 1.0},
        "voip_calling": {"color": "orange", "effect": "Calling", "brightness": 1.0},
        "voip_in_call": {"color": "green", "effect": "None", "brightness": 1.0},
        "error": {"color": "red", "effect": "None", "brightness": 0.7},
        "media": {"color": "green", "effect": "Slow Pulse", "brightness": 1.0},
        "boot": {"color": "red", "effect": "None", "brightness": 0.6},
        "no_wifi": {"color": "orange", "effect": "Blink", "brightness": 0.7},
        "no_ha": {"color": "blue", "effect": "Blink", "brightness": 0.6},
        "no_va": {"color": "violet", "effect": "Blink", "brightness": 0.6},
        "timer_ringing": {"color": "yellow", "effect": "Fast Pulse", "brightness": 1.0},
    },
}

LED_PRESETS["spotpear_rgb"] = {
    **LED_PRESETS["rgb_single"],
    "wake": {"color": "red", "effect": "Slow Pulse", "brightness": 0.7},
    "listening": {"color": "red", "effect": "Slow Pulse", "brightness": 0.7},
    "thinking": {"color": "yellow", "effect": "Fast Pulse", "brightness": 0.7},
    "responding": {"color": "blue", "effect": "None", "brightness": 1.0},
    "media": {"color": "green", "effect": "Slow Pulse", "brightness": 1.0},
}

FULL_VOICE_VOIP_GROUPS = {
    "va": ["va_start_requested", "va_starting", "va_listening", "va_thinking", "va_responding", "va_barging", "va_stopping"],
}

FULL_VOICE_VOIP_VOIP_STATES = {
    "ringing": {
        CONF_PRIORITY: 975,
        CONF_POLICIES: {
            "led_status": "voip_ringing",
            "display_status": "voip_ringing",
            "audio_policy": "duck",
            "ringtone": "play",
            "va_state": "idle",
        },
    },
    "calling": {
        CONF_PRIORITY: 974,
        CONF_POLICIES: {
            "led_status": "voip_calling",
            "display_status": "voip_calling",
            "audio_policy": "duck",
            "va_state": "idle",
        },
    },
    "in_call": {
        # Established calls are a persistent base state. They must dominate
        # media, but transient voice-assistant activity still needs to be
        # visible so wake/listening/thinking is not hidden by the call LED.
        CONF_PRIORITY: 700,
        CONF_POLICIES: {
            "led_status": "voip_in_call",
            "display_status": "voip_in_call",
            "audio_policy": "duck",
            "va_state": "idle",
        },
    },
}

FULL_VOICE_VOIP_ACTIVITIES = {
    "idle": {CONF_PRIORITY: 0, CONF_INITIAL: True, CONF_POLICIES: {
        "led_status": "idle", "display_status": "idle", "va_state": "idle", "va_response": "inactive",
        "audio_policy": "normal", "ringtone": "stop", "timer_alarm": "stop"}},
    "boot": {CONF_PRIORITY: 1000, CONF_POLICIES: {"led_status": "boot", "display_status": "boot", "va_state": "idle"}},
    "no_wifi": {CONF_PRIORITY: 990, CONF_POLICIES: {"led_status": "no_wifi", "display_status": "no_wifi", "va_state": "idle"}},
    "no_ha": {CONF_PRIORITY: 980, CONF_POLICIES: {"led_status": "no_ha", "display_status": "no_ha", "va_state": "idle"}},
    "no_va": {CONF_PRIORITY: 970, CONF_POLICIES: {"led_status": "no_va", "display_status": "no_va", "va_state": "idle"}},
    "both_muted": {CONF_PRIORITY: 660, CONF_POLICIES: {"led_status": "muted", "display_status": "muted", "va_state": "idle"}},
    "mic_muted": {CONF_PRIORITY: 650, CONF_POLICIES: {"led_status": "mic_muted", "display_status": "muted", "va_state": "idle"}},
    "speaker_muted": {CONF_PRIORITY: 640, CONF_POLICIES: {"led_status": "speaker_muted", "display_status": "muted", "va_state": "idle"}},
    "media": {CONF_PRIORITY: 100, CONF_POLICIES: {"led_status": "media", "display_status": "media", "audio_policy": "normal", "va_state": "idle"}},
    "announcement": {CONF_PRIORITY: 200, CONF_POLICIES: {"led_status": "media", "display_status": "media", "audio_policy": "duck", "va_state": "idle"}},
    "announcement_play_seen": {CONF_PRIORITY: 0, CONF_POLICIES: {}},
    "timer": {CONF_PRIORITY: 0, CONF_POLICIES: {}},
    "timer_ringing": {CONF_PRIORITY: 900, CONF_POLICIES: {"led_status": "timer_ringing", "display_status": "timer_ringing", "audio_policy": "duck", "timer_alarm": "play", "va_state": "idle"}},
    "va_start_requested": {CONF_PRIORITY: 810, CONF_POLICIES: {"led_status": "wake", "display_status": "wake", "audio_policy": "duck", "va_state": "idle", "va_response": "inactive"}},
    "va_starting": {CONF_PRIORITY: 810, CONF_POLICIES: {"led_status": "wake", "display_status": "wake", "audio_policy": "duck", "va_state": "idle", "va_response": "inactive"}},
    "va_barging": {CONF_PRIORITY: 825, CONF_POLICIES: {"led_status": "listening", "display_status": "listening", "audio_policy": "duck", "va_state": "listening", "va_response": "inactive"}},
    "va_stopping": {CONF_PRIORITY: 0, CONF_POLICIES: {}},
    "va_run_ended": {CONF_PRIORITY: 0, CONF_POLICIES: {}},
    "va_response_drained": {CONF_PRIORITY: 0, CONF_POLICIES: {}},
    "va_listening": {CONF_PRIORITY: 820, CONF_POLICIES: {"led_status": "listening", "display_status": "listening", "audio_policy": "duck", "va_state": "listening", "va_response": "inactive"}},
    "va_thinking": {CONF_PRIORITY: 830, CONF_POLICIES: {"led_status": "thinking", "display_status": "thinking", "audio_policy": "duck", "va_state": "thinking", "va_response": "inactive"}},
    "va_responding": {CONF_PRIORITY: 840, CONF_POLICIES: {"led_status": "responding", "display_status": "responding", "audio_policy": "duck", "va_state": "responding", "va_response": "active"}},
}

FULL_VOICE_VOIP_DERIVED = [
    {CONF_NAME: "both_muted", CONF_WHEN: {CONF_ALL_ACTIVE: ["mic_muted", "speaker_muted"]}},
]

FULL_VOICE_VOIP_EVENTS = {
    "boot_start": {CONF_ACTIVATE: ["boot", "no_wifi", "no_ha"]},
    "boot_ready": {CONF_DEACTIVATE: "boot"},
    "wifi_connected": {CONF_DEACTIVATE: "no_wifi"},
    "wifi_disconnected": {CONF_ACTIVATE: "no_wifi"},
    "ha_connected": {CONF_DEACTIVATE: "no_ha"},
    "ha_disconnected": {CONF_ACTIVATE: "no_ha"},
    "va_client_connected": {CONF_DEACTIVATE: "no_va"},
    "va_client_disconnected": {CONF_ACTIVATE: "no_va"},
    "media_paused": {CONF_DEACTIVATE: ["media", "announcement", "announcement_play_seen"]},
    "mic_muted": {CONF_ACTIVATE: "mic_muted"},
    "mic_unmuted": {CONF_DEACTIVATE: "mic_muted"},
    "speaker_muted": {CONF_ACTIVATE: "speaker_muted"},
    "speaker_unmuted": {CONF_DEACTIVATE: "speaker_muted"},
    "timer_started": {CONF_ACTIVATE: "timer"},
    "timer_stopped": {CONF_DEACTIVATE: ["timer", "timer_ringing"]},
    "timer_finished": {CONF_ACTIVATE: "timer_ringing"},
    "media_idle": {CONF_DEACTIVATE: "media", CONF_CASES: [
        {CONF_ALL: ["va_stopping"], CONF_DEACTIVATE: ["media", "announcement", "announcement_play_seen", "va_stopping"]},
        {CONF_ALL: ["va_barging"], CONF_DEACTIVATE: ["media", "announcement", "announcement_play_seen"]},
        {CONF_ALL: ["va_responding", "announcement", "va_run_ended"], CONF_DEACTIVATE: ["media", "va_responding", "announcement", "announcement_play_seen", "va_run_ended", "va_response_drained"]},
        {CONF_ALL: ["va_responding", "announcement"], CONF_ACTIVATE: "va_response_drained", CONF_DEACTIVATE: ["media", "announcement", "announcement_play_seen"]},
        {CONF_ALL: ["announcement"], CONF_DEACTIVATE: ["media", "announcement", "announcement_play_seen"]},
    ]},
    "media_playing": {CONF_ACTIVATE: "media", CONF_CASES: [
        {CONF_ALL: ["va_stopping"], CONF_ACTIVATE: "media", CONF_DEACTIVATE: ["announcement", "announcement_play_seen", "va_stopping"]},
        {CONF_ALL: ["va_barging"], CONF_ACTIVATE: "media", CONF_DEACTIVATE: ["announcement", "announcement_play_seen"]},
        {CONF_ALL: ["va_responding", "announcement", "va_run_ended"], CONF_ACTIVATE: "media"},
        {CONF_ALL: ["va_responding", "announcement"], CONF_ACTIVATE: "media"},
        {CONF_ALL: ["announcement"], CONF_ACTIVATE: "media", CONF_DEACTIVATE: ["announcement", "announcement_play_seen"]},
    ]},
    "announcement_started": {CONF_ACTIVATE: "announcement", CONF_DEACTIVATE: "announcement_play_seen", CONF_CASES: [
        {CONF_ANY: ["va_start_requested", "va_starting", "va_barging", "va_listening", "va_thinking", "va_stopping"],
         CONF_DEACTIVATE: ["announcement", "announcement_play_seen", "va_stopping"], CONF_ACTION: "stop_announcement"},
    ]},
    "wake_word": {CONF_ACTIVATE: "va_start_requested", CONF_ACTION: "voice_start", CONF_CASES: [
        {CONF_ANY: "va_start_requested"},
        {CONF_ALL: ["va_responding", "announcement"], CONF_ACTIVATE: ["va_start_requested", "va_barging"], CONF_DEACTIVATE: ["announcement", "announcement_play_seen", "va_responding"], CONF_ACTION: "voice_cancel_response"},
        {CONF_ALL: ["va_responding", "va_run_ended"], CONF_ACTIVATE: "va_start_requested", CONF_DEACTIVATE: ["va_responding", "va_run_ended", "va_response_drained"], CONF_ACTION: "voice_cancel_pipeline"},
        {CONF_ANY: ["va_starting", "va_listening", "va_thinking", "va_responding"], CONF_ACTIVATE: ["va_start_requested", "va_barging"], CONF_DEACTIVATE: ["va_starting", "va_listening", "va_thinking", "va_responding"], CONF_ACTION: "voice_cancel_pipeline"},
        {CONF_ANY: ["va_barging", "va_stopping"]},
    ]},
    "manual_voice_toggle": {CONF_ACTIVATE: "va_start_requested", CONF_ACTION: "voice_start", CONF_CASES: [
        {CONF_ALL: ["va_responding", "announcement"], CONF_ACTIVATE: "va_stopping", CONF_DEACTIVATE: ["va_start_requested", "va_starting", "va_barging", "va_listening", "va_thinking", "va_responding", "announcement", "announcement_play_seen"], CONF_ACTION: "voice_stop_all"},
        {CONF_ANY: "va_responding", CONF_ACTIVATE: "va_stopping", CONF_DEACTIVATE: ["va_start_requested", "va_starting", "va_barging", "va_listening", "va_thinking", "va_responding"], CONF_ACTION: "voice_stop_pipeline"},
        {CONF_ANY: ["va_start_requested", "va_starting", "va_barging", "va_listening", "va_thinking"], CONF_DEACTIVATE: ["va_start_requested", "va_starting", "va_barging", "va_listening", "va_thinking", "va_responding", "announcement", "announcement_play_seen"], CONF_ACTION: "voice_stop_pipeline"},
    ]},
    "va_start": {CONF_ACTIVATE: "va_starting", CONF_ACTION: "cancel_response_cleanup", CONF_CASES: [
        {CONF_ANY: "va_barging", CONF_ACTIVATE: "va_listening", CONF_DEACTIVATE: "va_barging", CONF_ACTION: "cancel_response_cleanup"},
    ]},
    "va_responding": {CONF_ACTIVATE: "va_responding", CONF_CASES: [{CONF_ANY: ["va_barging", "va_stopping"]}]},
    "va_end": {CONF_DEACTIVATE: ["va_start_requested", "va_starting", "va_listening", "va_thinking"], CONF_CASES: [
        {CONF_ANY: "va_barging", CONF_ACTIVATE: "va_start_requested", CONF_DEACTIVATE: ["va_barging", "va_responding", "announcement", "announcement_play_seen", "va_run_ended", "va_response_drained"]},
        {CONF_ALL: ["va_responding", "va_response_drained"], CONF_DEACTIVATE: ["va_responding", "va_run_ended", "va_response_drained", "announcement", "announcement_play_seen"]},
        {CONF_ANY: "va_responding", CONF_ACTIVATE: ["va_responding", "va_run_ended"]},
    ]},
    "va_idle": {CONF_DEACTIVATE: ["va_start_requested", "va_starting", "va_listening", "va_thinking", "va_responding", "announcement", "announcement_play_seen", "va_stopping", "va_run_ended", "va_response_drained"], CONF_CASES: [
        {CONF_ANY: "va_barging", CONF_ACTIVATE: "va_start_requested", CONF_DEACTIVATE: "va_barging"},
    ]},
    "va_response_done": {CONF_DEACTIVATE: ["va_responding", "announcement", "announcement_play_seen", "va_run_ended", "va_response_drained"]},
    "va_error": {CONF_DEACTIVATE: ["va_start_requested", "va_starting", "va_listening", "va_thinking", "va_responding", "va_barging", "va_stopping", "va_run_ended", "va_response_drained"]},
}


def _list_or_one(value_schema):
    return cv.Any(value_schema, cv.ensure_list(value_schema))


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _validate_color(value):
    if isinstance(value, str):
        key = value.lower().replace(" ", "_")
        if key not in COLOR_NAMES:
            raise cv.Invalid(f"Unknown LED color '{value}'")
        return key
    value = cv.ensure_list(cv.percentage)(value)
    if len(value) != 3:
        raise cv.Invalid("LED color list must contain red, green and blue")
    return value


def _resolve_color(value):
    if isinstance(value, str):
        return COLOR_NAMES[value]
    return tuple(value)


def _merged_led_states(led_conf):
    states = {name: dict(values) for name, values in LED_PRESETS[led_conf[CONF_PRESET]].items()}
    for name, override in led_conf[CONF_STATES].items():
        merged = states.get(name, {}).copy()
        merged.update(override)
        states[name] = merged
    return states


LED_STATE_SCHEMA = cv.Schema(
    {
        cv.Optional(CONF_COLOR): _validate_color,
        cv.Optional(CONF_EFFECT): cv.string_strict,
        cv.Optional(CONF_BRIGHTNESS): cv.percentage,
    }
)

LED_OUTPUT_SCHEMA = cv.Schema(
    {
        cv.Required(CONF_ID): cv.use_id(light.LightState),
        cv.Optional(CONF_PRESET, default="ws2812_ring"): cv.one_of(*LED_PRESETS.keys(), lower=True),
        cv.Optional(CONF_STATES, default={}): cv.Schema({cv.string_strict: LED_STATE_SCHEMA}),
    }
)

ACTIVITY_BODY_SCHEMA = cv.Schema(
    {
        cv.Optional(CONF_PRIORITY, default=0): cv.int_range(min=-32768, max=32767),
        cv.Optional(CONF_INITIAL, default=False): cv.boolean,
        cv.Optional(CONF_POLICIES, default={}): cv.Schema({cv.string_strict: cv.string_strict}),
    }
)
ACTIVITIES_SCHEMA = cv.Schema({cv.string_strict: ACTIVITY_BODY_SCHEMA})
GROUPS_SCHEMA = cv.Schema({cv.string_strict: cv.ensure_list(cv.string_strict)})

ACTION_TRIGGER_SCHEMA = automation.validate_automation(single=True)
POLICY_VALUE_SCHEMA = cv.Any(
    cv.int_,
    automation.validate_automation({cv.Optional(CONF_VALUE): cv.int_}, single=True),
)
POLICY_SCHEMA = cv.Schema(
    {
        cv.Optional(CONF_OUTPUT): cv.use_id(globals_component.GlobalsComponent),
        cv.Optional(CONF_VALUES, default={}): cv.Schema({cv.string_strict: POLICY_VALUE_SCHEMA}),
        cv.Optional(CONF_ON_CHANGE): ACTION_TRIGGER_SCHEMA,
    }
)

EVENT_CASE_SCHEMA = cv.Schema(
    {
        cv.Optional(CONF_ANY, default=[]): _list_or_one(cv.string_strict),
        cv.Optional(CONF_ALL, default=[]): _list_or_one(cv.string_strict),
        cv.Optional(CONF_NONE, default=[]): _list_or_one(cv.string_strict),
        cv.Optional(CONF_ACTIVATE, default=[]): _list_or_one(cv.string_strict),
        cv.Optional(CONF_DEACTIVATE, default=[]): _list_or_one(cv.string_strict),
        cv.Optional(CONF_ACTION): cv.string_strict,
    }
)
EVENT_SCHEMA = cv.Schema(
    {
        cv.Optional(CONF_ACTIVATE, default=[]): _list_or_one(cv.string_strict),
        cv.Optional(CONF_DEACTIVATE, default=[]): _list_or_one(cv.string_strict),
        cv.Optional(CONF_ACTION): cv.string_strict,
        cv.Optional(CONF_CASES, default=[]): cv.ensure_list(EVENT_CASE_SCHEMA),
        cv.Optional(CONF_THEN): ACTION_TRIGGER_SCHEMA,
    }
)

DERIVED_ACTIVITY_SCHEMA = cv.Schema(
    {
        cv.Required(CONF_NAME): cv.string_strict,
        cv.Optional(CONF_WHEN, default={}): cv.Schema(
            {
                cv.Optional(CONF_ANY_ACTIVE, default=[]): cv.ensure_list(cv.string_strict),
                cv.Optional(CONF_ALL_ACTIVE, default=[]): cv.ensure_list(cv.string_strict),
                cv.Optional(CONF_NONE_ACTIVE, default=[]): cv.ensure_list(cv.string_strict),
            }
        ),
    }
)

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(): cv.declare_id(RuntimeController),
        cv.Optional(CONF_DEBUG, default=False): cv.boolean,
        cv.Optional(CONF_PROFILE): cv.one_of(PROFILE_FULL_VOICE_VOIP, lower=True),
        cv.Optional(CONF_OBSERVE, default={}): cv.Schema(
            {
                cv.Optional(CONF_VOIP_STACK): cv.use_id(VoipStack),
            },
            extra=cv.ALLOW_EXTRA,
        ),
        cv.Optional(CONF_OUTPUTS, default={}): cv.Schema(
            {
                cv.Optional(CONF_LED): LED_OUTPUT_SCHEMA,
            },
            extra=cv.ALLOW_EXTRA,
        ),
        cv.Optional(CONF_OUTPUT_SCRIPT): cv.use_id(script.Script),
        cv.Optional(CONF_STATE_OUTPUTS, default={}): cv.Schema(
            {
                cv.Optional(CONF_ACTIVITY_MASK): cv.use_id(globals_component.GlobalsComponent),
                cv.Optional(CONF_SEQUENCE): cv.use_id(globals_component.GlobalsComponent),
            }
        ),
        cv.Optional(CONF_VOIP): cv.Schema(
            {
                cv.Required(CONF_ID): cv.use_id(VoipStack),
                cv.Optional(CONF_ACTIVITY_PREFIX, default="voip:"): cv.string_strict,
                cv.Optional(CONF_STATES, default={}): cv.Schema({cv.string_strict: ACTIVITY_BODY_SCHEMA}),
            }
        ),
        cv.Optional(CONF_ACTIVITIES, default={}): ACTIVITIES_SCHEMA,
        cv.Optional(CONF_GROUPS, default={}): GROUPS_SCHEMA,
        cv.Optional(CONF_AUTO_EVENTS, default=True): cv.boolean,
        cv.Optional(CONF_DERIVED_ACTIVITIES, default=[]): cv.ensure_list(DERIVED_ACTIVITY_SCHEMA),
        cv.Optional(CONF_EVENTS, default={}): cv.Schema({cv.string_strict: EVENT_SCHEMA}),
        cv.Optional(CONF_ACTIONS, default={}): cv.Schema({cv.string_strict: ACTION_TRIGGER_SCHEMA}),
        cv.Optional(CONF_POLICIES, default={}): cv.Schema({cv.string_strict: POLICY_SCHEMA}),
    }
).extend(cv.COMPONENT_SCHEMA)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    cg.add(var.set_debug(config[CONF_DEBUG]))
    if config[CONF_DEBUG]:
        cg.add_define("USE_RUNTIME_CONTROLLER_DEBUG")

    profile_full = config.get(CONF_PROFILE) == PROFILE_FULL_VOICE_VOIP
    activities = dict(FULL_VOICE_VOIP_ACTIVITIES) if profile_full else {}
    activities.update(config[CONF_ACTIVITIES])
    groups = {k: list(v) for k, v in (FULL_VOICE_VOIP_GROUPS if profile_full else {}).items()}
    for group, values in config[CONF_GROUPS].items():
        groups.setdefault(group, [])
        groups[group].extend(values)
    derived_activities = list(FULL_VOICE_VOIP_DERIVED if profile_full else [])
    derived_activities.extend(config[CONF_DERIVED_ACTIVITIES])
    events = dict(FULL_VOICE_VOIP_EVENTS) if profile_full else {}
    events.update(config[CONF_EVENTS])
    voip_states = dict(FULL_VOICE_VOIP_VOIP_STATES) if profile_full else {}
    event_then_names = {name for name, event_conf in events.items() if CONF_THEN in event_conf}
    action_names = set(config[CONF_ACTIONS])
    collisions = sorted(event_then_names & action_names)
    if collisions:
        raise cv.Invalid(
            "runtime_controller event 'then' names must not collide with top-level actions: "
            + ", ".join(collisions)
        )

    if CONF_OUTPUT_SCRIPT in config:
        output_script = await cg.get_variable(config[CONF_OUTPUT_SCRIPT])
        cg.add(var.set_output_script(output_script))

    state_outputs = config[CONF_STATE_OUTPUTS]
    if CONF_ACTIVITY_MASK in state_outputs:
        full_id, output = await cg.get_variable_with_full_id(state_outputs[CONF_ACTIVITY_MASK])
        template_arg = cg.TemplateArguments(full_id.type)
        cg.add(var.set_activity_mask_output.template(template_arg)(output))
    if CONF_SEQUENCE in state_outputs:
        full_id, output = await cg.get_variable_with_full_id(state_outputs[CONF_SEQUENCE])
        template_arg = cg.TemplateArguments(full_id.type)
        cg.add(var.set_sequence_output.template(template_arg)(output))

    outputs = config[CONF_OUTPUTS]
    if CONF_LED in outputs:
        led_conf = outputs[CONF_LED]
        led = await cg.get_variable(led_conf[CONF_ID])
        cg.add(var.set_led_light(led))
        for state, values in _merged_led_states(led_conf).items():
            red, green, blue = _resolve_color(values.get(CONF_COLOR, "off"))
            brightness = values.get(CONF_BRIGHTNESS, 0.0)
            effect = values.get(CONF_EFFECT, "None")
            cg.add(var.add_led_state(state, red, green, blue, brightness, effect))

    if profile_full and CONF_VOIP_STACK in config[CONF_OBSERVE]:
        voip = await cg.get_variable(config[CONF_OBSERVE][CONF_VOIP_STACK])
        cg.add(var.set_voip(voip))
        cg.add(var.set_voip_activity_prefix("voip:"))
        cg.add_define("USE_RUNTIME_CONTROLLER_VOIP")
        for state, activity in voip_states.items():
            name = f"voip:{state}"
            cg.add(var.add_activity(name, activity[CONF_PRIORITY], activity.get(CONF_INITIAL, False)))
            for policy, value in activity[CONF_POLICIES].items():
                cg.add(var.add_activity_policy(name, policy, value))

    if CONF_VOIP in config:
        voip_conf = config[CONF_VOIP]
        voip = await cg.get_variable(voip_conf[CONF_ID])
        cg.add(var.set_voip(voip))
        cg.add(var.set_voip_activity_prefix(voip_conf[CONF_ACTIVITY_PREFIX]))
        cg.add_define("USE_RUNTIME_CONTROLLER_VOIP")
        for state, activity in voip_conf[CONF_STATES].items():
            name = f"{voip_conf[CONF_ACTIVITY_PREFIX]}{state}"
            cg.add(var.add_activity(name, activity[CONF_PRIORITY], activity[CONF_INITIAL]))
            for policy, value in activity[CONF_POLICIES].items():
                cg.add(var.add_activity_policy(name, policy, value))

    for name, activity in activities.items():
        cg.add(
            var.add_activity(
                name,
                activity.get(CONF_PRIORITY, 0),
                activity.get(CONF_INITIAL, False),
            )
        )
        for policy, value in activity.get(CONF_POLICIES, {}).items():
            cg.add(var.add_activity_policy(name, policy, value))

    for group, group_activities in groups.items():
        for activity in group_activities:
            cg.add(var.set_activity_group(activity, group))

    if config[CONF_AUTO_EVENTS]:
        for name in activities:
            cg.add(var.add_event_activity(name, name, True))

    for derived in derived_activities:
        cg.add(var.add_derived_activity(derived[CONF_NAME]))
        when = derived.get(CONF_WHEN, {})
        for activity in when.get(CONF_ANY_ACTIVE, []):
            cg.add(var.add_derived_any_active(activity))
        for activity in when.get(CONF_ALL_ACTIVE, []):
            cg.add(var.add_derived_all_active(activity))
        for activity in when.get(CONF_NONE_ACTIVE, []):
            cg.add(var.add_derived_none_active(activity))

    for name, event_conf in events.items():
        for rule in event_conf.get(CONF_CASES, []):
            cg.add(var.add_event_rule(name, rule.get(CONF_ACTION, "")))
            for activity in _as_list(rule.get(CONF_ANY, [])):
                cg.add(var.add_event_rule_any_active(activity))
            for activity in _as_list(rule.get(CONF_ALL, [])):
                cg.add(var.add_event_rule_all_active(activity))
            for activity in _as_list(rule.get(CONF_NONE, [])):
                cg.add(var.add_event_rule_none_active(activity))
            for activity in _as_list(rule.get(CONF_ACTIVATE, [])):
                cg.add(var.add_event_rule_update(activity, True))
            for activity in _as_list(rule.get(CONF_DEACTIVATE, [])):
                cg.add(var.add_event_rule_update(activity, False))
        default_activate = _as_list(event_conf.get(CONF_ACTIVATE, []))
        default_deactivate = _as_list(event_conf.get(CONF_DEACTIVATE, []))
        default_action = event_conf.get(CONF_ACTION, "")
        if default_activate or default_deactivate or default_action:
            cg.add(var.add_event_rule(name, default_action))
            for activity in default_activate:
                cg.add(var.add_event_rule_update(activity, True))
            for activity in default_deactivate:
                cg.add(var.add_event_rule_update(activity, False))
        if CONF_THEN in event_conf:
            trigger = cg.new_Pvariable(event_conf[automation.CONF_TRIGGER_ID], cg.TemplateArguments())
            cg.add(var.add_event_trigger(name, trigger))
            await automation.build_automation(trigger, [], event_conf)

    for name, action_conf in config[CONF_ACTIONS].items():
        trigger = cg.new_Pvariable(action_conf[automation.CONF_TRIGGER_ID], cg.TemplateArguments())
        cg.add(var.add_action_trigger(name, trigger))
        await automation.build_automation(trigger, [], action_conf)

    for policy, policy_conf in config[CONF_POLICIES].items():
        if CONF_OUTPUT in policy_conf:
            full_id, output = await cg.get_variable_with_full_id(policy_conf[CONF_OUTPUT])
            template_arg = cg.TemplateArguments(full_id.type)
            cg.add(var.add_policy_global_output.template(template_arg)(policy, output))
        if CONF_ON_CHANGE in policy_conf:
            trigger = cg.new_Pvariable(
                policy_conf[CONF_ON_CHANGE][automation.CONF_TRIGGER_ID],
                cg.TemplateArguments(cg.int32),
            )
            cg.add(var.set_policy_change_trigger(policy, trigger))
            await automation.build_automation(trigger, [(cg.int32, "value")], policy_conf[CONF_ON_CHANGE])
        for value, action_conf in policy_conf[CONF_VALUES].items():
            if isinstance(action_conf, int):
                cg.add(var.add_policy_output(policy, value, action_conf))
                continue
            if CONF_VALUE in action_conf:
                cg.add(var.add_policy_output(policy, value, action_conf[CONF_VALUE]))
            if CONF_THEN in action_conf:
                trigger = cg.new_Pvariable(action_conf[automation.CONF_TRIGGER_ID], cg.TemplateArguments())
                cg.add(var.add_policy_value_trigger(policy, value, trigger))
                await automation.build_automation(trigger, [], action_conf)


async def _new_parented_action(config, action_id, template_arg):
    var = cg.new_Pvariable(action_id, template_arg)
    await cg.register_parented(var, config[CONF_ID])
    return var


@automation.register_action(
    "runtime_controller.event",
    EventAction,
    cv.Schema(
        {
            cv.GenerateID(): cv.use_id(RuntimeController),
            cv.Required(CONF_EVENT): cv.templatable(cv.string),
            cv.Optional(CONF_DUMP, default=False): cv.boolean,
            cv.Optional(CONF_REASON, default=""): cv.templatable(cv.string),
        }
    ),
    synchronous=True,
)
async def event_action_to_code(config, action_id, template_arg, args):
    var = await _new_parented_action(config, action_id, template_arg)
    templ = await cg.templatable(config[CONF_EVENT], args, cg.std_string)
    cg.add(var.set_event(templ))
    cg.add(var.set_dump(config[CONF_DUMP]))
    reason = await cg.templatable(config[CONF_REASON], args, cg.std_string)
    cg.add(var.set_reason(reason))
    return var


@automation.register_action(
    "runtime_controller.set_activity",
    SetActivityAction,
    cv.Schema(
        {
            cv.GenerateID(): cv.use_id(RuntimeController),
            cv.Required(CONF_ACTIVITY): cv.templatable(cv.string),
            cv.Required(CONF_ACTIVE): cv.templatable(cv.boolean),
        }
    ),
    synchronous=True,
)
async def set_activity_action_to_code(config, action_id, template_arg, args):
    var = await _new_parented_action(config, action_id, template_arg)
    activity = await cg.templatable(config[CONF_ACTIVITY], args, cg.std_string)
    active = await cg.templatable(config[CONF_ACTIVE], args, cg.bool_)
    cg.add(var.set_activity(activity))
    cg.add(var.set_active(active))
    return var


@automation.register_action(
    "runtime_controller.set_activities",
    SetActivitiesAction,
    cv.Schema(
        {
            cv.GenerateID(): cv.use_id(RuntimeController),
            cv.Required(CONF_SET): cv.Schema({cv.string_strict: cv.boolean}),
        }
    ),
    synchronous=True,
)
async def set_activities_action_to_code(config, action_id, template_arg, args):
    var = await _new_parented_action(config, action_id, template_arg)
    for activity, active in config[CONF_SET].items():
        cg.add(var.add_activity_state(activity, active))
    return var


@automation.register_action(
    "runtime_controller.request_action",
    RequestActionAction,
    cv.Schema(
        {
            cv.GenerateID(): cv.use_id(RuntimeController),
            cv.Required(CONF_ACTION): cv.templatable(cv.string),
        }
    ),
    synchronous=True,
)
async def request_action_action_to_code(config, action_id, template_arg, args):
    var = await _new_parented_action(config, action_id, template_arg)
    action = await cg.templatable(config[CONF_ACTION], args, cg.std_string)
    cg.add(var.set_action(action))
    return var


@automation.register_action(
    "runtime_controller.dump",
    DumpAction,
    cv.Schema(
        {
            cv.GenerateID(): cv.use_id(RuntimeController),
            cv.Optional(CONF_REASON, default="manual"): cv.templatable(cv.string),
        }
    ),
    synchronous=True,
)
async def dump_action_to_code(config, action_id, template_arg, args):
    var = await _new_parented_action(config, action_id, template_arg)
    reason = await cg.templatable(config[CONF_REASON], args, cg.std_string)
    cg.add(var.set_reason(reason))
    return var


@automation.register_condition(
    "runtime_controller.is_active",
    IsActiveCondition,
    cv.Schema(
        {
            cv.GenerateID(): cv.use_id(RuntimeController),
            cv.Required(CONF_ACTIVITY): cv.templatable(cv.string),
        }
    ),
)
async def is_active_condition_to_code(config, condition_id, template_arg, args):
    var = cg.new_Pvariable(condition_id, template_arg)
    await cg.register_parented(var, config[CONF_ID])
    activity = await cg.templatable(config[CONF_ACTIVITY], args, cg.std_string)
    cg.add(var.set_activity(activity))
    return var
