"""Qualify public VA completion for each upstream-supported output contract."""

import os
from pathlib import Path
import subprocess
import sys

import pytest

from test_runtime_profile_runtime import _profile_cpp


ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "esphome/components/runtime_controller"
STUBS = ROOT / "tests/fixtures/core/stubs"


@pytest.mark.parametrize("backend", ["speaker", "media_player", "none"])
def test_upstream_schema_and_generated_stream_end_hook(tmp_path, backend):
    output = {"speaker": "  speaker: hardware_speaker\n",
              "media_player": "  media_player: player\n", "none": ""}[backend]
    player = """
media_player:
  - platform: speaker
    id: player
    name: Backend fixture
    announcement_pipeline:
      speaker: hardware_speaker
      num_channels: 1
      format: WAV
""" if backend == "media_player" else ""
    observe = "    media_player: player\n" if backend == "media_player" else ""
    config = tmp_path / "backend.yaml"
    build = tmp_path / "build"
    config.write_text(f"""
esphome:
  name: voice-backend-contract
  build_path: {build}
esp32:
  board: esp32-s3-devkitc-1
  framework:
    type: esp-idf
logger:
wifi:
  ssid: test-network
  password: test-password
api:
external_components:
  - source: {COMPONENT.parent}
    components: [runtime_controller]
i2s_audio:
  id: audio_bus
  i2s_lrclk_pin: GPIO4
  i2s_bclk_pin: GPIO5
microphone:
  - platform: i2s_audio
    id: mic
    i2s_audio_id: audio_bus
    adc_type: external
    i2s_din_pin: GPIO6
    pdm: false
speaker:
  - platform: i2s_audio
    id: hardware_speaker
    i2s_audio_id: audio_bus
    dac_type: external
    i2s_dout_pin: GPIO7
    sample_rate: 16000
{player}
voice_assistant:
  id: va
  microphone: mic
{output}  on_end:
    then:
      - logger.log: user-end
{"  on_tts_stream_end:\n    then:\n      - logger.log: user-stream-end" if backend == "speaker" else ""}
runtime_controller:
  id: runtime
  profile: full_voice_voip
  features: [voice_assistant{", media_player" if backend == "media_player" else ""}]
  actions:
    voice_start:
      then: []
    voice_cancel_response:
      then: []
    voice_cancel_pipeline:
      then: []
    voice_stop_all:
      then: []
    voice_stop_pipeline:
      then: []
    cancel_response_cleanup:
      then: []
    stop_announcement:
      then: []
  observe:
    voice_assistant: va
{observe}  on_idle:
    then:
      - logger.log: resolved-idle
""")
    result = subprocess.run(
        [sys.executable, "-m", "esphome", "compile", "--only-generate", str(config)],
        env=os.environ.copy(), capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    cpp = (build / "src/main.cpp").read_text()
    defines = (build / "src/esphome/core/defines.h").read_text()
    assert cpp.count("get_tts_stream_end_trigger()") == (backend == "speaker")
    assert ('set_event("va_tts_stream_end")' in cpp) == (backend == "speaker")
    assert "user-end" in cpp
    assert ("USE_RUNTIME_CONTROLLER_VOICE_MEDIA" in defines) == (backend == "media_player")
    if backend == "speaker":
        assert "user-stream-end" in cpp


@pytest.mark.parametrize("backend", ["speaker", "none"])
@pytest.mark.parametrize("independent_player", [False, True])
@pytest.mark.parametrize("order", ["end_first", "drain_first"])
def test_real_reducer_joins_only_observable_playback(tmp_path, backend, order, independent_player):
    source = tmp_path / "backend.cpp"
    source.write_text(_profile_cpp(True, {
        "features": ["voice_assistant"] + (["media_player"] if independent_player else []),
        "_voice_playback": backend,
    }) + r'''
#include <cassert>
#include <cstring>
int main(int argc, char **argv) {
  assert(argc == 3);
  RuntimeController r; load_profile(r);
  r.event("boot_ready"); r.event("wifi_connected"); r.event("ha_connected");
  r.event("va_client_connected");
  for (unsigned run=0; run<2; ++run) {
    r.event("va_start"); r.event("va_listening"); r.event("va_thinking");
    r.event("va_responding");
    assert(std::strcmp(r.get_policy("va_state"), "responding") == 0);
    assert(std::strcmp(r.get_policy("audio_policy"), "duck") == 0);
    // A separately observed player's completion does not drain direct-speaker
    // output or supply the other half of its completion join.
    r.event("announcement_started"); r.event("media_idle");
    assert(!r.is_activity_active("va_response_drained"));
    const bool speaker=std::strcmp(argv[1], "speaker") == 0;
    const bool drain_first=std::strcmp(argv[2], "drain_first") == 0;
    if (speaker && drain_first) r.event("va_tts_stream_end");
    r.event("va_end");
    if (speaker && !drain_first) {
      assert(r.is_activity_active("va_responding"));
      assert(std::strcmp(r.get_policy("audio_policy"), "duck") == 0);
      r.event("va_tts_stream_end");
    }
    for (const char *name : {"va_start_requested", "va_starting", "va_listening",
         "va_thinking", "va_responding", "va_run_ended", "va_response_drained"})
      assert(!r.is_activity_active(name));
    assert(std::strcmp(r.get_policy("va_state"), "idle") == 0);
    assert(std::strcmp(r.get_policy("audio_policy"), "normal") == 0);
  }
}
''')
    binary = tmp_path / "backend"
    result = subprocess.run([
        "g++", "-std=c++17", "-Wall", "-Wextra", "-Werror",
        "-fsanitize=address,undefined", "-fno-omit-frame-pointer",
        "-I", str(STUBS), "-I", str(COMPONENT), str(source),
        str(COMPONENT / "runtime_controller.cpp"),
        str(COMPONENT / "runtime_controller_state.cpp"), "-o", str(binary),
    ], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    result = subprocess.run([str(binary), backend, order], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
