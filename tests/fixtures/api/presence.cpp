#include "runtime_controller.h"
#include "runtime_network_observers.h"
#include "esphome/components/api/api_server.h"
#include <cassert>
#include <string>

using namespace esphome;
using namespace esphome::runtime_controller;

struct CountOutput {
  uint16_t count{0};
  uint16_t &value() { return count; }
};

struct Scenario {
  api::APIServer server;
  RuntimeController runtime;
  RuntimeNetworkObservers observer;
  CountOutput output;

  Scenario() {
    api::global_api_server = &server;
    runtime.add_activity("no_ha", 0, false);
    runtime.add_event_activity("ha_connected", "no_ha", false);
    runtime.add_event_activity("ha_disconnected", "no_ha", true);
    runtime.setup();
    observer.set_runtime(&runtime);
    observer.set_api_clients_output(&output);
  }
  ~Scenario() { api::global_api_server = nullptr; }
  void setup() { observer.setup(); runtime.loop(); }
  void emit(const char *event, const std::string &name) {
    observer.source_event(event, name);
    runtime.loop();
  }
  api::APIConnection *authenticate(std::string name, bool notify = true) {
    auto *client = server.accept("192.0.2.20");
    client->name_ = std::move(name);
    client->authenticated = true;
    if (notify)
      emit("api_connected", client->name_);
    return client;
  }
  void close(api::APIConnection *client) {
    auto name = server.remove(client);
    emit("api_disconnected", name);
  }
  void advance(unsigned ms) { observer.advance(ms); runtime.loop(); }
  bool no_ha() const { return runtime.is_activity_active("no_ha"); }
  void online(unsigned count) const {
    assert(!no_ha());
    assert(output.count == count);
  }
};

int main(int argc, char **argv) {
  assert(argc == 2);
  const std::string test = argv[1];
  Scenario s;
  if (test == "no_hello") {
    s.setup();
    s.authenticate("Home Assistant");
    s.online(1);
    auto *tcp = s.server.accept("192.0.2.99");  // No Hello or authentication callback.
    s.close(tcp);
    s.advance(250);
    s.online(1);  // Original incident: a healthy HA connection must remain present.
  } else if (test == "loggers") {
    s.setup();
    auto *ha = s.authenticate("Home Assistant");
    for (const char *name : {"ESPHome Logs test", "ESPHome Dashboard x", "ESPHome Web x", ""}) {
      auto *logger = s.authenticate(name);
      s.online(1);
      s.close(logger);
      s.advance(300);
      s.online(1);
    }
    auto *logger = s.authenticate("ESPHome Logs remaining");
    s.close(ha); s.advance(250);
    assert(s.no_ha() && s.output.count == 0);
    s.close(logger); s.advance(300);
    assert(s.no_ha() && s.output.count == 0);
  } else if (test == "duplicate_names") {
    s.setup();
    auto *first = s.authenticate("Home Assistant");
    auto *second = s.authenticate("Home Assistant");
    s.online(2);
    s.close(first); s.advance(300); s.online(1);
    s.close(second); s.advance(250);
    assert(s.no_ha() && s.output.count == 0);
  } else if (test == "offline_delay_reconnect") {
    s.setup();
    auto *ha = s.authenticate("Home Assistant");
    s.close(ha);
    s.advance(249); assert(!s.no_ha() && s.output.count == 0);
    s.advance(1); assert(s.no_ha());
    ha = s.authenticate("Home Assistant"); s.online(1);
    s.close(ha); s.advance(249);
    s.authenticate("Home Assistant"); s.advance(1000); s.online(1);
    assert(s.observer.timers.empty());
  } else if (test == "boot_cancel") {
    s.setup(); s.advance(249); assert(!s.no_ha());
    s.authenticate("Home Assistant"); s.advance(1000); s.online(1);
    assert(s.observer.timers.empty());
  } else if (test == "boot_snapshot") {
    s.authenticate("Home Assistant", false);
    s.authenticate("Home Assistant", false);
    s.authenticate("ESPHome Logs startup", false);
    s.server.accept("192.0.2.99");
    s.setup(); s.advance(1000); s.online(2);
    assert(s.observer.timers.empty());
  } else if (test == "event_replay") {
    s.setup();
    auto *ha = s.authenticate("Home Assistant");
    s.emit("api_connected", "Home Assistant"); s.online(1);
    s.emit("api_disconnected", "192.0.2.99"); s.advance(250); s.online(1);
    s.close(ha);
    s.emit("api_disconnected", "Home Assistant");
    s.advance(250); assert(s.no_ha() && s.output.count == 0);
  } else if (test == "authentication_not_name") {
    s.setup();
    s.authenticate("192.0.2.99"); s.online(1);  // A valid name may look like an IP.
    auto *failed = s.server.accept("192.0.2.99");
    failed->name_ = "Home Assistant";  // Hello is insufficient without authentication.
    s.close(failed); s.advance(250); s.online(1);
    auto *generic = s.authenticate("aioesphomeapi"); s.online(2);
    s.close(generic); s.advance(250); s.online(1);
  } else if (test == "pending_removal") {
    auto *ha = s.authenticate("Home Assistant", false);
    ha->removing = true;
    s.setup(); s.advance(250); assert(s.no_ha() && s.output.count == 0);
    s.close(ha); s.advance(250); assert(s.no_ha());
  } else if (test == "boot_offline") {
    s.setup(); s.advance(249); assert(!s.no_ha());
    s.advance(1); assert(s.no_ha() && s.output.count == 0);
    assert(s.observer.timers.empty());
  } else if (test == "null_server") {
    api::global_api_server = nullptr;
    s.setup(); s.advance(250); assert(s.no_ha() && s.output.count == 0);
  } else {
    assert(false);
  }
  assert(!s.runtime.loop_enabled() && !s.observer.loop_enabled());
}
