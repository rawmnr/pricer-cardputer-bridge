#pragma once

#include <cstdint>

#include "bridge_protocol.hpp"

namespace eslbridge {

class DeviceUi {
public:
    void begin();
    void show_ready(std::uint8_t ir_gpio);
    void show_command(protocol::Command command, protocol::Status status, std::uint32_t tx_count);
    void update();
};

}  // namespace eslbridge
