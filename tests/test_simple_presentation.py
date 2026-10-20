"""Public presentation shorthand uses the existing policy reducer."""

import pytest
import subprocess
from pathlib import Path

from test_runtime_controller_contract import _load_component_module


def config(module, **values):
    return module.CONFIG_SCHEMA({"id": "runtime", **values})


def test_player_and_natural_triggers_need_no_manual_graph():
    m = _load_component_module()
    c = config(m, observe={"media_player": "player"},
               on_music={"then": [{"runtime_controller.dump": {"id": "runtime"}}]},
               on_idle={"then": [{"runtime_controller.dump": {"id": "runtime"}}]})
    _, activities, _, _, events = m._merged_runtime_config(c)
    assert activities["media"]["policies"]["presentation"] == "music"
    assert activities["announcement"]["policies"]["presentation"] == "announcement"
    assert "media_playing" in events and "media_idle" in events
    assert c["actions"] == {}
    assert "then" in c["policies"]["presentation"]["values"]["music"]


def test_simple_voip_observer_does_not_require_full_voice_profile():
    m = _load_component_module()
    c = config(m, observe={"voip_stack": "phone"},
               on_call={"then": [{"runtime_controller.dump": {"id": "runtime"}}]})
    assert c["profile"] == "presentation"
    _, activities, _, _, _ = m._merged_runtime_config(c)
    assert not any(name.startswith("va_") for name in activities)
    assert not c["actions"] and not c["outputs"]


def test_presentation_priorities_do_not_change_control_priorities():
    m = _load_component_module()
    c = config(m, observe={"media_player": "player"},
               presentation={"priorities": {"music": 1000}})
    _, activities, _, _, _ = m._merged_runtime_config(c)
    assert activities["media"]["priority"] == m.FULL_VOICE_VOIP_ACTIVITIES["media"]["priority"]
    assert c["presentation"]["priorities"]["music"] == 1000


def test_duplicate_natural_and_advanced_presentation_binding_rejected():
    m = _load_component_module()
    action = {"then": [{"runtime_controller.dump": {"id": "runtime"}}]}
    with pytest.raises(m.cv.Invalid, match="presentation.*music|music.*presentation"):
        config(m, observe={"media_player": "player"}, on_music=action,
               policies={"presentation": {"values": {"music": action}}})


def test_unknown_presentation_state_is_an_error():
    m = _load_component_module()
    with pytest.raises(m.cv.Invalid):
        config(m, observe={"media_player": "player"},
               presentation={"priorities": {"musci": 1000}})


def test_natural_triggers_follow_the_winner_and_keep_audio_policy(tmp_path):
    root = Path(__file__).resolve().parents[1]
    component = root / "esphome/components/runtime_controller"
    source = tmp_path / "presentation.cpp"
    source.write_text(r'''
#include "runtime_controller.h"
#include <cassert>
#include <cstring>
#include <string>
#include <utility>
#include <vector>
using esphome::runtime_controller::RuntimeController;
void load(RuntimeController &r) {
 r.add_activity("idle",0,true);r.add_activity_policy("idle","presentation","idle");
 r.add_activity_policy("idle","audio_policy","normal");
 r.add_activity("media",100,false);r.add_activity_policy("media","presentation","music");
 r.add_activity_policy("media","audio_policy","normal");
 r.add_activity_policy("media","led_status","music");
 r.add_activity("call",700,false);r.add_activity_policy("call","presentation","call");
 r.add_activity_policy("call","audio_policy","duck");
 r.add_activity_policy("call","led_status","call");
 r.add_event_activity("play","media",true);r.add_event_activity("stop","media",false);
 r.add_event_activity("answer","call",true);r.add_event_activity("hangup","call",false);
}
int main() {
 RuntimeController r;load(r);unsigned music=0,call=0,idle=0;
 esphome::Trigger<> on_music,on_call,on_idle;
 on_music.fn=[&]{++music;};on_call.fn=[&]{++call;};on_idle.fn=[&]{++idle;};
 r.add_policy_value_trigger("presentation","music",&on_music);
 r.add_policy_value_trigger("presentation","call",&on_call);
 r.add_policy_value_trigger("presentation","idle",&on_idle);
 std::vector<std::pair<std::string,std::string>> changes;
 esphome::Trigger<std::string,std::string> changed;
 changed.fn=[&](std::string before,std::string after){changes.emplace_back(before,after);};
 r.set_presentation_trigger(&changed);r.setup();assert(idle==1);
 r.event("play");r.event("play");assert(music==1);
 r.event("answer");assert(call==1 && music==1);
 r.event("play");assert(music==1); // background source must not overwrite call
 r.event("hangup");assert(music==2); // no new player event is needed
 assert(changes.back()==std::make_pair(std::string("call"),std::string("music")));
 r.event("stop");assert(idle==2);
 RuntimeController custom;load(custom);custom.set_activity_presentation_priority("media",1000);custom.setup();
 custom.event("play");custom.event("answer");
 assert(strcmp(custom.get_policy("presentation"),"music")==0);
 assert(strcmp(custom.get_policy("audio_policy"),"duck")==0);
 assert(strcmp(custom.get_policy("led_status"),"music")==0);
 assert(custom.is_activity_active("call")); // presentation cannot cancel the call
}
''')
    binary = tmp_path / "presentation"
    subprocess.run([
        "g++", "-std=c++17", "-Wall", "-Wextra", "-Werror",
        "-DUSE_RUNTIME_CONTROLLER_PRESENTATION_PRIORITY",
        "-DUSE_RUNTIME_CONTROLLER_PRESENTATION_TRIGGER",
        "-I", str(root / "tests/fixtures/core/stubs"), "-I", str(component),
        str(source), str(component / "runtime_controller.cpp"),
        str(component / "runtime_controller_state.cpp"), "-o", str(binary),
    ], check=True, capture_output=True, text=True)
    subprocess.run([str(binary)], check=True)
