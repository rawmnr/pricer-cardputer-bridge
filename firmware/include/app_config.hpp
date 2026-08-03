#pragma once

#include <cstddef>
#include <cstdint>

namespace eslbridge::config {

inline constexpr std::uint8_t kProtocolVersion = 1;
inline constexpr std::size_t kMaxPayload = 4096;
inline constexpr std::uint8_t kIrGpio = 44;
inline constexpr std::uint32_t kDefaultCarrierHz = 1'245'000;
inline constexpr std::uint8_t kDefaultDutyPercent = 50;
inline constexpr std::uint32_t kMaxCarrierTestUs = 5'000;
inline constexpr std::uint32_t kMinCarrierHz = 500'000;
inline constexpr std::uint32_t kMaxCarrierHz = 2'000'000;
inline constexpr std::uint8_t kMinDutyPercent = 10;
inline constexpr std::uint8_t kMaxDutyPercent = 60;
inline constexpr std::uint32_t kParserTimeoutMs = 2'000;

}  // namespace eslbridge::config
