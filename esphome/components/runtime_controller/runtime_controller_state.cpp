#include "runtime_controller_state.h"

#include <cstring>

namespace esphome::runtime_controller {

static bool str_eq(const char *left, const char *right) {
  return left == right || (left != nullptr && right != nullptr && strcmp(left, right) == 0);
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
