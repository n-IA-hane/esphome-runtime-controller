// Host tests compile the repository's real runtime_controller.cpp unchanged.
// Only ESPHome adapters are substituted; this file contains no reducer model.
#include "runtime_controller.h"
#include "esphome/components/script/script.h"

#include "esphome/components/light/light_state.h"
#include "esphome/components/voip_stack/voip_stack.h"

#include <cassert>
#include <cstring>
#include <iostream>
#include <string>
#include <vector>

using esphome::Trigger;
using esphome::runtime_controller::RuntimeController;

template<typename T> struct Global {
  using value_type = T;
  T stored{};
  T &value() { return this->stored; }
};

static bool policy_is(const RuntimeController &runtime, const char *policy, const char *value) {
  return std::strcmp(runtime.get_policy(policy), value) == 0;
}

static void add_phase(RuntimeController &runtime, const char *name, int32_t output) {
  runtime.add_activity(name, 1, false);
  runtime.set_activity_group(name, "phase");
  runtime.add_activity_policy(name, "phase", name);
  runtime.add_policy_output("phase", name, output);
}

static void add_phase_event(RuntimeController &runtime, const char *event, const char *phase,
                            const char *action = nullptr) {
  runtime.add_event_rule(event, action);
  runtime.add_event_rule_update(phase, true);
}

static void test_snapshot_publication() {
  RuntimeController runtime;
  runtime.set_storage_in_psram(false);
  runtime.add_activity("active", 1, false);
  runtime.add_activity_policy("active", "p", "yes");
  runtime.add_activity_policy("active", "q", "yes");
  runtime.add_activity_policy("active", "led_status", "on");
  runtime.add_policy_output("p", "yes", 11);
  runtime.add_policy_output("q", "yes", 22);
  Global<int32_t> p, q;
  Global<uint32_t> mask, sequence;
  runtime.add_policy_global_output("p", &p);
  runtime.add_policy_global_output("q", &q);
  runtime.set_activity_mask_output(&mask);
  runtime.set_sequence_output(&sequence);

  bool expect_active = true;
  auto check_snapshot = [&] {
    assert(runtime.is_activity_active("active") == expect_active);
    assert(p.value() == (expect_active ? 11 : 0));
    assert(q.value() == (expect_active ? 22 : 0));
    assert(mask.value() == (expect_active ? 1U : 0U));
    assert(mask.value() == runtime.get_activity_mask());
    assert(sequence.value() == (expect_active ? 1U : 2U));
    assert(sequence.value() == runtime.get_sequence());
    assert(policy_is(runtime, "p", expect_active ? "yes" : ""));
    assert(policy_is(runtime, "q", expect_active ? "yes" : ""));
  };
  std::vector<std::string> callbacks;
  Trigger<> value_p;
  value_p.fn = [&] {
    check_snapshot();
    callbacks.emplace_back("value_p");
  };
  Trigger<int32_t> change_p, change_q;
  change_p.fn = [&](int32_t value) {
    check_snapshot();
    assert(value == p.value());
    callbacks.emplace_back("change_p");
  };
  change_q.fn = [&](int32_t value) {
    check_snapshot();
    assert(value == q.value());
    callbacks.emplace_back("change_q");
  };
  esphome::light::LightState light;
  light.on_perform = [&] {
    check_snapshot();
    callbacks.emplace_back("light");
  };
  esphome::script::Script<> output;
  output.fn = [&] {
    check_snapshot();
    callbacks.emplace_back("output");
  };
  runtime.add_policy_value_trigger("p", "yes", &value_p);
  runtime.set_policy_change_trigger("p", &change_p);
  runtime.set_policy_change_trigger("q", &change_q);
  runtime.set_led_light(&light);
  runtime.add_led_state("on", 0, 1, 0, 1, "None");
  runtime.set_output_script(&output);
  runtime.setup();
  runtime.set_activity("active", true);
  assert((callbacks == std::vector<std::string>{"value_p", "change_p", "change_q", "light", "output"}));

  // Last-owner removal publishes zeroes before on_change and LED callbacks too.
  expect_active = false;
  callbacks.clear();
  runtime.set_activity("active", false);
  assert((callbacks == std::vector<std::string>{"change_p", "change_q", "light", "output"}));
  const uint32_t committed = runtime.get_sequence();
  runtime.set_activity("active", false);
  assert(runtime.get_sequence() == committed);
}

