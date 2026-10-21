"""Run source adapters and the real reducer with deterministic component I/O."""

from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def test_source_events_preserve_payload_order_timers_and_ha_presence(tmp_path):
    stubs = tmp_path / "stubs"
    shutil.copytree(ROOT / "tests/fixtures/core/stubs", stubs)
    component = stubs / "esphome/core/component.h"
    header = component.read_text().replace(
        "#pragma once", "#pragma once\n#include <functional>\n#include <map>\n#include <string>"
    ).replace("constexpr float PROCESSOR = 400;", "constexpr float PROCESSOR = 400, AFTER_WIFI = 200;")
    header = header.replace("  void mark_failed()", """
  std::map<std::string, std::function<void()>> timers;
  void set_timeout(const char *name, unsigned, std::function<void()> fn) { timers[name]=fn; }
  bool cancel_timeout(const char *name) { return timers.erase(name)>0; }
  void fire_timeouts() { auto ready=timers; timers.clear(); for(auto &item:ready)item.second(); }
  void mark_failed()""")
    component.write_text(header)
    voice = stubs / "esphome/components/voice_assistant/voice_assistant.h"
    voice.parent.mkdir(parents=True)
    voice.write_text(r'''
#pragma once
#include <string>
#include <vector>
namespace esphome::voice_assistant {
struct Timer { std::string id; };
struct VoiceAssistant {
 bool running=false; void *connection=nullptr; std::vector<Timer> timers;
 bool is_running() const{return running;}
 void *get_api_connection() const{return connection;}
 const std::vector<Timer> &get_timers() const{return timers;}
};
}
''')
    source = tmp_path / "source_observers.cpp"
    source.write_text(r'''
#include "runtime_controller.h"
#include "runtime_network_observers.h"
#include <cassert>
#include <cstring>
using namespace esphome::runtime_controller;
int main(){
 RuntimeController r;
 r.add_activity("idle",0,true);r.add_activity_policy("idle","presentation","idle");
 r.add_activity("listen",10,false);r.add_activity_policy("listen","presentation","listening");
 r.add_activity("timer",0,false);r.add_activity("alarm",20,false);
 r.add_activity("online",0,false);
 r.add_event_activity("va_listening","listen",true);r.add_event_activity("va_idle","listen",false);
 r.add_event_activity("timer_finished","alarm",true);
 r.add_event_activity("ha_connected","online",true);r.add_event_activity("ha_disconnected","online",false);
 bool user_text_updated=false;unsigned listening=0;
 esphome::Trigger<> listener;listener.fn=[&]{assert(user_text_updated);++listening;};
 r.add_policy_value_trigger("presentation","listening",&listener);r.setup();
 assert(!r.loop_enabled()); // an idle reducer must not poll
 esphome::voice_assistant::VoiceAssistant voice;
 RuntimeNetworkObservers o;o.set_runtime(&r);o.set_voice_assistant(&voice,true);o.setup();
 assert(!o.loop_enabled()); // source callbacks own subsequent observations
 assert(r.loop_enabled()); // startup observations wake the existing reducer
 r.loop();assert(!r.loop_enabled());
 o.source_event("va_listening","");assert(listening==0);assert(r.loop_enabled());
 user_text_updated=true;r.loop();assert(listening==1);assert(!r.loop_enabled());
 o.source_event("va_listening","");r.loop();assert(listening==1);
 voice.timers={{"first"},{"second"}};
 o.source_event("timer_started","first");r.loop();assert(r.is_activity_active("timer"));
 o.source_event("timer_cancelled","first");r.loop();assert(r.is_activity_active("timer"));
 voice.timers={{"second"}};
 o.source_event("timer_finished","second");r.loop();
 assert(!r.is_activity_active("timer") && r.is_activity_active("alarm"));
 assert(voice.timers.size()==1); // the adapter must not modify source-owned timers
 voice.timers={{"restored"}};o.source_event("timer_updated","restored");r.loop();
 assert(r.is_activity_active("timer")); // updates may introduce a timer after reconnect
 o.source_event("api_connected","ESPHome Logs test");r.loop();assert(!r.is_activity_active("online"));
 o.source_event("api_connected","Home Assistant A");o.source_event("api_connected","Home Assistant B");
 r.loop();assert(r.is_activity_active("online"));
 o.source_event("api_disconnected","Home Assistant A");o.fire_timeouts();r.loop();
 assert(r.is_activity_active("online"));
 o.source_event("api_disconnected","Home Assistant B");
 o.source_event("api_connected","Home Assistant C");o.fire_timeouts();r.loop();
 assert(r.is_activity_active("online"));
 o.source_event("api_disconnected","Home Assistant C");o.fire_timeouts();r.loop();
 assert(!r.is_activity_active("online"));
 assert(!r.loop_enabled() && !o.loop_enabled());
 assert(o.timers.empty()); // grace timeout is one-shot, not periodic polling
}
''')
    implementation = ROOT / "esphome/components/runtime_controller"
    binary = tmp_path / "source_observers"
    compiled = subprocess.run([
        "g++", "-std=c++17", "-Wall", "-Wextra", "-Werror",
        "-DUSE_RUNTIME_CONTROLLER_SOURCE_EVENTS", "-DUSE_RUNTIME_CONTROLLER_VOICE_ASSISTANT",
        "-DUSE_RUNTIME_CONTROLLER_API", "-I", str(stubs), "-I", str(implementation), "-I", str(ROOT),
        str(source), *(str(implementation / name) for name in (
            "runtime_controller.cpp", "runtime_controller_state.cpp", "runtime_network_observers.cpp")),
        "-o", str(binary),
    ], capture_output=True, text=True)
    assert compiled.returncode == 0, compiled.stderr
    subprocess.run([str(binary)], check=True)


