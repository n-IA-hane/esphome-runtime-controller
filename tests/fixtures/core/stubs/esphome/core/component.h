#pragma once
namespace esphome {
namespace setup_priority {
constexpr float PROCESSOR = 400;
}
class Component {
 public:
  virtual ~Component() = default;
  virtual void setup() {}
  virtual void loop() {}
  virtual void dump_config() {}
  virtual float get_setup_priority() const { return 0; }
  void mark_failed() { this->failed_ = true; }
  bool is_failed() const { return this->failed_; }
  void disable_loop() { this->loop_enabled_ = false; }
  void enable_loop_soon_any_context() { this->loop_enabled_ = true; }
  bool loop_enabled() const { return this->loop_enabled_; }

 private:
  bool failed_{false};
  bool loop_enabled_{true};
};
}  // namespace esphome
