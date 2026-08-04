#include "ir_transmitter.hpp"

#include <algorithm>
#include <array>

#include <Arduino.h>
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
    rmt_config_t config = RMT_DEFAULT_CONFIG_TX(
        static_cast<gpio_num_t>(config::kIrGpio), kRmtChannel);
    config.clk_div = kClockDivider;
    // One PP16 frame can contain 256 bytes = 512 nibble items.
    // Reserve all eight RMT memory blocks so the bounded frame fits without
    // heap-backed driver buffering or chunk-induced timing gaps.
    config.mem_block_num = 8;
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

protocol::Status IrTransmitter::send_pricer_frame(
    const std::uint8_t modulation,
    const std::uint16_t repeats,
    const std::uint32_t inter_repeat_gap_us,
    const std::uint8_t* frame_data,
    const std::size_t frame_length) {
    if (!initialized_) {
        return protocol::Status::kHardwareError;
    }
    if (state_ == protocol::TransmitterState::kBusy) {
        return protocol::Status::kBusy;
    }
    if (!detail::valid_pricer_frame_request(
            modulation, repeats, inter_repeat_gap_us, frame_length)) {
        return protocol::Status::kInvalidArgument;
    }
    if (modulation == config::kModulationPp4) {
        return protocol::Status::kNotImplemented;
    }

    state_ = protocol::TransmitterState::kBusy;

    const auto profile = pp16::make_provisional_profile();
    const auto enc_res = pp16::encode_frame(frame_data, frame_length, profile, encoded_frame_);
    if (enc_res != pp16::Status::kOk) {
        state_ = protocol::TransmitterState::kIdle;
        return protocol::Status::kInvalidArgument;
    }

    for (std::size_t i = 0; i < encoded_frame_.symbol_count; ++i) {
        pp16::RmtPhaseTicks ticks{};
        if (pp16::convert_symbol_to_ticks(encoded_frame_.symbols[i], ticks) != pp16::Status::kOk) {
            state_ = protocol::TransmitterState::kIdle;
            return protocol::Status::kInvalidArgument;
        }
        rmt_items_[i].level0 = 1;
        rmt_items_[i].duration0 = ticks.high_ticks;
        rmt_items_[i].level1 = 0;
        rmt_items_[i].duration1 = ticks.low_ticks;
    }

    const auto carrier = carrier_ticks(pp16::kPrecirCarrierHz, 50);
    if (rmt_set_tx_carrier(
            kRmtChannel, true, carrier.high, carrier.low, RMT_CARRIER_LEVEL_HIGH) != ESP_OK) {
        state_ = protocol::TransmitterState::kFault;
        return protocol::Status::kHardwareError;
    }

    const std::uint32_t frame_duration_ms = (encoded_frame_.total_duration_us + 999U) / 1000U;
    const TickType_t wait_ticks = pdMS_TO_TICKS(frame_duration_ms + kSchedulingMarginMs);

    for (std::uint16_t rep = 0; rep < repeats; ++rep) {
        const auto write_err = rmt_write_items(
            kRmtChannel,
            rmt_items_.data(),
            static_cast<int>(encoded_frame_.symbol_count),
            false);
        if (write_err != ESP_OK) {
            state_ = protocol::TransmitterState::kFault;
            return protocol::Status::kHardwareError;
        }

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

        if (rep + 1 < repeats && inter_repeat_gap_us > 0) {
            const std::uint32_t gap_ms = inter_repeat_gap_us / 1000U;
            const std::uint32_t gap_rem_us = inter_repeat_gap_us % 1000U;
            if (gap_ms > 0) {
                vTaskDelay(pdMS_TO_TICKS(gap_ms));
            }
            if (gap_rem_us > 0) {
                delayMicroseconds(gap_rem_us);
            }
        }
    }

    state_ = protocol::TransmitterState::kIdle;
    ++tx_count_;
    return protocol::Status::kOk;
}
}  // namespace eslbridge
