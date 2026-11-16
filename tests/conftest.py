"""Use the real ESPHome container in otherwise isolated controller host tests."""

import importlib.util
import os
from pathlib import Path

import pytest


@pytest.fixture(scope="session", autouse=True)
def native_static_ring_buffer(tmp_path_factory):
    utility = Path(__file__).with_name("native_core_headers.py")
    spec = importlib.util.spec_from_file_location("_runtime_native_core_headers", utility)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    directory = module.write_static_ring_buffer_header(
        tmp_path_factory.mktemp("native-static-ring-buffer")
    )
    previous = os.environ.get("CPLUS_INCLUDE_PATH")
    os.environ["CPLUS_INCLUDE_PATH"] = str(directory) + (os.pathsep + previous if previous else "")
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("CPLUS_INCLUDE_PATH", None)
        else:
            os.environ["CPLUS_INCLUDE_PATH"] = previous
