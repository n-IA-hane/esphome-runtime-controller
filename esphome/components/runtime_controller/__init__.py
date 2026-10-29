from copy import deepcopy

from esphome import automation
import esphome.codegen as cg
import esphome.config_validation as cv
import esphome.final_validate as fv
from esphome.core import Lambda
from esphome.components import (
    globals as globals_component,
    light,
    script,
    media_player,
    switch,
    wifi,
)
from esphome.const import CONF_ID, CONF_NAME, CONF_THEN

CODEOWNERS = ["@n-IA-hane"]
DEPENDENCIES = []

runtime_controller_ns = cg.esphome_ns.namespace("runtime_controller")
RuntimeController = runtime_controller_ns.class_("RuntimeController", cg.Component)
RuntimeNetworkObservers = runtime_controller_ns.class_(
    "RuntimeNetworkObservers", cg.Component
)
SourceEventAction = runtime_controller_ns.class_(
    "SourceEventAction", automation.Action, cg.Parented.template(RuntimeNetworkObservers)
)
VoiceAssistant = cg.esphome_ns.namespace("voice_assistant").class_("VoiceAssistant", cg.Component)
MicroWakeWord = cg.esphome_ns.namespace("micro_wake_word").class_("MicroWakeWord", cg.Component)
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
CONF_STORAGE_IN_PSRAM = "storage_in_psram"
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
CONF_FEATURES = "features"
CONF_WIFI = "wifi"
CONF_MICROPHONE_MUTE = "microphone_mute"
CONF_SPEAKER_MUTE = "speaker_mute"
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
CONF_TIMERS = "timers"
CONF_API = "api"
CONF_OBSERVER_BINDINGS = "_observer_bindings"

PROFILE_FULL_VOICE_VOIP = "full_voice_voip"
PROFILE_PRESENTATION = "presentation"
CONF_PRESENTATION = "presentation"
CONF_PRIORITIES = "priorities"

PRESENTATION_NAMES = (
    "idle", "music", "announcement", "ringing", "calling", "remote_ringing",
    "call", "wake", "listening", "thinking", "responding", "timer", "error",
    "boot", "no_wifi", "no_ha", "no_va", "muted", "mic_muted", "speaker_muted",
)
PRESENTATION_ALIASES = {
    "media": "music", "voip_ringing": "ringing", "voip_calling": "calling",
    "voip_remote_ringing": "remote_ringing", "voip_in_call": "call",
    "timer_ringing": "timer",
}

# Public ESPHome trigger names and the existing reducer events they represent.
SOURCE_HOOKS = {
    CONF_VOICE_ASSISTANT: {
        "on_start": "va_start", "on_listening": "va_listening",
        "on_stt_vad_end": "va_thinking", "on_intent_progress": "va_responding",
        "on_tts_start": "va_responding", "on_end": "va_end", "on_idle": "va_idle",
        "on_error": "va_error", "on_client_connected": "va_client_connected",
        "on_client_disconnected": "va_client_disconnected",
    },
    CONF_MICRO_WAKE_WORD: {"on_wake_word_detected": "wake_word"},
    CONF_TIMERS: {
        "on_timer_started": "timer_started", "on_timer_cancelled": "timer_cancelled",
        "on_timer_finished": "timer_finished", "on_timer_updated": "timer_updated",
    },
    CONF_API: {"on_client_connected": "api_connected", "on_client_disconnected": "api_disconnected"},
}

LED_POLICY = "led_status"


