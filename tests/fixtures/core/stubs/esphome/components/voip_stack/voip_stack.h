#pragma once
#include <functional>
#include <vector>
#include <string>
namespace esphome::voip_stack {
enum class CallState {DUMMY};
class VoipStack {
public:
 std::string state="idle";std::vector<std::function<void(CallState)>> callbacks;
 void add_on_state_callback(std::function<void(CallState)> fn){callbacks.push_back(fn);}
 const char *get_call_state_str(){return state.c_str();}
 void change(const char *s){state=s;for(auto &fn:callbacks)fn(CallState::DUMMY);}
};
}
