#include "ir_transmitter.hpp"

#include <algorithm>
#include <array>

#include <driver/rmt.h>
#include <esp_err.h>

#include "app_config.hpp"

namespace eslbridge {
namespace {

constexpr rmt_channel_t kRmtChannel = RMT_CHANNEL_0;
constexpr std::uint8_t kClockDivider = 8;  // 80 MHz APB / 8 = 10 MHz, 0.1 us per tick.
constexpr std::uint32_t kTicksPerMicrosecond = 10;
constexpr std::uint32_t kMaxItemTicks = 32767;
constexpr std::uint32_t kApbClockHz = 80'000'000;

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
    if (frequency_hz < config::kMinCarrierHz || frequency_hz > config::kMaxCarrierHz ||
        duration_us == 0 || duration_us > config::kMaxCarrierTestUs ||
        duty_percent < config::kMinDutyPercent || duty_percent > config::kMaxDutyPercent) {
        return protocol::Status::kInvalidArgument;
    }

    state_ = protocol::TransmitterState::kBusy;
    const auto ticks = carrier_ticks(frequency_hz, duty_percent);
    if (rmt_set_tx_carrier(
            kRmtChannel, true, ticks.high, ticks.low, RMT_CARRIER_LEVEL_HIGH) != ESP_OK) {
        state_ = protocol::TransmitterState::kFault;
        return protocol::Status::kHardwareError;
    }

    std::array<rmt_item32_t, 2> items{};
    std::uint32_t remaining_ticks = duration_us * kTicksPerMicrosecond;
    std::size_t item_count = 0;

    while (remaining_ticks > 0 && item_count < items.size()) {
        const auto high_ticks = std::min(remaining_ticks, kMaxItemTicks);
        remaining_ticks -= high_ticks;
        const auto low_ticks = remaining_ticks > 0 ? 1U : 1U;
        items[item_count].level0 = 1;
        items[item_count].duration0 = high_ticks;
        items[item_count].level1 = 0;
        items[item_count].duration1 = low_ticks;
        ++item_count;
    }

    if (remaining_ticks > 0) {
        state_ = protocol::TransmitterState::kIdle;
        return protocol::Status::kInvalidArgument;
    }

    const auto error = rmt_write_items(kRmtChannel, items.data(), item_count, true);
    state_ = error == ESP_OK ? protocol::TransmitterState::kIdle : protocol::TransmitterState::kFault;
    if (error != ESP_OK) {
        return protocol::Status::kHardwareError;
    }

    ++tx_count_;
    return protocol::Status::kOk;
}

protocol::Status IrTransmitter::send_pricer_frame() {
    return protocol::Status::kNotImplemented;
}

}  // namespace eslbridge
