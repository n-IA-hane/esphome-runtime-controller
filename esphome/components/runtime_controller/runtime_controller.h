#pragma once

#include "runtime_controller_state.h"

#include "esphome/core/automation.h"
#include "esphome/core/component.h"
#include "esphome/components/script/script.h"

#include <array>
#include <cstdint>
#include <string>

namespace esphome {
namespace light {
class LightState;
}
namespace voip_stack {
class VoipStack;
}
namespace runtime_controller {

class RuntimeController : public Component {
 public:
  static constexpr uint8_t INVALID_ACTIVITY = 0xFF;

  struct ActivityUpdate {
    const char *name{nullptr};
    bool active{false};
    uint8_t index{INVALID_ACTIVITY};
  };

  void setup() override;
  void loop() override;
  void dump_config() override;
  float get_setup_priority() const override { return setup_priority::PROCESSOR; }

  void set_debug(bool debug) { this->debug_ = debug; }
  void set_output_script(script::Script<> *script) { this->output_script_ = script; }
  void set_voip(voip_stack::VoipStack *voip) { this->voip_ = voip; }
  void set_voip_activity_prefix(const char *prefix) { this->voip_activity_prefix_ = prefix; }
  void add_activity(const char *name, int16_t priority, bool initial);
  void set_activity_group(const char *activity, const char *group);
  void add_activity_policy(const char *activity, const char *policy, const char *value);
  void add_action_trigger(const char *name, Trigger<> *trigger);
  void add_event_activity(const char *event, const char *activity, bool active);
  void add_event_rule(const char *event, const char *action);
  void add_event_rule_update(const char *activity, bool active);
  void add_event_rule_any_active(const char *activity);
  void add_event_rule_all_active(const char *activity);
  void add_event_rule_none_active(const char *activity);
  void add_derived_activity(const char *activity);
  void add_derived_any_active(const char *activity);
  void add_derived_all_active(const char *activity);
  void add_derived_none_active(const char *activity);
  void add_policy_value_trigger(const char *policy, const char *value, Trigger<> *trigger);
  void add_policy_output(const char *policy, const char *value, int32_t output);
  void set_policy_change_trigger(const char *policy, Trigger<int32_t> *trigger);
  void set_led_light(light::LightState *light) { this->led_light_ = light; }
  void add_led_state(const char *state, float red, float green, float blue, float brightness, const char *effect);
  template<typename C> void add_policy_global_output(const char *policy, C *target) {
    if (policy == nullptr || policy[0] == '\0' || target == nullptr)
      return;
    if (this->policy_global_output_count_ >= this->policy_global_outputs_.size())
      return;
    this->policy_global_outputs_[this->policy_global_output_count_++] = PolicyGlobalOutput{
        policy,
        target,
        [](void *ptr, int32_t value) {
          auto *global = static_cast<C *>(ptr);
          global->value() = static_cast<typename C::value_type>(value);
        },
    };
  }
  template<typename C> void set_activity_mask_output(C *target) {
    if (target == nullptr)
      return;
    this->activity_mask_output_ = StateOutput{
        target,
        [](void *ptr, uint32_t value) {
          auto *global = static_cast<C *>(ptr);
          global->value() = static_cast<typename C::value_type>(value);
        },
    };
  }
  template<typename C> void set_sequence_output(C *target) {
    if (target == nullptr)
      return;
    this->sequence_output_ = StateOutput{
        target,
        [](void *ptr, uint32_t value) {
          auto *global = static_cast<C *>(ptr);
          global->value() = static_cast<typename C::value_type>(value);
        },
    };
  }

  void on_voip_event();
  void event(const char *name);
  void set_activity(const char *name, bool active);
  void set_activities(const ActivityUpdate *updates, size_t count);
  void request_action(const char *name);
  void dump_state(const char *reason);
  bool is_activity_active(const char *name) const;

  const char *get_policy(const char *name, const char *fallback = "") const {
    return find_policy_value(this->resolved_policies_, name, fallback);
  }
  uint32_t get_activity_mask() const { return this->generic_activity_mask_; }
  uint32_t get_sequence() const { return this->sequence_; }

 protected:
  struct EventRule;
  struct DerivedActivity;

  static constexpr size_t MAX_ACTIVITIES = 32;
  static constexpr size_t MAX_ACTIONS = 16;
  static constexpr size_t MAX_EVENT_UPDATES = 64;

