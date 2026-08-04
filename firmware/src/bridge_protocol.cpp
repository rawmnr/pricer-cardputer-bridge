#include "bridge_protocol.hpp"

#include <algorithm>

namespace eslbridge::protocol {
namespace {

constexpr std::uint32_t kCrcPolynomial = 0xEDB88320U;

}  // namespace

std::uint32_t crc32(const ByteView data) {
    std::uint32_t crc = 0xFFFFFFFFU;
    for (const auto byte : data) {
        crc ^= byte;
        for (int bit = 0; bit < 8; ++bit) {
            const std::uint32_t mask = static_cast<std::uint32_t>(-(static_cast<std::int32_t>(crc & 1U)));
            crc = (crc >> 1U) ^ (kCrcPolynomial & mask);
        }
    }
    return crc ^ 0xFFFFFFFFU;
}

std::uint16_t read_u16_le(const std::uint8_t* data) {
    return static_cast<std::uint16_t>(data[0]) |
           (static_cast<std::uint16_t>(data[1]) << 8U);
}

std::uint32_t read_u32_le(const std::uint8_t* data) {
    return static_cast<std::uint32_t>(data[0]) |
           (static_cast<std::uint32_t>(data[1]) << 8U) |
           (static_cast<std::uint32_t>(data[2]) << 16U) |
           (static_cast<std::uint32_t>(data[3]) << 24U);
}

void write_u16_le(std::uint8_t* data, const std::uint16_t value) {
    data[0] = static_cast<std::uint8_t>(value & 0xFFU);
    data[1] = static_cast<std::uint8_t>((value >> 8U) & 0xFFU);
}

void write_u32_le(std::uint8_t* data, const std::uint32_t value) {
    data[0] = static_cast<std::uint8_t>(value & 0xFFU);
    data[1] = static_cast<std::uint8_t>((value >> 8U) & 0xFFU);
    data[2] = static_cast<std::uint8_t>((value >> 16U) & 0xFFU);
    data[3] = static_cast<std::uint8_t>((value >> 24U) & 0xFFU);
}

void StreamParser::reset() {
    size_ = 0;
    expected_size_ = 0;
    last_byte_ms_ = 0;
    message_ = {};
    error_ = Status::kOk;
}

bool StreamParser::magic_matches_prefix() const {
    if (size_ > kMagic.size()) {
        return false;
    }
    return std::equal(buffer_.begin(), buffer_.begin() + static_cast<std::ptrdiff_t>(size_), kMagic.begin());
}

StreamParser::Result StreamParser::push(const std::uint8_t byte, const std::uint32_t now_ms) {
    if (size_ > 0 && (now_ms - last_byte_ms_) > config::kParserTimeoutMs) {
        reset();
        error_ = Status::kTimeout;
    }
    last_byte_ms_ = now_ms;

    if (size_ < kMagic.size()) {
        buffer_[size_++] = byte;
        if (!magic_matches_prefix()) {
            // Retain a possible new first magic byte for fast resynchronization.
            const bool starts_new_magic = byte == kMagic[0];
            reset();
            if (starts_new_magic) {
                buffer_[0] = byte;
                size_ = 1;
                last_byte_ms_ = now_ms;
            }
            return Result::kDiscardedNoise;
        }
        return Result::kNeedMoreData;
    }

    if (size_ >= buffer_.size()) {
        error_ = Status::kBadLength;
        reset();
        return Result::kFrameError;
    }

    buffer_[size_++] = byte;

    if (size_ == kHeaderSize) {
        const auto payload_length = read_u16_le(buffer_.data() + 10);
        if (payload_length > config::kMaxPayload) {
            error_ = Status::kBadLength;
            reset();
            return Result::kFrameError;
        }
        expected_size_ = kHeaderSize + payload_length + kCrcSize;
    }

    if (expected_size_ != 0 && size_ == expected_size_) {
        if (!decode_current_frame()) {
            const auto result = Result::kFrameError;
            size_ = 0;
            expected_size_ = 0;
            return result;
        }
        return Result::kMessageReady;
    }

    return Result::kNeedMoreData;
}

bool StreamParser::decode_current_frame() {
    const auto payload_length = read_u16_le(buffer_.data() + 10);
    const auto expected_crc = read_u32_le(buffer_.data() + kHeaderSize + payload_length);
    const auto actual_crc = crc32(ByteView(buffer_.data() + 4, 8 + payload_length));

    if (buffer_[4] != config::kProtocolVersion) {
        error_ = Status::kBadVersion;
        return false;
    }
    if (expected_crc != actual_crc) {
        error_ = Status::kBadCrc;
        return false;
    }

    message_.version = buffer_[4];
    message_.command = static_cast<Command>(buffer_[5]);
    message_.flags = buffer_[6];
    message_.status = static_cast<Status>(buffer_[7]);
    message_.sequence = read_u16_le(buffer_.data() + 8);
    message_.payload = ByteView(buffer_.data() + kHeaderSize, payload_length);
    error_ = Status::kOk;
    return true;
}

std::size_t encode_response(
    const MutableByteView output,
    const Command command,
    const Status status,
    const std::uint16_t sequence,
    const ByteView payload) {
    const std::size_t required = kHeaderSize + payload.size() + kCrcSize;
    if (output.size() < required || payload.size() > config::kMaxPayload) {
        return 0;
    }

    std::copy(kMagic.begin(), kMagic.end(), output.begin());
    output[4] = config::kProtocolVersion;
    output[5] = static_cast<std::uint8_t>(command);
    output[6] = 0;
    output[7] = static_cast<std::uint8_t>(status);
    write_u16_le(output.data() + 8, sequence);
    write_u16_le(output.data() + 10, static_cast<std::uint16_t>(payload.size()));
    std::copy(payload.begin(), payload.end(), output.begin() + static_cast<std::ptrdiff_t>(kHeaderSize));

    const auto checksum = crc32(ByteView(output.data() + 4, 8 + payload.size()));
    write_u32_le(output.data() + kHeaderSize + payload.size(), checksum);
    return required;
}

}  // namespace eslbridge::protocol
