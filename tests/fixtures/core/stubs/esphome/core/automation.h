#pragma once
#include <functional>
#include <string>
namespace esphome {
template<typename... Ts> class Trigger { public: std::function<void(Ts...)> fn; void trigger(Ts... x){if(fn)fn(x...);} };
template<typename... Ts> class Action { public: virtual void play(const Ts &...x)=0; };
template<typename... Ts> class Condition { public: virtual bool check(const Ts &...x)=0; };
template<typename T> class Parented { protected: T *parent_{}; };
template<typename T> struct DummyTemplate { template<typename... Ts>T value(Ts...){return T{};} };
}
#define TEMPLATABLE_VALUE(type, name) esphome::DummyTemplate<type> name##_;
