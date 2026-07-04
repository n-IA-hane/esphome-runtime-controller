#include "runtime_controller.h"

#include "esphome/core/hal.h"
#include "esphome/core/log.h"
#include "esphome/components/light/light_state.h"

#include <cstdio>
#include <cstring>
#include <iterator>

#ifdef USE_RUNTIME_CONTROLLER_VOIP
#include "esphome/components/voip_stack/voip_stack.h"
#endif

namespace esphome::runtime_controller {

static const char *const TAG = "runtime_controller";

static bool str_eq(const char *left, const char *right) {
  return left == right || (left != nullptr && right != nullptr && strcmp(left, right) == 0);
}

static uint8_t activity_index_or_invalid(int index) {
  return index >= 0 ? static_cast<uint8_t>(index) : RuntimeController::INVALID_ACTIVITY;
}

void RuntimeController::setup() {
  if (this->config_error_) {
    ESP_LOGE(TAG, "Runtime Controller configuration overflow; refusing to run with a truncated reducer table");
    this->mark_failed();
    return;
  }
  const ResolvedPolicies old_policies = this->resolved_policies_;
  const uint32_t old_mask = this->generic_activity_mask_;
#ifdef USE_RUNTIME_CONTROLLER_VOIP
  if (this->voip_ != nullptr && !this->voip_callback_registered_) {
    this->voip_callback_registered_ = true;
    this->voip_->add_on_state_callback([this](voip_stack::CallState) { this->on_voip_event(); });
  }
#endif
  (void) this->sync_voip_activity_();
  (void) this->apply_derived_activities_();
  this->apply_generic_outputs_();
  this->commit_outputs_("setup", old_mask, old_policies);
  if (this->pending_action_count_ == 0 && this->pending_event_count_ == 0)
    this->disable_loop();
}

void RuntimeController::loop() {
  this->drain_pending_actions_();

  const uint32_t old_mask = this->generic_activity_mask_;
  const ResolvedPolicies old_policies = this->resolved_policies_;
  if (!this->sync_voip_activity_()) {
    if (this->pending_action_count_ == 0 && this->pending_event_count_ == 0)
      this->disable_loop();
    return;
  }
  (void) this->apply_derived_activities_();
  this->apply_generic_outputs_();
  this->commit_outputs_("observer", old_mask, old_policies);
  if (this->pending_action_count_ == 0 && this->pending_event_count_ == 0)
    this->disable_loop();
}

void RuntimeController::dump_config() {
  ESP_LOGCONFIG(TAG, "Runtime Controller:");
  ESP_LOGCONFIG(TAG, "  Activities: %u/%u", static_cast<unsigned>(this->activity_count_),
                static_cast<unsigned>(MAX_ACTIVITIES));
  ESP_LOGCONFIG(TAG, "  Actions: %u/%u", static_cast<unsigned>(this->action_count_),
                static_cast<unsigned>(MAX_ACTIONS));
  ESP_LOGCONFIG(TAG, "  Event rules: %u/%u", static_cast<unsigned>(this->event_rule_count_),
                static_cast<unsigned>(this->event_rules_.size()));
  ESP_LOGCONFIG(TAG, "  Event updates: %u/%u", static_cast<unsigned>(this->event_update_count_),
                static_cast<unsigned>(this->event_updates_.size()));
  ESP_LOGCONFIG(TAG, "  Derived activities: %u/%u", static_cast<unsigned>(this->derived_activity_count_),
                static_cast<unsigned>(this->derived_activities_.size()));
  ESP_LOGCONFIG(TAG, "  Debug: %s", YESNO(this->debug_));
  ESP_LOGCONFIG(TAG, "  Config valid: %s", YESNO(!this->config_error_));
#ifdef USE_RUNTIME_CONTROLLER_VOIP
  ESP_LOGCONFIG(TAG, "  VoIP observer: %s", this->voip_ != nullptr ? "configured" : "missing");
#endif
}

void RuntimeController::mark_config_error_() { this->config_error_ = true; }

void RuntimeController::add_activity(const char *name, int16_t priority, bool initial) {
  if (name == nullptr || name[0] == '\0')
    return;
  if (this->activity_count_ >= MAX_ACTIVITIES) {
    ESP_LOGE(TAG, "Cannot add activity '%s': maximum %u activities reached", name,
             static_cast<unsigned>(MAX_ACTIVITIES));
    this->mark_config_error_();
    return;
  }
  ActivityConfig activity;
  activity.name = name;
  activity.bit = 1u << this->activity_count_;
  activity.priority = priority;
  activity.active = initial;
  this->activities_[this->activity_count_++] = activity;
}

void RuntimeController::set_activity_group(const char *activity_name, const char *group) {
  int index = this->find_activity_(activity_name);
  if (index < 0 || group == nullptr || group[0] == '\0')
    return;
  this->activities_[index].group = group;
}

void RuntimeController::add_activity_policy(const char *activity_name, const char *policy, const char *value) {
  int index = this->find_activity_(activity_name);
  if (index < 0) {
    ESP_LOGE(TAG, "Cannot add policy '%s': unknown activity '%s'", policy != nullptr ? policy : "-",
             activity_name != nullptr ? activity_name : "-");
    return;
  }
  auto &activity = this->activities_[index];
  if (activity.policy_count >= MAX_ACTIVITY_POLICIES) {
    ESP_LOGE(TAG, "Cannot add policy '%s' to activity '%s': maximum %u policies reached",
             policy != nullptr ? policy : "-", activity_name, static_cast<unsigned>(MAX_ACTIVITY_POLICIES));
    this->mark_config_error_();
    return;
  }
  activity.policies[activity.policy_count++] = PolicyValue{policy, value};
}

void RuntimeController::add_event_activity(const char *event, const char *activity, bool active) {
  if (event == nullptr || event[0] == '\0' || activity == nullptr || activity[0] == '\0')
    return;
  if (this->event_update_count_ >= this->event_updates_.size()) {
    ESP_LOGE(TAG, "Cannot add event update '%s:%s': maximum reached", event, activity);
    this->mark_config_error_();
    return;
  }
  this->event_updates_[this->event_update_count_++] = EventActivity{
      event, activity, active, activity_index_or_invalid(this->find_activity_(activity))};
}

void RuntimeController::add_event_rule(const char *event, const char *action) {
  if (event == nullptr || event[0] == '\0')
    return;
  if (this->event_rule_count_ >= this->event_rules_.size()) {
    ESP_LOGE(TAG, "Cannot add event rule '%s': maximum reached", event);
    this->mark_config_error_();
    return;
  }
  this->event_rules_[this->event_rule_count_++] = EventRule{event, action};
}

void RuntimeController::add_event_rule_update(const char *activity, bool active) {
  if (this->event_rule_count_ == 0 || activity == nullptr || activity[0] == '\0')
    return;
  auto &rule = this->event_rules_[this->event_rule_count_ - 1];
  if (rule.update_count >= std::size(rule.updates)) {
    ESP_LOGE(TAG, "Cannot add event rule update '%s': maximum reached", activity);
    this->mark_config_error_();
    return;
  }
  ActivityUpdate update{activity, active, activity_index_or_invalid(this->find_activity_(activity))};
  rule.updates[rule.update_count++] = update;
}

void RuntimeController::add_event_rule_any_active(const char *activity) {
  if (this->event_rule_count_ == 0 || activity == nullptr || activity[0] == '\0')
    return;
  auto &rule = this->event_rules_[this->event_rule_count_ - 1];
  if (rule.any_count >= std::size(rule.any_active)) {
    ESP_LOGE(TAG, "Cannot add event rule any condition '%s': maximum reached", activity);
    this->mark_config_error_();
    return;
  }
  const size_t index = rule.any_count++;
  rule.any_active[index] = activity;
  rule.any_active_index[index] = activity_index_or_invalid(this->find_activity_(activity));
}

void RuntimeController::add_event_rule_all_active(const char *activity) {
  if (this->event_rule_count_ == 0 || activity == nullptr || activity[0] == '\0')
    return;
  auto &rule = this->event_rules_[this->event_rule_count_ - 1];
  if (rule.all_count >= std::size(rule.all_active)) {
    ESP_LOGE(TAG, "Cannot add event rule all condition '%s': maximum reached", activity);
    this->mark_config_error_();
    return;
  }
  const size_t index = rule.all_count++;
  rule.all_active[index] = activity;
  rule.all_active_index[index] = activity_index_or_invalid(this->find_activity_(activity));
}

void RuntimeController::add_event_rule_none_active(const char *activity) {
  if (this->event_rule_count_ == 0 || activity == nullptr || activity[0] == '\0')
    return;
  auto &rule = this->event_rules_[this->event_rule_count_ - 1];
  if (rule.none_count >= std::size(rule.none_active)) {
    ESP_LOGE(TAG, "Cannot add event rule none condition '%s': maximum reached", activity);
    this->mark_config_error_();
    return;
  }
  const size_t index = rule.none_count++;
  rule.none_active[index] = activity;
  rule.none_active_index[index] = activity_index_or_invalid(this->find_activity_(activity));
}

void RuntimeController::add_derived_activity(const char *activity) {
  if (activity == nullptr || activity[0] == '\0')
    return;
  if (this->derived_activity_count_ >= this->derived_activities_.size()) {
    ESP_LOGE(TAG, "Cannot add derived activity '%s': maximum reached", activity);
    this->mark_config_error_();
    return;
  }
  DerivedActivity derived;
  derived.activity = activity;
  derived.activity_index = activity_index_or_invalid(this->find_activity_(activity));
  this->derived_activities_[this->derived_activity_count_++] = derived;
}

void RuntimeController::add_derived_any_active(const char *activity) {
  if (this->derived_activity_count_ == 0 || activity == nullptr || activity[0] == '\0')
    return;
  auto &derived = this->derived_activities_[this->derived_activity_count_ - 1];
  if (derived.any_count >= std::size(derived.any_active)) {
    ESP_LOGE(TAG, "Cannot add derived any condition '%s': maximum reached", activity);
    this->mark_config_error_();
    return;
  }
  const size_t index = derived.any_count++;
  derived.any_active[index] = activity;
  derived.any_active_index[index] = activity_index_or_invalid(this->find_activity_(activity));
}

void RuntimeController::add_derived_all_active(const char *activity) {
  if (this->derived_activity_count_ == 0 || activity == nullptr || activity[0] == '\0')
    return;
  auto &derived = this->derived_activities_[this->derived_activity_count_ - 1];
  if (derived.all_count >= std::size(derived.all_active)) {
    ESP_LOGE(TAG, "Cannot add derived all condition '%s': maximum reached", activity);
    this->mark_config_error_();
    return;
  }
  const size_t index = derived.all_count++;
  derived.all_active[index] = activity;
  derived.all_active_index[index] = activity_index_or_invalid(this->find_activity_(activity));
}

void RuntimeController::add_derived_none_active(const char *activity) {
  if (this->derived_activity_count_ == 0 || activity == nullptr || activity[0] == '\0')
    return;
  auto &derived = this->derived_activities_[this->derived_activity_count_ - 1];
  if (derived.none_count >= std::size(derived.none_active)) {
    ESP_LOGE(TAG, "Cannot add derived none condition '%s': maximum reached", activity);
    this->mark_config_error_();
    return;
  }
  const size_t index = derived.none_count++;
  derived.none_active[index] = activity;
  derived.none_active_index[index] = activity_index_or_invalid(this->find_activity_(activity));
}

void RuntimeController::add_action_trigger(const char *name, Trigger<> *trigger) {
  if (name == nullptr || name[0] == '\0' || trigger == nullptr)
    return;
  if (this->action_count_ >= MAX_ACTIONS) {
    ESP_LOGE(TAG, "Cannot add action '%s': maximum %u actions reached", name, static_cast<unsigned>(MAX_ACTIONS));
    this->mark_config_error_();
    return;
  }
  this->actions_[this->action_count_++] = NamedAction{name, trigger};
}

void RuntimeController::add_event_trigger(const char *name, Trigger<> *trigger) {
  if (name == nullptr || name[0] == '\0' || trigger == nullptr)
    return;
  if (this->event_trigger_count_ >= MAX_ACTIONS) {
    ESP_LOGE(TAG, "Cannot add event trigger '%s': maximum %u triggers reached", name,
             static_cast<unsigned>(MAX_ACTIONS));
    this->mark_config_error_();
    return;
  }
  this->event_triggers_[this->event_trigger_count_++] = NamedAction{name, trigger};
}

void RuntimeController::add_policy_value_trigger(const char *policy, const char *value, Trigger<> *trigger) {
  if (policy == nullptr || policy[0] == '\0' || value == nullptr || trigger == nullptr)
    return;
  if (this->policy_value_action_count_ >= this->policy_value_actions_.size()) {
    ESP_LOGE(TAG, "Cannot add policy action '%s:%s': maximum reached", policy, value);
    this->mark_config_error_();
    return;
  }
  this->policy_value_actions_[this->policy_value_action_count_++] = PolicyValueAction{policy, value, trigger};
}

void RuntimeController::add_policy_output(const char *policy, const char *value, int32_t output) {
  if (policy == nullptr || policy[0] == '\0' || value == nullptr)
    return;
  if (this->policy_output_count_ >= this->policy_outputs_.size()) {
    ESP_LOGE(TAG, "Cannot add policy output '%s:%s': maximum reached", policy, value);
    this->mark_config_error_();
    return;
  }
  this->policy_outputs_[this->policy_output_count_++] = PolicyOutput{policy, value, output};
}

void RuntimeController::set_policy_change_trigger(const char *policy, Trigger<int32_t> *trigger) {
  if (policy == nullptr || policy[0] == '\0' || trigger == nullptr)
    return;
  if (this->policy_change_trigger_count_ >= this->policy_change_triggers_.size()) {
    ESP_LOGE(TAG, "Cannot add policy on_change '%s': maximum reached", policy);
    this->mark_config_error_();
    return;
  }
  this->policy_change_triggers_[this->policy_change_trigger_count_++] = PolicyChangeTrigger{policy, trigger};
}

void RuntimeController::add_led_state(const char *state, float red, float green, float blue, float brightness,
                                      const char *effect) {
  if (state == nullptr || state[0] == '\0')
    return;
  if (this->led_state_count_ >= this->led_states_.size()) {
    ESP_LOGE(TAG, "Cannot add LED state '%s': maximum reached", state);
    this->mark_config_error_();
    return;
  }
  this->led_states_[this->led_state_count_++] = LedState{state, red, green, blue, brightness, effect};
}

void RuntimeController::on_voip_event() {
  const uint32_t old_mask = this->generic_activity_mask_;
  const ResolvedPolicies old_policies = this->resolved_policies_;
  if (!this->sync_voip_activity_())
    return;
  (void) this->apply_derived_activities_();
  this->apply_generic_outputs_();
  this->commit_outputs_("voip_event", old_mask, old_policies);
}

void RuntimeController::event(const char *name) {
  if (this->dispatching_) {
    (void) this->enqueue_event_(name);
    return;
  }
  if (this->debug_) {
    ESP_LOGI(TAG, "EVENT seq=%" PRIu32 " name=%s mask=0x%08" PRIx32, this->sequence_,
             name != nullptr ? name : "-", this->generic_activity_mask_);
  }
  const uint32_t old_mask = this->generic_activity_mask_;
  const ResolvedPolicies old_policies = this->resolved_policies_;
  bool changed = false;
  bool event_known = false;

  for (size_t i = 0; i < this->event_rule_count_; i++) {
    auto &rule = this->event_rules_[i];
    if (!str_eq(rule.event, name))
      continue;
    event_known = true;
    if (!this->rule_matches_(rule))
      continue;
    for (size_t j = 0; j < rule.update_count; j++)
      changed |= this->apply_activity_update_(rule.updates[j]);
    changed |= this->apply_derived_activities_();
    if (changed) {
      this->apply_generic_outputs_();
      this->commit_outputs_(name != nullptr ? name : "event", old_mask, old_policies);
    }
    this->run_named_action_(rule.action);
    this->run_event_trigger_(name);
    return;
  }

  for (size_t i = 0; i < this->event_update_count_; i++) {
    const auto &update = this->event_updates_[i];
    if (str_eq(update.event, name)) {
      event_known = true;
      changed |= update.activity_index != INVALID_ACTIVITY
                     ? this->apply_activity_update_by_index_(update.activity_index, update.active)
                     : this->apply_activity_update_(update.activity, update.active);
    }
  }
  if (changed) {
    changed |= this->apply_derived_activities_();
    this->apply_generic_outputs_();
    this->commit_outputs_(name != nullptr ? name : "event", old_mask, old_policies);
  }
  int action_index = this->find_action_(name);
  if (action_index >= 0) {
    this->run_named_action_(this->actions_[action_index].name);
  }
  const bool has_event_trigger = this->find_event_trigger_(name) >= 0;
  if (has_event_trigger) {
    this->run_event_trigger_(name);
  } else if (action_index < 0 && !event_known && !changed) {
    ESP_LOGW(TAG, "Ignoring unknown event '%s'", name != nullptr ? name : "-");
  }
}

void RuntimeController::set_activity(const char *name, bool active) {
  if (this->dispatching_) {
    (void) this->enqueue_activity_update_(name, active);
    return;
  }
  const uint32_t old_mask = this->generic_activity_mask_;
  const ResolvedPolicies old_policies = this->resolved_policies_;
  bool changed = this->apply_activity_update_(name, active);
  changed |= this->apply_derived_activities_();
  if (!changed)
    return;

  this->apply_generic_outputs_();
  this->commit_outputs_(name != nullptr ? name : "set_activity", old_mask, old_policies);
}

void RuntimeController::set_activities(const ActivityUpdate *updates, size_t count) {
  if (updates == nullptr || count == 0)
    return;
  if (this->dispatching_) {
    (void) this->enqueue_activity_updates_(updates, count);
    return;
  }

  const uint32_t old_mask = this->generic_activity_mask_;
  const ResolvedPolicies old_policies = this->resolved_policies_;
  bool changed = false;
  for (size_t i = 0; i < count; i++)
    changed |= this->apply_activity_update_(updates[i].name, updates[i].active);
  changed |= this->apply_derived_activities_();
  if (!changed)
    return;

  this->apply_generic_outputs_();
  this->commit_outputs_("set_activities", old_mask, old_policies);
}

void RuntimeController::request_action(const char *name) {
  this->run_named_action_(name);
}

void RuntimeController::dump_state(const char *reason) {
#ifdef USE_RUNTIME_CONTROLLER_DEBUG
  ESP_LOGI(TAG, "SNAPSHOT reason=%s seq=%" PRIu32 " mask=0x%08" PRIx32,
           reason != nullptr ? reason : "-", this->sequence_, this->generic_activity_mask_);
  for (size_t i = 0; i < this->activity_count_; i++) {
    const auto &activity = this->activities_[i];
    if (activity.active) {
      ESP_LOGI(TAG, "  activity %s priority=%d group=%s", activity.name != nullptr ? activity.name : "-",
               static_cast<int>(activity.priority), activity.group != nullptr ? activity.group : "-");
    }
  }
  for (size_t i = 0; i < this->resolved_policies_.value_count; i++) {
    const auto &policy = this->resolved_policies_.values[i];
    ESP_LOGI(TAG, "  policy %s=%s output=%" PRId32, policy.policy != nullptr ? policy.policy : "-",
             policy.value != nullptr ? policy.value : "-", this->resolve_policy_output_(policy.policy, policy.value));
  }
#ifdef USE_RUNTIME_CONTROLLER_VOIP
  if (this->voip_ != nullptr) {
    ESP_LOGI(TAG, "  observed voip=%s activity=%s", this->voip_->get_call_state_str(),
             this->last_voip_activity_[0] != '\0' ? this->last_voip_activity_ : "-");
  }
#endif
}
#else
  (void) reason;
  if (this->debug_) {
    ESP_LOGI(TAG, "SNAPSHOT seq=%" PRIu32 " mask=0x%08" PRIx32, this->sequence_, this->generic_activity_mask_);
  }
}
#endif

