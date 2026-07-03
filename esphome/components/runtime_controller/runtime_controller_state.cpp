#include "runtime_controller_state.h"

#include <cstring>

namespace esphome::runtime_controller {

static bool str_eq(const char *left, const char *right) {
  return left == right || (left != nullptr && right != nullptr && strcmp(left, right) == 0);
}

struct PolicyWinner {
  const char *policy{nullptr};
  const char *value{nullptr};
  int16_t priority{-32768};
};

ResolvedPolicies reduce_generic_activities(const GenericActivity *activities, size_t count) {
  ResolvedPolicies output;
  PolicyWinner winners[MAX_POLICIES]{};
  size_t winner_count = 0;

  for (size_t i = 0; i < count; i++) {
    const auto &activity = activities[i];
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
  return output;
}

const char *find_policy_value(const ResolvedPolicies &output, const char *policy, const char *fallback) {
  if (policy == nullptr)
    return fallback;
  for (size_t i = 0; i < output.value_count; i++) {
    if (str_eq(output.values[i].policy, policy))
      return output.values[i].value;
  }
  return fallback;
}

}  // namespace esphome::runtime_controller
