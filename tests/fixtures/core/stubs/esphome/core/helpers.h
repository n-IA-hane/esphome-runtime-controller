#pragma once
#include <new>
#include <cstdint>
namespace esphome {
namespace testing {
inline bool fail_allocations = false;
inline unsigned allocation_attempts = 0;
}
template<typename T> class RAMAllocator {
 public:
  static constexpr uint8_t ALLOC_EXTERNAL = 1, ALLOC_INTERNAL = 2;
  explicit RAMAllocator(uint8_t = 0) {}
  T *allocate(unsigned count) {
    testing::allocation_attempts++;
    if (testing::fail_allocations)
      return nullptr;
    return static_cast<T *>(::operator new(sizeof(T) * count, std::nothrow));
  }
  void deallocate(T *ptr, unsigned) { ::operator delete(ptr); }
};
}  // namespace esphome
