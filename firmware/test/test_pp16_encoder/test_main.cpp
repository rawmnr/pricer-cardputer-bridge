#include <unity.h>

#include <cstdint>

#include "pp16_encoder.hpp"
// Include implementation directly for isolated PlatformIO test unit linking.
#include "../../src/pp16_encoder.cpp"

using namespace eslbridge::pp16;

void setUp(void) {}
void tearDown(void) {}

void test_provisional_profile_validation(void) {
    TimingProfile profile = make_provisional_profile();
    TEST_ASSERT_TRUE(profile.is_provisional);
    TEST_ASSERT_TRUE(profile.validate());
    TEST_ASSERT_EQUAL_UINT32(1250000, profile.carrier_frequency_hz);
    TEST_ASSERT_EQUAL_UINT32(21, profile.symbol_burst_us);
    TEST_ASSERT_EQUAL_UINT8(50, profile.duty_percent);
}

void test_invalid_profile_rejection(void) {
    TimingProfile bad_freq = make_provisional_profile();
    bad_freq.carrier_frequency_hz = 100000;
    TEST_ASSERT_FALSE(bad_freq.validate());

    TimingProfile bad_duty = make_provisional_profile();
    bad_duty.duty_percent = 80;
    TEST_ASSERT_FALSE(bad_duty.validate());

    TimingProfile bad_burst = make_provisional_profile();
    bad_burst.symbol_burst_us = 0;
    TEST_ASSERT_FALSE(bad_burst.validate());

    EncodedFrame frame{};
    std::uint8_t payload = 0x12;
    TEST_ASSERT_EQUAL(
        static_cast<int>(Status::kInvalidProfile),
        static_cast<int>(encode_frame(&payload, 1, bad_freq, frame)));
}

void test_nibble_gap_calculation(void) {
    TimingProfile profile = make_provisional_profile();
    for (std::uint8_t n = 0; n < 16; ++n) {
        std::uint32_t expected_total = kPrecirNibbleTotalDurationsUs[n];
        std::uint32_t expected_gap = expected_total - 21;
        TEST_ASSERT_EQUAL_UINT32(expected_gap, profile.symbol_gap_us(n));

        Pp16Symbol sym = profile.symbol_timing(n);
        TEST_ASSERT_EQUAL_UINT32(21, sym.burst_us);
        TEST_ASSERT_EQUAL_UINT32(expected_gap, sym.gap_us);
        TEST_ASSERT_EQUAL_UINT32(expected_total, sym.total_us());
    }
}

void test_encode_single_byte(void) {
    TimingProfile profile = make_provisional_profile();
    EncodedFrame frame{};
    std::uint8_t payload[1] = {0x12};  // high = 1, low = 2

    Status status = encode_frame(payload, 1, profile, frame);
    TEST_ASSERT_EQUAL(static_cast<int>(Status::kOk), static_cast<int>(status));
    TEST_ASSERT_EQUAL_UINT32(2, frame.symbol_count);

    // 0: High nibble (1)
    TEST_ASSERT_EQUAL_UINT32(21, frame.symbols[0].burst_us);
    TEST_ASSERT_EQUAL_UINT32(profile.symbol_gap_us(1), frame.symbols[0].gap_us);

    // 1: Low nibble (2)
    TEST_ASSERT_EQUAL_UINT32(21, frame.symbols[1].burst_us);
    TEST_ASSERT_EQUAL_UINT32(profile.symbol_gap_us(2), frame.symbols[1].gap_us);

    std::uint32_t expected_total = frame.symbols[0].total_us() + frame.symbols[1].total_us();
    TEST_ASSERT_EQUAL_UINT32(expected_total, frame.total_duration_us);
}

void test_encode_empty_and_null_payload(void) {
    TimingProfile profile = make_provisional_profile();
    EncodedFrame frame{};
    std::uint8_t payload = 0x55;

    TEST_ASSERT_EQUAL(
        static_cast<int>(Status::kEmptyPayload),
        static_cast<int>(encode_frame(nullptr, 1, profile, frame)));

    TEST_ASSERT_EQUAL(
        static_cast<int>(Status::kEmptyPayload),
        static_cast<int>(encode_frame(&payload, 0, profile, frame)));
}

void test_encode_capacity_boundary(void) {
    TimingProfile profile = make_provisional_profile();
    EncodedFrame frame{};
    static std::uint8_t max_payload[kMaxFrameBytes];
    for (std::size_t i = 0; i < kMaxFrameBytes; ++i) {
        max_payload[i] = 0xAA;
    }

    // 256 bytes payload -> (256*2) = 512 symbols
    Status status = encode_frame(max_payload, kMaxFrameBytes, profile, frame);
    TEST_ASSERT_EQUAL(static_cast<int>(Status::kOk), static_cast<int>(status));
    TEST_ASSERT_EQUAL_UINT32(512, frame.symbol_count);

    // 257 bytes payload -> payload too large
    status = encode_frame(max_payload, kMaxFrameBytes + 1, profile, frame);
    TEST_ASSERT_EQUAL(static_cast<int>(Status::kPayloadTooLarge), static_cast<int>(status));
}

void test_symbol_to_ticks_conversion(void) {
    Pp16Symbol sym{21, 100};
    RmtPhaseTicks ticks{};

    Status status = convert_symbol_to_ticks(sym, ticks);
    TEST_ASSERT_EQUAL(static_cast<int>(Status::kOk), static_cast<int>(status));
    TEST_ASSERT_EQUAL_UINT16(210, ticks.high_ticks);
    TEST_ASSERT_EQUAL_UINT16(1000, ticks.low_ticks);

    // Excess duration > 32767 ticks (e.g. 3277 us = 32770 ticks)
    Pp16Symbol overflow_sym{3277, 100};
    status = convert_symbol_to_ticks(overflow_sym, ticks);
    TEST_ASSERT_EQUAL(static_cast<int>(Status::kDurationOverflow), static_cast<int>(status));
}

void run_all_tests(void) {
    UNITY_BEGIN();
    RUN_TEST(test_provisional_profile_validation);
    RUN_TEST(test_invalid_profile_rejection);
    RUN_TEST(test_nibble_gap_calculation);
    RUN_TEST(test_encode_single_byte);
    RUN_TEST(test_encode_empty_and_null_payload);
    RUN_TEST(test_encode_capacity_boundary);
    RUN_TEST(test_symbol_to_ticks_conversion);
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