def _validate_storage_in_psram(value):
    value = cv.boolean(value)
    if value:
        return cv.requires_component("psram")(value)
    return value


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
    "none": {},
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
        "voip_remote_ringing": {
            "color": "orange",
            "effect": "Ringing",
            "brightness": 1.0,
        },
        "voip_in_call": {
            "color": [0.3, 0.69, 0.31],
            "effect": "None",
            "brightness": 1.0,
        },
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
        "voip_remote_ringing": {
            "color": "orange",
            "effect": "Ringing",
            "brightness": 1.0,
        },
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
    "va": [
        "va_start_requested",
        "va_starting",
        "va_listening",
        "va_thinking",
        "va_responding",
        "va_barging",
        "va_stopping",
    ],
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
    "remote_ringing": {
        CONF_PRIORITY: 974,
        CONF_POLICIES: {
            "led_status": "voip_remote_ringing",
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
    "idle": {
        CONF_PRIORITY: 0,
        CONF_INITIAL: True,
        CONF_POLICIES: {
            "led_status": "idle",
            "display_status": "idle",
            "va_state": "idle",
            "va_response": "inactive",
            "audio_policy": "normal",
            "ringtone": "stop",
            "timer_alarm": "stop",
        },
    },
    "boot": {
        CONF_PRIORITY: 1000,
        CONF_POLICIES: {
            "led_status": "boot",
            "display_status": "boot",
            "va_state": "idle",
        },
    },
    "no_wifi": {
        CONF_PRIORITY: 990,
        CONF_POLICIES: {
            "led_status": "no_wifi",
            "display_status": "no_wifi",
            "va_state": "idle",
        },
    },
    "no_ha": {
        CONF_PRIORITY: 980,
        CONF_POLICIES: {
            "led_status": "no_ha",
            "display_status": "no_ha",
            "va_state": "idle",
        },
    },
    "no_va": {
        CONF_PRIORITY: 970,
        CONF_POLICIES: {
            "led_status": "no_va",
            "display_status": "no_va",
            "va_state": "idle",
        },
    },
    "both_muted": {
        CONF_PRIORITY: 660,
        CONF_POLICIES: {
            "led_status": "muted",
            "display_status": "muted",
            "va_state": "idle",
        },
    },
    "mic_muted": {
        CONF_PRIORITY: 650,
        CONF_POLICIES: {
            "led_status": "mic_muted",
            "display_status": "muted",
            "va_state": "idle",
        },
    },
    "speaker_muted": {
        CONF_PRIORITY: 640,
        CONF_POLICIES: {
            "led_status": "speaker_muted",
            "display_status": "muted",
            "va_state": "idle",
        },
    },
    "media": {
        CONF_PRIORITY: 100,
        CONF_POLICIES: {
            "led_status": "media",
            "display_status": "media",
            "audio_policy": "normal",
            "va_state": "idle",
        },
    },
    "announcement": {
        CONF_PRIORITY: 200,
        CONF_POLICIES: {
            "led_status": "media",
            "display_status": "media",
            "audio_policy": "duck",
            "va_state": "idle",
        },
    },
    "timer": {CONF_PRIORITY: 0, CONF_POLICIES: {}},
    "timer_ringing": {
        CONF_PRIORITY: 900,
        CONF_POLICIES: {
            "led_status": "timer_ringing",
            "display_status": "timer_ringing",
            "audio_policy": "duck",
            "timer_alarm": "play",
            "va_state": "idle",
        },
    },
    "va_start_requested": {
        CONF_PRIORITY: 810,
        CONF_POLICIES: {
            "led_status": "wake",
            "display_status": "wake",
            "audio_policy": "duck",
            "va_state": "idle",
            "va_response": "inactive",
        },
    },
    "va_starting": {
        CONF_PRIORITY: 810,
        CONF_POLICIES: {
            "led_status": "wake",
            "display_status": "wake",
            "audio_policy": "duck",
            "va_state": "idle",
            "va_response": "inactive",
        },
    },
    "va_barging": {
        CONF_PRIORITY: 825,
        CONF_POLICIES: {
            "led_status": "listening",
            "display_status": "listening",
            "audio_policy": "duck",
            "va_state": "listening",
            "va_response": "inactive",
        },
    },
    "va_stopping": {CONF_PRIORITY: 0, CONF_POLICIES: {}},
    "va_run_ended": {CONF_PRIORITY: 0, CONF_POLICIES: {}},
    "va_response_drained": {CONF_PRIORITY: 0, CONF_POLICIES: {}},
    "va_listening": {
        CONF_PRIORITY: 820,
        CONF_POLICIES: {
            "led_status": "listening",
            "display_status": "listening",
            "audio_policy": "duck",
            "va_state": "listening",
            "va_response": "inactive",
        },
    },
    "va_thinking": {
        CONF_PRIORITY: 830,
        CONF_POLICIES: {
            "led_status": "thinking",
            "display_status": "thinking",
            "audio_policy": "duck",
            "va_state": "thinking",
            "va_response": "inactive",
        },
    },
    "va_responding": {
        CONF_PRIORITY: 840,
        CONF_POLICIES: {
            "led_status": "responding",
            "display_status": "responding",
            "audio_policy": "duck",
            "va_state": "responding",
            "va_response": "active",
        },
    },
}

FULL_VOICE_VOIP_DERIVED = [
    {
        CONF_NAME: "both_muted",
        CONF_WHEN: {CONF_ALL_ACTIVE: ["mic_muted", "speaker_muted"]},
    },
]


def _media_completion_event(playing):
    """Leaving an announcement preserves music state and completes the VA join."""
    event = {
        (CONF_ACTIVATE if playing else CONF_DEACTIVATE): "media",
        CONF_CASES: [
            {CONF_ALL: ["va_stopping"], CONF_DEACTIVATE: ["announcement"]},
            {CONF_ALL: ["va_barging"], CONF_DEACTIVATE: ["announcement"]},
            {
                CONF_ALL: ["va_responding", "announcement", "va_run_ended"],
                CONF_DEACTIVATE: [
                    "va_responding",
                    "announcement",
                    "va_run_ended",
                    "va_response_drained",
                ],
            },
            {
                CONF_ALL: ["va_responding", "announcement"],
                CONF_ACTIVATE: "va_response_drained",
                CONF_DEACTIVATE: ["announcement"],
            },
            {CONF_ALL: ["announcement"], CONF_DEACTIVATE: ["announcement"]},
        ],
    }

    # Cases are alternatives to the default rule, not appended updates.
    key = CONF_ACTIVATE if playing else CONF_DEACTIVATE
    for case in event[CONF_CASES]:
        case[key] = (
            case.get(key, []) if isinstance(case.get(key, []), list) else [case[key]]
        ) + ["media"]
    return event


FULL_VOICE_VOIP_EVENTS = {
    "boot_start": {CONF_ACTIVATE: ["boot", "no_wifi", "no_ha"]},
    "boot_ready": {CONF_DEACTIVATE: "boot"},
    "wifi_connected": {CONF_DEACTIVATE: "no_wifi"},
    "wifi_disconnected": {CONF_ACTIVATE: "no_wifi"},
    "ha_connected": {CONF_DEACTIVATE: "no_ha"},
    "ha_disconnected": {CONF_ACTIVATE: "no_ha"},
    "va_client_connected": {CONF_DEACTIVATE: "no_va"},
    "va_client_disconnected": {
        CONF_ACTIVATE: "no_va",
        CONF_DEACTIVATE: [
            "va_start_requested",
            "va_starting",
            "va_listening",
            "va_thinking",
            "va_responding",
            "va_barging",
            "va_stopping",
            "va_run_ended",
            "va_response_drained",
        ],
    },
    "mic_muted": {CONF_ACTIVATE: "mic_muted"},
    "mic_unmuted": {CONF_DEACTIVATE: "mic_muted"},
    "speaker_muted": {CONF_ACTIVATE: "speaker_muted"},
    "speaker_unmuted": {CONF_DEACTIVATE: "speaker_muted"},
    "timer_started": {CONF_ACTIVATE: "timer"},
    "timer_stopped": {CONF_DEACTIVATE: "timer_ringing"},
    "timer_finished": {CONF_ACTIVATE: "timer_ringing"},
    "media_idle": _media_completion_event(False),
    "media_paused": _media_completion_event(False),
    "media_playing": _media_completion_event(True),
    "announcement_started": {
        CONF_ACTIVATE: "announcement",
        CONF_CASES: [
            {
                CONF_ANY: [
                    "va_start_requested",
                    "va_starting",
                    "va_barging",
                    "va_listening",
                    "va_thinking",
                    "va_stopping",
                ],
                CONF_DEACTIVATE: [
                    "announcement",
                    "va_stopping",
                ],
                CONF_ACTION: "stop_announcement",
            },
        ],
    },
    "wake_word": {
        CONF_ACTIVATE: "va_start_requested",
        CONF_ACTION: "voice_start",
        CONF_CASES: [
            {CONF_ANY: "va_start_requested"},
            {
                CONF_ALL: ["va_responding", "announcement"],
                CONF_ACTIVATE: ["va_start_requested", "va_barging"],
                CONF_DEACTIVATE: [
                    "announcement",
                    "va_responding",
                ],
                CONF_ACTION: "voice_cancel_response",
            },
            {
                CONF_ALL: ["va_responding", "va_run_ended"],
                CONF_ACTIVATE: "va_start_requested",
                CONF_DEACTIVATE: [
                    "va_responding",
                    "va_run_ended",
                    "va_response_drained",
                ],
                CONF_ACTION: "voice_cancel_pipeline",
            },
            {
                CONF_ANY: [
                    "va_starting",
                    "va_listening",
                    "va_thinking",
                    "va_responding",
                ],
                CONF_ACTIVATE: ["va_start_requested", "va_barging"],
                CONF_DEACTIVATE: [
                    "va_starting",
                    "va_listening",
                    "va_thinking",
                    "va_responding",
                ],
                CONF_ACTION: "voice_cancel_pipeline",
            },
            {CONF_ANY: ["va_barging", "va_stopping"]},
        ],
    },
    "voice_stop": {
        CONF_ACTIVATE: "va_stopping",
        CONF_DEACTIVATE: [
            "va_start_requested",
            "va_starting",
            "va_barging",
            "va_listening",
            "va_thinking",
            "va_responding",
            "announcement",
            "va_run_ended",
            "va_response_drained",
        ],
        CONF_ACTION: "voice_stop_all",
    },
    "manual_voice_toggle": {
        CONF_ACTIVATE: "va_start_requested",
        CONF_ACTION: "voice_start",
        CONF_CASES: [
            {CONF_ANY: "va_stopping"},
            {
                CONF_ALL: ["va_responding", "announcement"],
                CONF_ACTIVATE: "va_stopping",
                CONF_DEACTIVATE: [
                    "va_start_requested",
                    "va_starting",
                    "va_barging",
                    "va_listening",
                    "va_thinking",
                    "va_responding",
                    "announcement",
                ],
                CONF_ACTION: "voice_stop_all",
            },
            {
                CONF_ANY: "va_responding",
                CONF_ACTIVATE: "va_stopping",
                CONF_DEACTIVATE: [
                    "va_start_requested",
                    "va_starting",
                    "va_barging",
                    "va_listening",
                    "va_thinking",
                    "va_responding",
                ],
                CONF_ACTION: "voice_stop_pipeline",
            },
            {
                CONF_ANY: [
                    "va_start_requested",
                    "va_starting",
                    "va_barging",
                    "va_listening",
                    "va_thinking",
                ],
                CONF_ACTIVATE: "va_stopping",
                CONF_DEACTIVATE: [
                    "va_start_requested",
                    "va_starting",
                    "va_barging",
                    "va_listening",
                    "va_thinking",
                    "va_responding",
                    "announcement",
                ],
                CONF_ACTION: "voice_stop_pipeline",
            },
        ],
    },
    "va_start": {
        CONF_ACTIVATE: "va_starting",
        CONF_ACTION: "cancel_response_cleanup",
        CONF_CASES: [
            {
                CONF_ANY: "va_barging",
                CONF_ACTIVATE: "va_listening",
                CONF_DEACTIVATE: "va_barging",
                CONF_ACTION: "cancel_response_cleanup",
            },
        ],
    },
    "va_responding": {
        CONF_ACTIVATE: "va_responding",
        CONF_CASES: [{CONF_ANY: ["va_barging", "va_stopping"]}],
    },
    "va_end": {
        CONF_DEACTIVATE: [
            "va_start_requested",
            "va_starting",
            "va_listening",
            "va_thinking",
        ],
        CONF_CASES: [
            {
                CONF_ANY: "va_barging",
                CONF_ACTIVATE: "va_start_requested",
                CONF_DEACTIVATE: [
                    "va_barging",
                    "va_responding",
                    "announcement",
                    "va_run_ended",
                    "va_response_drained",
                ],
            },
            {
                CONF_ALL: ["va_responding", "va_response_drained"],
                CONF_DEACTIVATE: [
                    "va_responding",
                    "va_run_ended",
                    "va_response_drained",
                    "announcement",
                ],
            },
            {
                CONF_ANY: "va_responding",
                CONF_ACTIVATE: ["va_responding", "va_run_ended"],
            },
        ],
    },
    "va_idle": {
        CONF_DEACTIVATE: [
            "va_start_requested",
            "va_starting",
            "va_listening",
            "va_thinking",
            "va_responding",
            "announcement",
            "va_stopping",
            "va_run_ended",
            "va_response_drained",
        ],
        CONF_CASES: [
            {
                CONF_ANY: "va_barging",
                CONF_ACTIVATE: "va_start_requested",
                CONF_DEACTIVATE: "va_barging",
            },
        ],
    },
    "va_response_done": {
        CONF_DEACTIVATE: [
            "va_responding",
            "announcement",
            "va_run_ended",
            "va_response_drained",
        ]
    },
    "va_stop_complete": {CONF_DEACTIVATE: "va_stopping"},
    "va_start_rejected": {
        CONF_DEACTIVATE: ["va_start_requested", "va_starting", "va_barging"]
    },
    "va_stop_timeout": {CONF_DEACTIVATE: ["va_barging", "va_start_requested"]},
    "va_error": {
        CONF_DEACTIVATE: [
            "va_start_requested",
            "va_starting",
            "va_listening",
            "va_thinking",
            "va_responding",
            "va_barging",
            "va_stopping",
            "va_run_ended",
            "va_response_drained",
        ]
    },
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
    states = {
        name: dict(values)
        for name, values in LED_PRESETS[led_conf[CONF_PRESET]].items()
    }
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
        cv.Optional(CONF_PRESET, default="ws2812_ring"): cv.one_of(
            *LED_PRESETS.keys(), lower=True
        ),
        cv.Optional(CONF_STATES, default={}): cv.Schema(
            {cv.string_strict: LED_STATE_SCHEMA}
        ),
    }
)

