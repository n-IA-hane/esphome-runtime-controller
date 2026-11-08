"""Exercise real runtime presence with the archived API callback lifecycle."""

import os
from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def presence_binary(tmp_path_factory):
    directory = tmp_path_factory.mktemp("presence")
    stubs = directory / "stubs"
    shutil.copytree(ROOT / "tests/fixtures/core/stubs", stubs)
    component = stubs / "esphome/core/component.h"
    header = component.read_text().replace(
        "#pragma once", "#pragma once\n#include <functional>\n#include <map>\n#include <string>\n#include <cstdint>"
    ).replace("constexpr float PROCESSOR = 400;", "constexpr float PROCESSOR = 400, AFTER_WIFI = 200;")
    header = header.replace("  void mark_failed()", """
  struct Timeout { uint64_t due; std::function<void()> fn; };
  uint64_t now{0};
  std::map<std::string, Timeout> timers;
  void set_timeout(const char *name, unsigned delay, std::function<void()> fn) {
    timers.insert_or_assign(name, Timeout{now + delay, std::move(fn)});
  }
  bool cancel_timeout(const char *name) { return timers.erase(name)>0; }
  void advance(unsigned ms) {
    now += ms;
    for (auto it=timers.begin(); it!=timers.end();) {
      if(it->second.due>now) {++it; continue;}
      auto fn=std::move(it->second.fn); it=timers.erase(it); fn();
    }
  }
  void mark_failed()""")
    component.write_text(header)
    api = stubs / "esphome/components/api/api_server.h"
    api.parent.mkdir(parents=True)
    shutil.copy2(ROOT / "tests/fixtures/api/api_server.h", api)
    implementation = ROOT / "esphome/components/runtime_controller"
    observer = Path(os.environ.get("RUNTIME_OBSERVER_SOURCE", str(implementation / "runtime_network_observers.cpp")))
    binary = directory / "presence"
    command = [
        "g++", "-std=c++17", "-Wall", "-Wextra", "-Werror",
        "-DUSE_RUNTIME_CONTROLLER_SOURCE_EVENTS", "-DUSE_RUNTIME_CONTROLLER_API",
        "-DUSE_RUNTIME_CONTROLLER_API_CLIENT_OUTPUT",
        "-I", str(stubs), "-I", str(implementation), "-I", str(ROOT),
        str(ROOT / "tests/fixtures/api/presence.cpp"),
        str(implementation / "runtime_controller.cpp"),
        str(implementation / "runtime_controller_state.cpp"), str(observer), "-o", str(binary),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return binary


@pytest.mark.parametrize("scenario", [
    "no_hello", "loggers", "duplicate_names", "offline_delay_reconnect",
    "boot_cancel", "boot_snapshot", "event_replay", "authentication_not_name",
    "pending_removal", "boot_offline", "null_server",
])
def test_presence(presence_binary, scenario):
    result = subprocess.run([str(presence_binary), scenario], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