bool RuntimeController::is_activity_active(const char *name) const {
  const int index = this->find_activity_(name);
  if (index < 0)
    return false;
  return this->activities_[index].active;
}

bool RuntimeController::is_activity_active_(const char *name, uint8_t index) const {
  if (index != INVALID_ACTIVITY && static_cast<size_t>(index) < this->activity_count_)
    return this->activities_[index].active;
  return this->is_activity_active(name);
}

bool RuntimeController::rule_matches_(const RuntimeController::EventRule &rule) const {
  if (rule.any_count > 0) {
    bool any = false;
    for (size_t i = 0; i < rule.any_count; i++)
      any |= this->is_activity_active_(rule.any_active[i], rule.any_active_index[i]);
    if (!any)
      return false;
  }
  for (size_t i = 0; i < rule.all_count; i++) {
    if (!this->is_activity_active_(rule.all_active[i], rule.all_active_index[i]))
      return false;
  }
  for (size_t i = 0; i < rule.none_count; i++) {
    if (this->is_activity_active_(rule.none_active[i], rule.none_active_index[i]))
      return false;
  }
  return true;
}

bool RuntimeController::derived_matches_(const RuntimeController::DerivedActivity &derived) const {
  if (derived.any_count > 0) {
    bool any = false;
    for (size_t i = 0; i < derived.any_count; i++)
      any |= this->is_activity_active_(derived.any_active[i], derived.any_active_index[i]);
    if (!any)
      return false;
  }
  for (size_t i = 0; i < derived.all_count; i++) {
    if (!this->is_activity_active_(derived.all_active[i], derived.all_active_index[i]))
      return false;
  }
  for (size_t i = 0; i < derived.none_count; i++) {
    if (this->is_activity_active_(derived.none_active[i], derived.none_active_index[i]))
      return false;
  }
  return true;
}

