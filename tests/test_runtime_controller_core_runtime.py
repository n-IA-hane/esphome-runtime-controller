"""Execute the production C++ controller with small host-side ESPHome adapters."""

from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "esphome" / "components" / "runtime_controller"
FIXTURES = ROOT / "tests" / "fixtures" / "core"
CORE_CASES = (
    "snapshot",
    "event_order",
    "nested_setters",
    "fifo",
    "event_bounds",
    "action_bounds",
    "priorities",
    "derived",
    "allocation_failure",
)
VOIP_CASES = ("voip_reentrancy", "voip_capture", "voip_overflow")


@pytest.fixture(scope="session")
def core_binary(request, tmp_path_factory):
    compiler = shutil.which("g++")
    assert compiler is not None, "The production-core regression tests require g++"
    voip = request.param
    build = tmp_path_factory.mktemp("runtime-core-voip" if voip else "runtime-core")
    binary = build / "runtime-core-tests"
    command = [
        compiler,
        "-std=c++17",
        "-Wall",
        "-Wextra",
        "-Werror",
        "-DUSE_RUNTIME_CONTROLLER_DEBUG",
        "-DUSE_RUNTIME_CONTROLLER_LED",
        "-DUSE_RUNTIME_CONTROLLER_OUTPUT_SCRIPT",
        "-I",
        str(FIXTURES / "stubs"),
        "-I",
        str(COMPONENT),
        str(FIXTURES / "runtime_controller_core_test.cpp"),
        str(COMPONENT / "runtime_controller.cpp"),
        str(COMPONENT / "runtime_controller_state.cpp"),
        "-o",
        str(binary),
    ]
    if voip:
        command.append("-DUSE_RUNTIME_CONTROLLER_VOIP")
    result = subprocess.run(command, text=True, capture_output=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    return binary


CASES = [
    pytest.param(voip, case, id=f"{'voip' if voip else 'plain'}-{case}")
    for voip in (False, True)
    for case in CORE_CASES + (VOIP_CASES if voip else ())
]


@pytest.mark.parametrize(("core_binary", "case"), CASES, indirect=("core_binary",))
def test_production_core(core_binary, case):
    result = subprocess.run(
        [str(core_binary), case],
        cwd=core_binary.parent,
        text=True,
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == f"PASS {case}"
