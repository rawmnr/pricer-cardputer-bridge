#include "ir_transmitter.hpp"

#include <algorithm>
#include <array>

#include <driver/rmt.h>
#include <esp_err.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include "app_config.hpp"

namespace eslbridge {
namespace {

constexpr rmt_channel_t kRmtChannel = RMT_CHANNEL_0;
constexpr std::uint8_t kClockDivider = 8;  // 80 MHz APB / 8 = 10 MHz, 0.1 us per tick.
constexpr std::uint32_t kTicksPerMicrosecond = 10;
constexpr std::uint32_t kMaxItemTicks = 32767;
constexpr std::uint32_t kApbClockHz = 80'000'000;
constexpr std::uint32_t kSchedulingMarginMs = 50;

struct CarrierTicks {
    std::uint16_t high;
    std::uint16_t low;
};

CarrierTicks carrier_ticks(const std::uint32_t frequency_hz, const std::uint8_t duty_percent) {
    const auto period = std::max<std::uint32_t>(
        2U, (kApbClockHz + (frequency_hz / 2U)) / frequency_hz);
    const auto high = std::clamp<std::uint32_t>(
        (period * duty_percent + 50U) / 100U, 1U, period - 1U);
    return {
        static_cast<std::uint16_t>(high),
        static_cast<std::uint16_t>(period - high),
    };
}

}  // namespace

protocol::Status IrTransmitter::begin() {
    rmt_config_t config = RMT_DEFAULT_CONFIG_TX(static_cast<gpio_num_t>(config::kIrGpio), kRmtChannel);
    config.clk_div = kClockDivider;
    config.mem_block_num = 1;
    config.tx_config.loop_en = false;
    config.tx_config.carrier_en = true;
    config.tx_config.carrier_freq_hz = config::kDefaultCarrierHz;
    config.tx_config.carrier_duty_percent = config::kDefaultDutyPercent;
    config.tx_config.carrier_level = RMT_CARRIER_LEVEL_HIGH;
    config.tx_config.idle_level = RMT_IDLE_LEVEL_LOW;
    config.tx_config.idle_output_en = true;

    if (rmt_config(&config) != ESP_OK) {
        state_ = protocol::TransmitterState::kFault;
        return protocol::Status::kHardwareError;
    }
    if (rmt_driver_install(kRmtChannel, 0, 0) != ESP_OK) {
        state_ = protocol::TransmitterState::kFault;
        return protocol::Status::kHardwareError;
    }

    initialized_ = true;
    state_ = protocol::TransmitterState::kIdle;
    return protocol::Status::kOk;
}

protocol::Status IrTransmitter::carrier_test(
    const std::uint32_t frequency_hz,
    const std::uint32_t duration_us,
    const std::uint8_t duty_percent) {
    if (!initialized_) {
        return protocol::Status::kHardwareError;
    }
    if (state_ == protocol::TransmitterState::kBusy) {
        return protocol::Status::kBusy;
    }
    if (!detail::valid_carrier_request(frequency_hz, duration_us, duty_percent)) {
        return protocol::Status::kInvalidArgument;
    }

    state_ = protocol::TransmitterState::kBusy;
    const auto ticks = carrier_ticks(frequency_hz, duty_percent);
    if (rmt_set_tx_carrier(
            kRmtChannel, true, ticks.high, ticks.low, RMT_CARRIER_LEVEL_HIGH) != ESP_OK) {
        state_ = protocol::TransmitterState::kFault;
        return protocol::Status::kHardwareError;
    }

    const auto plan = detail::make_carrier_burst_plan(duration_us);
    rmt_item32_t item{};
    item.level0 = 1;
    item.duration0 = plan.first_ticks;
    item.level1 = plan.second_ticks > 0 ? 1 : 0;
    item.duration1 = plan.second_ticks;

    const auto write_err = rmt_write_items(kRmtChannel, &item, 1, false);
    if (write_err != ESP_OK) {
        state_ = protocol::TransmitterState::kFault;
        return protocol::Status::kHardwareError;
    }

    const std::uint32_t duration_ms = (duration_us + 999U) / 1000U;
    const TickType_t wait_ticks = pdMS_TO_TICKS(duration_ms + kSchedulingMarginMs);

    const auto wait_err = rmt_wait_tx_done(kRmtChannel, wait_ticks);
    if (wait_err == ESP_ERR_TIMEOUT) {
        rmt_tx_stop(kRmtChannel);
        state_ = protocol::TransmitterState::kFault;
        return protocol::Status::kTimeout;
    }
    if (wait_err != ESP_OK) {
        rmt_tx_stop(kRmtChannel);
        state_ = protocol::TransmitterState::kFault;
        return protocol::Status::kHardwareError;
    }

    state_ = protocol::TransmitterState::kIdle;
    ++tx_count_;
    return protocol::Status::kOk;
}

protocol::Status IrTransmitter::send_pricer_frame() {
    return protocol::Status::kNotImplemented;
}

}  // namespace eslbridge
