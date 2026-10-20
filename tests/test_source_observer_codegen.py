"""Generate real ESPHome automations, preserving each source trigger's owner."""

import os
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def test_voice_timer_and_api_observers_extend_one_automation(tmp_path):
    config = tmp_path / "observer.yaml"
    build = tmp_path / "build"
    config.write_text(f"""
esphome:
  name: observer-contract
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
  on_client_connected:
    then:
      - logger.log: user-api-connected
external_components:
  - source: {ROOT / 'esphome/components'}
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
  - platform: mixer
    id: audio_mixer
    output_speaker: hardware_speaker
    source_speakers:
      - id: music_input
      - id: announcement_input
media_player:
  - platform: speaker
    id: player
    name: Observer fixture player
    media_pipeline:
      speaker: music_input
      num_channels: 1
      format: WAV
    announcement_pipeline:
      speaker: announcement_input
      num_channels: 1
      format: WAV
output:
  - platform: template
    id: lamp_output
    type: float
    write_action: []
light:
  - platform: monochromatic
    id: status_led
    output: lamp_output
    effects:
      - pulse:
voice_assistant:
  id: va
  microphone: mic
  on_start:
    then:
      - logger.log: user-before-delay
      - delay: 5ms
      - logger.log: user-after-delay
micro_wake_word:
  id: mww
  microphone: mic
  models: []
  on_wake_word_detected:
    then:
      - logger.log: user-wake-word
runtime_controller:
  id: runtime
  observe:
    media_player: player
    voice_assistant: va
    micro_wake_word: mww
    timers: va
    api: true
  presentation:
    priorities:
      announcement: 300
  on_music:
    then:
      - light.turn_on:
          id: status_led
          effect: Pulse
  on_idle:
    then:
      - light.turn_off: status_led
  on_listening:
    then:
      - logger.log: resolved-listening
  on_state_change:
    then:
      - logger.log:
          format: '%s to %s'
          args: ['previous.c_str()', 'current.c_str()']
""")
    result = subprocess.run(
        [sys.executable, "-m", "esphome", "compile", "--only-generate", str(config)],
        env=os.environ.copy(), capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    cpp = (build / "src/main.cpp").read_text()
    for hook in ("get_start_trigger", "get_listening_trigger", "get_timer_finished_trigger",
                 "get_wake_word_detected_trigger"):
        assert cpp.count(hook + "()") == 1, hook
    assert "user-before-delay" in cpp and "user-after-delay" in cpp
    assert "user-api-connected" in cpp and "resolved-listening" in cpp
    assert "user-wake-word" in cpp
    assert "SourceEventAction" in cpp and 'set_event("va_start")' in cpp
    assert "set_presentation_trigger" in cpp
    assert 'set_activity_presentation_priority("announcement", 300)' in cpp
    assert "LightControlAction" in cpp
    assert "USE_RUNTIME_CONTROLLER_LED" not in (build / "src/esphome/core/defines.h").read_text()
    # A single normal ActionList retains the observer, user work and delay.
    start_action = re.search(r'(\w+)->set_event\("va_start"\)', cpp).group(1)
    assert re.search(r'add_actions\(\{' + start_action + r', [^}]+\}\)', cpp)
