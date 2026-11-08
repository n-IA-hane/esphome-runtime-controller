#pragma once
#include <array>
#include <cassert>
#include <memory>
#include <string>

namespace esphome::api {
class APIConnection {
 public:
  explicit APIConnection(std::string name) : name_(std::move(name)) {}
  bool is_authenticated() { return authenticated; }
  bool is_marked_for_removal() const { return removing; }
  const char *get_name() const { return name_.c_str(); }
  std::string name_;
  bool authenticated{false};
  bool removing{false};
};

class APIServer {
 public:
  using APIConnectionPtr = std::unique_ptr<APIConnection>;
  class ActiveClientsView {
   public:
    ActiveClientsView(const APIConnectionPtr *b, const APIConnectionPtr *e) : begin_(b), end_(e) {}
    const APIConnectionPtr *begin() const { return begin_; }
    const APIConnectionPtr *end() const { return end_; }
   private:
    const APIConnectionPtr *begin_;
    const APIConnectionPtr *end_;
  };
  ActiveClientsView active_clients() const { return {clients_.data(), clients_.data() + count_}; }
  APIConnection *accept(std::string peer) {
    assert(count_ < clients_.size());
    clients_[count_] = std::make_unique<APIConnection>(std::move(peer));
    return clients_[count_++].get();
  }
  std::string remove(APIConnection *client) {
    for (size_t i = 0; i < count_; ++i) {
      if (clients_[i].get() != client)
        continue;
      const auto name = client->name_;
      --count_;
      std::swap(clients_[i], clients_[count_]);
      clients_[count_].reset();
      return name;  // Caller emits disconnect only after the removal.
    }
    assert(false);
    return {};
  }
 private:
  std::array<APIConnectionPtr, 8> clients_;
  size_t count_{0};
};
inline APIServer *global_api_server = nullptr;
}  // namespace esphome::api
