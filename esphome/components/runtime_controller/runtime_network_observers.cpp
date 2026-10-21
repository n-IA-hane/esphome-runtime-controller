#include "runtime_network_observers.h"

#if defined(USE_RUNTIME_CONTROLLER_WIFI) || defined(USE_RUNTIME_CONTROLLER_MEDIA_PLAYER) || \
    defined(USE_RUNTIME_CONTROLLER_MICROPHONE_MUTE) || defined(USE_RUNTIME_CONTROLLER_SPEAKER_MUTE) || \
    defined(USE_RUNTIME_CONTROLLER_SOURCE_EVENTS)

#include "esphome/components/runtime_controller/runtime_controller.h"
#include <cstring>

namespace esphome::runtime_controller {

void RuntimeNetworkObservers::setup() {
  if (this->runtime_ == nullptr) {
    this->mark_failed();
    return;
  }
#ifdef USE_RUNTIME_CONTROLLER_API
  this->publish_api_presence_();
#endif
#ifdef USE_RUNTIME_CONTROLLER_VOICE_ASSISTANT
  if (this->voice_assistant_ != nullptr && this->observe_timers_)
    this->runtime_->observe_activity("timer", !this->voice_assistant_->get_timers().empty());
  if (this->voice_assistant_ != nullptr && this->observe_voice_state_) {
    this->runtime_->observe_event(this->voice_assistant_->get_api_connection() != nullptr
                                      ? "va_client_connected" : "va_client_disconnected");
    // A public idle flag is authoritative. Do not invent a detailed phase for
    // a pipeline that was already running before this observer started.
    if (!this->voice_assistant_->is_running())
      this->runtime_->observe_event("va_idle");
  }
#endif

#ifdef USE_RUNTIME_CONTROLLER_WIFI
  if (this->wifi_ != nullptr) {
    this->wifi_->add_connect_state_listener(this);
    // Replay after the runtime and WiFi have completed setup. Initial state
    // must not depend on whether their startup callback ran before our setup.
    this->runtime_->event(this->wifi_->is_connected() ? "wifi_connected" : "wifi_disconnected");
  }
#endif
#ifdef USE_RUNTIME_CONTROLLER_MICROPHONE_MUTE
  if (this->microphone_mute_ != nullptr) {
    this->microphone_mute_->add_on_state_callback([this](bool muted) {
      this->runtime_->event(muted ? "mic_muted" : "mic_unmuted");
    });
    this->runtime_->event(this->microphone_mute_->state ? "mic_muted" : "mic_unmuted");
  }
#endif
#ifdef USE_RUNTIME_CONTROLLER_SPEAKER_MUTE
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
      if (event == nullptr ||
          (this->last_media_event_ != nullptr && std::strcmp(event, this->last_media_event_) == 0))
        return;
      // Volume and metadata updates may republish the same state. Store the
      // observation before dispatch because an action may change the player.
      this->last_media_event_ = event;
      this->runtime_->event(event);
    };
    this->media_player_->add_on_state_callback(publish);
    publish(this->media_player_->state);
  }
#endif
  // All later work arrives through listeners; this adapter has no poll loop.
  this->disable_loop();
}

#ifdef USE_RUNTIME_CONTROLLER_SOURCE_EVENTS
void RuntimeNetworkObservers::source_event(const char *event, const std::string &text) {
  (void) text;
  if (this->runtime_ == nullptr || event == nullptr)
    return;
#ifdef USE_RUNTIME_CONTROLLER_API
  if (std::strcmp(event, "api_connected") == 0 || std::strcmp(event, "api_disconnected") == 0) {
    if (text.empty() || text.rfind("ESPHome Logs", 0) == 0 || text.rfind("ESPHome Dashboard", 0) == 0 ||
        text.rfind("ESPHome Web", 0) == 0)
      return;
    if (std::strcmp(event, "api_connected") == 0) {
      if (this->api_clients_ < UINT16_MAX)
        ++this->api_clients_;
    } else {
      if (this->api_clients_ > 0)
        --this->api_clients_;
    }
    this->publish_api_presence_();
    return;
  }
#endif
#ifdef USE_RUNTIME_CONTROLLER_VOICE_ASSISTANT
  if (this->voice_assistant_ != nullptr && std::strncmp(event, "timer_", 6) == 0) {
    bool active = std::strcmp(event, "timer_started") == 0 || std::strcmp(event, "timer_updated") == 0;
    for (const auto &timer : this->voice_assistant_->get_timers()) {
      if (timer.id != text)
        active = true;
    }
    this->runtime_->observe_activity("timer", active);
    // Cancel/update are snapshots, not alarm operations. Keep the established
    // started/finished reducer events; raw user callbacks remain on VA.
    if (std::strcmp(event, "timer_cancelled") == 0 || std::strcmp(event, "timer_updated") == 0)
      return;
  }
#endif
  // Defer reduction until the source's synchronous user actions have run.
  // Text/keyword display updates keep their ordering; delayed user actions
  // remain in the original Automation and do not delay state observation.
  this->runtime_->observe_event(event);
}
#endif

#ifdef USE_RUNTIME_CONTROLLER_API
void RuntimeNetworkObservers::publish_api_presence_() {
#ifdef USE_RUNTIME_CONTROLLER_API_CLIENT_OUTPUT
  if (this->api_clients_output_ != nullptr)
    this->publish_api_clients_(this->api_clients_output_, this->api_clients_);
#endif
  if (this->api_clients_ > 0) {
    this->cancel_timeout("ha-presence");
    this->runtime_->observe_event("ha_connected");
  } else {
    this->set_timeout("ha-presence", 250, [this]() {
      if (this->api_clients_ == 0)
        this->runtime_->observe_event("ha_disconnected");
    });
  }
}
#endif

#ifdef USE_RUNTIME_CONTROLLER_WIFI
void RuntimeNetworkObservers::on_wifi_connect_state(StringRef ssid, std::span<const uint8_t, 6>) {
  // ESPHome sends an empty SSID through the same listener on disconnect.
  this->runtime_->event(ssid.empty() ? "wifi_disconnected" : "wifi_connected");
}
#endif

}  // namespace esphome::runtime_controller

#endif
