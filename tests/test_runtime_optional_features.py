"""Compile the real reducer without unused component headers and compare storage."""

from itertools import combinations
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "esphome/components/runtime_controller"
STUBS = ROOT / "tests/fixtures/core/stubs"


def test_optional_components_remove_code_and_storage(tmp_path):
    sizes = {}
    features = ("LED", "OUTPUT_SCRIPT", "VOIP")
    for count in range(4):
        for selected in combinations(features, count):
            work = tmp_path / ("_".join(selected) or "base")
            work.mkdir()
            shutil.copytree(STUBS / "esphome/core", work / "esphome/core")
            for flag, component in (
                ("LED", "light"),
                ("OUTPUT_SCRIPT", "script"),
                ("VOIP", "voip_stack"),
            ):
                if flag in selected:
                    shutil.copytree(
                        STUBS / "esphome/components" / component,
                        work / "esphome/components" / component,
                    )
            main = work / "main.cpp"
            main.write_text(r"""
#include "runtime_controller.h"
#include <cassert>
#include <cstring>
#include <iostream>
#ifdef USE_RUNTIME_CONTROLLER_LED
#include "esphome/components/light/light_state.h"
#endif
#ifdef USE_RUNTIME_CONTROLLER_OUTPUT_SCRIPT
#include "esphome/components/script/script.h"
#endif
#ifdef USE_RUNTIME_CONTROLLER_VOIP
#include "esphome/components/voip_stack/voip_stack.h"
#endif
using esphome::runtime_controller::RuntimeController;
struct Probe : RuntimeController {
  static size_t storage_size() { return sizeof(Storage); }
};
int main() {
  Probe r;
  r.add_activity("idle", 0, true);
  r.add_activity_policy("idle", "led_status", "idle");
  r.add_activity("busy", 10, false);
  r.add_activity_policy("busy", "led_status", "busy");
  r.add_event_activity("start", "busy", true);
  r.add_event_activity("stop", "busy", false);
#ifdef USE_RUNTIME_CONTROLLER_LED
  esphome::light::LightState light;
  unsigned rendered=0;
  light.on_perform=[&] { ++rendered; };
  r.set_led_light(&light);
  r.add_led_state("idle", 0, 0, 0, 0, "None");
  r.add_led_state("busy", 0, 1, 0, 1, "None");
#endif
#ifdef USE_RUNTIME_CONTROLLER_OUTPUT_SCRIPT
  esphome::script::Script<> script;
  unsigned scripts=0;
  script.fn=[&] { ++scripts; };
  r.set_output_script(&script);
#endif
#ifdef USE_RUNTIME_CONTROLLER_VOIP
  esphome::voip_stack::VoipStack phone;
  r.set_voip(&phone);
  r.set_voip_activity_prefix("voip:");
  r.add_activity("voip:ringing", 20, false);
  r.add_activity_policy("voip:ringing", "led_status", "busy");
#endif
  r.setup();
  assert(std::strcmp(r.get_policy("led_status"), "idle")==0);
  r.event("start");
  assert(r.is_activity_active("busy"));
  assert(std::strcmp(r.get_policy("led_status"), "busy")==0);
  r.event("stop");
  assert(!r.is_activity_active("busy"));
  assert(std::strcmp(r.get_policy("led_status"), "idle")==0);
#ifdef USE_RUNTIME_CONTROLLER_LED
  assert(rendered==3);
#endif
#ifdef USE_RUNTIME_CONTROLLER_OUTPUT_SCRIPT
  assert(scripts==3);
#endif
#ifdef USE_RUNTIME_CONTROLLER_VOIP
  phone.change("ringing");
  assert(r.is_activity_active("voip:ringing"));
  phone.change("idle");
  assert(!r.is_activity_active("voip:ringing"));
#endif
  std::cout << sizeof(Probe) << " " << Probe::storage_size() << "\n";
}
""")
            binary = work / "probe"
            compiled = subprocess.run(
                [
                    "g++",
                    "-std=c++17",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    *(f"-DUSE_RUNTIME_CONTROLLER_{flag}" for flag in selected),
                    "-I" + str(work),
                    "-I" + str(COMPONENT),
                    str(COMPONENT / "runtime_controller.cpp"),
                    str(COMPONENT / "runtime_controller_state.cpp"),
                    str(main),
                    "-o",
                    str(binary),
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            assert compiled.returncode == 0, compiled.stderr
            run = subprocess.run(
                [str(binary)], capture_output=True, text=True, timeout=10
            )
            assert run.returncode == 0, run.stderr
            sizes[frozenset(selected)] = tuple(map(int, run.stdout.split()))
            symbols = subprocess.check_output(["nm", "-C", str(binary)], text=True)
            if "LED" not in selected:
                assert "RuntimeController::add_led_state" not in symbols
                assert "RuntimeController::apply_led_state_" not in symbols
                assert "esphome::light::" not in symbols
            if "VOIP" not in selected:
                assert "RuntimeController::on_voip_event" not in symbols
                assert "RuntimeController::capture_voip_activity_" not in symbols
                assert "esphome::voip_stack::" not in symbols
            if "OUTPUT_SCRIPT" not in selected:
                assert "esphome::script::" not in symbols
    # Compare actual layouts, not source text. No LED means no 32-entry LED table.
    for selected, (object_size, storage_size) in sizes.items():
        if "LED" not in selected:
            with_led = sizes[selected | {"LED"}]
            assert with_led[0] > object_size
            assert with_led[1] >= storage_size + 32 * 24
        if "VOIP" not in selected:
            assert sizes[selected | {"VOIP"}][0] >= object_size + 128
        if "OUTPUT_SCRIPT" not in selected:
            assert sizes[selected | {"OUTPUT_SCRIPT"}][0] > object_size