bool RuntimeController::apply_derived_activities_() {
  bool changed = false;
  for (size_t i = 0; i < this->derived_activity_count_; i++) {
    const auto &derived = this->derived_activities_[i];
    changed |= derived.activity_index != INVALID_ACTIVITY
                   ? this->set_activity_value_by_index_(derived.activity_index, this->derived_matches_(derived))
                   : this->set_activity_value_(derived.activity, this->derived_matches_(derived));
  }
  return changed;
}

void RuntimeController::publish_outputs_() {
  this->publish_state_outputs_();
  if (this->output_script_ != nullptr)
    this->output_script_->execute();
}

void RuntimeController::publish_state_outputs_() {
  if (this->activity_mask_output_.target != nullptr && this->activity_mask_output_.set != nullptr)
    this->activity_mask_output_.set(this->activity_mask_output_.target, this->generic_activity_mask_);
  if (this->sequence_output_.target != nullptr && this->sequence_output_.set != nullptr)
    this->sequence_output_.set(this->sequence_output_.target, this->sequence_);
}

void RuntimeController::apply_generic_outputs_() {
  struct PolicyWinner {
    const char *policy{nullptr};
    const char *value{nullptr};
    int16_t priority{-32768};
  };

  ResolvedPolicies output;
  PolicyWinner winners[MAX_POLICIES]{};
  size_t winner_count = 0;

  for (size_t i = 0; i < this->activity_count_; i++) {
    const auto &activity = this->activities_[i];
    if (!activity.active)
      continue;
    output.mask |= activity.bit;

    for (size_t j = 0; j < activity.policy_count; j++) {
      const auto &candidate = activity.policies[j];
      if (candidate.policy == nullptr || candidate.policy[0] == '\0' || candidate.value == nullptr)
        continue;

      PolicyWinner *winner = nullptr;
      for (size_t k = 0; k < winner_count; k++) {
        if (str_eq(winners[k].policy, candidate.policy)) {
          winner = &winners[k];
          break;
        }
      }
      if (winner == nullptr) {
        if (winner_count >= MAX_POLICIES)
          continue;
        winner = &winners[winner_count++];
        winner->policy = candidate.policy;
      }
      if (activity.priority >= winner->priority) {
        winner->priority = activity.priority;
        winner->value = candidate.value;
      }
    }
  }

  output.value_count = winner_count;
  for (size_t i = 0; i < winner_count; i++) {
    output.values[i].policy = winners[i].policy;
    output.values[i].value = winners[i].value;
  }

  this->generic_activity_mask_ = output.mask;
  this->resolved_policies_ = output;
}