ACTIVITY_BODY_SCHEMA = cv.Schema(
    {
        cv.Optional(CONF_PRIORITY, default=0): cv.int_range(min=-32768, max=32767),
        cv.Optional(CONF_INITIAL, default=False): cv.boolean,
        cv.Optional(CONF_POLICIES, default={}): cv.Schema(
            {cv.string_strict: cv.string_strict}
        ),
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
        cv.Optional(CONF_VALUES, default={}): cv.Schema(
            {cv.string_strict: POLICY_VALUE_SCHEMA}
        ),
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
                cv.Optional(CONF_ANY_ACTIVE, default=[]): cv.ensure_list(
                    cv.string_strict
                ),
                cv.Optional(CONF_ALL_ACTIVE, default=[]): cv.ensure_list(
                    cv.string_strict
                ),
                cv.Optional(CONF_NONE_ACTIVE, default=[]): cv.ensure_list(
                    cv.string_strict
                ),
            }
        ),
    }
)


PROFILE_FEATURES = ("voice_assistant", "media_player", "timers")


def _selected_profile(config):
    """Select declarative rules only; adapters and hardware remain package-owned."""
    features = set(config.get(CONF_FEATURES, PROFILE_FEATURES))
    activities = dict(FULL_VOICE_VOIP_ACTIVITIES)
    if "voice_assistant" not in features:
        activities = {
            k: v
            for k, v in activities.items()
            if not k.startswith("va_") and k != "no_va"
        }
    if "media_player" not in features:
        activities = {
            k: v for k, v in activities.items() if k not in ("media", "announcement")
        }
    if "timers" not in features:
        activities = {
            k: v for k, v in activities.items() if k not in ("timer", "timer_ringing")
        }
    names = set(activities)
    events = {}
    for name, event in FULL_VOICE_VOIP_EVENTS.items():
        if "voice_assistant" not in features and (
            name.startswith("va_")
            or name in ("wake_word", "manual_voice_toggle", "voice_stop", "voice_quiet")
        ):
            continue
        if "media_player" not in features and (
            name.startswith("media_") or name == "announcement_started"
        ):
            continue
        if "timers" not in features and name.startswith("timer_"):
            continue

        def select_rule(rule):
            if set(_as_list(rule.get(CONF_ALL, []))) - names:
                return None
            selected = dict(rule)
            for key in (CONF_ANY, CONF_ALL, CONF_NONE, CONF_ACTIVATE, CONF_DEACTIVATE):
                if key in selected:
                    selected[key] = [x for x in _as_list(selected[key]) if x in names]
            if CONF_ANY in rule and not selected[CONF_ANY]:
                return None
            return selected

        selected = select_rule(event)
        if selected is not None:
            if CONF_CASES in event:
                selected[CONF_CASES] = [
                    r
                    for case in event[CONF_CASES]
                    if (r := select_rule(case)) is not None
                ]
            events[name] = selected
    groups = {
        k: [x for x in v if x in names] for k, v in FULL_VOICE_VOIP_GROUPS.items()
    }
    return activities, groups, list(FULL_VOICE_VOIP_DERIVED), events


