"""Extract the unchanged installed ESPHome template for isolated host compilers."""

import hashlib
import json
import os
from pathlib import Path


def _installed_helpers():
    import esphome

    return Path(esphome.__file__).parent / "core/helpers.h"


def write_static_ring_buffer_header(directory, source_root=None):
    source_root = source_root or os.environ.get("ESPHOME_SOURCE_DIR")
    header = (
        Path(source_root) / "esphome/core/helpers.h"
        if source_root
        else _installed_helpers()
    )
    source = header.read_text()
    start = source.index("template<typename T, size_t N> class StaticRingBuffer {")
    opening = source.index("{", start)
    depth, end = 1, opening + 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    template = source[start : end + 1]
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "runtime_native_static_ring_buffer.h").write_text(
        "#pragma once\n#include <cstddef>\n#include <cstdint>\n"
        "#include <limits>\n#include <type_traits>\nnamespace esphome {\n"
        + template
        + "\n}\n"
    )
    (directory / "source.json").write_text(
        json.dumps(
            {
                "source": str(header),
                "header_sha256": hashlib.sha256(source.encode()).hexdigest(),
                "template_sha256": hashlib.sha256(template.encode()).hexdigest(),
            },
            indent=2,
        )
        + "\n"
    )
    return directory
