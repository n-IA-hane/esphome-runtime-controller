"""Mixed public inputs preserve FIFO while all sixteen payload slots are reused."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "esphome/components/runtime_controller"


def test_mixed_event_batch_and_voip_inputs_reuse_all_slots_without_aliasing(tmp_path):
    source = tmp_path / "mixed.cpp"
    source.write_text(r'''
#include "runtime_controller.h"
#include "esphome/components/voip_stack/voip_stack.h"
#include <array>
#include <cassert>
#include <string>
#include <vector>
using esphome::Trigger;using esphome::runtime_controller::RuntimeController;
int main(){
 RuntimeController runtime;runtime.set_storage_in_psram(false);
 esphome::voip_stack::VoipStack phone;runtime.set_voip(&phone);runtime.set_voip_activity_prefix("voip:");
 std::array<std::string,16>names;
 for(unsigned i=0;i<16;++i){names[i]="activity"+std::to_string(i);runtime.add_activity(names[i].c_str(),0,false);}
 for(const char*name:{"voip:idle","voip:ringing","voip:in_call"})runtime.add_activity(name,0,false);
 const std::string long_name(47,'x');unsigned round=0,long_calls=0;std::vector<unsigned>observed;
 Trigger<>observe,long_event,outer;
 observe.fn=[&]{observed.push_back(runtime.get_activity_mask()&0xffff);};
 long_event.fn=[&]{const bool ringing=(long_calls++%2)==0;
  assert(runtime.is_activity_active(ringing?"voip:ringing":"voip:in_call"));
  assert((runtime.get_activity_mask()&0xffff)==(ringing?0xffffU:0U));};
 outer.fn=[&]{
  std::array<std::string,16>temporary_names=names;
  std::array<RuntimeController::ActivityUpdate,16>updates;
  for(unsigned i=0;i<16;++i)updates[i]={temporary_names[i].c_str(),true};
  for(unsigned n=0;n<2;++n){
   for(auto&u:updates)u.active=true;runtime.set_activities(updates.data(),updates.size());
   runtime.event("observe");phone.change("ringing");runtime.event(long_name.c_str());
   for(auto&u:updates)u.active=false;runtime.set_activities(updates.data(),updates.size());
   runtime.event("observe");phone.change("in_call");
   if(n==0||round%2==0)runtime.event(long_name.c_str());
  }
  // Exactly sixteen inputs admit four long events; the seventeenth is rejected.
  if(round%2==0)runtime.event(long_name.c_str());
 };
 runtime.add_event_trigger("observe",&observe);runtime.add_event_trigger(long_name.c_str(),&long_event);runtime.add_event_trigger("outer",&outer);
 runtime.setup();
 for(round=0;round<64;++round){observed.clear();long_calls=0;runtime.event("outer");
  assert((observed==std::vector<unsigned>{65535,0,65535,0}));assert(long_calls==(round%2?3U:4U));
  assert(runtime.is_activity_active("voip:in_call")&&!runtime.is_activity_active("voip:ringing"));
 }
}
''')
    binary = tmp_path / "mixed"
    command = ["g++", "-std=c++17", "-O1", "-Wall", "-Wextra", "-Werror", "-Wno-misleading-indentation", "-g",
        "-fsanitize=address,undefined", "-fno-pie", "-no-pie", "-DUSE_RUNTIME_CONTROLLER_VOIP", "-DUSE_RUNTIME_CONTROLLER_DEBUG",
        "-I", str(ROOT / "tests/fixtures/core/stubs"), "-I", str(COMPONENT), str(source), str(COMPONENT / "runtime_controller.cpp"),
        str(COMPONENT / "runtime_controller_state.cpp"), "-o", str(binary)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    result = subprocess.run([binary], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stdout + result.stderr