static void test_event_run_to_completion() {
  RuntimeController runtime;
  runtime.set_storage_in_psram(false);
  add_phase(runtime, "a", 1);
  add_phase(runtime, "b", 2);
  add_phase_event(runtime, "A", "a", "actionA");
  add_phase_event(runtime, "B", "b", "actionB");
  Global<int32_t> phase;
  runtime.add_policy_global_output("phase", &phase);
  std::vector<std::string> order;
  Trigger<> action_a, action_b, value_a, then_a, then_b;
  action_a.fn = [&] { order.emplace_back("actionA"); };
  action_b.fn = [&] { order.emplace_back("actionB"); };
  value_a.fn = [&] {
    order.emplace_back("valueA");
    runtime.event("B");
    assert(policy_is(runtime, "phase", "a"));
    assert(phase.value() == 1);
  };
  then_a.fn = [&] {
    assert(policy_is(runtime, "phase", "a"));
    assert(phase.value() == 1);
    order.emplace_back("thenA");
  };
  then_b.fn = [&] {
    assert(policy_is(runtime, "phase", "b"));
    assert(phase.value() == 2);
    order.emplace_back("thenB");
  };
  runtime.add_action_trigger("actionA", &action_a);
  runtime.add_action_trigger("actionB", &action_b);
  runtime.add_policy_value_trigger("phase", "a", &value_a);
  runtime.add_event_trigger("A", &then_a);
  runtime.add_event_trigger("B", &then_b);
  runtime.setup();
  runtime.event("A");
  assert((order == std::vector<std::string>{"valueA", "thenA", "thenB"}));
  runtime.loop();
  assert((order == std::vector<std::string>{"valueA", "thenA", "thenB", "actionA", "actionB"}));
}

static void test_reentrant_setters_and_temporary_names() {
  RuntimeController runtime;
  runtime.set_storage_in_psram(false);
  add_phase(runtime, "a", 1);
  add_phase(runtime, "b", 2);
  add_phase(runtime, "c", 3);
  add_phase(runtime, "d", 4);
  add_phase_event(runtime, "A", "a");
  add_phase_event(runtime, "D", "d");
  std::vector<std::string> observed;
  Trigger<int32_t> changed;
  changed.fn = [&](int32_t) { observed.emplace_back(runtime.get_policy("phase")); };
  runtime.set_policy_change_trigger("phase", &changed);
  Trigger<> value_a, then_a;
  value_a.fn = [&] {
    {
      std::string temporary = "b";
      runtime.set_activity(temporary.c_str(), true);
    }
    {
      std::string first = "b", second = "c";
      RuntimeController::ActivityUpdate updates[] = {{first.c_str(), false}, {second.c_str(), true}};
      runtime.set_activities(updates, 2);
    }
    {
      std::string temporary = "D";
      runtime.event(temporary.c_str());
    }
    assert(policy_is(runtime, "phase", "a"));
    assert(runtime.is_activity_active("a"));
    assert(!runtime.is_activity_active("b"));
  };
  then_a.fn = [&] { assert(policy_is(runtime, "phase", "a")); };
  runtime.add_policy_value_trigger("phase", "a", &value_a);
  runtime.add_event_trigger("A", &then_a);
  runtime.setup();
  runtime.event("A");
  assert((observed == std::vector<std::string>{"a", "b", "c", "d"}));
  assert(runtime.get_sequence() == 4);
  assert(runtime.get_activity_mask() == 8);
}

static void test_pending_inputs_keep_fifo() {
  RuntimeController runtime;
  runtime.set_storage_in_psram(false);
  for (const char *phase : {"a", "b", "c", "d"})
    add_phase(runtime, phase, phase[0] - 'a' + 1);
  add_phase_event(runtime, "A", "a");
  add_phase_event(runtime, "B", "b");
  add_phase_event(runtime, "C", "c");
  add_phase_event(runtime, "D", "d");
  Trigger<> then_a, then_b;
  then_a.fn = [&] { runtime.event("B"); };
  then_b.fn = [&] { runtime.event("C"); };
  runtime.add_event_trigger("A", &then_a);
  runtime.add_event_trigger("B", &then_b);
  std::vector<int32_t> observed;
  Trigger<int32_t> changed;
  changed.fn = [&](int32_t value) { observed.push_back(value); };
  runtime.set_policy_change_trigger("phase", &changed);
  runtime.setup();
  runtime.event("A");
  assert((observed == std::vector<int32_t>{1, 2}));
  // C was emitted by the drained batch. An external D must not overtake it.
  runtime.event("D");
  assert((observed == std::vector<int32_t>{1, 2, 3, 4}));
  assert(policy_is(runtime, "phase", "d"));
}

