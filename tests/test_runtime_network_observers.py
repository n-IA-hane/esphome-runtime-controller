"""Compile the native network/switch adapters with all optional feature sets."""

from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "esphome/components/runtime_controller"


@pytest.mark.parametrize(
    "features",
    [
        (),
        ("WIFI",),
        ("SWITCH",),
        ("WIFI", "SWITCH"),
        ("MEDIA_PLAYER",),
        ("WIFI", "SWITCH", "MEDIA_PLAYER"),
    ],
)
def test_native_network_observers_preserve_callbacks_and_replay_state(
    tmp_path, features
):
    headers = {
        "esphome/core/component.h": r"""
#pragma once
namespace esphome {
namespace setup_priority { constexpr float AFTER_WIFI=200.0f; }
class Component {
 public:
  virtual ~Component()=default;
  virtual void setup() {}
  virtual float get_setup_priority() const { return 0; }
  void mark_failed() { failed=true; }
  void disable_loop() { loop_disabled=true; }
  bool failed=false, loop_disabled=false;
};
}
""",
        "esphome/components/runtime_controller/runtime_controller.h": r"""
#pragma once
#include <string>
#include <vector>
namespace esphome::runtime_controller {
struct RuntimeController {
  std::vector<std::string> events;
  void event(const char *name) { events.emplace_back(name); }
};
}
""",
        "esphome/components/wifi/wifi_component.h": r"""
#pragma once
#include <cstdint>
#include <span>
#include <string>
#include <vector>
namespace esphome {
using StringRef=std::string;
namespace wifi {
class WiFiConnectStateListener {
 public:
  virtual void on_wifi_connect_state(StringRef ssid, std::span<const uint8_t,6> bssid)=0;
};
class WiFiComponent {
 public:
  bool connected=false;
  std::vector<WiFiConnectStateListener*> listeners;
  bool is_connected() const { return connected; }
  void add_connect_state_listener(WiFiConnectStateListener *listener) { listeners.push_back(listener); }
  void publish(bool value) {
    connected=value;
    static constexpr uint8_t bssid[6]={};
    for (auto *listener:listeners) listener->on_wifi_connect_state(value ? "ssid" : "", bssid);
  }
};
}
}
""",
        "esphome/components/switch/switch.h": r"""
#pragma once
#include <functional>
#include <utility>
#include <vector>
namespace esphome::switch_ {
class Switch {
 public:
  bool state=false;
  std::vector<std::function<void(bool)>> callbacks;
  template<typename F> void add_on_state_callback(F &&callback) {
    callbacks.emplace_back(std::forward<F>(callback));
  }
  void publish_state(bool value) {
    state=value;
    for (const auto &callback:callbacks) callback(value);
  }
};
}
""",
    }
    headers["esphome/components/media_player/media_player.h"] = r"""
#pragma once
#include <functional>
#include <vector>
namespace esphome::media_player {
enum MediaPlayerState { MEDIA_PLAYER_STATE_NONE, MEDIA_PLAYER_STATE_IDLE,
 MEDIA_PLAYER_STATE_PLAYING, MEDIA_PLAYER_STATE_PAUSED, MEDIA_PLAYER_STATE_ANNOUNCING,
 MEDIA_PLAYER_STATE_OFF, MEDIA_PLAYER_STATE_ON };
class MediaPlayer {
 public:
  MediaPlayerState state=MEDIA_PLAYER_STATE_NONE;
  std::vector<std::function<void(MediaPlayerState)>> callbacks;
  template<typename F> void add_on_state_callback(F callback) { callbacks.push_back(callback); }
  void publish(MediaPlayerState value) { state=value; for (auto &cb:callbacks) cb(value); }
};
}
"""
    for name, content in headers.items():
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)

    main = tmp_path / "native_observers.cpp"
    main.write_text(r"""
#include "runtime_network_observers.h"
#include "esphome/components/runtime_controller/runtime_controller.h"
#include <cassert>
using namespace esphome;
using namespace esphome::runtime_controller;
#ifdef USE_RUNTIME_CONTROLLER_WIFI
class ExistingWiFiListener : public wifi::WiFiConnectStateListener {
 public:
  int calls=0;
  void on_wifi_connect_state(StringRef, std::span<const uint8_t,6>) override { ++calls; }
};
#endif
int main() {
  RuntimeNetworkObservers unconfigured;
  unconfigured.setup(); assert(unconfigured.failed);

  RuntimeController runtime;
  RuntimeNetworkObservers observer;
  observer.set_runtime(&runtime);
  assert(observer.get_setup_priority()<400.0f);
  std::vector<std::string> expected;
#ifdef USE_RUNTIME_CONTROLLER_WIFI
  wifi::WiFiComponent wifi;
  ExistingWiFiListener existing_wifi;
  wifi.add_connect_state_listener(&existing_wifi);
  wifi.connected=true; observer.set_wifi(&wifi);
  expected.emplace_back("wifi_connected");
#endif
#ifdef USE_RUNTIME_CONTROLLER_SWITCH
  switch_::Switch microphone, speaker;
  int microphone_user_calls=0, speaker_user_calls=0;
  microphone.add_on_state_callback([&](bool) { ++microphone_user_calls; });
  speaker.add_on_state_callback([&](bool) { ++speaker_user_calls; });
  microphone.state=true; speaker.state=false;
  observer.set_microphone_mute(&microphone);
  observer.set_speaker_mute(&speaker);
  expected.emplace_back("mic_muted");
  expected.emplace_back("speaker_unmuted");
#endif
#ifdef USE_RUNTIME_CONTROLLER_MEDIA_PLAYER
  media_player::MediaPlayer media;
  int media_user_calls=0;
  media.add_on_state_callback([&](media_player::MediaPlayerState) { ++media_user_calls; });
  media.state=media_player::MEDIA_PLAYER_STATE_PAUSED;
  observer.set_media_player(&media);
  expected.emplace_back("media_paused");
#endif
  observer.setup(); assert(observer.loop_disabled && !observer.failed);
  assert(runtime.events==expected);
#ifdef USE_RUNTIME_CONTROLLER_WIFI
  wifi.publish(false); expected.emplace_back("wifi_disconnected");
  wifi.publish(true); expected.emplace_back("wifi_connected");
  assert(existing_wifi.calls==2);
  assert(wifi.listeners.size()==2);
#endif
#ifdef USE_RUNTIME_CONTROLLER_SWITCH
  microphone.publish_state(false); expected.emplace_back("mic_unmuted");
  speaker.publish_state(true); expected.emplace_back("speaker_muted");
  microphone.publish_state(true); expected.emplace_back("mic_muted");
  speaker.publish_state(false); expected.emplace_back("speaker_unmuted");
  assert(microphone_user_calls==2 && speaker_user_calls==2);
  assert(microphone.callbacks.size()==2 && speaker.callbacks.size()==2);
#endif
  assert(runtime.events==expected);

#ifdef USE_RUNTIME_CONTROLLER_MEDIA_PLAYER
  media.publish(media_player::MEDIA_PLAYER_STATE_ANNOUNCING); expected.emplace_back("announcement_started");
  media.publish(media_player::MEDIA_PLAYER_STATE_IDLE); expected.emplace_back("media_idle");
  media.publish(media_player::MEDIA_PLAYER_STATE_PLAYING); expected.emplace_back("media_playing");
  media.publish(media_player::MEDIA_PLAYER_STATE_PAUSED); expected.emplace_back("media_paused");
  assert(media_user_calls==4 && media.callbacks.size()==2);
  assert(runtime.events==expected);
#endif
  // Optional bindings stay optional; registering one observer must not require
  // unrelated components or invent their initial states.
  RuntimeController optional_runtime;
  RuntimeNetworkObservers optional;
  optional.set_runtime(&optional_runtime);
  optional.setup(); assert(optional_runtime.events.empty());
}
""")
    binary = tmp_path / "native_observers"
    subprocess.run(
        [
            "g++",
            "-std=c++20",
            "-Wall",
            "-Wextra",
            "-Werror",
            *("-DUSE_RUNTIME_CONTROLLER_" + feature for feature in features),
            "-I" + str(tmp_path),
            "-I" + str(COMPONENT),
            str(COMPONENT / "runtime_network_observers.cpp"),
            str(main),
            "-o",
            str(binary),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run([str(binary)], check=True, capture_output=True, text=True)
