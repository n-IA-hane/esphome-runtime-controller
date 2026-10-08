"""Explicit LED mappings without inherited presets."""

import os
from pathlib import Path
import subprocess
import sys

import pytest

from test_runtime_controller_contract import _load_component_module

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("preset", ["none", "NONE", "None"])
def test_none_schema_preserves_only_explicit_states(preset):
    module = _load_component_module()
    config = module.LED_OUTPUT_SCHEMA({
        "id": "status_led", "preset": preset,
        "states": {"listening": {"color": [0, 1, 0], "brightness": 0.3, "effect": "Custom listening"}},
    })
    assert config["preset"] == "none"
    assert module._merged_led_states(config) == {
        "listening": {"color": [0, 1, 0], "brightness": 0.3, "effect": "Custom listening"},
    }
    defaults = module.LED_OUTPUT_SCHEMA({"id": "status_led"})
    assert defaults["preset"] == "ws2812_ring"
    assert "idle" in module._merged_led_states(defaults)


def test_none_codegen_uses_configured_effect_without_default_states(tmp_path):
    path = tmp_path / "led.yaml"
    path.write_text(f"""
esphome:
  name: runtime-led-none
esp32:
  board: esp32-s3-devkitc-1
  framework:
    type: esp-idf
external_components:
  - source: {ROOT / 'esphome/components'}
    components: [runtime_controller]
output:
  - platform: ledc
    pin: GPIO4
    id: red
  - platform: ledc
    pin: GPIO5
    id: green
  - platform: ledc
    pin: GPIO6
    id: blue
light:
  - platform: rgb
    id: status_led
    red: red
    green: green
    blue: blue
    effects:
      - pulse:
          name: Custom listening
runtime_controller:
  activities:
    listening:
      initial: true
      policies:
        led_status: listening
  outputs:
    led:
      id: status_led
      preset: NONE
      states:
        listening:
          color: [0%, 100%, 0%]
          brightness: 30%
          effect: Custom listening
""")
    result = subprocess.run([
        os.environ.get("ESPHOME_PYTHON", sys.executable), "-m", "esphome", "compile", str(path), "--only-generate",
    ], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    generated = next(tmp_path.rglob("main.cpp")).read_text()
    statements = [line for line in generated.splitlines() if "->add_led_state(" in line]
    assert len(statements) == 1
    assert '"listening", 0.0f, 1.0f, 0.0f, 0.3f, "Custom listening"' in statements[0]


def test_unmapped_state_preserves_current_led_behavior(tmp_path):
    component = ROOT / "esphome/components/runtime_controller"
    stubs = ROOT / "tests/fixtures/core/stubs"
    source = tmp_path / "led.cpp"
    source.write_text(r'''
#include "runtime_controller.h"
#include "esphome/components/light/light_state.h"
#include <cassert>
using esphome::runtime_controller::RuntimeController;
struct Probe:RuntimeController {using RuntimeController::apply_led_state_;};
int main() {
  Probe controller; esphome::light::LightState led; unsigned writes=0;
  led.on_perform=[&]{writes++;}; controller.set_led_light(&led);
  controller.add_led_state("listening",0,1,0,0.3,"Custom listening");
  controller.apply_led_state_("listening"); assert(writes==1);
  controller.apply_led_state_("unconfigured"); assert(writes==1);
  controller.apply_led_state_(nullptr); assert(writes==2);
}
''')
    binary = tmp_path / "led"
    subprocess.run([
        "g++", "-std=c++17", "-Wall", "-Wextra", "-Werror", "-DUSE_RUNTIME_CONTROLLER_LED",
        "-I", str(stubs), "-I", str(component), str(source),
        str(component / "runtime_controller.cpp"), str(component / "runtime_controller_state.cpp"),
        "-o", str(binary),
    ], check=True, capture_output=True, text=True)
    subprocess.run([str(binary)], check=True, capture_output=True, text=True)
