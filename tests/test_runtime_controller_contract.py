#!/usr/bin/env python3
"""Contracts for deterministic bounded runtime reduction."""

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "esphome" / "components" / "runtime_controller"


def _load_component_module():
    spec = importlib.util.spec_from_file_location(
        "runtime_controller_external", COMPONENT / "__init__.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _minimal_config(module):
    return {
        module.CONF_ACTIVITIES: {},
        module.CONF_GROUPS: {},
        module.CONF_DERIVED_ACTIVITIES: [],
        module.CONF_EVENTS: {},
        module.CONF_ACTIONS: {},
        module.CONF_POLICIES: {},
        module.CONF_OBSERVE: {},
        module.CONF_OUTPUTS: {},
        module.CONF_AUTO_EVENTS: True,
    }


def test_derived_activities_resolve_to_a_fixed_point() -> None:
    cpp = (COMPONENT / "runtime_controller.cpp").read_text(encoding="utf-8")
    body = cpp[
        cpp.index("bool RuntimeController::apply_derived_activities_()") :
        cpp.index("\nvoid RuntimeController::publish_outputs_()")
    ]
    assert "for (size_t pass = 0; pass < this->derived_activity_count_; pass++)" in body
    assert "if (!pass_changed)" in body


def test_removed_policies_reset_outputs() -> None:
    cpp = (COMPONENT / "runtime_controller.cpp").read_text(encoding="utf-8")
    body = cpp[
        cpp.index("void RuntimeController::run_policy_actions_(") :
        cpp.index("\nvoid RuntimeController::apply_led_state_")
    ]
    assert "find_policy_value(new_policies, policy, nullptr) == nullptr" in body
    assert "apply_change(policy, nullptr);" in body
    assert 'value != nullptr ? value : "(unset)"' in body


def test_schema_rejects_unknown_overflowing_and_cyclic_graphs() -> None:
    init = (COMPONENT / "__init__.py").read_text(encoding="utf-8")
    assert "def _validate_runtime_controller(config):" in init
    assert "derived activity cycle" in init
    assert "references unknown activities" in init
    assert "supports at most 32 activities" in init
    assert "supports at most 8 resolved policies" in init
    assert "supports at most 8 policy global outputs" in init
    assert "supports at most 8 policy change triggers" in init
    assert "supports at most 64 policy value outputs" in init
    assert "supports at most 32 policy value actions" in init
    assert "CONFIG_SCHEMA = cv.All" in init


def test_policy_table_validation_counts_only_bounded_bindings() -> None:
    module = _load_component_module()
    config = _minimal_config(module)
    config[module.CONF_POLICIES] = {
        f"policy_{index}": {module.CONF_VALUES: {}} for index in range(9)
    }

    # Policy declarations without a global output or on_change trigger do not
    # consume either of the two eight-entry C++ binding arrays.
    assert module._validate_runtime_controller(config) is config

    config[module.CONF_POLICIES] = {
        f"policy_{index}": {module.CONF_VALUES: {}, module.CONF_OUTPUT: object()}
        for index in range(9)
    }
    with pytest.raises(module.cv.Invalid, match="policy global outputs"):
        module._validate_runtime_controller(config)

    config[module.CONF_POLICIES] = {
        f"policy_{index}": {module.CONF_VALUES: {}, module.CONF_ON_CHANGE: object()}
        for index in range(9)
    }
    with pytest.raises(module.cv.Invalid, match="policy change triggers"):
        module._validate_runtime_controller(config)


def test_queued_templates_are_canonicalized_and_drained_in_bounded_batches() -> None:
    cpp = (COMPONENT / "runtime_controller.cpp").read_text(encoding="utf-8")
    header = (COMPONENT / "runtime_controller.h").read_text(encoding="utf-8")

    assert "changed |= this->apply_activity_update_(updates[i]);" in cpp
    assert "this->activities_[index].name, updates[i].active" in cpp
    assert "name = this->actions_[action_index].name;" in cpp
    assert "size_t remaining = this->pending_action_count_;" in cpp
    assert "size_t remaining = this->pending_event_count_;" in cpp
    assert "bool draining_pending_events_{false};" in header
    assert "this->drain_pending_events_();" in cpp[cpp.index("void RuntimeController::loop()") :]


def test_schema_rejects_names_that_cannot_fit_runtime_buffers() -> None:
    module = _load_component_module()
    config = _minimal_config(module)
    config[module.CONF_EVENTS] = {"e" * 48: {}}
    with pytest.raises(module.cv.Invalid, match="47 UTF-8 bytes"):
        module._validate_runtime_controller(config)

    config = _minimal_config(module)
    config[module.CONF_VOIP] = {
        module.CONF_ACTIVITY_PREFIX: "p" * 63,
        module.CONF_STATES: {"state": {}},
    }
    with pytest.raises(module.cv.Invalid, match="63 UTF-8 bytes"):
        module._validate_runtime_controller(config)


@pytest.mark.parametrize(
    ("policies", "message"),
    [({"": "normal"}, "policy names"), ({"audio": ""}, "policy values")],
)
def test_schema_rejects_empty_policy_names_and_values(policies, message) -> None:
    module = _load_component_module()
    config = _minimal_config(module)
    config[module.CONF_ACTIVITIES] = {
        "idle": {
            module.CONF_PRIORITY: 0,
            module.CONF_INITIAL: True,
            module.CONF_POLICIES: policies,
        }
    }
    with pytest.raises(module.cv.Invalid, match=message):
        module._validate_runtime_controller(config)


@pytest.mark.parametrize(
    ("policies", "message"),
    [({"": {"values": {}}}, "configured policy names"),
     ({"audio": {"values": {"": 0}}}, "configured policy values")],
)
def test_schema_rejects_empty_configured_policy_bindings(policies, message) -> None:
    module = _load_component_module()
    config = _minimal_config(module)
    config[module.CONF_POLICIES] = policies
    with pytest.raises(module.cv.Invalid, match=message):
        module._validate_runtime_controller(config)


def test_no_second_dead_reducer_implementation_is_shipped() -> None:
    header = (COMPONENT / "runtime_controller_state.h").read_text(encoding="utf-8")
    state_cpp = (COMPONENT / "runtime_controller_state.cpp").read_text(encoding="utf-8")
    runtime_cpp = (COMPONENT / "runtime_controller.cpp").read_text(encoding="utf-8")

    assert "GenericActivity" not in header
    assert "reduce_generic_activities" not in state_cpp
    assert runtime_cpp.count("struct PolicyWinner") == 1
