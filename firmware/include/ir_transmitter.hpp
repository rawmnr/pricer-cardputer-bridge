#pragma once

#include <array>
#include <cstdint>

#include "app_config.hpp"
#include "bridge_protocol.hpp"
#include "pp4_encoder.hpp"

namespace eslbridge::detail {

struct CarrierPlan {
    std::uint32_t requested_hz{0};
    std::uint32_t effective_hz{0};
    std::uint16_t high_ticks{0};
    std::uint16_t low_ticks{0};
};

constexpr CarrierPlan make_carrier_plan(
    const std::uint32_t requested_hz,
    const std::uint8_t duty_percent) {
    if (requested_hz == 0) {
        return CarrierPlan{};
    }
    const auto period_ticks = (pp4::kApbClockHz + (requested_hz / 2U)) / requested_hz;
    const auto bounded_period_ticks = period_ticks < 2U ? 2U : period_ticks;
    const auto high_ticks = (bounded_period_ticks * duty_percent + 50U) / 100U;
    const auto bounded_high_ticks =
        high_ticks < 1U
            ? 1U
            : (high_ticks >= bounded_period_ticks ? bounded_period_ticks - 1U : high_ticks);
    return CarrierPlan{
        requested_hz,
        pp4::kApbClockHz / bounded_period_ticks,
        static_cast<std::uint16_t>(bounded_high_ticks),
        static_cast<std::uint16_t>(bounded_period_ticks - bounded_high_ticks),
    };
}

}  // namespace eslbridge::detail

#include "pp16_encoder.hpp"

#if __has_include(<driver/rmt.h>)
#include <driver/rmt.h>
#else
typedef struct {
    std::uint32_t duration0 : 15;
    std::uint32_t level0 : 1;
    std::uint32_t duration1 : 15;
    std::uint32_t level1 : 1;
} rmt_item32_t;
#endif

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
constexpr bool valid_pricer_frame_request(
    const std::uint8_t modulation,
    const std::uint16_t repeats,
    const std::uint32_t inter_repeat_gap_us,
    const std::size_t frame_length) {
    if (modulation != config::kModulationPp4 && modulation != config::kModulationPp16) {
        return false;
    }
    if (repeats < config::kMinPricerRepeats || repeats > config::kMaxPricerRepeats) {
        return false;
    }
    if (inter_repeat_gap_us > config::kMaxInterRepeatGapUs) {
        return false;
    }
    if (frame_length < config::kMinPricerFrameBytes || frame_length > config::kMaxPricerFrameBytes) {
        return false;
    }
    return true;
}

}  // namespace detail

class IrTransmitter {
public:
    protocol::Status begin();
    protocol::Status carrier_test(std::uint32_t frequency_hz, std::uint32_t duration_us, std::uint8_t duty_percent);
    protocol::Status send_pricer_frame(
        std::uint8_t modulation,
        std::uint16_t repeats,
        std::uint32_t inter_repeat_gap_us,
        const std::uint8_t* frame_data,
        std::size_t frame_length);
    protocol::TransmitterState state() const { return state_; }
    std::uint32_t tx_count() const { return tx_count_; }

private:
    protocol::TransmitterState state_{protocol::TransmitterState::kIdle};
    std::uint32_t tx_count_{0};
    bool initialized_{false};
    pp4::EncodedFrame encoded_pp4_frame_{};
    std::array<rmt_item32_t, pp4::kMaxSymbolsPerFrame> pp4_rmt_items_{};
    pp16::EncodedFrame encoded_frame_{};
    std::array<rmt_item32_t, pp16::kMaxSymbolsPerFrame> rmt_items_{};
};

}  // namespace eslbridge
