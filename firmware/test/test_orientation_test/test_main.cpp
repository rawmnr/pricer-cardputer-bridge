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
void assert_same_frame(
    const OrientationTestFrame& actual,
    const OrientationTestFrame& expected) {
    TEST_ASSERT_EQUAL_UINT32(expected.length, actual.length);
    for (std::size_t index = 0; index < expected.length; ++index) {
        TEST_ASSERT_EQUAL_UINT8(expected.data[index], actual.data[index]);
    }
    TEST_ASSERT_EQUAL_UINT16(expected.repeats, actual.repeats);
    TEST_ASSERT_EQUAL_UINT32(
        expected.inter_repeat_gap_us, actual.inter_repeat_gap_us);
    TEST_ASSERT_EQUAL_UINT32(
        expected.pre_transmit_gap_us, actual.pre_transmit_gap_us);
}

void assert_orientation_summary(
    const OrientationTest test,
    const std::uint32_t expected_frame_count,
    const std::uint32_t expected_airframe_count,
    const std::uint32_t expected_encoded_byte_count) {
    const auto& summary = orientation_test_summary(test);
    TEST_ASSERT_EQUAL_UINT32(expected_frame_count, summary.frame_count);
    TEST_ASSERT_EQUAL_UINT32(expected_airframe_count, summary.airframe_count);
    TEST_ASSERT_EQUAL_UINT32(
        expected_encoded_byte_count, summary.encoded_byte_count);
    TEST_ASSERT_EQUAL_UINT8(4, summary.modulation);
    TEST_ASSERT_EQUAL_UINT8(44, summary.ir_gpio);
    TEST_ASSERT_EQUAL_UINT32(1254902, summary.requested_carrier_hz);
    TEST_ASSERT_EQUAL_UINT32(1250000, summary.effective_carrier_hz);
    TEST_ASSERT_EQUAL_UINT8(50, summary.duty_percent);
}

void test_orientation_summary_contract_for_all_keys(void) {
    assert_orientation_summary(OrientationTest::kOne, 2, 242, 45);
    assert_orientation_summary(OrientationTest::kTwo, 4, 121, 130);
    assert_orientation_summary(OrientationTest::kThree, 4, 121, 130);
    assert_orientation_summary(OrientationTest::kFour, 295, 994, 10024);
}

void test_orientation_kThree_is_tagtinker_rle_white_plan(void) {
    constexpr std::uint8_t expected_white[] = {
        0x85, 0x02, 0xB3, 0xB7, 0x3F, 0x34, 0x00, 0x00, 0x00, 0x20,
        0x00, 0x00, 0x80, 0x00, 0xB6, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x37, 0x68,
    };

    const auto& black = orientation_test_plan(OrientationTest::kTwo);
    const auto& plan = orientation_test_plan(OrientationTest::kThree);

    TEST_ASSERT_EQUAL_STRING(
        "TAGTINKER_RLE_WHITE", orientation_test_name(OrientationTest::kThree));
    TEST_ASSERT_EQUAL_UINT32(4, plan.frame_count);

    assert_same_frame(plan.frames[0], black.frames[0]);
    assert_same_frame(plan.frames[1], black.frames[1]);

    const auto& data = plan.frames[2];
    assert_frame_bytes(data, expected_white, sizeof(expected_white));
    TEST_ASSERT_EQUAL_UINT16(3, data.repeats);
    TEST_ASSERT_EQUAL_UINT32(500, data.inter_repeat_gap_us);
    TEST_ASSERT_EQUAL_UINT32(50000, data.pre_transmit_gap_us);

    assert_same_frame(plan.frames[3], black.frames[3]);
}

void test_orientation_kFour_is_tagtinker_raw_plan(void) {
    const auto& plan = orientation_test_plan(OrientationTest::kFour);

    TEST_ASSERT_EQUAL_STRING(
        "TAGTINKER_1327_RAW", orientation_test_name(OrientationTest::kFour));
    TEST_ASSERT_EQUAL_UINT32(295, plan.frame_count);
}