def _prepare_presentation(config):
    """Expand natural triggers into existing policy actions before validation."""
    if not isinstance(config, dict):
        return config
    config = deepcopy(config)
    triggers = {name: config.pop(f"on_{name}") for name in PRESENTATION_NAMES
                if f"on_{name}" in config}
    if triggers:
        policy = config.setdefault(CONF_POLICIES, {}).setdefault(CONF_PRESENTATION, {})
        values = policy.setdefault(CONF_VALUES, {})
        for name, actions in triggers.items():
            if name in values:
                raise cv.Invalid(f"Duplicate presentation binding for {name}")
            values[name] = actions
        config.setdefault(CONF_PRESENTATION, {})
    if "on_state_change" in config:
        presentation = config.setdefault(CONF_PRESENTATION, {})
        if CONF_ON_CHANGE in presentation:
            raise cv.Invalid("Duplicate presentation on_state_change binding")
        presentation[CONF_ON_CHANGE] = config.pop("on_state_change")
    if (CONF_PROFILE not in config and config.get(CONF_OBSERVE)
            and not any(config.get(key) for key in (
                CONF_ACTIVITIES, CONF_GROUPS, CONF_DERIVED_ACTIVITIES, CONF_EVENTS,
            ))):
        config[CONF_PROFILE] = PROFILE_PRESENTATION
    if config.get(CONF_PROFILE) == PROFILE_PRESENTATION and CONF_FEATURES not in config:
        observed = config.get(CONF_OBSERVE, {})
        config[CONF_FEATURES] = [name for name in PROFILE_FEATURES if observed.get(name)]
    bindings = []
    for source, hooks in SOURCE_HOOKS.items():
        if not config.get(CONF_OBSERVE, {}).get(source):
            continue
        for hook, event in hooks.items():
            action = {"event": event}
            if source == CONF_API:
                action["text"] = Lambda("return client_info;")
            elif source == CONF_TIMERS:
                action["text"] = Lambda("return timer.id;")
            if hook == "on_intent_progress":
                action["enabled"] = Lambda("return !x.empty();")
            bindings.append({"source": source, "hook": hook,
                             "automation": {CONF_THEN: [{"runtime_controller.source_event": action}]}})
    if bindings:
        config[CONF_OBSERVER_BINDINGS] = bindings
    return config


def _attach_source_observers(config):
    """Compose validated actions into one official Automation per source trigger.

    IDs are reserved and resolved in this component's schema before final
    validation. Source codegen then builds the combined chain exactly once.
    """
    full = fv.full_config.get()
    attachments = full.data.setdefault("runtime_controller.observer_bindings", set())
    observed = config[CONF_OBSERVE]
    if observed.get(CONF_WIFI) and CONF_WIFI not in full:
        raise cv.Invalid("observe.wifi requires the wifi component")
    if (observed.get(CONF_VOICE_ASSISTANT) and observed.get(CONF_TIMERS)
            and observed[CONF_VOICE_ASSISTANT] != observed[CONF_TIMERS]):
        raise cv.Invalid("Voice Assistant and timer observers must refer to the same component")
    if config[CONF_STATE_OUTPUTS].get("api_clients") and not observed.get(CONF_API):
        raise cv.Invalid("state_outputs.api_clients requires observe.api")
    for binding in config.pop(CONF_OBSERVER_BINDINGS, []):
        source, hook = binding["source"], binding["hook"]
        if source == CONF_API:
            if CONF_API not in full:
                raise cv.Invalid("observe.api requires the api component")
            target = full[CONF_API]
        else:
            path = full.get_path_for_id(observed[source])[:-1]
            target = full.get_config_for_path(path)
        key = (str(config[CONF_ID]), source, hook)
        if key in attachments:
            continue
        addition = binding["automation"]
        if hook in target:
            expected = SOURCE_HOOKS[source][hook]
            existing = [item.get("runtime_controller.source_event") for item in target[hook][CONF_THEN]]
            if any(isinstance(item, dict) and item.get(CONF_EVENT) == expected
                   and str(item.get(CONF_ID)) == str(config["observers_id"]) for item in existing):
                attachments.add(key)
                continue
            for item in target[hook][CONF_THEN]:
                forwarded = item.get("runtime_controller.event")
                if (isinstance(forwarded, dict)
                        and str(forwarded.get(CONF_ID)) == str(config[CONF_ID])
                        and forwarded.get(CONF_EVENT) == expected):
                    raise cv.Invalid(
                        f"{source}.{hook} already forwards {expected}; remove that forwarding "
                        f"when enabling observe.{source}"
                    )
            target[hook][CONF_THEN] = addition[CONF_THEN] + target[hook][CONF_THEN]
        else:
            target[hook] = addition
        attachments.add(key)
    return config


def _has_presentation(config):
    return config.get(CONF_PROFILE) == PROFILE_PRESENTATION or CONF_PRESENTATION in config


def _with_presentation(activities, *, simple=False):
    result = deepcopy(activities)
    for name, activity in result.items():
        policies = activity.setdefault(CONF_POLICIES, {})
        value = policies.get(LED_POLICY)
        if value is not None:
            policies[CONF_PRESENTATION] = (
                "announcement" if name == "announcement"
                else PRESENTATION_ALIASES.get(value, value)
            )
        if simple:
            activity[CONF_POLICIES] = {
                key: value for key, value in policies.items()
                if key in (CONF_PRESENTATION, LED_POLICY, "display_status")
            }
    return result


def _presentation_profile(config):
    """Observe facts without requesting voice/media control operations."""
    activities, groups, derived, events = _selected_profile(config)
    observed = config[CONF_OBSERVE]
    remove = {"boot"}
    for source, activity in ((CONF_WIFI, "no_wifi"), ("api", "no_ha"),
                             (CONF_MICROPHONE_MUTE, "mic_muted"),
                             (CONF_SPEAKER_MUTE, "speaker_muted")):
        if not observed.get(source):
            remove.add(activity)
    if not (observed.get(CONF_MICROPHONE_MUTE) and observed.get(CONF_SPEAKER_MUTE)):
        remove.add("both_muted")
    activities = {k: v for k, v in activities.items() if k not in remove}
    names = set(activities)
    groups = {k: [v for v in values if v in names] for k, values in groups.items()}
    derived = [v for v in derived if v[CONF_NAME] in names]
    filtered = {}
    for name, event in events.items():
        if name in ("wake_word", "manual_voice_toggle", "voice_stop", "voice_quiet"):
            continue
        event = deepcopy(event)
        for rule in [event, *event.get(CONF_CASES, [])]:
            rule.pop(CONF_ACTION, None)
            for key in (CONF_ANY, CONF_ALL, CONF_NONE, CONF_ACTIVATE, CONF_DEACTIVATE):
                if key in rule:
                    rule[key] = [v for v in _as_list(rule[key]) if v in names]
        filtered[name] = event
    return _with_presentation(activities, simple=True), groups, derived, filtered


def _voip_states(config):
    if _has_presentation(config):
        return _with_presentation(FULL_VOICE_VOIP_VOIP_STATES,
                                  simple=config.get(CONF_PROFILE) == PROFILE_PRESENTATION)
    return FULL_VOICE_VOIP_VOIP_STATES


def _merged_runtime_config(config):
    profile_full = config.get(CONF_PROFILE) in (PROFILE_FULL_VOICE_VOIP, PROFILE_PRESENTATION)
    base_activities, base_groups, base_derived, base_events = (
        _presentation_profile(config) if config.get(CONF_PROFILE) == PROFILE_PRESENTATION
        else _selected_profile(config) if profile_full else ({}, {}, [], {})
    )
    activities = dict(base_activities)
    activities.update(config[CONF_ACTIVITIES])
    groups = {key: list(value) for key, value in base_groups.items()}
    for group, values in config[CONF_GROUPS].items():
        groups.setdefault(group, []).extend(values)
    derived = list(base_derived) + list(config[CONF_DERIVED_ACTIVITIES])
    events = dict(base_events)
    events.update(config[CONF_EVENTS])
    if _has_presentation(config):
        activities = _with_presentation(activities)
    return profile_full, activities, groups, derived, events