bool RuntimeController::set_activity_value_(const char *name, bool active) {
  int index = this->find_activity_(name);
  if (index < 0) {
    ESP_LOGW(TAG, "Ignoring unknown activity '%s'", name != nullptr ? name : "-");
    return false;
  }

  return this->set_activity_value_by_index_(index, active);
}

bool RuntimeController::set_activity_value_by_index_(int index, bool active) {
  if (index < 0 || static_cast<size_t>(index) >= this->activity_count_)
    return false;
  ActivityConfig &activity = this->activities_[index];
  if (activity.active == active)
    return false;
  activity.active = active;
  return true;
}

bool RuntimeController::apply_activity_update_(const char *name, bool active) {
  int index = this->find_activity_(name);
  if (index < 0) {
    ESP_LOGW(TAG, "Ignoring unknown activity '%s'", name != nullptr ? name : "-");
    return false;
  }

  return this->apply_activity_update_by_index_(index, active);
}

bool RuntimeController::apply_activity_update_(const ActivityUpdate &update) {
  if (update.index != INVALID_ACTIVITY)
    return this->apply_activity_update_by_index_(update.index, update.active);
  return this->apply_activity_update_(update.name, update.active);
}

bool RuntimeController::apply_activity_update_by_index_(int index, bool active) {
  if (index < 0 || static_cast<size_t>(index) >= this->activity_count_)
    return false;

  bool changed = false;
  ActivityConfig &activity = this->activities_[index];
  if (active && activity.group != nullptr && activity.group[0] != '\0') {
    for (size_t i = 0; i < this->activity_count_; i++) {
      if (i == static_cast<size_t>(index))
        continue;
      ActivityConfig &peer = this->activities_[i];
      if (str_eq(peer.group, activity.group) && peer.active) {
        peer.active = false;
        changed = true;
      }
    }
  }
  changed |= this->set_activity_value_by_index_(index, active);
  return changed;
}