void test_orientation_kFour_raw_frame_order_and_count(void) {
    const auto& plan = orientation_test_plan(OrientationTest::kFour);

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

void test_orientation_kFour_raw_repeat_metadata(void) {
    const auto& plan = orientation_test_plan(OrientationTest::kFour);

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

void test_orientation_kFour_raw_upstream_pre_transmit_gaps(void) {
    const auto& plan = orientation_test_plan(OrientationTest::kFour);

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

void test_orientation_kTwo_is_tagtinker_rle_black_plan(void) {
    constexpr std::uint8_t expected_ping[] = {
        0x85, 0x02, 0xB3, 0xB7, 0x3F, 0x97, 0x01, 0x00, 0x00, 0x00,
        0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01,
        0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01,
        0x40, 0x2C,
    };
    constexpr std::uint8_t expected_params[] = {
        0x85, 0x02, 0xB3, 0xB7, 0x3F, 0x34, 0x00, 0x00, 0x00, 0x05,
        0x00, 0x14, 0x00, 0x02, 0x00, 0x00, 0xD0, 0x00, 0x70, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x88, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x23, 0xD0,
    };
    constexpr std::uint8_t expected_data[] = {
        0x85, 0x02, 0xB3, 0xB7, 0x3F, 0x34, 0x00, 0x00, 0x00, 0x20,
        0x00, 0x00, 0x00, 0x01, 0x6C, 0x00, 0x00, 0x0B, 0x60, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x11, 0xE7,
    };
    constexpr std::uint8_t expected_refresh[] = {
        0x85, 0x02, 0xB3, 0xB7, 0x3F, 0x34, 0x00, 0x00, 0x00, 0x01,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFB,
        0xD5,
    };

    const auto& plan = orientation_test_plan(OrientationTest::kTwo);

    TEST_ASSERT_EQUAL_STRING(
        "TAGTINKER_RLE_BLACK", orientation_test_name(OrientationTest::kTwo));
    TEST_ASSERT_EQUAL_UINT32(4, plan.frame_count);

    const auto& ping = plan.frames[0];
    assert_frame_bytes(ping, expected_ping, sizeof(expected_ping));
    TEST_ASSERT_EQUAL_UINT16(81, ping.repeats);
    TEST_ASSERT_EQUAL_UINT32(500, ping.inter_repeat_gap_us);
    TEST_ASSERT_EQUAL_UINT32(0, ping.pre_transmit_gap_us);

    const auto& params = plan.frames[1];
    assert_frame_bytes(params, expected_params, sizeof(expected_params));
    TEST_ASSERT_EQUAL_UINT16(16, params.repeats);
    TEST_ASSERT_EQUAL_UINT32(500, params.inter_repeat_gap_us);
    TEST_ASSERT_EQUAL_UINT32(50000, params.pre_transmit_gap_us);
    TEST_ASSERT_EQUAL_UINT16(
        20, static_cast<std::uint16_t>((params.data[10] << 8U) | params.data[11]));
    TEST_ASSERT_EQUAL_UINT8(2, params.data[13]);
    TEST_ASSERT_EQUAL_UINT8(0, params.data[14]);
    TEST_ASSERT_EQUAL_UINT16(
        208, static_cast<std::uint16_t>((params.data[15] << 8U) | params.data[16]));
    TEST_ASSERT_EQUAL_UINT16(
        112, static_cast<std::uint16_t>((params.data[17] << 8U) | params.data[18]));

    const auto& data = plan.frames[2];
    assert_frame_bytes(data, expected_data, sizeof(expected_data));
    TEST_ASSERT_EQUAL_UINT16(3, data.repeats);
    TEST_ASSERT_EQUAL_UINT32(500, data.inter_repeat_gap_us);
    TEST_ASSERT_EQUAL_UINT32(50000, data.pre_transmit_gap_us);

    const auto& refresh = plan.frames[3];
    assert_frame_bytes(refresh, expected_refresh, sizeof(expected_refresh));
    TEST_ASSERT_EQUAL_UINT16(21, refresh.repeats);
    TEST_ASSERT_EQUAL_UINT32(500, refresh.inter_repeat_gap_us);
    TEST_ASSERT_EQUAL_UINT32(50000, refresh.pre_transmit_gap_us);
}



void run_all_tests(void) {
    UNITY_BEGIN();
    RUN_TEST(test_orientation_summary_contract_for_all_keys);
    RUN_TEST(test_orientation_kOne_is_tag_tinker_blink_plan);
    RUN_TEST(test_orientation_kTwo_is_tagtinker_rle_black_plan);
    RUN_TEST(test_orientation_kThree_is_tagtinker_rle_white_plan);
    RUN_TEST(test_orientation_kFour_is_tagtinker_raw_plan);
    RUN_TEST(test_orientation_kFour_raw_frame_order_and_count);
    RUN_TEST(test_orientation_kFour_raw_repeat_metadata);
    RUN_TEST(test_orientation_kFour_raw_upstream_pre_transmit_gaps);
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