static void test_bounded_event_queue() {
  RuntimeController runtime;
  runtime.set_storage_in_psram(false);
  runtime.set_storage_in_psram(false);
  unsigned ticks = 0;
  bool repeat = true;
  Trigger<> tick;
  tick.fn = [&] {
    ticks++;
    if (repeat)
      runtime.event("tick");
  };
  runtime.add_event_trigger("tick", &tick);
  runtime.setup();
  runtime.event("tick");
  assert(ticks == 2);
  assert(runtime.loop_enabled());
  runtime.loop();
  assert(ticks == 3);
  runtime.loop();
  assert(ticks == 4);
  repeat = false;
  runtime.loop();
  assert(ticks == 5);
  assert(!runtime.loop_enabled());

  Trigger<> flood;
  flood.fn = [&] {
    for (unsigned i = 0; i < 20; i++)
      runtime.event("tick");
  };
  runtime.add_event_trigger("flood", &flood);
  runtime.event("flood");
  assert(ticks == 21);  // 16 bounded slots; overflowing events are rejected.
}

static void test_bounded_actions_and_canonical_names() {
  RuntimeController runtime;
  runtime.set_storage_in_psram(false);
  unsigned executions = 0;
  bool repeat = true;
  Trigger<> action;
  action.fn = [&] {
    executions++;
    if (repeat) {
      std::string temporary = "again";
      runtime.request_action(temporary.c_str());
    }
  };
  runtime.add_action_trigger("again", &action);
  runtime.setup();
  {
    std::string temporary = "again";
    runtime.request_action(temporary.c_str());
    runtime.request_action(temporary.c_str());  // Preserve action deduplication.
  }
  runtime.loop();
  assert(executions == 1);
  assert(runtime.loop_enabled());
  runtime.loop();
  assert(executions == 2);
  repeat = false;
  runtime.loop();
  assert(executions == 3);
  assert(!runtime.loop_enabled());
}

static void test_priorities_groups_and_atomic_updates() {
  RuntimeController runtime;
  runtime.set_storage_in_psram(false);
  runtime.add_activity("idle", 0, true);
  runtime.add_activity_policy("idle", "phase", "idle");
  runtime.add_policy_output("phase", "idle", 0);
  add_phase(runtime, "a", 1);
  add_phase(runtime, "b", 2);
  runtime.add_activity("call", 10, false);
  runtime.add_activity_policy("call", "phase", "call");
  runtime.add_policy_output("phase", "call", 9);
  std::vector<int32_t> outputs;
  Trigger<int32_t> changed;
  changed.fn = [&](int32_t value) { outputs.push_back(value); };
  runtime.set_policy_change_trigger("phase", &changed);
  runtime.setup();
  runtime.set_activity("a", true);
  runtime.set_activity("call", true);
  RuntimeController::ActivityUpdate updates[] = {{"a", false}, {"b", true}};
  const uint32_t before = runtime.get_sequence();
  runtime.set_activities(updates, 2);
  assert(runtime.get_sequence() == before + 1);
  assert(!runtime.is_activity_active("a"));
  assert(runtime.is_activity_active("b"));
  assert(policy_is(runtime, "phase", "call"));
  assert((outputs == std::vector<int32_t>{0, 1, 9}));
  runtime.set_activity("call", false);
  assert(policy_is(runtime, "phase", "b"));
  runtime.set_activity("b", false);
  assert(policy_is(runtime, "phase", "idle"));
  assert((outputs == std::vector<int32_t>{0, 1, 9, 2, 0}));
  const uint32_t final_sequence = runtime.get_sequence();
  runtime.set_activity("unknown", true);
  runtime.set_activity("b", false);
  assert(runtime.get_sequence() == final_sequence);
}

