#pragma once

#include "esphome/core/component.h"

#ifdef USE_RUNTIME_CONTROLLER_WIFI
#include "esphome/components/wifi/wifi_component.h"
#endif
#ifdef USE_RUNTIME_CONTROLLER_SWITCH
#include "esphome/components/switch/switch.h"
#endif

#ifdef USE_RUNTIME_CONTROLLER_MEDIA_PLAYER
#include "esphome/components/media_player/media_player.h"
#endif

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
#ifdef USE_RUNTIME_CONTROLLER_MEDIA_PLAYER
  void set_media_player(media_player::MediaPlayer *player) { this->media_player_ = player; }
#endif
  float get_setup_priority() const override { return setup_priority::AFTER_WIFI; }

#ifdef USE_RUNTIME_CONTROLLER_WIFI
  void set_wifi(wifi::WiFiComponent *wifi) { this->wifi_ = wifi; }
  void on_wifi_connect_state(StringRef ssid, std::span<const uint8_t, 6> bssid) override;
#endif
#ifdef USE_RUNTIME_CONTROLLER_SWITCH
  void set_microphone_mute(switch_::Switch *mute) { this->microphone_mute_ = mute; }
  void set_speaker_mute(switch_::Switch *mute) { this->speaker_mute_ = mute; }
#endif

 protected:
  RuntimeController *runtime_{nullptr};
#ifdef USE_RUNTIME_CONTROLLER_MEDIA_PLAYER
  media_player::MediaPlayer *media_player_{nullptr};
#endif
#ifdef USE_RUNTIME_CONTROLLER_WIFI
  wifi::WiFiComponent *wifi_{nullptr};
#endif
#ifdef USE_RUNTIME_CONTROLLER_SWITCH
  switch_::Switch *microphone_mute_{nullptr};
  switch_::Switch *speaker_mute_{nullptr};
#endif
};

}  // namespace esphome::runtime_controller