  void publish_outputs_();
  void publish_state_outputs_();
  void apply_generic_outputs_();
  bool set_activity_value_(const char *name, bool active);
  bool set_activity_value_by_index_(int index, bool active);
  bool apply_activity_update_(const char *name, bool active);
  bool apply_activity_update_(const ActivityUpdate &update);
  bool apply_activity_update_by_index_(int index, bool active);
  bool set_activity_value_if_known_(const char *name, bool active);
  void commit_outputs_(const char *reason, uint32_t old_mask, const ResolvedPolicies &old_policies);
  bool sync_voip_activity_();
  void build_voip_activity_name_(const char *state);
  int find_activity_(const char *name) const;
  int find_action_(const char *name) const;
  bool rule_matches_(const EventRule &rule) const;
  bool derived_matches_(const DerivedActivity &derived) const;
  bool is_activity_active_(const char *name, uint8_t index) const;
  bool apply_derived_activities_();
  bool enqueue_event_(const char *name);
  bool enqueue_activity_update_(const char *name, bool active);
  bool enqueue_activity_updates_(const ActivityUpdate *updates, size_t count);
  void drain_pending_events_();
  void run_named_action_(const char *name);
  void execute_named_action_(const char *name);
  void drain_pending_actions_();
  void run_policy_actions_(const ResolvedPolicies &old_policies, const ResolvedPolicies &new_policies);
  void apply_led_state_(const char *state);
  int32_t resolve_policy_output_(const char *policy, const char *value) const;
  void mark_config_error_();

  script::Script<> *output_script_{nullptr};
  light::LightState *led_light_{nullptr};
  voip_stack::VoipStack *voip_{nullptr};
  const char *voip_activity_prefix_{nullptr};

  bool debug_{false};
  bool config_error_{false};
  bool voip_callback_registered_{false};
  uint32_t sequence_{0};
  ResolvedPolicies resolved_policies_{};
  char voip_activity_[64]{};
  char last_voip_activity_[64]{};

  struct ActivityConfig {
    const char *name{nullptr};
    const char *group{nullptr};
    uint32_t bit{0};
    int16_t priority{0};
    bool active{false};
    PolicyValue policies[MAX_ACTIVITY_POLICIES]{};
    size_t policy_count{0};
  };
  struct NamedAction {
    const char *name{nullptr};
    Trigger<> *trigger{nullptr};
  };
  struct EventActivity {
    const char *event{nullptr};
    const char *activity{nullptr};
    bool active{false};
    uint8_t activity_index{INVALID_ACTIVITY};
  };
  struct EventRule {
    const char *event{nullptr};
    const char *action{nullptr};
    ActivityUpdate updates[16]{};
    const char *any_active[8]{};
    const char *all_active[8]{};
    const char *none_active[8]{};
    uint8_t any_active_index[8]{INVALID_ACTIVITY, INVALID_ACTIVITY, INVALID_ACTIVITY, INVALID_ACTIVITY,
                                INVALID_ACTIVITY, INVALID_ACTIVITY, INVALID_ACTIVITY, INVALID_ACTIVITY};
    uint8_t all_active_index[8]{INVALID_ACTIVITY, INVALID_ACTIVITY, INVALID_ACTIVITY, INVALID_ACTIVITY,
                                INVALID_ACTIVITY, INVALID_ACTIVITY, INVALID_ACTIVITY, INVALID_ACTIVITY};
    uint8_t none_active_index[8]{INVALID_ACTIVITY, INVALID_ACTIVITY, INVALID_ACTIVITY, INVALID_ACTIVITY,
                                 INVALID_ACTIVITY, INVALID_ACTIVITY, INVALID_ACTIVITY, INVALID_ACTIVITY};
    size_t update_count{0};
    size_t any_count{0};
    size_t all_count{0};
    size_t none_count{0};
  };
  struct DerivedActivity {
    const char *activity{nullptr};
    uint8_t activity_index{INVALID_ACTIVITY};
    const char *any_active[8]{};
    const char *all_active[8]{};
    const char *none_active[8]{};
    uint8_t any_active_index[8]{INVALID_ACTIVITY, INVALID_ACTIVITY, INVALID_ACTIVITY, INVALID_ACTIVITY,
                                INVALID_ACTIVITY, INVALID_ACTIVITY, INVALID_ACTIVITY, INVALID_ACTIVITY};
    uint8_t all_active_index[8]{INVALID_ACTIVITY, INVALID_ACTIVITY, INVALID_ACTIVITY, INVALID_ACTIVITY,
                                INVALID_ACTIVITY, INVALID_ACTIVITY, INVALID_ACTIVITY, INVALID_ACTIVITY};
    uint8_t none_active_index[8]{INVALID_ACTIVITY, INVALID_ACTIVITY, INVALID_ACTIVITY, INVALID_ACTIVITY,
                                 INVALID_ACTIVITY, INVALID_ACTIVITY, INVALID_ACTIVITY, INVALID_ACTIVITY};
    size_t any_count{0};
    size_t all_count{0};
    size_t none_count{0};
  };
  struct PolicyValueAction {
    const char *policy{nullptr};
    const char *value{nullptr};
    Trigger<> *trigger{nullptr};
  };
  struct PolicyOutput {
    const char *policy{nullptr};
    const char *value{nullptr};
    int32_t output{0};
  };
  struct PolicyChangeTrigger {
    const char *policy{nullptr};
    Trigger<int32_t> *trigger{nullptr};
  };
  struct PolicyGlobalOutput {
    const char *policy{nullptr};
    void *target{nullptr};
    void (*set)(void *, int32_t){nullptr};
  };
  struct StateOutput {
    void *target{nullptr};
    void (*set)(void *, uint32_t){nullptr};
  };
  struct LedState {
    const char *state{nullptr};
    float red{0.0f};
    float green{0.0f};
    float blue{0.0f};
    float brightness{0.0f};
    const char *effect{"None"};
  };
  enum class PendingEventKind : uint8_t {
    EVENT,
    SET_ACTIVITIES,
  };
  struct PendingEvent {
    PendingEventKind kind{PendingEventKind::EVENT};
    char name[48]{};
    ActivityUpdate updates[16]{};
    size_t update_count{0};
  };

