#include <unity.h>

#include <cstdint>
#include <vector>

#include "app_config.hpp"
#include "bridge_protocol.hpp"
// Include implementation directly for isolated PlatformIO test unit linking.
#include "../../src/bridge_protocol.cpp"

using namespace eslbridge::protocol;

void setUp(void) {}
void tearDown(void) {}

static std::vector<std::uint8_t> make_frame(
    Command cmd,
    std::uint16_t seq,
    Status status = Status::kOk,
    const std::vector<std::uint8_t>& payload = {},
    std::uint8_t version = eslbridge::config::kProtocolVersion,
    bool corrupt_crc = false) {
    std::vector<std::uint8_t> frame;
    frame.reserve(kHeaderSize + payload.size() + kCrcSize);
    frame.insert(frame.end(), kMagic.begin(), kMagic.end());
    frame.push_back(version);
    frame.push_back(static_cast<std::uint8_t>(cmd));
    frame.push_back(0);  // flags
    frame.push_back(static_cast<std::uint8_t>(status));
    frame.push_back(static_cast<std::uint8_t>(seq & 0xFF));
    frame.push_back(static_cast<std::uint8_t>((seq >> 8) & 0xFF));
    std::uint16_t len = static_cast<std::uint16_t>(payload.size());
    frame.push_back(static_cast<std::uint8_t>(len & 0xFF));
    frame.push_back(static_cast<std::uint8_t>((len >> 8) & 0xFF));
    frame.insert(frame.end(), payload.begin(), payload.end());

    ByteView body(frame.data() + 4, frame.size() - 4);
    std::uint32_t checksum = crc32(body);
    if (corrupt_crc) {
        checksum ^= 0xFFFFFFFFU;
    }
    frame.push_back(static_cast<std::uint8_t>(checksum & 0xFFU));
    frame.push_back(static_cast<std::uint8_t>((checksum >> 8U) & 0xFFU));
    frame.push_back(static_cast<std::uint8_t>((checksum >> 16U) & 0xFFU));
    frame.push_back(static_cast<std::uint8_t>((checksum >> 24U) & 0xFFU));
    return frame;
}

void test_fragmented_valid_frame(void) {
    StreamParser parser;
    auto frame = make_frame(Command::kHello, 0x1234);
    std::uint32_t now = 1000;

    for (std::size_t i = 0; i < frame.size() - 1; ++i) {
        StreamParser::Result res = parser.push(frame[i], now);
        TEST_ASSERT_EQUAL(static_cast<int>(StreamParser::Result::kNeedMoreData), static_cast<int>(res));
    }

    StreamParser::Result final_res = parser.push(frame.back(), now);
    TEST_ASSERT_EQUAL(static_cast<int>(StreamParser::Result::kMessageReady), static_cast<int>(final_res));
    TEST_ASSERT_EQUAL_UINT8(static_cast<std::uint8_t>(Command::kHello), static_cast<std::uint8_t>(parser.message().command));
    TEST_ASSERT_EQUAL_UINT16(0x1234, parser.message().sequence);
    TEST_ASSERT_EQUAL_UINT8(eslbridge::config::kProtocolVersion, parser.message().version);
    TEST_ASSERT_EQUAL(static_cast<int>(Status::kOk), static_cast<int>(parser.error()));
}

void test_concatenated_frames(void) {
    StreamParser parser;
    auto frame1 = make_frame(Command::kHello, 1);
    auto frame2 = make_frame(Command::kGetStatus, 2);
    std::uint32_t now = 2000;

    // Push frame 1
    for (std::size_t i = 0; i < frame1.size(); ++i) {
        auto res = parser.push(frame1[i], now);
        if (i == frame1.size() - 1) {
            TEST_ASSERT_EQUAL(static_cast<int>(StreamParser::Result::kMessageReady), static_cast<int>(res));
            TEST_ASSERT_EQUAL_UINT8(static_cast<std::uint8_t>(Command::kHello), static_cast<std::uint8_t>(parser.message().command));
            TEST_ASSERT_EQUAL_UINT16(1, parser.message().sequence);
        }
    }
    parser.reset();

    // Push frame 2 immediately
    for (std::size_t i = 0; i < frame2.size(); ++i) {
        auto res = parser.push(frame2[i], now);
        if (i == frame2.size() - 1) {
            TEST_ASSERT_EQUAL(static_cast<int>(StreamParser::Result::kMessageReady), static_cast<int>(res));
            TEST_ASSERT_EQUAL_UINT8(static_cast<std::uint8_t>(Command::kGetStatus), static_cast<std::uint8_t>(parser.message().command));
            TEST_ASSERT_EQUAL_UINT16(2, parser.message().sequence);
        }
    }
}