bool RuntimeController::set_activity_value_if_known_(const char *name, bool active) {
  return this->find_activity_(name) >= 0 && this->apply_activity_update_(name, active);
}

void RuntimeController::commit_outputs_(const char *reason, uint32_t old_mask, const ResolvedPolicies &old_policies) {
  if (old_mask == this->generic_activity_mask_) {
    bool policy_changed = old_policies.value_count != this->resolved_policies_.value_count;
    for (size_t i = 0; !policy_changed && i < this->resolved_policies_.value_count; i++) {
      const char *policy = this->resolved_policies_.values[i].policy;
      const char *old_value = find_policy_value(old_policies, policy, nullptr);
      const char *new_value = this->resolved_policies_.values[i].value;
      policy_changed = old_value == nullptr || new_value == nullptr || !str_eq(old_value, new_value);
    }
    if (!policy_changed)
      return;
  }

  this->sequence_++;
  if (this->debug_) {
    ESP_LOGI(TAG, "REDUCE seq=%" PRIu32 " reason=%s mask=0x%08" PRIx32 "->0x%08" PRIx32, this->sequence_,
             reason != nullptr ? reason : "-", old_mask, this->generic_activity_mask_);
  }
  const bool was_dispatching = this->dispatching_;
  this->dispatching_ = true;
  this->run_policy_actions_(old_policies, this->resolved_policies_);
  this->publish_outputs_();
  this->dispatching_ = was_dispatching;
  if (!this->dispatching_)
    this->drain_pending_events_();
}

