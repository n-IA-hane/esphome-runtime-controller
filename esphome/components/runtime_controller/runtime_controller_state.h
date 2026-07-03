#pragma once

#include <cstddef>
#include <cstdint>

namespace esphome::runtime_controller {

static constexpr size_t MAX_POLICIES = 8;
static constexpr size_t MAX_ACTIVITY_POLICIES = 8;

struct PolicyValue {
  const char *policy{nullptr};
  const char *value{nullptr};
};

struct GenericActivity {
  uint32_t bit{0};
  int16_t priority{0};
  bool active{false};
  PolicyValue policies[MAX_ACTIVITY_POLICIES]{};
  size_t policy_count{0};
};

struct ResolvedPolicies {
  uint32_t mask{0};
  PolicyValue values[MAX_POLICIES]{};
  size_t value_count{0};
};

ResolvedPolicies reduce_generic_activities(const GenericActivity *activities, size_t count);
const char *find_policy_value(const ResolvedPolicies &output, const char *policy, const char *fallback = nullptr);

}  // namespace esphome::runtime_controller