void test_noise_magic_resync(void) {
    StreamParser parser;
    std::uint32_t now = 3000;

    // Push noise bytes including partial magic mismatch
    TEST_ASSERT_EQUAL(static_cast<int>(StreamParser::Result::kDiscardedNoise), static_cast<int>(parser.push(0xFF, now)));
    TEST_ASSERT_EQUAL(static_cast<int>(StreamParser::Result::kNeedMoreData), static_cast<int>(parser.push('E', now)));
    TEST_ASSERT_EQUAL(static_cast<int>(StreamParser::Result::kNeedMoreData), static_cast<int>(parser.push('S', now)));
    TEST_ASSERT_EQUAL(static_cast<int>(StreamParser::Result::kDiscardedNoise), static_cast<int>(parser.push(0x99, now)));

    // Push a valid frame
    auto frame = make_frame(Command::kCarrierTest, 42);
    StreamParser::Result last_res = StreamParser::Result::kNeedMoreData;
    for (auto b : frame) {
        last_res = parser.push(b, now);
    }
    TEST_ASSERT_EQUAL(static_cast<int>(StreamParser::Result::kMessageReady), static_cast<int>(last_res));
    TEST_ASSERT_EQUAL_UINT8(static_cast<std::uint8_t>(Command::kCarrierTest), static_cast<std::uint8_t>(parser.message().command));
    TEST_ASSERT_EQUAL_UINT16(42, parser.message().sequence);
}

void test_max_payload_boundary(void) {
    StreamParser parser;
    std::vector<std::uint8_t> payload(eslbridge::config::kMaxPayload, 0xAB);
    auto frame = make_frame(Command::kSendPricerFrame, 100, Status::kOk, payload);
    std::uint32_t now = 4000;

    StreamParser::Result last_res = StreamParser::Result::kNeedMoreData;
    for (auto b : frame) {
        last_res = parser.push(b, now);
    }
    TEST_ASSERT_EQUAL(static_cast<int>(StreamParser::Result::kMessageReady), static_cast<int>(last_res));
    TEST_ASSERT_EQUAL(eslbridge::config::kMaxPayload, parser.message().payload.size());
    TEST_ASSERT_EQUAL_UINT16(100, parser.message().sequence);
}

void test_oversized_header(void) {
    StreamParser parser;
    std::uint32_t now = 5000;

    // Header with payload_length = 4097 (> kMaxPayload)
    std::vector<std::uint8_t> hdr;
    hdr.insert(hdr.end(), kMagic.begin(), kMagic.end());
    hdr.push_back(eslbridge::config::kProtocolVersion);
    hdr.push_back(static_cast<std::uint8_t>(Command::kSendPricerFrame));
    hdr.push_back(0); // flags
    hdr.push_back(0); // status
    hdr.push_back(0x66); // seq low
    hdr.push_back(0x55); // seq high (seq = 0x5566)
    hdr.push_back(0x01); // payload len low (4097 = 0x1001)
    hdr.push_back(0x10); // payload len high

    StreamParser::Result res = StreamParser::Result::kNeedMoreData;
    for (auto b : hdr) {
        res = parser.push(b, now);
    }
    TEST_ASSERT_EQUAL(static_cast<int>(StreamParser::Result::kFrameError), static_cast<int>(res));
    TEST_ASSERT_EQUAL(static_cast<int>(Status::kBadLength), static_cast<int>(parser.error()));
    TEST_ASSERT_TRUE(parser.has_error_context());
    TEST_ASSERT_EQUAL_UINT8(static_cast<std::uint8_t>(Command::kSendPricerFrame), static_cast<std::uint8_t>(parser.error_command()));
    TEST_ASSERT_EQUAL_UINT16(0x5566, parser.error_sequence());
}

