#include "runtime_network_observers.h"

#include "esphome/components/runtime_controller/runtime_controller.h"

namespace esphome::runtime_controller {

void RuntimeNetworkObservers::setup() {
  if (this->runtime_ == nullptr) {
    this->mark_failed();
    return;
  }

#ifdef USE_RUNTIME_CONTROLLER_WIFI
  if (this->wifi_ != nullptr) {
    this->wifi_->add_connect_state_listener(this);
    // Replay after the runtime and WiFi have completed setup. Initial state
    // must not depend on whether their startup callback ran before our setup.
    this->runtime_->event(this->wifi_->is_connected() ? "wifi_connected" : "wifi_disconnected");
  }
#endif
#ifdef USE_RUNTIME_CONTROLLER_SWITCH
  if (this->microphone_mute_ != nullptr) {
    this->microphone_mute_->add_on_state_callback([this](bool muted) {
      this->runtime_->event(muted ? "mic_muted" : "mic_unmuted");
    });
    this->runtime_->event(this->microphone_mute_->state ? "mic_muted" : "mic_unmuted");
  }
  if (this->speaker_mute_ != nullptr) {
    this->speaker_mute_->add_on_state_callback([this](bool muted) {
      this->runtime_->event(muted ? "speaker_muted" : "speaker_unmuted");
    });
    this->runtime_->event(this->speaker_mute_->state ? "speaker_muted" : "speaker_unmuted");
  }
#endif
#ifdef USE_RUNTIME_CONTROLLER_MEDIA_PLAYER
  if (this->media_player_ != nullptr) {
    auto publish = [this](media_player::MediaPlayerState state) {
      const char *event = nullptr;
      switch (state) {
        case media_player::MEDIA_PLAYER_STATE_PLAYING: event = "media_playing"; break;
        case media_player::MEDIA_PLAYER_STATE_PAUSED: event = "media_paused"; break;
        case media_player::MEDIA_PLAYER_STATE_ANNOUNCING: event = "announcement_started"; break;
        case media_player::MEDIA_PLAYER_STATE_NONE:
        case media_player::MEDIA_PLAYER_STATE_IDLE:
        case media_player::MEDIA_PLAYER_STATE_OFF:
        case media_player::MEDIA_PLAYER_STATE_ON: event = "media_idle"; break;
        default: break;
      }
      if (event != nullptr) this->runtime_->event(event);
    };
    this->media_player_->add_on_state_callback(publish);
    publish(this->media_player_->state);
  }
#endif
  // All later work arrives through listeners; this adapter has no poll loop.
  this->disable_loop();
}

#ifdef USE_RUNTIME_CONTROLLER_WIFI
void RuntimeNetworkObservers::on_wifi_connect_state(StringRef ssid, std::span<const uint8_t, 6>) {
  // ESPHome sends an empty SSID through the same listener on disconnect.
  this->runtime_->event(ssid.empty() ? "wifi_disconnected" : "wifi_connected");
}
#endif

}  // namespace esphome::runtime_controller
