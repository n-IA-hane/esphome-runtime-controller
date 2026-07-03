# Source

This repository was extracted from `n-IA-hane/esphome-intercom` during the 2026.7.0-dev pre-release split.

Initial contents:

- `esphome/components/runtime_controller`
- `packages/runtime_controller`

The goal is to keep runtime state arbitration independently reusable while `esphome-intercom` focuses on VoIP/Home Assistant integration and `esphome-audio-stack` focuses on audio hardware, AEC and AFE.