def _validate_runtime_controller(config):
    profile_full, activities, groups, derived, events = _merged_runtime_config(config)

    if not profile_full and CONF_FEATURES in config:
        raise cv.Invalid(
            "runtime_controller features requires profile: full_voice_voip"
        )
    if not profile_full and CONF_VOIP_STACK in config[CONF_OBSERVE]:
        raise cv.Invalid(
            "observe.voip_stack requires profile: full_voice_voip; use the voip block for custom state mappings"
        )

    generated_voip_names: set[str] = set()
    if profile_full and CONF_VOIP_STACK in config[CONF_OBSERVE]:
        generated_voip_names.update(
            f"voip:{state}" for state in FULL_VOICE_VOIP_VOIP_STATES
        )
    if CONF_VOIP in config:
        if profile_full and CONF_VOIP_STACK in config[CONF_OBSERVE]:
            raise cv.Invalid(
                "runtime_controller cannot configure both profile observe.voip_stack and voip"
            )
        voip_conf = config[CONF_VOIP]
        if voip_conf[CONF_STATES] and not voip_conf[CONF_ACTIVITY_PREFIX]:
            raise cv.Invalid(
                "runtime_controller voip activity_prefix must not be empty"
            )
        generated_voip_names.update(
            f"{voip_conf[CONF_ACTIVITY_PREFIX]}{state}"
            for state in voip_conf[CONF_STATES]
        )
    oversized_voip_names = [
        name for name in generated_voip_names if len(name.encode("utf-8")) > 63
    ]
    if oversized_voip_names:
        raise cv.Invalid(
            "runtime_controller VoIP activity names must fit in 63 UTF-8 bytes: "
            + ", ".join(sorted(oversized_voip_names))
        )
    collisions = generated_voip_names & set(activities)
    if collisions:
        raise cv.Invalid(
            "runtime_controller duplicate VoIP activities: "
            + ", ".join(sorted(collisions))
        )

    activity_names = set(activities) | generated_voip_names
    if len(activity_names) > 32:
        raise cv.Invalid(
            f"runtime_controller supports at most 32 activities, got {len(activity_names)}"
        )
    if any(not str(name).strip() for name in activity_names):
        raise cv.Invalid("runtime_controller activity names must not be empty")

    group_owner: dict[str, str] = {}
    for group, members in groups.items():
        if not group.strip():
            raise cv.Invalid("runtime_controller group names must not be empty")
        for activity in members:
            if activity not in activity_names:
                raise cv.Invalid(
                    f"runtime_controller group '{group}' references unknown activity '{activity}'"
                )
            previous = group_owner.setdefault(activity, group)
            if previous != group:
                raise cv.Invalid(
                    f"runtime_controller activity '{activity}' belongs to multiple groups: '{previous}', '{group}'"
                )

    for group, members in groups.items():
        initial = [
            name
            for name in set(members)
            if activities.get(name, {}).get(CONF_INITIAL, False)
        ]
        if len(initial) > 1:
            raise cv.Invalid(
                f"runtime_controller group '{group}' has multiple initially active members"
            )
    if len(derived) > 16:
        raise cv.Invalid(
            f"runtime_controller supports at most 16 derived activities, got {len(derived)}"
        )
    derived_names = [item[CONF_NAME] for item in derived]
    if len(set(derived_names)) != len(derived_names):
        raise cv.Invalid("runtime_controller derived activity targets must be unique")
    grouped_derived = set(derived_names) & set(group_owner)
    if grouped_derived:
        raise cv.Invalid(
            "runtime_controller derived activities cannot belong to exclusive groups: "
            + ", ".join(sorted(grouped_derived))
        )
    unknown_targets = set(derived_names) - activity_names
    if unknown_targets:
        raise cv.Invalid(
            "runtime_controller derived targets are unknown: "
            + ", ".join(sorted(unknown_targets))
        )
    derived_graph: dict[str, set[str]] = {}
    for item in derived:
        when = item.get(CONF_WHEN, {})
        refs = (
            list(when.get(CONF_ANY_ACTIVE, []))
            + list(when.get(CONF_ALL_ACTIVE, []))
            + list(when.get(CONF_NONE_ACTIVE, []))
        )
        if any(
            len(when.get(key, [])) > 8
            for key in (CONF_ANY_ACTIVE, CONF_ALL_ACTIVE, CONF_NONE_ACTIVE)
        ):
            raise cv.Invalid(
                f"runtime_controller derived activity '{item[CONF_NAME]}' has more than 8 conditions"
            )
        unknown = set(refs) - activity_names
        if unknown:
            raise cv.Invalid(
                f"runtime_controller derived activity '{item[CONF_NAME]}' references unknown activities: "
                + ", ".join(sorted(unknown))
            )
        derived_graph[item[CONF_NAME]] = set(refs) & set(derived_names)

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(name: str) -> None:
        if name in visiting:
            raise cv.Invalid(
                f"runtime_controller derived activity cycle includes '{name}'"
            )
        if name in visited:
            return
        visiting.add(name)
        for dependency in derived_graph.get(
            name, ()
        ):  # pragma: no branch - bounded graph
            visit(dependency)
        visiting.remove(name)
        visited.add(name)

    for name in derived_graph:
        visit(name)

    action_names = set(config[CONF_ACTIONS])
    if any(not name.strip() for name in action_names):
        raise cv.Invalid("runtime_controller action names must not be empty")
    if any(not name.strip() for name in events):
        raise cv.Invalid("runtime_controller event names must not be empty")
    oversized_event_names = [name for name in events if len(name.encode("utf-8")) > 47]
    if oversized_event_names:
        raise cv.Invalid(
            "runtime_controller event names must fit in 47 UTF-8 bytes: "
            + ", ".join(sorted(oversized_event_names))
        )
    event_then_names = {
        name for name, event_conf in events.items() if CONF_THEN in event_conf
    }
    action_collisions = event_then_names & action_names
    if action_collisions:
        raise cv.Invalid(
            "runtime_controller event 'then' names must not collide with top-level actions: "
            + ", ".join(sorted(action_collisions))
        )
    for event_name, event_conf in events.items():
        rules = list(event_conf.get(CONF_CASES, []))
        if (
            event_conf.get(CONF_ACTIVATE)
            or event_conf.get(CONF_DEACTIVATE)
            or event_conf.get(CONF_ACTION)
        ):
            rules.append(event_conf)
        for rule in rules:
            refs = (
                _as_list(rule.get(CONF_ANY, []))
                + _as_list(rule.get(CONF_ALL, []))
                + _as_list(rule.get(CONF_NONE, []))
                + _as_list(rule.get(CONF_ACTIVATE, []))
                + _as_list(rule.get(CONF_DEACTIVATE, []))
            )
            unknown = set(refs) - activity_names
            if unknown:
                raise cv.Invalid(
                    f"runtime_controller event '{event_name}' references unknown activities: "
                    + ", ".join(sorted(unknown))
                )
            if any(
                len(_as_list(rule.get(key, []))) > 8
                for key in (CONF_ANY, CONF_ALL, CONF_NONE)
            ):
                raise cv.Invalid(
                    f"runtime_controller event '{event_name}' has more than 8 conditions"
                )
            if (
                len(_as_list(rule.get(CONF_ACTIVATE, [])))
                + len(_as_list(rule.get(CONF_DEACTIVATE, [])))
                > 16
            ):
                raise cv.Invalid(
                    f"runtime_controller event '{event_name}' has more than 16 updates in one rule"
                )
            action = rule.get(CONF_ACTION, "")
            if action and action not in action_names:
                raise cv.Invalid(
                    f"runtime_controller event '{event_name}' references unknown action '{action}'"
                )
    event_rule_count = _event_rule_count(events)
    if event_rule_count > 64:
        raise cv.Invalid(
            f"runtime_controller supports at most 64 event rules, got {event_rule_count}"
        )
    if len(action_names) > 16:
        raise cv.Invalid(
            f"runtime_controller supports at most 16 actions, got {len(action_names)}"
        )
    event_triggers = sum(CONF_THEN in event_conf for event_conf in events.values())
    if event_triggers > 16:
        raise cv.Invalid(
            f"runtime_controller supports at most 16 event triggers, got {event_triggers}"
        )

    all_activity_configs = list(activities.values())
    if profile_full and CONF_VOIP_STACK in config[CONF_OBSERVE]:
        all_activity_configs.extend(_voip_states(config).values())
    if CONF_VOIP in config:
        all_activity_configs.extend(config[CONF_VOIP][CONF_STATES].values())
    policy_names: set[str] = set()
    for activity in all_activity_configs:
        policies = activity.get(CONF_POLICIES, {})
        if len(policies) > 8:
            raise cv.Invalid(
                "runtime_controller supports at most 8 policies per activity"
            )
        empty_policy = next((name for name in policies if not name.strip()), None)
        if empty_policy is not None:
            raise cv.Invalid("runtime_controller policy names must not be empty")
        empty_value = next(
            (value for value in policies.values() if not value.strip()), None
        )
        if empty_value is not None:
            raise cv.Invalid("runtime_controller policy values must not be empty")
        policy_names.update(policies)
    if len(policy_names) > 8:
        raise cv.Invalid(
            f"runtime_controller supports at most 8 resolved policies, got {len(policy_names)}"
        )

    configured_policies = config[CONF_POLICIES]
    if _has_presentation(config):
        available = {item.get(CONF_POLICIES, {}).get(CONF_PRESENTATION) for item in all_activity_configs}
        requested = set(config.get(CONF_PRESENTATION, {}).get(CONF_PRIORITIES, {}))
        requested.update(configured_policies.get(CONF_PRESENTATION, {}).get(CONF_VALUES, {}))
        missing = requested - available
        if missing:
            raise cv.Invalid("Presentation states have no observed or configured activity: "
                             + ", ".join(sorted(missing)))
    if any(not policy.strip() for policy in configured_policies):
        raise cv.Invalid("runtime_controller configured policy names must not be empty")
    if any(
        not value.strip()
        for policy_conf in configured_policies.values()
        for value in policy_conf[CONF_VALUES]
    ):
        raise cv.Invalid(
            "runtime_controller configured policy values must not be empty"
        )
    policy_global_output_count = sum(
        CONF_OUTPUT in item for item in configured_policies.values()
    )
    if policy_global_output_count > 8:
        raise cv.Invalid(
            "runtime_controller supports at most 8 policy global outputs, "
            f"got {policy_global_output_count}"
        )
    policy_change_trigger_count = sum(
        CONF_ON_CHANGE in item for item in configured_policies.values()
    )
    if policy_change_trigger_count > 8:
        raise cv.Invalid(
            "runtime_controller supports at most 8 policy change triggers, "
            f"got {policy_change_trigger_count}"
        )
    policy_output_count = 0
    policy_value_action_count = 0
    for policy_conf in configured_policies.values():
        for value_conf in policy_conf[CONF_VALUES].values():
            if isinstance(value_conf, int):
                policy_output_count += 1
                continue
            if CONF_VALUE in value_conf:
                policy_output_count += 1
            if CONF_THEN in value_conf:
                policy_value_action_count += 1
    if policy_output_count > 64:
        raise cv.Invalid(
            f"runtime_controller supports at most 64 policy value outputs, got {policy_output_count}"
        )
    if policy_value_action_count > 32:
        raise cv.Invalid(
            f"runtime_controller supports at most 32 policy value actions, got {policy_value_action_count}"
        )

    if (
        CONF_LED in config[CONF_OUTPUTS]
        and len(_merged_led_states(config[CONF_OUTPUTS][CONF_LED])) > 32
    ):
        raise cv.Invalid("runtime_controller supports at most 32 LED states")
    return config


