#pragma once

#include <array>
#include <cstddef>
#include <cstdint>

#include "bridge_protocol.hpp"

namespace eslbridge {

class IrTransmitter;

enum class OrientationTest : std::uint8_t {
    kNone = 0,
    kOne = 1,
    kTwo = 2,
    kThree = 3,
    kFour = 4,
};

struct OrientationTestFrame {
    const std::uint8_t* data{};
    std::size_t length{};
    std::uint16_t repeats{};
    std::uint32_t inter_repeat_gap_us{};
    std::uint32_t pre_transmit_gap_us{};
};

struct OrientationTestPlan {
    std::array<OrientationTestFrame, 5> frames;
    std::size_t frame_count;
};

const OrientationTestPlan& orientation_test_plan(OrientationTest test);
const char* orientation_test_name(OrientationTest test);
protocol::Status run_orientation_test(IrTransmitter& transmitter, OrientationTest test);

}  // namespace eslbridge