void RuntimeController::build_voip_activity_name_(const char *state) {
  this->voip_activity_[0] = '\0';
#ifdef USE_RUNTIME_CONTROLLER_VOIP
  if (this->voip_activity_prefix_ == nullptr || this->voip_activity_prefix_[0] == '\0' || state == nullptr ||
      state[0] == '\0')
    return;
  std::snprintf(this->voip_activity_, sizeof(this->voip_activity_), "%s%s", this->voip_activity_prefix_,
                state);
#else
  (void) state;
#endif
}

bool RuntimeController::sync_voip_activity_() {
#ifdef USE_RUNTIME_CONTROLLER_VOIP
  if (this->voip_ == nullptr || this->voip_activity_prefix_ == nullptr)
    return false;

  this->build_voip_activity_name_(this->voip_->get_call_state_str());
  if (str_eq(this->voip_activity_, this->last_voip_activity_))
    return false;

  bool changed = false;
  if (this->last_voip_activity_[0] != '\0')
    changed |= this->set_activity_value_if_known_(this->last_voip_activity_, false);
  if (this->voip_activity_[0] != '\0')
    changed |= this->set_activity_value_if_known_(this->voip_activity_, true);

  std::snprintf(this->last_voip_activity_, sizeof(this->last_voip_activity_), "%s", this->voip_activity_);
  return changed;
#else
  return false;
#endif
}

