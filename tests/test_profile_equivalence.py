"""Compare the existing full profile against traces captured before migration."""

import json
from pathlib import Path
import subprocess

from test_runtime_controller_contract import _load_component_module
from test_runtime_profile_runtime import _profile_cpp


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/full_profile_trace.json"


def build_trace(directory, component, *, observers=True):
    directory.mkdir(parents=True, exist_ok=True)
    module = _load_component_module()
    quote = json.dumps
    lines = [_profile_cpp(), r'''
#include "esphome/components/voip_stack/voip_stack.h"
#include <cassert>
#include <iostream>
#include <map>
#include <string>
#include <vector>
int main() {
 RuntimeController r;esphome::voip_stack::VoipStack phone;
 r.set_voip(&phone);r.set_voip_activity_prefix("voip:");
''']
    for state, config in module.FULL_VOICE_VOIP_VOIP_STATES.items():
        name = "voip:" + state
        lines.append(f'r.add_activity({quote(name)},{config["priority"]},false);')
        for policy, value in config["policies"].items():
            lines.append(f'r.add_activity_policy({quote(name)},{quote(policy)},{quote(value)});')
    actions = set()
    for event in module.FULL_VOICE_VOIP_EVENTS.values():
        for rule in [event, *event.get("cases", [])]:
            if rule.get("action"):
                actions.add(rule["action"])
    lines += ['std::vector<std::string> actions;', 'std::map<std::string,esphome::Trigger<>> triggers;']
    for name in sorted(actions):
        lines.append(f'triggers[{quote(name)}].fn=[&]{{actions.emplace_back({quote(name)});}};')
        lines.append(f'r.add_action_trigger({quote(name)},&triggers[{quote(name)}]);')
    lines += [r'''
 load_profile(r);
 std::string input;
 while(std::getline(std::cin,input)) {
   actions.clear();
   if(input.rfind("phone:",0)==0)phone.change(input.substr(6).c_str());
   else if(input=="timer:finish") {r.set_activity("timer",false);r.event("timer_finished");}
   else if(input.rfind("observe:",0)==0) {
#ifdef TEST_SOURCE_OBSERVERS
     r.observe_event(input.substr(8).c_str());
#else
     r.event(input.substr(8).c_str());
#endif
   } else r.event(input.c_str());
   unsigned budget=100;
   do {r.loop();} while(r.loop_enabled() && --budget);
   assert(budget>0);
   std::cout<<r.get_activity_mask()<<"|"<<r.get_sequence();
   for(const char *policy:{"led_status","display_status","audio_policy","ringtone","timer_alarm","va_state","va_response"})
     std::cout<<"|"<<r.get_policy(policy);
   for(const auto &action:actions)std::cout<<"|action:"<<action;
   std::cout<<"\n";
 }
}
''']
    cpp = directory / "trace.cpp"
    cpp.write_text("\n".join(lines))
    binary = directory / "trace"
    compile_result = subprocess.run([
        "g++", "-std=c++17", "-DUSE_RUNTIME_CONTROLLER_VOIP",
        *(["-DTEST_SOURCE_OBSERVERS"] if observers else []),
        "-I", str(ROOT / "tests/fixtures/core/stubs"), "-I", str(component),
        str(cpp), str(component / "runtime_controller.cpp"),
        str(component / "runtime_controller_state.cpp"), "-o", str(binary),
    ], capture_output=True, text=True)
    assert compile_result.returncode == 0, compile_result.stderr
    return binary


def test_full_profile_preserves_pre_migration_outputs_and_actions(tmp_path):
    fixture = json.loads(FIXTURE.read_text())
    binary = build_trace(tmp_path, ROOT / "esphome/components/runtime_controller")
    result = subprocess.run([str(binary)], input="\n".join(fixture["inputs"]) + "\n",
                            capture_output=True, text=True, check=True)
    assert result.stdout.splitlines() == fixture["expected"]
