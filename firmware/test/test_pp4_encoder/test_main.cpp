#include <unity.h>

#include <cstdint>

#include "pp4_encoder.hpp"
// Include implementation directly for isolated PlatformIO test unit linking.
#include "../../src/pp4_encoder.cpp"

using namespace eslbridge::pp4;

void setUp(void) {}
void tearDown(void) {}

void test_tagtinker_profile_and_effective_carrier(void) {
    const TimingProfile profile = make_tagtinker_profile();
    TEST_ASSERT_TRUE(profile.is_provisional);
    TEST_ASSERT_TRUE(profile.validate());
    TEST_ASSERT_EQUAL_UINT32(kTagTinkerCarrierHz, profile.carrier_frequency_hz);
    TEST_ASSERT_EQUAL_UINT32(kTagTinkerEffectiveCarrierHz, profile.effective_carrier_frequency_hz());
    TEST_ASSERT_EQUAL_UINT8(50, profile.duty_percent);
    TEST_ASSERT_EQUAL_UINT32(40, profile.symbol_burst_us);
    TEST_ASSERT_EQUAL_UINT16(403, profile.symbol_burst_rmt_ticks);
}

void test_symbol_gap_lookup_uses_raw_two_bit_value(void) {
    const TimingProfile profile = make_tagtinker_profile();
    const std::uint16_t expected_rmt_gaps[] = {605, 2419, 1210, 1814};
    for (std::uint8_t symbol = 0; symbol < 4; ++symbol) {
        TEST_ASSERT_EQUAL_UINT32(kTagTinkerSymbolGapsUs[symbol], profile.symbol_gap_us(symbol));
        const auto timing = profile.symbol_timing(symbol);
        TEST_ASSERT_EQUAL_UINT8(symbol, timing.value);
        TEST_ASSERT_EQUAL_UINT32(40, timing.burst_us);
        TEST_ASSERT_EQUAL_UINT32(kTagTinkerSymbolGapsUs[symbol], timing.gap_us);
        TEST_ASSERT_EQUAL_UINT16(403, timing.rmt_high_ticks);
        TEST_ASSERT_EQUAL_UINT16(expected_rmt_gaps[symbol], timing.rmt_low_ticks);
    }
}

void test_all_raw_symbols_are_lsb_pair_first(void) {
    const TimingProfile profile = make_tagtinker_profile();
    EncodedFrame frame{};
    const std::uint8_t payload[] = {0xE4};  // 00, 01, 10, 11, LSB pair first.

    TEST_ASSERT_EQUAL(
        static_cast<int>(Status::kOk),
        static_cast<int>(encode_frame(payload, 1, profile, frame)));
    TEST_ASSERT_EQUAL_UINT32(5, frame.symbol_count);
    const std::uint8_t expected_symbols[] = {0, 1, 2, 3, 0};
    const std::uint32_t expected_starts[] = {0, 101, 383, 544, 765};
    std::uint32_t elapsed = 0;
    for (std::size_t i = 0; i < frame.symbol_count; ++i) {
        TEST_ASSERT_EQUAL_UINT32(expected_starts[i], elapsed);
        TEST_ASSERT_EQUAL_UINT8(expected_symbols[i], frame.symbols[i].value);
        TEST_ASSERT_EQUAL_UINT32(40, frame.symbols[i].burst_us);
        elapsed += frame.symbols[i].total_us();
    }
    TEST_ASSERT_EQUAL_UINT32(805, frame.total_duration_us);
    TEST_ASSERT_EQUAL_UINT32(805, elapsed);
    TEST_ASSERT_EQUAL_UINT32(0, frame.symbols[4].gap_us);
}

void test_golden_single_byte_patterns_and_closing_burst(void) {
    const TimingProfile profile = make_tagtinker_profile();
    const std::uint8_t payloads[] = {0x00, 0x55, 0xAA, 0xFF};
    const std::uint32_t expected_data_symbol_total_us[] = {404, 1128, 644, 884};
    const std::uint32_t expected_total_us[] = {444, 1168, 684, 924};
    const std::uint32_t expected_gap_us[] = {61, 242, 121, 181};
    const std::uint32_t expected_terminal_start_us[] = {404, 1128, 644, 884};
    for (std::size_t case_index = 0; case_index < 4; ++case_index) {
        EncodedFrame frame{};
        TEST_ASSERT_EQUAL(
            static_cast<int>(Status::kOk),
            static_cast<int>(encode_frame(&payloads[case_index], 1, profile, frame)));
        TEST_ASSERT_EQUAL_UINT32(5, frame.symbol_count);
        std::uint32_t elapsed = 0;
        for (std::size_t symbol_index = 0; symbol_index < 4; ++symbol_index) {
            TEST_ASSERT_EQUAL_UINT8(
                static_cast<std::uint8_t>(case_index == 0 ? 0 : case_index),
                frame.symbols[symbol_index].value);
            TEST_ASSERT_EQUAL_UINT32(expected_gap_us[case_index], frame.symbols[symbol_index].gap_us);
            elapsed += frame.symbols[symbol_index].total_us();
        }
        TEST_ASSERT_EQUAL_UINT32(expected_data_symbol_total_us[case_index],
                                 frame.total_duration_us - kTagTinkerBurstUs);
        TEST_ASSERT_EQUAL_UINT32(expected_total_us[case_index], frame.total_duration_us);
        TEST_ASSERT_EQUAL_UINT32(expected_terminal_start_us[case_index], elapsed);
        TEST_ASSERT_EQUAL_UINT32(kTagTinkerBurstUs, frame.symbols[4].burst_us);
        TEST_ASSERT_EQUAL_UINT32(0, frame.symbols[4].gap_us);
    }
}