CONFIG_SCHEMA = cv.All(
    cv.require_esphome_version(2026, 10, 0),
    _prepare_presentation,
    cv.Schema(
        {
            cv.GenerateID(): cv.declare_id(RuntimeController),
            cv.GenerateID("observers_id"): cv.declare_id(RuntimeNetworkObservers),
            cv.Optional(CONF_DEBUG, default=False): cv.boolean,
            cv.Optional(
                CONF_STORAGE_IN_PSRAM, default=False
            ): _validate_storage_in_psram,
            cv.Optional(CONF_PROFILE): cv.one_of(PROFILE_FULL_VOICE_VOIP, PROFILE_PRESENTATION, lower=True),
            cv.Optional(CONF_PRESENTATION): cv.Schema({
                cv.Optional(CONF_PRIORITIES, default={}): cv.Schema({
                    cv.one_of(*PRESENTATION_NAMES): cv.int_range(min=-32768, max=32767),
                }),
                cv.Optional(CONF_ON_CHANGE): ACTION_TRIGGER_SCHEMA,
            }),
            cv.Optional(CONF_FEATURES): cv.ensure_list(cv.one_of(*PROFILE_FEATURES)),
            cv.Optional(CONF_OBSERVE, default={}): cv.Schema(
                {
                    cv.Optional(CONF_VOIP_STACK): cv.use_id(VoipStack),
                    cv.Optional(CONF_MEDIA_PLAYER): cv.use_id(media_player.MediaPlayer),
                    cv.Optional(CONF_VOICE_ASSISTANT): cv.use_id(VoiceAssistant),
                    cv.Optional(CONF_MICRO_WAKE_WORD): cv.use_id(MicroWakeWord),
                    cv.Optional(CONF_TIMERS): cv.use_id(VoiceAssistant),
                    cv.Optional(CONF_API, default=False): cv.boolean,
                    cv.Optional(CONF_WIFI, default=False): cv.boolean,
                    cv.Optional(CONF_MICROPHONE_MUTE): cv.use_id(switch.Switch),
                    cv.Optional(CONF_SPEAKER_MUTE): cv.use_id(switch.Switch),
                }
            ),
            cv.Optional(CONF_OBSERVER_BINDINGS, default=[]): cv.ensure_list(cv.Schema({
                cv.Required("source"): cv.one_of(*SOURCE_HOOKS),
                cv.Required("hook"): cv.string_strict,
                cv.Required("automation"): ACTION_TRIGGER_SCHEMA,
            })),
            cv.Optional(CONF_OUTPUTS, default={}): cv.Schema(
                {
                    cv.Optional(CONF_LED): LED_OUTPUT_SCHEMA,
                },
                extra=cv.ALLOW_EXTRA,
            ),
            cv.Optional(CONF_OUTPUT_SCRIPT): cv.use_id(script.Script),
            cv.Optional(CONF_STATE_OUTPUTS, default={}): cv.Schema(
                {
                    cv.Optional(CONF_ACTIVITY_MASK): cv.use_id(
                        globals_component.GlobalsComponent
                    ),
                    cv.Optional(CONF_SEQUENCE): cv.use_id(
                        globals_component.GlobalsComponent
                    ),
                    cv.Optional("api_clients"): cv.use_id(globals_component.GlobalsComponent),
                }
            ),
            cv.Optional(CONF_VOIP): cv.Schema(
                {
                    cv.Required(CONF_ID): cv.use_id(VoipStack),
                    cv.Optional(
                        CONF_ACTIVITY_PREFIX, default="voip:"
                    ): cv.string_strict,
                    cv.Optional(CONF_STATES, default={}): cv.Schema(
                        {cv.string_strict: ACTIVITY_BODY_SCHEMA}
                    ),
                }
            ),
            cv.Optional(CONF_ACTIVITIES, default={}): ACTIVITIES_SCHEMA,
            cv.Optional(CONF_GROUPS, default={}): GROUPS_SCHEMA,
            cv.Optional(CONF_AUTO_EVENTS, default=True): cv.boolean,
            cv.Optional(CONF_DERIVED_ACTIVITIES, default=[]): cv.ensure_list(
                DERIVED_ACTIVITY_SCHEMA
            ),
            cv.Optional(CONF_EVENTS, default={}): cv.Schema(
                {cv.string_strict: EVENT_SCHEMA}
            ),
            cv.Optional(CONF_ACTIONS, default={}): cv.Schema(
                {cv.string_strict: ACTION_TRIGGER_SCHEMA}
            ),
            cv.Optional(CONF_POLICIES, default={}): cv.Schema(
                {cv.string_strict: POLICY_SCHEMA}
            ),
        }
    ).extend(cv.COMPONENT_SCHEMA),
    _validate_runtime_controller,
)

