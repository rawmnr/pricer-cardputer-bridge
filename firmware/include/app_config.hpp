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
inline constexpr std::uint8_t kModulationPp4 = 4;
inline constexpr std::uint8_t kModulationPp16 = 16;
inline constexpr std::size_t kMinPricerFrameBytes = 1;
inline constexpr std::size_t kMaxPricerFrameBytes = 256;
inline constexpr std::uint16_t kMinPricerRepeats = 1;
inline constexpr std::uint16_t kMaxPricerRepeats = 100;
inline constexpr std::uint32_t kMaxInterRepeatGapUs = 1'000'000;

}  // namespace eslbridge::config
