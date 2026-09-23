#pragma once
#include <functional>
namespace esphome::script {
template<typename... Ts>class Script{public:std::function<void()>fn;void execute(){if(fn)fn();}};
}