FINAL_VALIDATE_SCHEMA = _attach_source_observers


def _event_rule_count(events):
    """Count the rules after profile/observer expansion, as codegen emits them."""
    return sum(
        len(event.get(CONF_CASES, []))
        + bool(event.get(CONF_ACTIVATE) or event.get(CONF_DEACTIVATE) or event.get(CONF_ACTION))
        for event in events.values()
    )


def _ordered_activities(config, profile_full, activities):
    """One index order for emitted activities and immutable rule references."""
    ordered = []
    if profile_full and CONF_VOIP_STACK in config[CONF_OBSERVE]:
        ordered.extend((f"voip:{name}", activity) for name, activity in _voip_states(config).items())
    if CONF_VOIP in config:
        voip = config[CONF_VOIP]
        ordered.extend((voip[CONF_ACTIVITY_PREFIX] + name, activity)
                       for name, activity in voip[CONF_STATES].items())
    ordered.extend(activities.items())
    return ordered


def _storage_capacities(config, ordered, activities, derived, events):
    policies = config[CONF_POLICIES]
    values = [value for policy in policies.values() for value in policy[CONF_VALUES].values()]
    led = config[CONF_OUTPUTS].get(CONF_LED)
    return (
        len(ordered), len(config[CONF_ACTIONS]),
        sum(CONF_THEN in event for event in events.values()),
        len(activities) if config[CONF_AUTO_EVENTS] else 0, len(derived),
        sum(isinstance(value, dict) and CONF_THEN in value for value in values),
        sum(isinstance(value, int) or CONF_VALUE in value for value in values),
        sum(CONF_ON_CHANGE in policy for policy in policies.values()),
        sum(CONF_OUTPUT in policy for policy in policies.values()),
        len(_merged_led_states(led)) if led is not None else 0,
    )


