#include <unity.h>

#include <cstddef>
#include <cstdint>

#include "orientation_test.hpp"
#include "ir_transmitter.hpp"

#ifndef ARDUINO
inline void delayMicroseconds(unsigned int) {}
#endif

// Include implementation directly for isolated PlatformIO test unit linking.
#include "../../src/orientation_test.cpp"

namespace eslbridge {

// The schedule tests inspect plans only; provide the transmit symbol required by
// the implementation without coupling this suite to RMT hardware.
protocol::Status IrTransmitter::send_pricer_frame(
    std::uint8_t,
    std::uint16_t,
    std::uint32_t,
    const std::uint8_t*,
    std::size_t) {
    return protocol::Status::kOk;
}

}  // namespace eslbridge

using namespace eslbridge;

void setUp(void) {}
void tearDown(void) {}
void assert_frame_bytes(
    const OrientationTestFrame& frame,
    const std::uint8_t* expected,
    const std::size_t expected_length) {
    TEST_ASSERT_EQUAL_UINT32(expected_length, frame.length);
    for (std::size_t index = 0; index < expected_length; ++index) {
        TEST_ASSERT_EQUAL_UINT8(expected[index], frame.data[index]);
    }
}

void test_orientation_kOne_is_tag_tinker_blink_plan(void) {
    constexpr std::uint8_t expected_ping[] = {
        0x85, 0x02, 0xB3, 0xB7, 0x3F, 0x97, 0x01, 0x00, 0x00, 0x00,
        0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01,
        0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01,
        0x40, 0x2C,
    };
    constexpr std::uint8_t expected_flash[] = {
        0x85, 0x02, 0xB3, 0xB7, 0x3F, 0x06, 0x49, 0x00, 0x00, 0x00,
        0x05, 0xE7, 0xDF,
    };

    const auto& plan = orientation_test_plan(OrientationTest::kOne);

    TEST_ASSERT_EQUAL_STRING("TAGTINKER_BLINK", orientation_test_name(OrientationTest::kOne));
    TEST_ASSERT_EQUAL_UINT32(2, plan.frame_count);

    const auto& ping = plan.frames[0];
    assert_frame_bytes(ping, expected_ping, sizeof(expected_ping));
    TEST_ASSERT_EQUAL_UINT16(161, ping.repeats);
    TEST_ASSERT_EQUAL_UINT32(5000, ping.inter_repeat_gap_us);
    TEST_ASSERT_EQUAL_UINT32(0, ping.pre_transmit_gap_us);

    const auto& flash = plan.frames[1];
    assert_frame_bytes(flash, expected_flash, sizeof(expected_flash));
    TEST_ASSERT_EQUAL_UINT16(81, flash.repeats);
    TEST_ASSERT_EQUAL_UINT32(5000, flash.inter_repeat_gap_us);
    TEST_ASSERT_EQUAL_UINT32(20000, flash.pre_transmit_gap_us);
}


void test_all_orientation_keys_share_one_plan(void) {
    const auto& two = orientation_test_plan(OrientationTest::kTwo);
    const auto& three = orientation_test_plan(OrientationTest::kThree);
    const auto& four = orientation_test_plan(OrientationTest::kFour);

    TEST_ASSERT_EQUAL_STRING("TAGTINKER_1327_RAW", orientation_test_name(OrientationTest::kTwo));
    TEST_ASSERT_EQUAL_STRING("TAGTINKER_1327_RAW", orientation_test_name(OrientationTest::kThree));
    TEST_ASSERT_EQUAL_STRING("TAGTINKER_1327_RAW", orientation_test_name(OrientationTest::kFour));
    TEST_ASSERT_EQUAL_UINT32(295, two.frame_count);
    TEST_ASSERT_TRUE(two.frames == three.frames);
    TEST_ASSERT_TRUE(two.frames == four.frames);
    TEST_ASSERT_EQUAL_UINT32(two.frame_count, three.frame_count);
    TEST_ASSERT_EQUAL_UINT32(two.frame_count, four.frame_count);
}

