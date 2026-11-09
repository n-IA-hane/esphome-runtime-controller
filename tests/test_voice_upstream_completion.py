"""Exercise public source observations without a noncontinuous VA on_idle hook."""

from pathlib import Path
import shutil
import subprocess

import pytest

from test_runtime_profile_runtime import _profile_cpp


ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "esphome/components/runtime_controller"


@pytest.fixture(scope="module")
def upstream_completion_binary(tmp_path_factory):
    directory = tmp_path_factory.mktemp("upstream-completion")
    stubs = directory / "stubs"
    shutil.copytree(ROOT / "tests/fixtures/core/stubs", stubs)
    component = stubs / "esphome/core/component.h"
    component.write_text(component.read_text().replace(
        "constexpr float PROCESSOR = 400;",
        "constexpr float PROCESSOR = 400, AFTER_WIFI = 200;",
    ))
    headers = {
        "voice_assistant/voice_assistant.h": r'''
#pragma once
#include <string>
#include <vector>
namespace esphome::voice_assistant {
struct Timer { std::string id; };
struct VoiceAssistant {
  bool running=false;
  std::vector<Timer> timers;
  bool is_running() const { return running; }
  void *get_api_connection() const { return nullptr; }
  const std::vector<Timer> &get_timers() const { return timers; }
};
}
''',
        "media_player/media_player.h": r'''
#pragma once
#include <functional>
#include <vector>
namespace esphome::media_player {
enum MediaPlayerState { MEDIA_PLAYER_STATE_NONE, MEDIA_PLAYER_STATE_IDLE,
  MEDIA_PLAYER_STATE_PLAYING, MEDIA_PLAYER_STATE_PAUSED, MEDIA_PLAYER_STATE_ANNOUNCING,
  MEDIA_PLAYER_STATE_OFF, MEDIA_PLAYER_STATE_ON };
struct MediaPlayer {
  MediaPlayerState state=MEDIA_PLAYER_STATE_IDLE;
  std::vector<std::function<void(MediaPlayerState)>> callbacks;
  template<typename F> void add_on_state_callback(F callback) { callbacks.push_back(callback); }
  void publish(MediaPlayerState value) { state=value; for (auto &cb:callbacks) cb(value); }
};
}
''',
    }
    for name, content in headers.items():
        target = stubs / "esphome/components" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    source = directory / "upstream_completion.cpp"
    source.write_text(_profile_cpp(static_rules=True) + r'''
#include "runtime_network_observers.h"
#include <cassert>
#include <cstring>
using namespace esphome;
using namespace esphome::runtime_controller;
int main(int argc, char **argv) {
  assert(argc == 2);
  RuntimeController runtime; load_profile(runtime);
  voice_assistant::VoiceAssistant voice;
  media_player::MediaPlayer player;
  RuntimeNetworkObservers observer;
  observer.set_runtime(&runtime);
  observer.set_voice_assistant(&voice, true);
  observer.set_media_player(&player);
  observer.setup();
  auto settle = [&] {
    unsigned budget=16;
    while (runtime.loop_enabled() && --budget) runtime.loop();
    assert(budget && !observer.loop_enabled());
  };
  settle();
  runtime.event("boot_ready"); runtime.event("wifi_connected");
  runtime.event("ha_connected"); runtime.event("va_client_connected");
  unsigned idle_events=0;
  unsigned announcement_stops=0;
  Trigger<> stop_announcement;
  stop_announcement.fn=[&] { ++announcement_stops; };
  runtime.add_action_trigger("stop_announcement", &stop_announcement);
  Trigger<> idle_observed; idle_observed.fn=[&] { ++idle_events; };
  runtime.add_event_trigger("va_idle", &idle_observed);
  auto event = [&](const char *name) { observer.source_event(name, ""); settle(); };
  auto start = [&] { event("va_start"); event("va_listening"); };
  auto response = [&] { start(); event("va_thinking"); event("va_responding"); };
  auto media = [&](media_player::MediaPlayerState state) { player.publish(state); settle(); };
  auto inactive = [&] {
    for (const char *name : {"va_start_requested", "va_starting", "va_listening",
         "va_thinking", "va_responding", "va_barging", "va_stopping",
         "va_run_ended", "va_response_drained", "announcement"})
      assert(!runtime.is_activity_active(name));
    assert(std::strcmp(runtime.get_policy("va_state"), "idle") == 0);
    assert(std::strcmp(runtime.get_policy("audio_policy"), "normal") == 0);
  };
  const char *scenario=argv[1];
  if (std::strncmp(scenario, "playback_", 9) == 0) {
    const bool responding_first=std::strstr(scenario, "responding_first") != nullptr;
    const bool drain_first=std::strstr(scenario, "drain_first") != nullptr;
    const bool listening=std::strstr(scenario, "listening") != nullptr;
    start();
    if (!listening) event("va_thinking");
    // Real adverse ordering: ANNOUNCING is published by player.loop(), not
    // synchronously by make_call().perform(). INTENT_PROGRESS is deferred.
    if (responding_first) observer.source_event("va_responding", "");
    player.publish(media_player::MEDIA_PLAYER_STATE_ANNOUNCING);
    if (!responding_first) observer.source_event("va_responding", "");
    settle();
    assert(announcement_stops == 0);
    assert(runtime.is_activity_active("announcement"));
    assert(runtime.is_activity_active("va_responding"));
    assert(std::strcmp(runtime.get_policy("audio_policy"), "duck") == 0);
    if (drain_first) media(media_player::MEDIA_PLAYER_STATE_IDLE);
    event("va_end");
    if (!drain_first) {
      assert(runtime.is_activity_active("va_responding"));
      media(media_player::MEDIA_PLAYER_STATE_IDLE);
    }
    inactive();
  } else if (std::strcmp(scenario, "foreign_announcement") == 0) {
    start(); event("va_thinking");
    player.publish(media_player::MEDIA_PLAYER_STATE_ANNOUNCING);
    settle(); assert(announcement_stops == 1);
    assert(runtime.is_activity_active("announcement"));
    media(media_player::MEDIA_PLAYER_STATE_IDLE); event("va_end"); inactive();
  } else if (std::strcmp(scenario, "drain_before_response_callback") == 0) {
    start(); event("va_thinking");
    player.publish(media_player::MEDIA_PLAYER_STATE_ANNOUNCING);
    player.publish(media_player::MEDIA_PLAYER_STATE_IDLE);
    observer.source_event("va_responding", "");
    settle(); assert(announcement_stops == 0);
    assert(runtime.is_activity_active("va_response_drained"));
    event("va_end"); inactive();
  } else if (std::strcmp(scenario, "explicit_stop_keeps_intent") == 0) {
    start(); event("va_thinking");
    player.publish(media_player::MEDIA_PLAYER_STATE_ANNOUNCING);
    observer.source_event("va_responding", "");
    runtime.request_action("stop_announcement");
    settle(); assert(announcement_stops == 1);
    event("va_end"); media(media_player::MEDIA_PLAYER_STATE_IDLE); inactive();
  } else if (std::strcmp(scenario, "explicit_stop_queued_first") == 0) {
    start(); event("va_thinking");
    runtime.request_action("stop_announcement");
    player.publish(media_player::MEDIA_PLAYER_STATE_ANNOUNCING);
    observer.source_event("va_responding", "");
    settle(); assert(announcement_stops == 1);
    event("va_end"); media(media_player::MEDIA_PLAYER_STATE_IDLE); inactive();
  } else if (std::strcmp(scenario, "stopping_rejects_stale_response") == 0) {
    start(); runtime.event("voice_stop");
    player.publish(media_player::MEDIA_PLAYER_STATE_ANNOUNCING);
    observer.source_event("va_responding", "");
    settle(); assert(announcement_stops == 1);
    assert(!runtime.is_activity_active("va_responding"));
    assert(runtime.is_activity_active("va_stopping"));
    media(media_player::MEDIA_PLAYER_STATE_IDLE);
    runtime.event("va_stop_complete"); inactive();
  } else if (std::strcmp(scenario, "new_run_invalidates_stop") == 0) {
    start(); player.publish(media_player::MEDIA_PLAYER_STATE_ANNOUNCING);
    observer.source_event("va_start", "");
    observer.source_event("va_listening", "");
    settle(); assert(announcement_stops == 0);
    media(media_player::MEDIA_PLAYER_STATE_IDLE); event("va_end"); inactive();
  } else if (std::strcmp(scenario, "new_run_cannot_adopt_old_drain") == 0) {
    start(); player.publish(media_player::MEDIA_PLAYER_STATE_ANNOUNCING);
    player.publish(media_player::MEDIA_PLAYER_STATE_IDLE);
    observer.source_event("va_start", "");
    observer.source_event("va_listening", "");
    observer.source_event("va_thinking", "");
    observer.source_event("va_responding", "");
    observer.source_event("va_end", "");
    settle(); assert(announcement_stops == 0);
    assert(runtime.is_activity_active("va_responding"));
    assert(!runtime.is_activity_active("va_response_drained"));
    media(media_player::MEDIA_PLAYER_STATE_ANNOUNCING);
    media(media_player::MEDIA_PLAYER_STATE_IDLE); inactive();
  } else if (std::strcmp(scenario, "new_playback_invalidates_stop") == 0) {
    start(); player.publish(media_player::MEDIA_PLAYER_STATE_ANNOUNCING);
    player.publish(media_player::MEDIA_PLAYER_STATE_IDLE);
    observer.source_event("va_responding", "");
    player.publish(media_player::MEDIA_PLAYER_STATE_ANNOUNCING);
    settle(); assert(announcement_stops == 0);
    event("va_end"); media(media_player::MEDIA_PLAYER_STATE_IDLE); inactive();
  } else if (std::strcmp(scenario, "no_tts_listening") == 0 ||
      std::strcmp(scenario, "no_tts_thinking") == 0) {
    start();
    if (std::strcmp(scenario, "no_tts_thinking") == 0) event("va_thinking");
    event("va_end"); inactive();
  } else if (std::strcmp(scenario, "late_announcement") == 0) {
    response(); event("va_end");
    assert(runtime.is_activity_active("va_responding"));
    assert(runtime.is_activity_active("va_run_ended"));
    assert(std::strcmp(runtime.get_policy("audio_policy"), "duck") == 0);
    // No fabricated idle, timeout or polling ends a response awaiting playback.
    settle(); assert(runtime.is_activity_active("va_responding"));
    media(media_player::MEDIA_PLAYER_STATE_ANNOUNCING);
    media(media_player::MEDIA_PLAYER_STATE_IDLE); inactive();
  } else if (std::strcmp(scenario, "audio_first_music") == 0) {
    response(); media(media_player::MEDIA_PLAYER_STATE_ANNOUNCING);
    media(media_player::MEDIA_PLAYER_STATE_PLAYING);
    assert(runtime.is_activity_active("va_response_drained"));
    assert(runtime.is_activity_active("va_responding"));
    event("va_end"); inactive(); assert(runtime.is_activity_active("media"));
  } else if (std::strcmp(scenario, "error") == 0 ||
             std::strcmp(scenario, "disconnect") == 0) {
    response(); media(media_player::MEDIA_PLAYER_STATE_ANNOUNCING);
    event(std::strcmp(scenario, "error") == 0 ? "va_error" : "va_client_disconnected");
    // VA failure cannot falsify a still-active player-owned announcement.
    assert(!runtime.is_activity_active("va_responding"));
    assert(runtime.is_activity_active("announcement"));
    media(media_player::MEDIA_PLAYER_STATE_IDLE); inactive();
  } else if (std::strcmp(scenario, "stop_ack") == 0) {
    response(); media(media_player::MEDIA_PLAYER_STATE_ANNOUNCING);
    runtime.event("voice_stop");
    event("va_end"); media(media_player::MEDIA_PLAYER_STATE_IDLE);
    assert(runtime.is_activity_active("va_stopping"));
    runtime.event("va_stop_complete"); inactive();
  } else if (std::strcmp(scenario, "barge_after_run_end") == 0 ||
             std::strcmp(scenario, "barge_after_audio_drain") == 0) {
    const bool run_ended=std::strcmp(scenario, "barge_after_run_end") == 0;
    response(); media(media_player::MEDIA_PLAYER_STATE_ANNOUNCING);
    if (run_ended) event("va_end");
    else media(media_player::MEDIA_PLAYER_STATE_IDLE);
    event("wake_word"); media(media_player::MEDIA_PLAYER_STATE_IDLE);
    runtime.event("va_stop_complete");
    // The existing binding may start VA after is_running() acknowledges stop,
    // without needing another HA run-end or an on_idle callback.
    start();
    assert(runtime.is_activity_active("va_listening"));
    assert(!runtime.is_activity_active("va_barging"));
    event("va_thinking"); event("va_responding");
    if (run_ended) {
      media(media_player::MEDIA_PLAYER_STATE_ANNOUNCING);
      media(media_player::MEDIA_PLAYER_STATE_IDLE);
      // The old run-end must not stand in for this run's still-missing end.
      assert(runtime.is_activity_active("va_responding"));
      assert(runtime.is_activity_active("va_response_drained"));
      event("va_end"); inactive();
    } else {
      event("va_end");
      // The old drain must not stand in for this run's still-pending playout.
      assert(runtime.is_activity_active("va_responding"));
      media(media_player::MEDIA_PLAYER_STATE_ANNOUNCING);
      media(media_player::MEDIA_PLAYER_STATE_IDLE); inactive();
    }
  } else {
    assert(false);
  }
  assert(idle_events == 0);  // No noncontinuous va_idle was supplied or synthesized.
  assert(!runtime.loop_enabled() && !observer.loop_enabled());
}
''')
    binary = directory / "upstream_completion"
    result = subprocess.run([
        "g++", "-std=c++17", "-Wall", "-Wextra", "-Werror",
        "-fsanitize=address,undefined", "-fno-omit-frame-pointer",
        "-DUSE_RUNTIME_CONTROLLER_SOURCE_EVENTS", "-DUSE_RUNTIME_CONTROLLER_VOICE_ASSISTANT",
        "-DUSE_RUNTIME_CONTROLLER_MEDIA_PLAYER", "-DUSE_RUNTIME_CONTROLLER_VOICE_MEDIA",
        "-I", str(stubs), "-I", str(COMPONENT),
        "-I", str(ROOT), str(source),
        *(str(COMPONENT / name) for name in (
            "runtime_controller.cpp", "runtime_controller_state.cpp", "runtime_network_observers.cpp")),
        "-o", str(binary),
    ], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return binary


@pytest.mark.parametrize("scenario", [
    "no_tts_listening", "no_tts_thinking", "late_announcement", "audio_first_music",
    "error", "disconnect", "stop_ack", "barge_after_run_end", "barge_after_audio_drain",
    "playback_responding_first_end_first", "playback_responding_first_drain_first",
    "playback_first_end_first", "playback_first_drain_first",
    "playback_first_listening_end_first", "playback_first_listening_drain_first",
    "foreign_announcement", "new_run_invalidates_stop", "new_playback_invalidates_stop",
    "drain_before_response_callback", "explicit_stop_keeps_intent",
    "explicit_stop_queued_first",
    "stopping_rejects_stale_response", "new_run_cannot_adopt_old_drain",
])
def test_public_completion_does_not_require_noncontinuous_on_idle(
    upstream_completion_binary, scenario,
):
    result = subprocess.run(
        [str(upstream_completion_binary), scenario], capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