void RuntimeController::run_policy_actions_(const ResolvedPolicies &old_policies, const ResolvedPolicies &new_policies) {
  for (size_t i = 0; i < new_policies.value_count; i++) {
    const char *policy = new_policies.values[i].policy;
    const char *value = new_policies.values[i].value;
    const char *old_value = find_policy_value(old_policies, policy, nullptr);
    if (str_eq(old_value, value))
      continue;
    if (value != nullptr && str_eq(policy, "led_status"))
      this->apply_led_state_(value);
    for (size_t j = 0; j < this->policy_value_action_count_; j++) {
      const auto &action = this->policy_value_actions_[j];
      if (str_eq(action.policy, policy) && str_eq(action.value, value)) {
        if (this->debug_)
          ESP_LOGI(TAG, "POLICY seq=%" PRIu32 " %s=%s", this->sequence_, policy, value);
        action.trigger->trigger();
      }
    }
    const int32_t output = this->resolve_policy_output_(policy, value);
    for (size_t j = 0; j < this->policy_global_output_count_; j++) {
      const auto &target = this->policy_global_outputs_[j];
      if (target.set != nullptr && str_eq(target.policy, policy)) {
        target.set(target.target, output);
      }
    }
    for (size_t j = 0; j < this->policy_change_trigger_count_; j++) {
      const auto &trigger = this->policy_change_triggers_[j];
      if (str_eq(trigger.policy, policy)) {
        if (this->debug_) {
          ESP_LOGI(TAG, "POLICY_CHANGE seq=%" PRIu32 " %s=%s output=%" PRId32, this->sequence_, policy, value,
                   output);
        }
        trigger.trigger->trigger(output);
      }
    }
  }
}

void RuntimeController::apply_led_state_(const char *state) {
  if (this->led_light_ == nullptr || state == nullptr)
    return;
  const LedState *match = nullptr;
  for (size_t i = 0; i < this->led_state_count_; i++) {
    if (str_eq(this->led_states_[i].state, state)) {
      match = &this->led_states_[i];
      break;
    }
  }
  if (match == nullptr) {
    ESP_LOGW(TAG, "No LED mapping for led_status '%s'", state);
    return;
  }
  if (match->brightness <= 0.0f) {
    auto call = this->led_light_->turn_off();
    call.set_save(false);
    call.perform();
    return;
  }
  auto call = this->led_light_->turn_on();
  call.set_rgb(match->red, match->green, match->blue);
  call.set_brightness(match->brightness);
  call.set_effect(match->effect != nullptr ? match->effect : "None");
  call.set_save(false);
  call.perform();
}

int32_t RuntimeController::resolve_policy_output_(const char *policy, const char *value) const {
  if (policy == nullptr || value == nullptr)
    return 0;
  for (size_t i = 0; i < this->policy_output_count_; i++) {
    const auto &entry = this->policy_outputs_[i];
    if (str_eq(entry.policy, policy) && str_eq(entry.value, value))
      return entry.output;
  }
  return 0;
}

int RuntimeController::find_activity_(const char *name) const {
  if (name == nullptr)
    return -1;
  for (size_t i = 0; i < this->activity_count_; i++) {
    if (str_eq(this->activities_[i].name, name))
      return static_cast<int>(i);
  }
  return -1;
}

int RuntimeController::find_action_(const char *name) const {
  if (name == nullptr)
    return -1;
  for (size_t i = 0; i < this->action_count_; i++) {
    if (str_eq(this->actions_[i].name, name))
      return static_cast<int>(i);
  }
  return -1;
}

int RuntimeController::find_event_trigger_(const char *name) const {
  if (name == nullptr)
    return -1;
  for (size_t i = 0; i < this->event_trigger_count_; i++) {
    if (str_eq(this->event_triggers_[i].name, name))
      return static_cast<int>(i);
  }
  return -1;
}