  std::array<ActivityConfig, MAX_ACTIVITIES> activities_{};
  std::array<NamedAction, MAX_ACTIONS> actions_{};
  std::array<EventActivity, MAX_EVENT_UPDATES> event_updates_{};
  std::array<EventRule, 64> event_rules_{};
  std::array<DerivedActivity, 16> derived_activities_{};
  std::array<PolicyValueAction, 32> policy_value_actions_{};
  std::array<PolicyOutput, 64> policy_outputs_{};
  std::array<PolicyChangeTrigger, MAX_POLICIES> policy_change_triggers_{};
  std::array<PolicyGlobalOutput, MAX_POLICIES> policy_global_outputs_{};
  std::array<LedState, 32> led_states_{};
  std::array<const char *, 16> pending_actions_{};
  std::array<PendingEvent, 16> pending_events_{};
  StateOutput activity_mask_output_{};
  StateOutput sequence_output_{};
  size_t activity_count_{0};
  size_t action_count_{0};
  size_t event_update_count_{0};
  size_t event_rule_count_{0};
  size_t derived_activity_count_{0};
  size_t policy_value_action_count_{0};
  size_t policy_output_count_{0};
  size_t policy_change_trigger_count_{0};
  size_t policy_global_output_count_{0};
  size_t led_state_count_{0};
  size_t pending_action_count_{0};
  size_t pending_event_count_{0};
  bool dispatching_{false};
  uint32_t generic_activity_mask_{0};
};

template<typename... Ts> class EventAction : public Action<Ts...>, public Parented<RuntimeController> {
 public:
  TEMPLATABLE_VALUE(std::string, event)
  TEMPLATABLE_VALUE(std::string, reason)

  void set_dump(bool dump) { this->dump_ = dump; }

  void play(const Ts &...x) override {
    auto event = this->event_.value(x...);
    this->parent_->event(event.c_str());
    if (this->dump_) {
      auto reason = this->reason_.value(x...);
      this->parent_->dump_state(reason.empty() ? event.c_str() : reason.c_str());
    }
  }

 protected:
  bool dump_{false};
};

template<typename... Ts> class SetActivityAction : public Action<Ts...>, public Parented<RuntimeController> {
 public:
  TEMPLATABLE_VALUE(std::string, activity)
  TEMPLATABLE_VALUE(bool, active)

  void play(const Ts &...x) override {
    auto activity = this->activity_.value(x...);
    this->parent_->set_activity(activity.c_str(), this->active_.value(x...));
  }
};

template<typename... Ts> class SetActivitiesAction : public Action<Ts...>, public Parented<RuntimeController> {
 public:
  void add_activity_state(const char *name, bool active) {
    if (name == nullptr || name[0] == '\0' || this->update_count_ >= this->updates_.size())
      return;
    this->updates_[this->update_count_++] = RuntimeController::ActivityUpdate{name, active};
  }

  void play(const Ts &...x) override {
    (void) sizeof...(x);
    this->parent_->set_activities(this->updates_.data(), this->update_count_);
  }

 protected:
  std::array<RuntimeController::ActivityUpdate, 16> updates_{};
  size_t update_count_{0};
};

template<typename... Ts> class RequestActionAction : public Action<Ts...>, public Parented<RuntimeController> {
 public:
  TEMPLATABLE_VALUE(std::string, action)

  void play(const Ts &...x) override {
    auto action = this->action_.value(x...);
    this->parent_->request_action(action.c_str());
  }
};

template<typename... Ts> class DumpAction : public Action<Ts...>, public Parented<RuntimeController> {
 public:
  TEMPLATABLE_VALUE(std::string, reason)

  void play(const Ts &...x) override {
    auto reason = this->reason_.value(x...);
    this->parent_->dump_state(reason.c_str());
  }
};

template<typename... Ts> class IsActiveCondition : public Condition<Ts...>, public Parented<RuntimeController> {
 public:
  TEMPLATABLE_VALUE(std::string, activity)

  bool check(const Ts &...x) override {
    auto activity = this->activity_.value(x...);
    return this->parent_->is_activity_active(activity.c_str());
  }
};

}  // namespace runtime_controller
}  // namespace esphome
