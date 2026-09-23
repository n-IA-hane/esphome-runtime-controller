#pragma once
#include <cinttypes>
namespace esphome::testing {
// Evaluate arguments, like an enabled firmware logger. In particular this does
// not hide invalid storage accesses inside dump_config()'s logging arguments.
template<typename... Ts> void log(Ts...) {}
}
#define ESP_LOGE(...) esphome::testing::log(__VA_ARGS__)
#define ESP_LOGW(...) esphome::testing::log(__VA_ARGS__)
#define ESP_LOGI(...) esphome::testing::log(__VA_ARGS__)
#define ESP_LOGCONFIG(...) esphome::testing::log(__VA_ARGS__)
#define YESNO(x) ((x)?"YES":"NO")