bool RuntimeController::enqueue_event_(const char *name) {
  if (name == nullptr || name[0] == '\0')
    return false;
  if (this->pending_event_count_ >= this->pending_events_.size()) {
    ESP_LOGE(TAG, "Cannot queue event '%s': queue full", name);
    return false;
  }
  auto &event = this->pending_events_[this->pending_event_count_++];
  event.name[0] = '\0';
  event.update_count = 0;
  event.kind = PendingEventKind::EVENT;
  std::snprintf(event.name, sizeof(event.name), "%s", name);
  if (this->debug_)
    ESP_LOGI(TAG, "EVENT_QUEUE seq=%" PRIu32 " name=%s", this->sequence_, event.name);
  this->enable_loop_soon_any_context();
  return true;
}

bool RuntimeController::enqueue_activity_update_(const char *name, bool active) {
  ActivityUpdate update{name, active};
  return this->enqueue_activity_updates_(&update, 1);
}

bool RuntimeController::enqueue_activity_updates_(const ActivityUpdate *updates, size_t count) {
  if (updates == nullptr || count == 0)
    return false;
  if (this->pending_event_count_ >= this->pending_events_.size()) {
    ESP_LOGE(TAG, "Cannot queue activity update: queue full");
    return false;
  }
  auto &event = this->pending_events_[this->pending_event_count_++];
  event.name[0] = '\0';
  event.update_count = 0;
  event.kind = PendingEventKind::SET_ACTIVITIES;
  event.update_count = count > std::size(event.updates) ? std::size(event.updates) : count;
  for (size_t i = 0; i < event.update_count; i++)
    event.updates[i] = updates[i];
  if (this->debug_)
    ESP_LOGI(TAG, "SET_QUEUE seq=%" PRIu32 " count=%u", this->sequence_, static_cast<unsigned>(event.update_count));
  this->enable_loop_soon_any_context();
  return true;
}

void RuntimeController::drain_pending_events_() {
  while (!this->dispatching_ && this->pending_event_count_ > 0) {
    PendingEvent event = this->pending_events_[0];
    for (size_t i = 1; i < this->pending_event_count_; i++)
      this->pending_events_[i - 1] = this->pending_events_[i];
    auto &last = this->pending_events_[--this->pending_event_count_];
    last.kind = PendingEventKind::EVENT;
    last.name[0] = '\0';
    last.update_count = 0;

    if (event.kind == PendingEventKind::EVENT) {
      this->event(event.name);
    } else {
      this->set_activities(event.updates, event.update_count);
    }
  }
}

void RuntimeController::run_named_action_(const char *name) {
  if (name == nullptr || name[0] == '\0')
    return;
  if (this->find_action_(name) < 0) {
    ESP_LOGW(TAG, "Ignoring unknown action '%s'", name);
    return;
  }
  for (size_t i = 0; i < this->pending_action_count_; i++) {
    if (str_eq(this->pending_actions_[i], name)) {
      if (this->debug_)
        ESP_LOGI(TAG, "ACTION_SKIP_DUP seq=%" PRIu32 " name=%s", this->sequence_, name);
      return;
    }
  }
  if (this->pending_action_count_ >= this->pending_actions_.size()) {
    ESP_LOGE(TAG, "Cannot queue action '%s': queue full", name);
    return;
  }
  if (this->debug_)
    ESP_LOGI(TAG, "ACTION_QUEUE seq=%" PRIu32 " name=%s", this->sequence_, name);
  this->pending_actions_[this->pending_action_count_++] = name;
  this->enable_loop_soon_any_context();
}

void RuntimeController::execute_named_action_(const char *name) {
  int index = this->find_action_(name);
  if (index < 0) {
    ESP_LOGW(TAG, "Ignoring unknown queued action '%s'", name != nullptr ? name : "-");
    return;
  }
  if (this->debug_)
    ESP_LOGI(TAG, "ACTION_RUN seq=%" PRIu32 " name=%s", this->sequence_, this->actions_[index].name);
  this->actions_[index].trigger->trigger();
}

void RuntimeController::drain_pending_actions_() {
  while (this->pending_action_count_ > 0) {
    const char *name = this->pending_actions_[0];
    for (size_t i = 1; i < this->pending_action_count_; i++)
      this->pending_actions_[i - 1] = this->pending_actions_[i];
    this->pending_actions_[--this->pending_action_count_] = nullptr;
    this->execute_named_action_(name);
  }
}

void RuntimeController::run_event_trigger_(const char *name) {
  const int index = this->find_event_trigger_(name);
  if (index < 0)
    return;
  if (this->debug_)
    ESP_LOGI(TAG, "EVENT_THEN seq=%" PRIu32 " name=%s", this->sequence_, this->event_triggers_[index].name);
  const bool was_dispatching = this->dispatching_;
  this->dispatching_ = true;
  this->event_triggers_[index].trigger->trigger();
  this->dispatching_ = was_dispatching;
  if (!this->dispatching_) {
    this->drain_pending_events_();
  }
}

}  // namespace esphome::runtime_controller
