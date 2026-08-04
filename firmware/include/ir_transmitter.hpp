#pragma once

#include <cstdint>

#include "app_config.hpp"
#include "bridge_protocol.hpp"

namespace eslbridge {

namespace detail {

struct CarrierBurstPlan {
    std::uint16_t first_ticks{0};
    std::uint16_t second_ticks{0};

    constexpr std::uint32_t total_ticks() const {
        return static_cast<std::uint32_t>(first_ticks) + static_cast<std::uint32_t>(second_ticks);
    }
};

constexpr bool valid_carrier_request(
    const std::uint32_t frequency_hz,
    const std::uint32_t duration_us,
    const std::uint8_t duty_percent) {
    if (duration_us == 0 || duration_us > config::kMaxCarrierTestUs) {
        return false;
    }
    if (frequency_hz < config::kMinCarrierHz || frequency_hz > config::kMaxCarrierHz) {
        return false;
    }
    if (duty_percent < config::kMinDutyPercent || duty_percent > config::kMaxDutyPercent) {
        return false;
    }
    return true;
}

constexpr CarrierBurstPlan make_carrier_burst_plan(const std::uint32_t duration_us) {
    if (duration_us == 0 || duration_us > config::kMaxCarrierTestUs) {
        return CarrierBurstPlan{0, 0};
    }
    constexpr std::uint32_t kTicksPerUs = 10;
    constexpr std::uint32_t kMaxPhaseTicks = 32767;

    const std::uint32_t total_ticks = duration_us * kTicksPerUs;
    if (total_ticks <= kMaxPhaseTicks) {
        return CarrierBurstPlan{static_cast<std::uint16_t>(total_ticks), 0};
    }
    const std::uint16_t first = static_cast<std::uint16_t>(kMaxPhaseTicks);
    const std::uint16_t second = static_cast<std::uint16_t>(total_ticks - kMaxPhaseTicks);
    return CarrierBurstPlan{first, second};
}

}  // namespace detail

class IrTransmitter {
public:
    protocol::Status begin();
    protocol::Status carrier_test(std::uint32_t frequency_hz, std::uint32_t duration_us, std::uint8_t duty_percent);
    protocol::Status send_pricer_frame();
    protocol::TransmitterState state() const { return state_; }
    std::uint32_t tx_count() const { return tx_count_; }

private:
    protocol::TransmitterState state_{protocol::TransmitterState::kIdle};
    std::uint32_t tx_count_{0};
    bool initialized_{false};
};

}  // namespace eslbridge