def _emit_static_rules(var, config, ordered, events):
    """Emit constant, indexed rules; update order preserves exclusive-group semantics."""
    prefix = f"{config[CONF_ID].id}_rules"
    indices = {name: index for index, (name, _) in enumerate(ordered)}
    rows = []
    for name, event in events.items():
        rules = list(event.get(CONF_CASES, []))
        if event.get(CONF_ACTIVATE) or event.get(CONF_DEACTIVATE) or event.get(CONF_ACTION):
            rules.append(event)
        for rule in rules:
            updates = [(indices[activity], True) for activity in _as_list(rule.get(CONF_ACTIVATE, []))]
            updates += [(indices[activity], False) for activity in _as_list(rule.get(CONF_DEACTIVATE, []))]
            conditions = [_as_list(rule.get(key, [])) for key in (CONF_ANY, CONF_ALL, CONF_NONE)]
            suffix = str(len(rows))
            update_name = f"{prefix}_updates_{suffix}" if updates else "nullptr"
            condition_name = f"{prefix}_conditions_{suffix}" if any(conditions) else "nullptr"
            if updates:
                content = ", ".join(f"{{{index}, {'true' if active else 'false'}}}" for index, active in updates)
                cg.add_global(cg.RawStatement(
                    f"static constexpr runtime_controller::RuntimeController::IndexedUpdate {update_name}[] = {{{content}}};"))
            if any(conditions):
                content = ", ".join(str(indices[activity]) for group in conditions for activity in group)
                cg.add_global(cg.RawStatement(f"static constexpr uint8_t {condition_name}[] = {{{content}}};"))
            rows.append("{" + ", ".join((str(cg.safe_exp(name)), str(cg.safe_exp(rule.get(CONF_ACTION, ""))),
                         update_name, condition_name, str(len(updates)), *(str(len(group)) for group in conditions))) + "}")
    if rows:
        cg.add_global(cg.RawStatement(
            f"static constexpr runtime_controller::RuntimeController::StaticEventRule {prefix}[] = {{" + ", ".join(rows) + "};"))
        cg.add(var.set_static_event_rules(cg.RawExpression(prefix), len(rows)))


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    profile_full, activities, groups, derived_activities, events = _merged_runtime_config(config)
    ordered = _ordered_activities(config, profile_full, activities)
    capacities = _storage_capacities(config, ordered, activities, derived_activities, events)
    cg.add(var.set_event_rule_capacity(0))
    cg.add(var.set_storage_capacities(cg.RawExpression(
        "runtime_controller::RuntimeController::StorageCapacities{" + ", ".join(map(str, capacities)) + "}")))
    cg.add(var.set_storage_in_psram(config[CONF_STORAGE_IN_PSRAM]))
    cg.add(var.set_debug(config[CONF_DEBUG]))
    if config[CONF_DEBUG]:
        cg.add_define("USE_RUNTIME_CONTROLLER_DEBUG")
    presentation = config.get(CONF_PRESENTATION, {})
    if presentation.get(CONF_PRIORITIES):
        cg.add_define("USE_RUNTIME_CONTROLLER_PRESENTATION_PRIORITY")
    if CONF_ON_CHANGE in presentation:
        cg.add_define("USE_RUNTIME_CONTROLLER_PRESENTATION_TRIGGER")
        action = presentation[CONF_ON_CHANGE]
        trigger = cg.new_Pvariable(action[automation.CONF_TRIGGER_ID],
                                   cg.TemplateArguments(cg.std_string, cg.std_string))
        cg.add(var.set_presentation_trigger(trigger))
        await automation.build_automation(
            trigger, [(cg.std_string, "previous"), (cg.std_string, "current")], action
        )

    voip_states = dict(_voip_states(config)) if profile_full else {}

    if CONF_OUTPUT_SCRIPT in config:
        cg.add_define("USE_RUNTIME_CONTROLLER_OUTPUT_SCRIPT")
        output_script = await cg.get_variable(config[CONF_OUTPUT_SCRIPT])
        cg.add(var.set_output_script(output_script))

    state_outputs = config[CONF_STATE_OUTPUTS]
    if CONF_ACTIVITY_MASK in state_outputs:
        full_id, output = await cg.get_variable_with_full_id(
            state_outputs[CONF_ACTIVITY_MASK]
        )
        template_arg = cg.TemplateArguments(full_id.type)
        cg.add(var.set_activity_mask_output.template(template_arg)(output))
    if CONF_SEQUENCE in state_outputs:
        full_id, output = await cg.get_variable_with_full_id(
            state_outputs[CONF_SEQUENCE]
        )
        template_arg = cg.TemplateArguments(full_id.type)
        cg.add(var.set_sequence_output.template(template_arg)(output))

    outputs = config[CONF_OUTPUTS]
    if CONF_LED in outputs:
        cg.add_define("USE_RUNTIME_CONTROLLER_LED")
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

    observed = config[CONF_OBSERVE]
    source_events = any(observed.get(key) for key in SOURCE_HOOKS)
    if source_events or observed.get(CONF_WIFI) or any(
        key in observed
        for key in (CONF_MICROPHONE_MUTE, CONF_SPEAKER_MUTE, CONF_MEDIA_PLAYER)
    ):
        observer = cg.new_Pvariable(config["observers_id"])
        await cg.register_component(observer, config)
        cg.add(observer.set_runtime(var))
        if source_events:
            cg.add_define("USE_RUNTIME_CONTROLLER_SOURCE_EVENTS")
        if observed.get(CONF_VOICE_ASSISTANT) or observed.get(CONF_TIMERS):
            cg.add_define("USE_RUNTIME_CONTROLLER_VOICE_ASSISTANT")
            source = observed.get(CONF_VOICE_ASSISTANT) or observed[CONF_TIMERS]
            cg.add(observer.set_voice_assistant(await cg.get_variable(source),
                                                CONF_VOICE_ASSISTANT in observed, CONF_TIMERS in observed))
        if observed.get(CONF_API):
            cg.add_define("USE_RUNTIME_CONTROLLER_API")
            if "api_clients" in state_outputs:
                cg.add_define("USE_RUNTIME_CONTROLLER_API_CLIENT_OUTPUT")
                cg.add(observer.set_api_clients_output(await cg.get_variable(state_outputs["api_clients"])))
        if observed.get(CONF_WIFI):
            wifi.request_wifi_connect_state_listener()
            cg.add_define("USE_RUNTIME_CONTROLLER_WIFI")
            cg.add(observer.set_wifi(wifi.wifi_ns.global_wifi_component))
        for key, setter in (
            (CONF_MICROPHONE_MUTE, "set_microphone_mute"),
            (CONF_SPEAKER_MUTE, "set_speaker_mute"),
            (CONF_MEDIA_PLAYER, "set_media_player"),
        ):
            if key in observed:
                cg.add_define(
                    "USE_RUNTIME_CONTROLLER_MEDIA_PLAYER"
                    if key == CONF_MEDIA_PLAYER
                    else f"USE_RUNTIME_CONTROLLER_{key.upper()}"
                )
                cg.add(getattr(observer, setter)(await cg.get_variable(observed[key])))

    if CONF_VOIP in config:
        voip_conf = config[CONF_VOIP]
        voip = await cg.get_variable(voip_conf[CONF_ID])
        cg.add(var.set_voip(voip))
        cg.add(var.set_voip_activity_prefix(voip_conf[CONF_ACTIVITY_PREFIX]))
        cg.add_define("USE_RUNTIME_CONTROLLER_VOIP")

    for name, activity in ordered:
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

    if presentation.get(CONF_PRIORITIES):
        candidates = dict(activities)
        if profile_full and CONF_VOIP_STACK in config[CONF_OBSERVE]:
            candidates.update({f"voip:{state}": item for state, item in voip_states.items()})
        if CONF_VOIP in config:
            custom = config[CONF_VOIP]
            candidates.update({custom[CONF_ACTIVITY_PREFIX] + state: item
                               for state, item in custom[CONF_STATES].items()})
        for name, activity in candidates.items():
            state = activity.get(CONF_POLICIES, {}).get(CONF_PRESENTATION)
            if state in presentation[CONF_PRIORITIES]:
                cg.add(var.set_activity_presentation_priority(name, presentation[CONF_PRIORITIES][state]))

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

    _emit_static_rules(var, config, ordered, events)
    for name, event_conf in events.items():
        if CONF_THEN in event_conf:
            trigger = cg.new_Pvariable(
                event_conf[CONF_THEN][automation.CONF_TRIGGER_ID],
                cg.TemplateArguments(),
            )
            cg.add(var.add_event_trigger(name, trigger))
            await automation.build_automation(trigger, [], event_conf[CONF_THEN])

    for name, action_conf in config[CONF_ACTIONS].items():
        trigger = cg.new_Pvariable(
            action_conf[automation.CONF_TRIGGER_ID], cg.TemplateArguments()
        )
        cg.add(var.add_action_trigger(name, trigger))
        await automation.build_automation(trigger, [], action_conf)

    for policy, policy_conf in config[CONF_POLICIES].items():
        if CONF_OUTPUT in policy_conf:
            full_id, output = await cg.get_variable_with_full_id(
                policy_conf[CONF_OUTPUT]
            )
            template_arg = cg.TemplateArguments(full_id.type)
            cg.add(var.add_policy_global_output.template(template_arg)(policy, output))
        if CONF_ON_CHANGE in policy_conf:
            trigger = cg.new_Pvariable(
                policy_conf[CONF_ON_CHANGE][automation.CONF_TRIGGER_ID],
                cg.TemplateArguments(cg.int32),
            )
            cg.add(var.set_policy_change_trigger(policy, trigger))
            await automation.build_automation(
                trigger, [(cg.int32, "value")], policy_conf[CONF_ON_CHANGE]
            )
        for value, action_conf in policy_conf[CONF_VALUES].items():
            if isinstance(action_conf, int):
                cg.add(var.add_policy_output(policy, value, action_conf))
                continue
            if CONF_VALUE in action_conf:
                cg.add(var.add_policy_output(policy, value, action_conf[CONF_VALUE]))
            if CONF_THEN in action_conf:
                trigger = cg.new_Pvariable(
                    action_conf[automation.CONF_TRIGGER_ID], cg.TemplateArguments()
                )
                cg.add(var.add_policy_value_trigger(policy, value, trigger))
                await automation.build_automation(trigger, [], action_conf)


async def _new_parented_action(config, action_id, template_arg):
    var = cg.new_Pvariable(action_id, template_arg)
    await cg.register_parented(var, config[CONF_ID])
    return var


@automation.register_action(
    "runtime_controller.source_event", SourceEventAction,
    cv.Schema({
        cv.GenerateID(): cv.use_id(RuntimeNetworkObservers),
        cv.Required("event"): cv.string_strict,
        cv.Optional("text", default=""): cv.templatable(cv.string),
        cv.Optional("enabled", default=True): cv.templatable(cv.boolean),
    }), synchronous=True,
)
async def source_event_to_code(config, action_id, template_arg, args):
    var = cg.new_Pvariable(action_id, template_arg)
    await cg.register_parented(var, config[CONF_ID])
    cg.add(var.set_event(config["event"]))
    cg.add(var.set_text(await cg.templatable(config["text"], args, cg.std_string)))
    cg.add(var.set_enabled(await cg.templatable(config["enabled"], args, cg.bool_)))
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