void test_ordering_crosses_byte_boundary(void) {
    const TimingProfile profile = make_tagtinker_profile();
    EncodedFrame frame{};
    const std::uint8_t payload[] = {0xE4, 0x1B};  // second byte: 11, 10, 01, 00.
    const std::uint8_t expected_symbols[] = {0, 1, 2, 3, 3, 2, 1, 0, 0};

    TEST_ASSERT_EQUAL(
        static_cast<int>(Status::kOk),
        static_cast<int>(encode_frame(payload, 2, profile, frame)));
    TEST_ASSERT_EQUAL_UINT32(9, frame.symbol_count);
    std::uint32_t elapsed = 0;
    for (std::size_t i = 0; i < frame.symbol_count; ++i) {
        TEST_ASSERT_EQUAL_UINT8(expected_symbols[i], frame.symbols[i].value);
        elapsed += frame.symbols[i].total_us();
    }
    TEST_ASSERT_EQUAL_UINT32(elapsed, frame.total_duration_us);
    TEST_ASSERT_EQUAL_UINT32(0, frame.symbols[8].gap_us);
}

void test_encode_maximum_frame_is_bounded(void) {
    const TimingProfile profile = make_tagtinker_profile();
    EncodedFrame frame{};
    static std::uint8_t max_payload[kMaxFrameBytes];
    for (std::size_t i = 0; i < kMaxFrameBytes; ++i) {
        max_payload[i] = 0xAA;
    }

    TEST_ASSERT_EQUAL(
        static_cast<int>(Status::kOk),
        static_cast<int>(encode_frame(max_payload, kMaxFrameBytes, profile, frame)));
    TEST_ASSERT_EQUAL_UINT32(kMaxSymbolsPerFrame, frame.symbol_count);
    TEST_ASSERT_EQUAL_UINT32((256U * 4U * (40U + 121U)) + 40U, frame.total_duration_us);
    std::uint32_t elapsed = 0;
    for (std::size_t i = 0; i < frame.symbol_count; ++i) {
        if (i == frame.symbol_count - 1) {
            TEST_ASSERT_EQUAL_UINT32(256U * 4U * (40U + 121U), elapsed);
        }
        elapsed += frame.symbols[i].total_us();
    }
    TEST_ASSERT_EQUAL_UINT32(frame.total_duration_us, elapsed);
    TEST_ASSERT_EQUAL_UINT8(0, frame.symbols[kMaxSymbolsPerFrame - 1].value);
    TEST_ASSERT_EQUAL_UINT32(0, frame.symbols[kMaxSymbolsPerFrame - 1].gap_us);

    TEST_ASSERT_EQUAL(
        static_cast<int>(Status::kPayloadTooLarge),
        static_cast<int>(encode_frame(max_payload, kMaxFrameBytes + 1, profile, frame)));
}

void test_empty_payload_and_invalid_profile_rejected(void) {
    const TimingProfile profile = make_tagtinker_profile();
    EncodedFrame frame{};
    std::uint8_t payload = 0x00;

    TEST_ASSERT_EQUAL(
        static_cast<int>(Status::kEmptyPayload),
        static_cast<int>(encode_frame(nullptr, 1, profile, frame)));
    TEST_ASSERT_EQUAL(
        static_cast<int>(Status::kEmptyPayload),
        static_cast<int>(encode_frame(&payload, 0, profile, frame)));

    TimingProfile invalid = profile;
    invalid.symbol_gaps_us[1] = 0;
    TEST_ASSERT_EQUAL(
        static_cast<int>(Status::kInvalidProfile),
        static_cast<int>(encode_frame(&payload, 1, invalid, frame)));
}

void test_symbol_to_ticks_conversion(void) {
    const Pp4Symbol symbol{1, 40, 243};
    RmtPhaseTicks ticks{};
    TEST_ASSERT_EQUAL(
        static_cast<int>(Status::kOk),
        static_cast<int>(convert_symbol_to_ticks(symbol, ticks)));
    TEST_ASSERT_EQUAL_UINT16(400, ticks.high_ticks);
    TEST_ASSERT_EQUAL_UINT16(2430, ticks.low_ticks);

    const Pp4Symbol overflow_symbol{0, 3277, 1};
    TEST_ASSERT_EQUAL(
        static_cast<int>(Status::kDurationOverflow),
        static_cast<int>(convert_symbol_to_ticks(overflow_symbol, ticks)));
}

void run_all_tests(void) {
    UNITY_BEGIN();
    RUN_TEST(test_tagtinker_profile_and_effective_carrier);
    RUN_TEST(test_symbol_gap_lookup_uses_raw_two_bit_value);
    RUN_TEST(test_all_raw_symbols_are_lsb_pair_first);
    RUN_TEST(test_golden_single_byte_patterns_and_closing_burst);
    RUN_TEST(test_ordering_crosses_byte_boundary);
    RUN_TEST(test_encode_maximum_frame_is_bounded);
    RUN_TEST(test_empty_payload_and_invalid_profile_rejected);
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
