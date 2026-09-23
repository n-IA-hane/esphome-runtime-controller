"""Reject configurations for which the runtime cannot preserve its invariants."""

import pytest

from test_runtime_controller_contract import _load_component_module, _minimal_config


def test_group_rejects_multiple_initial_members():
    module = _load_component_module()
    config = _minimal_config(module)
    config[module.CONF_ACTIVITIES] = {
        "listening": {module.CONF_INITIAL: True},
        "responding": {module.CONF_INITIAL: True},
    }
    config[module.CONF_GROUPS] = {"voice_phase": ["listening", "responding"]}
    with pytest.raises(module.cv.Invalid, match="multiple initially active members"):
        module._validate_runtime_controller(config)


def test_group_accepts_one_initial_member_and_duplicate_membership():
    module = _load_component_module()
    config = _minimal_config(module)
    config[module.CONF_ACTIVITIES] = {
        "listening": {module.CONF_INITIAL: True},
        "responding": {module.CONF_INITIAL: False},
    }
    config[module.CONF_GROUPS] = {
        "voice_phase": ["listening", "listening", "responding"]
    }
    assert module._validate_runtime_controller(config) is config


def test_group_rejects_derived_member():
    module = _load_component_module()
    config = _minimal_config(module)
    config[module.CONF_ACTIVITIES] = {"a": {}, "b": {}, "condition": {}}
    config[module.CONF_GROUPS] = {"phase": ["a", "b"]}
    config[module.CONF_DERIVED_ACTIVITIES] = [
        {
            module.CONF_NAME: "b",
            module.CONF_WHEN: {module.CONF_ALL_ACTIVE: ["condition"]},
        }
    ]
    with pytest.raises(module.cv.Invalid, match="cannot belong to exclusive groups"):
        module._validate_runtime_controller(config)


def test_ungrouped_derived_activity_remains_supported():
    module = _load_component_module()
    config = _minimal_config(module)
    config[module.CONF_ACTIVITIES] = {"a": {}, "b": {}, "condition": {}}
    config[module.CONF_GROUPS] = {"phase": ["a"]}
    config[module.CONF_DERIVED_ACTIVITIES] = [
        {
            module.CONF_NAME: "b",
            module.CONF_WHEN: {module.CONF_ALL_ACTIVE: ["condition"]},
        }
    ]
    assert module._validate_runtime_controller(config) is config


def test_observe_voip_without_profile_is_not_ignored():
    module = _load_component_module()
    config = _minimal_config(module)
    config[module.CONF_OBSERVE] = {"voip_stack": "phone"}
    with pytest.raises(module.cv.Invalid, match="use the voip block"):
        module._validate_runtime_controller(config)


@pytest.mark.parametrize(
    "features",
    [[], ["media_player"], ["voice_assistant"], ["voice_assistant", "media_player"]],
)
def test_feature_selection_needs_only_selected_actions(features):
    module = _load_component_module()
    config = _minimal_config(module)
    config[module.CONF_PROFILE] = module.PROFILE_FULL_VOICE_VOIP
    config[module.CONF_FEATURES] = features
    if "voice_assistant" in features:
        config[module.CONF_ACTIONS] = {
            key: {}
            for key in (
                "voice_start",
                "voice_cancel_response",
                "voice_cancel_pipeline",
                "voice_stop_all",
                "voice_stop_pipeline",
                "cancel_response_cleanup",
                "stop_announcement",
            )
        }
    module._validate_runtime_controller(config)
    _, activities, _, _, _ = module._merged_runtime_config(config)
    assert ("va_responding" in activities) == ("voice_assistant" in features)
    assert ("media" in activities) == ("media_player" in features)
    assert "timer_ringing" not in activities
