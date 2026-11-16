"""Test both the independent minimum and the coordinated Core in host CI."""
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_host_matrix_keeps_legacy_and_adds_the_immutable_coordinated_core():
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text())
    job = workflow["jobs"]["contract"]
    matrix = job["strategy"]["matrix"]["include"]
    assert {item["esphome"] for item in matrix} == {"2026.10.0", "373224c1"}
    choices = {item["esphome"]: item["requirement"] for item in matrix}
    assert choices["2026.10.0"] == "esphome==2026.10.0"
    assert choices["373224c1"] == "esphome @ git+https://github.com/esphome/esphome.git@373224c141dceadbb67ace263040cbfc802c5968"
    install = next(step for step in job["steps"] if step.get("name") == "Install test dependencies")
    assert '"${{ matrix.requirement }}"' in install["run"]
    assert all("esphome compile" not in step.get("run", "") for step in job["steps"])