static void test_derived_fixed_point() {
  RuntimeController runtime;
  runtime.set_storage_in_psram(false);
  runtime.add_activity("input", 0, false);
  runtime.add_activity("first", 0, false);
  runtime.add_activity("second", 0, false);
  // Reverse dependency order must still settle within the same transaction.
  runtime.add_derived_activity("second");
  runtime.add_derived_all_active("first");
  runtime.add_derived_activity("first");
  runtime.add_derived_all_active("input");
  esphome::script::Script<> snapshot;
  std::vector<uint32_t> masks;
  snapshot.fn = [&] { masks.push_back(runtime.get_activity_mask()); };
  runtime.set_output_script(&snapshot);
  runtime.setup();
  runtime.set_activity("input", true);
  runtime.set_activity("input", false);
  assert((masks == std::vector<uint32_t>{7, 0}));
}

static void test_allocation_failure_is_fail_closed() {
  esphome::testing::fail_allocations = true;
  const unsigned before = esphome::testing::allocation_attempts;
  RuntimeController runtime;
  runtime.set_storage_in_psram(false);
  runtime.set_storage_in_psram(false);
  Trigger<> plain;
  Trigger<int32_t> changed;
  Global<int32_t> global;
  Global<uint32_t> mask, sequence;
  esphome::light::LightState light;
  esphome::script::Script<> output;
  esphome::voip_stack::VoipStack phone;
  // This is the codegen sequence after the first allocation failed. Exercise
  // every storage-backed configurator instead of only the first crashing one.
  runtime.add_activity("idle", 0, true);
  runtime.set_activity_group("idle", "phase");
  runtime.add_activity_policy("idle", "phase", "idle");
  runtime.add_action_trigger("action", &plain);
  runtime.add_event_trigger("event", &plain);
  runtime.add_event_activity("event", "idle", true);
  runtime.add_event_rule("event", "action");
  runtime.add_event_rule_update("idle", true);
  runtime.add_event_rule_any_active("idle");
  runtime.add_event_rule_all_active("idle");
  runtime.add_event_rule_none_active("idle");
  runtime.add_derived_activity("idle");
  runtime.add_derived_any_active("idle");
  runtime.add_derived_all_active("idle");
  runtime.add_derived_none_active("idle");
  runtime.add_policy_value_trigger("phase", "idle", &plain);
  runtime.add_policy_output("phase", "idle", 1);
  runtime.set_policy_change_trigger("phase", &changed);
  runtime.add_policy_global_output("phase", &global);
  runtime.add_led_state("idle", 1, 1, 1, 1, "None");
  runtime.set_led_light(&light);
  runtime.set_output_script(&output);
  runtime.set_activity_mask_output(&mask);
  runtime.set_sequence_output(&sequence);
  runtime.set_voip(&phone);
  runtime.set_voip_activity_prefix("voip:");
  runtime.set_debug(true);
  runtime.dump_config();
  runtime.dump_state("failed");
  runtime.setup();
  assert(runtime.is_failed());
  assert(esphome::testing::allocation_attempts == before + 1);

  // A later successful allocator must not revive an incomplete configuration.
  esphome::testing::fail_allocations = false;
  runtime.add_activity("late", 1, true);
  runtime.set_storage_in_psram(true);
  RuntimeController::ActivityUpdate update{"idle", true};
  runtime.event("event");
  runtime.set_activity("idle", true);
  runtime.set_activities(&update, 1);
  runtime.request_action("action");
  runtime.on_voip_event();
  runtime.loop();
  runtime.setup();
  assert(!runtime.is_activity_active("idle"));
  assert(runtime.get_activity_mask() == 0);
  assert(runtime.get_sequence() == 0);
  assert(esphome::testing::allocation_attempts == before + 1);
}

#ifdef USE_RUNTIME_CONTROLLER_VOIP
static void configure_voip_test(RuntimeController &runtime, esphome::voip_stack::VoipStack &phone,
                                Global<int32_t> &status) {
  runtime.set_voip(&phone);
  runtime.set_voip_activity_prefix("voip:");
  runtime.add_activity("responding", 1, false);
  runtime.add_activity_policy("responding", "status", "responding");
  runtime.add_activity("voip:ringing", 10, false);
  runtime.add_activity_policy("voip:ringing", "status", "ringing");
  runtime.add_policy_output("status", "responding", 1);
  runtime.add_policy_output("status", "ringing", 2);
  runtime.add_policy_global_output("status", &status);
}

