"""Debug-off removes trace strings even without optimizer help; errors remain."""

from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "esphome/components/runtime_controller"
STUBS = ROOT / "tests/fixtures/core/stubs"


@pytest.mark.parametrize("debug", [False, True])
def test_debug_trace_is_compile_gated_and_preserves_reducer(tmp_path, debug):
    shutil.copytree(STUBS / "esphome/core", tmp_path / "esphome/core")
    (tmp_path / "esphome/core/log.h").write_text(r"""
#pragma once
#include <cinttypes>
#include <cstdarg>
#include <cstdio>
namespace esphome::testing {
inline void log(const char *, const char *format, ...) {
  std::va_list args;
  va_start(args, format);
  std::vfprintf(stderr, format, args);
  va_end(args);
  std::fputc('\n', stderr);
}
}
#define ESP_LOGE(...) esphome::testing::log(__VA_ARGS__)
#define ESP_LOGW(...) esphome::testing::log(__VA_ARGS__)
#define ESP_LOGI(...) esphome::testing::log(__VA_ARGS__)
#define ESP_LOGCONFIG(...) esphome::testing::log(__VA_ARGS__)
#define YESNO(x) ((x)?"YES":"NO")
""")
    main = tmp_path / "main.cpp"
    main.write_text(r"""
#include "runtime_controller.h"
#include <cassert>
using esphome::runtime_controller::RuntimeController;
int main() {
  RuntimeController controller;
  controller.set_debug(true);  // A runtime setter cannot enable absent trace code.
  controller.add_activity("busy", 1, false);
  controller.add_event_activity("start", "busy", true);
  controller.add_event_activity("stop", "busy", false);
  controller.setup();
  controller.event("start");
  assert(controller.is_activity_active("busy"));
  controller.event("stop");
  assert(!controller.is_activity_active("busy"));
  controller.request_action("missing");  // Essential warning is never gated.
  controller.dump_state("manual");
}
""")
    executable = tmp_path / "debug-gate"
    compiled = subprocess.run(
        [
            "g++", "-std=c++17", "-O0", "-Wall", "-Wextra", "-Werror",
            "-Wformat-security", "-Werror=format-security",
            *(["-DUSE_RUNTIME_CONTROLLER_DEBUG"] if debug else []),
            "-I" + str(tmp_path), "-I" + str(COMPONENT),
            str(COMPONENT / "runtime_controller.cpp"),
            str(COMPONENT / "runtime_controller_state.cpp"), str(main),
            "-o", str(executable),
        ],
        capture_output=True, text=True, timeout=60,
    )
    assert compiled.returncode == 0, compiled.stderr
    binary = executable.read_bytes()
    for trace in (b"EVENT seq=", b"REDUCE seq=", b"EVENT_QUEUE seq=", b"ACTION_RUN seq=", b"SNAPSHOT reason="):
        assert (trace in binary) == debug
    assert b"Runtime Controller configuration or storage error" in binary
    run = subprocess.run([str(executable)], capture_output=True, text=True, timeout=10)
    assert run.returncode == 0, run.stderr
    assert "Ignoring unknown action 'missing'" in run.stderr
    assert ("EVENT seq=" in run.stderr) == debug
    assert ("SNAPSHOT reason=manual" in run.stderr) == debug
