#pragma once
#include <functional>
namespace esphome::light {
class LightCall {
 public:
  explicit LightCall(std::function<void()> *fn) : fn_(fn) {}
  void set_save(bool) {}
  void perform() {
    if (*this->fn_)
      (*this->fn_)();
  }
  void set_rgb(float, float, float) {}
  void set_brightness(float) {}
  void set_effect(const char *) {}

 private:
  std::function<void()> *fn_;
};
class LightState {
 public:
  std::function<void()> on_perform;
  LightCall turn_off() { return LightCall(&this->on_perform); }
  LightCall turn_on() { return LightCall(&this->on_perform); }
};
}  // namespace esphome::light
