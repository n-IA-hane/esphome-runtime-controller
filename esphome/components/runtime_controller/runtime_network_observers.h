#pragma once

#include "esphome/core/component.h"
#include <cstdint>
#ifdef USE_RUNTIME_CONTROLLER_SOURCE_EVENTS
#include "esphome/core/automation.h"
#endif
#ifdef USE_RUNTIME_CONTROLLER_VOICE_ASSISTANT
#include "esphome/components/voice_assistant/voice_assistant.h"
#endif

#ifdef USE_RUNTIME_CONTROLLER_WIFI
#include "esphome/components/wifi/wifi_component.h"
#endif
#if defined(USE_RUNTIME_CONTROLLER_MICROPHONE_MUTE) || defined(USE_RUNTIME_CONTROLLER_SPEAKER_MUTE)
#include "esphome/components/switch/switch.h"
#endif

#ifdef USE_RUNTIME_CONTROLLER_MEDIA_PLAYER
#include "esphome/components/media_player/media_player.h"
#endif

#if defined(USE_RUNTIME_CONTROLLER_WIFI) || defined(USE_RUNTIME_CONTROLLER_MEDIA_PLAYER) || \
    defined(USE_RUNTIME_CONTROLLER_MICROPHONE_MUTE) || defined(USE_RUNTIME_CONTROLLER_SPEAKER_MUTE) || \
    defined(USE_RUNTIME_CONTROLLER_SOURCE_EVENTS)

namespace esphome::runtime_controller {

class RuntimeController;

// Optional native lifecycle adapters. These subscribe beside user automations;
// they never install another Automation parent on a component's Trigger.
class RuntimeNetworkObservers : public Component
#ifdef USE_RUNTIME_CONTROLLER_WIFI
    , public wifi::WiFiConnectStateListener
#endif
{
 public:
  void set_runtime(RuntimeController *runtime) { this->runtime_ = runtime; }
  void setup() override;
#ifdef USE_RUNTIME_CONTROLLER_API_CLIENT_OUTPUT
  template<typename T> void set_api_clients_output(T *output) {
    this->api_clients_output_ = output;
    this->publish_api_clients_ = [](void *target, uint16_t count) { static_cast<T *>(target)->value() = count; };
  }
#endif
#ifdef USE_RUNTIME_CONTROLLER_SOURCE_EVENTS
  void source_event(const char *event, const std::string &text);
#endif
#ifdef USE_RUNTIME_CONTROLLER_VOICE_ASSISTANT
  void set_voice_assistant(voice_assistant::VoiceAssistant *source, bool observe_state, bool observe_timers = false) {
    this->voice_assistant_ = source;
    this->observe_voice_state_ = observe_state;
    this->observe_timers_ = observe_timers;
  }
#endif
#ifdef USE_RUNTIME_CONTROLLER_MEDIA_PLAYER
  void set_media_player(media_player::MediaPlayer *player) { this->media_player_ = player; }
#endif
  float get_setup_priority() const override { return setup_priority::AFTER_WIFI; }

#ifdef USE_RUNTIME_CONTROLLER_WIFI
  void set_wifi(wifi::WiFiComponent *wifi) { this->wifi_ = wifi; }
  void on_wifi_connect_state(StringRef ssid, std::span<const uint8_t, 6> bssid) override;
#endif
#ifdef USE_RUNTIME_CONTROLLER_MICROPHONE_MUTE
  void set_microphone_mute(switch_::Switch *mute) { this->microphone_mute_ = mute; }
#endif
#ifdef USE_RUNTIME_CONTROLLER_SPEAKER_MUTE
  void set_speaker_mute(switch_::Switch *mute) { this->speaker_mute_ = mute; }
#endif

 protected:
  RuntimeController *runtime_{nullptr};
#ifdef USE_RUNTIME_CONTROLLER_API
  uint16_t api_clients_{0};
  void publish_api_presence_();
#endif
#ifdef USE_RUNTIME_CONTROLLER_API_CLIENT_OUTPUT
  void *api_clients_output_{nullptr};
  void (*publish_api_clients_)(void *, uint16_t){nullptr};
#endif
#ifdef USE_RUNTIME_CONTROLLER_VOICE_ASSISTANT
  voice_assistant::VoiceAssistant *voice_assistant_{nullptr};
  bool observe_voice_state_{false};
  bool observe_timers_{false};
#endif
#ifdef USE_RUNTIME_CONTROLLER_MEDIA_PLAYER
  media_player::MediaPlayer *media_player_{nullptr};
#endif
#ifdef USE_RUNTIME_CONTROLLER_WIFI
  wifi::WiFiComponent *wifi_{nullptr};
#endif
#ifdef USE_RUNTIME_CONTROLLER_MICROPHONE_MUTE
  switch_::Switch *microphone_mute_{nullptr};
#endif
#ifdef USE_RUNTIME_CONTROLLER_SPEAKER_MUTE
  switch_::Switch *speaker_mute_{nullptr};
#endif
};

#ifdef USE_RUNTIME_CONTROLLER_SOURCE_EVENTS
template<typename... Ts> class SourceEventAction : public Action<Ts...>, public Parented<RuntimeNetworkObservers> {
 public:
  void set_event(const char *event) { this->event_ = event; }
  TEMPLATABLE_VALUE(std::string, text)
  TEMPLATABLE_VALUE(bool, enabled)
  void play(const Ts &...x) override {
    if (this->enabled_.value(x...))
      this->parent_->source_event(this->event_, this->text_.value(x...));
  }

 protected:
  const char *event_{nullptr};
};
#endif

}  // namespace esphome::runtime_controller

#endif
