#pragma once

#include <cstdint>

#include "bridge_protocol.hpp"

namespace eslbridge {

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