static void test_voip_observer_is_transactional() {
  RuntimeController runtime;
  runtime.set_storage_in_psram(false);
  esphome::voip_stack::VoipStack phone;
  Global<int32_t> status;
  configure_voip_test(runtime, phone, status);
  Trigger<> response;
  response.fn = [&] {
    phone.change("ringing");
    assert(policy_is(runtime, "status", "responding"));
    assert(status.value() == 1);
    assert(!runtime.is_activity_active("voip:ringing"));
  };
  runtime.add_policy_value_trigger("status", "responding", &response);
  runtime.setup();
  runtime.set_activity("responding", true);
  assert(policy_is(runtime, "status", "ringing"));
  assert(status.value() == 2);
  assert(runtime.get_sequence() == 2);
}

static void test_voip_queue_captures_intermediate_states() {
  RuntimeController runtime;
  runtime.set_storage_in_psram(false);
  esphome::voip_stack::VoipStack phone;
  Global<int32_t> status;
  configure_voip_test(runtime, phone, status);
  bool emitted = false;
  Trigger<> response;
  response.fn = [&] {
    if (!emitted) {
      emitted = true;
      phone.change("ringing");
      phone.change("idle");
    }
  };
  runtime.add_policy_value_trigger("status", "responding", &response);
  std::vector<int32_t> values;
  Trigger<int32_t> changed;
  changed.fn = [&](int32_t value) {
    assert(value == status.value());
    values.push_back(value);
  };
  runtime.set_policy_change_trigger("status", &changed);
  runtime.setup();
  runtime.set_activity("responding", true);
  assert((values == std::vector<int32_t>{1, 2, 1}));
  assert(policy_is(runtime, "status", "responding"));
  assert(!runtime.is_activity_active("voip:ringing"));
  assert(runtime.get_sequence() == 3);
}

static void test_voip_overflow_reconciles_latest_state() {
  RuntimeController runtime;
  runtime.set_storage_in_psram(false);
  esphome::voip_stack::VoipStack phone;
  Global<int32_t> status;
  configure_voip_test(runtime, phone, status);
  Trigger<> noop, response;
  unsigned noops = 0;
  noop.fn = [&] { noops++; };
  runtime.add_event_trigger("noop", &noop);
  response.fn = [&] {
    for (unsigned i = 0; i < 16; i++)
      runtime.event("noop");
    phone.change("ringing");
  };
  runtime.add_policy_value_trigger("status", "responding", &response);
  runtime.setup();
  runtime.set_activity("responding", true);
  assert(noops == 16);
  assert(status.value() == 1);
  assert(runtime.loop_enabled());
  runtime.loop();
  assert(policy_is(runtime, "status", "ringing"));
  assert(status.value() == 2);
}
#endif

int main(int argc, char **argv) {
  assert(argc == 2);
  const std::string test = argv[1];
  if (test == "snapshot")
    test_snapshot_publication();
  else if (test == "event_order")
    test_event_run_to_completion();
  else if (test == "nested_setters")
    test_reentrant_setters_and_temporary_names();
  else if (test == "fifo")
    test_pending_inputs_keep_fifo();
  else if (test == "event_bounds")
    test_bounded_event_queue();
  else if (test == "action_bounds")
    test_bounded_actions_and_canonical_names();
  else if (test == "priorities")
    test_priorities_groups_and_atomic_updates();
  else if (test == "derived")
    test_derived_fixed_point();
  else if (test == "allocation_failure")
    test_allocation_failure_is_fail_closed();
#ifdef USE_RUNTIME_CONTROLLER_VOIP
  else if (test == "voip_reentrancy")
    test_voip_observer_is_transactional();
  else if (test == "voip_capture")
    test_voip_queue_captures_intermediate_states();
  else if (test == "voip_overflow")
    test_voip_overflow_reconciles_latest_state();
#endif
  else
    return 2;
  std::cout << "PASS " << test << '\n';
}