def test_media_observer_reduces_transitions_once_with_real_controller(tmp_path):
    stubs = tmp_path / "stubs"
    shutil.copytree(ROOT / "tests/fixtures/core/stubs", stubs)
    component = stubs / "esphome/core/component.h"
    component.write_text(component.read_text().replace(
        "constexpr float PROCESSOR = 400;", "constexpr float PROCESSOR = 400, AFTER_WIFI = 200;"
    ))
    media = stubs / "esphome/components/media_player/media_player.h"
    media.parent.mkdir(parents=True)
    media.write_text(r'''
#pragma once
#include <functional>
#include <vector>
namespace esphome::media_player {
enum MediaPlayerState { MEDIA_PLAYER_STATE_NONE, MEDIA_PLAYER_STATE_IDLE,
 MEDIA_PLAYER_STATE_PLAYING, MEDIA_PLAYER_STATE_PAUSED, MEDIA_PLAYER_STATE_ANNOUNCING,
 MEDIA_PLAYER_STATE_OFF, MEDIA_PLAYER_STATE_ON };
class MediaPlayer {
 public:
  MediaPlayerState state=MEDIA_PLAYER_STATE_IDLE;
  std::vector<std::function<void(MediaPlayerState)>> callbacks;
  template<typename F> void add_on_state_callback(F callback) { callbacks.push_back(callback); }
  void publish(MediaPlayerState value) { state=value; for(auto &cb:callbacks) cb(value); }
};
}
''')
    main = tmp_path / "media_observer.cpp"
    main.write_text(r'''
#include "runtime_controller.h"
#include "runtime_network_observers.h"
#include <cassert>
using namespace esphome;
using namespace esphome::runtime_controller;
int main() {
 RuntimeController r;
 r.add_activity("media",10,false);
 r.add_event_activity("media_playing","media",true);
 r.add_event_activity("media_paused","media",false);
 r.add_event_activity("media_idle","media",false);
 media_player::MediaPlayer player;
 unsigned user_callbacks=0, actions=0;
 bool pause_in_action=false;
 player.add_on_state_callback([&](auto){++user_callbacks;});
 Trigger<> play;
 play.fn=[&]{++actions;if(pause_in_action)player.publish(media_player::MEDIA_PLAYER_STATE_PAUSED);};
 r.add_event_trigger("media_playing",&play);
 r.setup();
 RuntimeNetworkObservers observer;observer.set_runtime(&r);observer.set_media_player(&player);observer.setup();
 assert(!r.loop_enabled() && !observer.loop_enabled());
 player.publish(media_player::MEDIA_PLAYER_STATE_PLAYING);
 assert(actions==1 && r.is_activity_active("media"));
 const auto revision=r.get_sequence();
 for(unsigned i=0;i<100;++i)player.publish(media_player::MEDIA_PLAYER_STATE_PLAYING);
 assert(user_callbacks==101 && actions==1 && r.get_sequence()==revision);
 player.publish(media_player::MEDIA_PLAYER_STATE_PAUSED);
 assert(!r.is_activity_active("media"));
 pause_in_action=true;
 player.publish(media_player::MEDIA_PLAYER_STATE_PLAYING);
 r.loop();
 assert(actions==2 && !r.is_activity_active("media"));
 player.publish(media_player::MEDIA_PLAYER_STATE_PAUSED);r.loop();
 assert(actions==2 && !r.loop_enabled());
 // Explicit operation events can intentionally repeat an action.
 pause_in_action=false;
 r.event("media_playing");r.event("media_playing");
 assert(actions==4 && r.is_activity_active("media"));
 assert(player.state==media_player::MEDIA_PLAYER_STATE_PAUSED);
}
''')
    implementation = ROOT / "esphome/components/runtime_controller"
    binary = tmp_path / "media_observer"
    result = subprocess.run([
        "g++", "-std=c++17", "-Wall", "-Wextra", "-Werror",
        "-DUSE_RUNTIME_CONTROLLER_MEDIA_PLAYER", "-I", str(stubs), "-I", str(implementation), "-I", str(ROOT),
        str(main), *(str(implementation / name) for name in (
            "runtime_controller.cpp", "runtime_controller_state.cpp", "runtime_network_observers.cpp")),
        "-o", str(binary),
    ], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    subprocess.run([str(binary)], check=True)
