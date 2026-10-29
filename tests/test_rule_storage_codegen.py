"""The generated capacity must match all emitted rules for each instance."""

from pathlib import Path
import re
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("count", [0, 1, 17, 62, 64])
def test_exact_rule_capacity_in_real_codegen(tmp_path, count):
    rules = "\n".join("        - action: noop" for _ in range(count))
    events = f"  events:\n    go:\n      cases:\n{rules}\n" if count else ""
    config = tmp_path / "device.yaml"
    config.write_text(f"""
esphome:
  name: rule-storage-{count}
  build_path: {tmp_path / 'build'}
esp32:
  board: esp32-s3-devkitc-1
  framework:
    type: esp-idf
logger:
external_components:
  - source: {ROOT / 'esphome/components'}
    components: [runtime_controller]
runtime_controller:
  id: controller
  auto_events: false
  actions:
    noop:
      then: []
{events}
""")
    result = subprocess.run(
        [sys.executable, "-m", "esphome", "compile", str(config), "--only-generate"],
        capture_output=True, text=True, timeout=90,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    main = (tmp_path / "build/src/main.cpp").read_text()
    assert re.search(r"controller->set_event_rule_capacity\(0\);", main)
    assert "controller->add_event_rule(" not in main
    if count:
        assert f"controller->set_static_event_rules(controller_rules, {count});" in main
    assert "controller->set_storage_capacities(" in main
    assert main.index("controller->set_event_rule_capacity(") < main.index("controller->set_storage_in_psram(")
