#pragma once
#include <new>
#include <cstdint>
namespace esphome {
namespace testing {
inline bool fail_allocations = false;
inline unsigned allocation_attempts = 0;
inline unsigned fail_on_attempt = 0;
inline unsigned last_allocation_flags = 0;
inline size_t allocated_bytes = 0;
inline size_t released_bytes = 0;
}
template<typename T> class RAMAllocator {
 public:
  static constexpr uint8_t ALLOC_EXTERNAL = 1, ALLOC_INTERNAL = 2;
  explicit RAMAllocator(uint8_t flags = 0) : flags_(flags) {}
  T *allocate(unsigned count) {
    testing::allocation_attempts++;
    testing::last_allocation_flags = flags_;
    if (testing::fail_allocations || testing::allocation_attempts == testing::fail_on_attempt)
      return nullptr;
    auto *result = static_cast<T *>(::operator new(sizeof(T) * count, std::nothrow));
    if (result != nullptr) testing::allocated_bytes += sizeof(T) * count;
    return result;
  }
  void deallocate(T *ptr, unsigned count) {
    if (ptr != nullptr) testing::released_bytes += sizeof(T) * count;
    ::operator delete(ptr);
  }
 private:
  uint8_t flags_;
};
}  // namespace esphome