void test_crc_and_version_errors_with_context(void) {
    // Version error test
    {
        StreamParser parser;
        std::uint32_t now = 6000;
        auto frame = make_frame(Command::kGetStatus, 77, Status::kOk, {}, 2 /* invalid version */);
        StreamParser::Result res = StreamParser::Result::kNeedMoreData;
        for (auto b : frame) {
            res = parser.push(b, now);
        }
        TEST_ASSERT_EQUAL(static_cast<int>(StreamParser::Result::kFrameError), static_cast<int>(res));
        TEST_ASSERT_EQUAL(static_cast<int>(Status::kBadVersion), static_cast<int>(parser.error()));
        TEST_ASSERT_TRUE(parser.has_error_context());
        TEST_ASSERT_EQUAL_UINT8(static_cast<std::uint8_t>(Command::kGetStatus), static_cast<std::uint8_t>(parser.error_command()));
        TEST_ASSERT_EQUAL_UINT16(77, parser.error_sequence());
    }

    // CRC error test
    {
        StreamParser parser;
        std::uint32_t now = 6500;
        auto frame = make_frame(Command::kCarrierTest, 88, Status::kOk, {}, eslbridge::config::kProtocolVersion, true /* corrupt crc */);
        StreamParser::Result res = StreamParser::Result::kNeedMoreData;
        for (auto b : frame) {
            res = parser.push(b, now);
        }
        TEST_ASSERT_EQUAL(static_cast<int>(StreamParser::Result::kFrameError), static_cast<int>(res));
        TEST_ASSERT_EQUAL(static_cast<int>(Status::kBadCrc), static_cast<int>(parser.error()));
        TEST_ASSERT_TRUE(parser.has_error_context());
        TEST_ASSERT_EQUAL_UINT8(static_cast<std::uint8_t>(Command::kCarrierTest), static_cast<std::uint8_t>(parser.error_command()));
        TEST_ASSERT_EQUAL_UINT16(88, parser.error_sequence());
    }
}

void test_timeout_via_poll(void) {
    // Timeout with complete header
    {
        StreamParser parser;
        auto frame = make_frame(Command::kSendPricerFrame, 200);
        std::uint32_t now = 7000;
        // Push only header (12 bytes)
        for (std::size_t i = 0; i < kHeaderSize; ++i) {
            parser.push(frame[i], now);
        }

        // Poll at exactly timeout threshold should not time out yet
        TEST_ASSERT_EQUAL(static_cast<int>(StreamParser::Result::kNeedMoreData), static_cast<int>(parser.poll(now + eslbridge::config::kParserTimeoutMs)));

        // Poll past timeout threshold
        auto poll_res = parser.poll(now + eslbridge::config::kParserTimeoutMs + 1);
        TEST_ASSERT_EQUAL(static_cast<int>(StreamParser::Result::kTimeout), static_cast<int>(poll_res));
        TEST_ASSERT_EQUAL(static_cast<int>(Status::kTimeout), static_cast<int>(parser.error()));
        TEST_ASSERT_TRUE(parser.has_error_context());
        TEST_ASSERT_EQUAL_UINT8(static_cast<std::uint8_t>(Command::kSendPricerFrame), static_cast<std::uint8_t>(parser.error_command()));
        TEST_ASSERT_EQUAL_UINT16(200, parser.error_sequence());
    }

    // Timeout with partial header (unrecoverable noise/partial header)
    {
        StreamParser parser;
        std::uint32_t now = 8000;
        parser.push('E', now);
        parser.push('S', now);

        auto poll_res = parser.poll(now + eslbridge::config::kParserTimeoutMs + 1);
        TEST_ASSERT_EQUAL(static_cast<int>(StreamParser::Result::kTimeout), static_cast<int>(poll_res));
        TEST_ASSERT_EQUAL(static_cast<int>(Status::kTimeout), static_cast<int>(parser.error()));
        TEST_ASSERT_FALSE(parser.has_error_context());
    }
}

void test_successful_recovery_afterward(void) {
    StreamParser parser;
    std::uint32_t now = 9000;

    // Trigger CRC error first
    auto bad_frame = make_frame(Command::kHello, 1, Status::kOk, {}, eslbridge::config::kProtocolVersion, true);
    for (auto b : bad_frame) {
        parser.push(b, now);
    }
    TEST_ASSERT_TRUE(parser.has_error_context());
    parser.reset();

    // Now push valid frame
    auto good_frame = make_frame(Command::kGetStatus, 300);
    StreamParser::Result last_res = StreamParser::Result::kNeedMoreData;
    for (auto b : good_frame) {
        last_res = parser.push(b, now + 10);
    }
    TEST_ASSERT_EQUAL(static_cast<int>(StreamParser::Result::kMessageReady), static_cast<int>(last_res));
    TEST_ASSERT_EQUAL_UINT8(static_cast<std::uint8_t>(Command::kGetStatus), static_cast<std::uint8_t>(parser.message().command));
    TEST_ASSERT_EQUAL_UINT16(300, parser.message().sequence);
    TEST_ASSERT_EQUAL(static_cast<int>(Status::kOk), static_cast<int>(parser.error()));
}

void run_all_tests(void) {
    UNITY_BEGIN();
    RUN_TEST(test_fragmented_valid_frame);
    RUN_TEST(test_concatenated_frames);
    RUN_TEST(test_noise_magic_resync);
    RUN_TEST(test_max_payload_boundary);
    RUN_TEST(test_oversized_header);
    RUN_TEST(test_crc_and_version_errors_with_context);
    RUN_TEST(test_timeout_via_poll);
    RUN_TEST(test_successful_recovery_afterward);
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
