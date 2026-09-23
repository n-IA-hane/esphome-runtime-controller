"""Execute public lifecycle sequences against the actual generated profile and C++ reducer."""

import json
import subprocess
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "esphome/components/runtime_controller"
CORE_STUBS = ROOT / "tests/fixtures/core/stubs"


def _list(value):
    return value if isinstance(value, list) else [value]


def _profile_cpp():
    """Read literal profile definitions without importing ESPHome codegen."""
    from test_runtime_controller_contract import _load_component_module

    module = _load_component_module()
    values = vars(module)
    quote = json.dumps
    lines = [
        '#include "runtime_controller.h"',
        "using esphome::runtime_controller::RuntimeController;",
        "void load_profile(RuntimeController &r) {",
        "r.set_storage_in_psram(false);",
    ]
    for name, config in values["FULL_VOICE_VOIP_ACTIVITIES"].items():
        initial = str(config.get("initial", False)).lower()
        lines.append(
            f"r.add_activity({quote(name)}, {config.get('priority', 0)}, {initial});"
        )
        for policy, value in config.get("policies", {}).items():
            lines.append(
                f"r.add_activity_policy({quote(name)}, {quote(policy)}, {quote(value)});"
            )
        lines.append(f"r.add_event_activity({quote(name)}, {quote(name)}, true);")
    for group, names in values["FULL_VOICE_VOIP_GROUPS"].items():
        for name in names:
            lines.append(f"r.set_activity_group({quote(name)}, {quote(group)});")
    for config in values["FULL_VOICE_VOIP_DERIVED"]:
        lines.append(f"r.add_derived_activity({quote(config['name'])});")
        for condition in ("any_active", "all_active", "none_active"):
            for name in _list(config.get("when", {}).get(condition, [])):
                lines.append(f"r.add_derived_{condition}({quote(name)});")
    for name, config in values["FULL_VOICE_VOIP_EVENTS"].items():
        rules = list(config.get("cases", []))
        if config.get("activate") or config.get("deactivate") or config.get("action"):
            rules.append(
                {key: value for key, value in config.items() if key != "cases"}
            )
        for rule in rules:
            lines.append(
                f"r.add_event_rule({quote(name)}, {quote(rule.get('action', ''))});"
            )
            for condition in ("any", "all", "none"):
                for activity in _list(rule.get(condition, [])):
                    lines.append(
                        f"r.add_event_rule_{condition}_active({quote(activity)});"
                    )
            for key, enabled in (("activate", "true"), ("deactivate", "false")):
                for activity in _list(rule.get(key, [])):
                    lines.append(
                        f"r.add_event_rule_update({quote(activity)}, {enabled});"
                    )
    return "\n".join(lines) + "\nr.setup();\n}\n"


@pytest.fixture(scope="module")
def profile_binary(tmp_path_factory):
    path = tmp_path_factory.mktemp("profile-runtime")
    cpp = path / "profile.cpp"
    cpp.write_text(
        _profile_cpp()
        + r"""
#include <cassert>
#include <cstring>
#include <iostream>
int main(int argc, char **argv) {
  assert(argc == 3);
  RuntimeController r; load_profile(r);
  r.event("boot_ready"); r.event("wifi_connected"); r.event("ha_connected");
  r.event("va_client_connected");
  r.event("va_start"); r.event("va_listening"); r.event("va_thinking");
  r.event("va_responding"); r.event("announcement_started");
  if (std::strcmp(argv[2], "stop") == 0) {
    r.event("voice_stop");
    assert(r.is_activity_active("va_stopping"));
    r.event("va_end");
    assert(r.is_activity_active("va_stopping"));
    r.event("va_stop_complete");
    assert(!r.is_activity_active("va_stopping"));
    return 0;
  }
  if (std::strcmp(argv[2], "disconnect") == 0) {
    r.event("va_client_disconnected"); r.event("va_client_connected");
  } else if (std::strcmp(argv[2], "pipeline_first") == 0) {
    r.event("va_end"); r.event(argv[1]);
  } else {
    r.event(argv[1]); r.event("va_end");
  }
  assert(!r.is_activity_active("va_responding"));
  assert(!r.is_activity_active("va_run_ended"));
  assert(!r.is_activity_active("va_response_drained"));
  assert(std::strcmp(r.get_policy("audio_policy"), "normal") == 0);
  assert(r.is_activity_active("media") == (std::strcmp(argv[1],"media_playing")==0 && std::strcmp(argv[2],"disconnect")!=0));
  std::cout << "PASS";
}
"""
    )
    binary = path / "profile"
    result = subprocess.run(
        [
            "g++",
            "-std=c++17",
            "-I",
            str(CORE_STUBS),
            "-I",
            str(COMPONENT),
            str(cpp),
            str(COMPONENT / "runtime_controller.cpp"),
            str(COMPONENT / "runtime_controller_state.cpp"),
            "-o",
            str(binary),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return binary


@pytest.mark.parametrize("media", ["media_idle", "media_paused", "media_playing"])
@pytest.mark.parametrize("order", ["pipeline_first", "audio_first"])
def test_voice_completion_preserves_underlying_music(profile_binary, media, order):
    result = subprocess.run(
        [str(profile_binary), media, order], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr


def test_pipeline_end_is_not_physical_stop_acknowledgement(profile_binary):
    result = subprocess.run(
        [str(profile_binary), "media_idle", "stop"],
        cwd=profile_binary.parent,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