void test_orientation_frame_order_and_count(void) {
    const auto& plan = orientation_test_plan(OrientationTest::kTwo);

    // The sequence is ping, parameters, 292 indexed data packets, refresh.
    TEST_ASSERT_EQUAL_UINT32(32, plan.frames[0].length);
    TEST_ASSERT_EQUAL_UINT8(0x85, plan.frames[0].data[0]);
    TEST_ASSERT_EQUAL_UINT8(0x97, plan.frames[0].data[5]);

    TEST_ASSERT_EQUAL_UINT32(34, plan.frames[1].length);
    TEST_ASSERT_EQUAL_UINT8(0x34, plan.frames[1].data[5]);
    TEST_ASSERT_EQUAL_UINT8(0x05, plan.frames[1].data[9]);
    TEST_ASSERT_EQUAL_UINT8(0x16, plan.frames[1].data[10]);
    TEST_ASSERT_EQUAL_UINT8(0xD0, plan.frames[1].data[11]);

    for (std::size_t packet = 0; packet < 292; ++packet) {
        const auto& frame = plan.frames[2 + packet];
        TEST_ASSERT_EQUAL_UINT32(34, frame.length);
        TEST_ASSERT_EQUAL_UINT8(0x85, frame.data[0]);
        TEST_ASSERT_EQUAL_UINT8(0x34, frame.data[5]);
        TEST_ASSERT_EQUAL_UINT8(0x20, frame.data[9]);
        TEST_ASSERT_EQUAL_UINT8(
            static_cast<std::uint8_t>((packet >> 8U) & 0xFFU), frame.data[10]);
        TEST_ASSERT_EQUAL_UINT8(
            static_cast<std::uint8_t>(packet & 0xFFU), frame.data[11]);
    }

    const auto& refresh = plan.frames[294];
    TEST_ASSERT_EQUAL_UINT32(30, refresh.length);
    TEST_ASSERT_EQUAL_UINT8(0x85, refresh.data[0]);
    TEST_ASSERT_EQUAL_UINT8(0x34, refresh.data[5]);
    TEST_ASSERT_EQUAL_UINT8(0x01, refresh.data[9]);
}

void test_orientation_repeat_metadata(void) {
    const auto& plan = orientation_test_plan(OrientationTest::kTwo);

    TEST_ASSERT_EQUAL_UINT16(81, plan.frames[0].repeats);
    TEST_ASSERT_EQUAL_UINT16(16, plan.frames[1].repeats);
    for (std::size_t packet = 0; packet < 292; ++packet) {
        TEST_ASSERT_EQUAL_UINT16(3, plan.frames[2 + packet].repeats);
    }
    TEST_ASSERT_EQUAL_UINT16(21, plan.frames[294].repeats);

    for (std::size_t index = 0; index < plan.frame_count; ++index) {
        TEST_ASSERT_EQUAL_UINT32(500, plan.frames[index].inter_repeat_gap_us);
    }
}

void test_orientation_upstream_pre_transmit_gaps(void) {
    const auto& plan = orientation_test_plan(OrientationTest::kTwo);

    TEST_ASSERT_EQUAL_UINT32(0, plan.frames[0].pre_transmit_gap_us);
    TEST_ASSERT_EQUAL_UINT32(50000, plan.frames[1].pre_transmit_gap_us);
    TEST_ASSERT_EQUAL_UINT32(50000, plan.frames[2].pre_transmit_gap_us);

    // Settle for 1 ms before packets following each 32-packet boundary.
    for (std::size_t packet = 1; packet < 292; ++packet) {
        const auto expected = packet % 32U == 0U ? 1000U : 0U;
        TEST_ASSERT_EQUAL_UINT32(expected, plan.frames[2 + packet].pre_transmit_gap_us);
    }

    TEST_ASSERT_EQUAL_UINT32(50000, plan.frames[294].pre_transmit_gap_us);
}


void run_all_tests(void) {
    UNITY_BEGIN();
    RUN_TEST(test_orientation_kOne_is_tag_tinker_blink_plan);
    RUN_TEST(test_all_orientation_keys_share_one_plan);
    RUN_TEST(test_orientation_frame_order_and_count);
    RUN_TEST(test_orientation_repeat_metadata);
    RUN_TEST(test_orientation_upstream_pre_transmit_gaps);
    UNITY_END();
}

#ifdef ARDUINO
#include <Arduino.h>
void setup() {
    run_all_tests();
}
void loop() {}
#else
int main(int argc, char** argv) {
    (void)argc;
    (void)argv;
    run_all_tests();
    return 0;
}
#endif
