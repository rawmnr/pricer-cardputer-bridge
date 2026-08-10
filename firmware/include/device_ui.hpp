#pragma once

#include <cstdint>

#include "bridge_protocol.hpp"

namespace eslbridge {

enum class OrientationTest : std::uint8_t;

class DeviceUi {
public:
    void begin();
    void show_ready(
        std::uint8_t ir_gpio,
        const char* firmware_version,
        const char* git_sha,
        const char* build_provenance,
        const char* pp16_profile_revision);
    void show_command(protocol::Command command, protocol::Status status, std::uint32_t tx_count);
    void show_orientation_test_start(OrientationTest test);
    void show_orientation_test_result(
        OrientationTest test,
        protocol::Status status,
        std::uint32_t tx_delta);
    OrientationTest update();
};
}  // namespace eslbridge
