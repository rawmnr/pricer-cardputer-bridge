#pragma once

#include <array>
#include <cstddef>
#include <cstdint>

#include "app_config.hpp"

namespace eslbridge::protocol {

class ByteView {
public:
    constexpr ByteView() = default;
    constexpr ByteView(const std::uint8_t* data, const std::size_t size) : data_(data), size_(size) {}

    constexpr const std::uint8_t* data() const { return data_; }
    constexpr std::size_t size() const { return size_; }
    constexpr bool empty() const { return size_ == 0; }
    constexpr const std::uint8_t* begin() const { return data_; }
    constexpr const std::uint8_t* end() const { return data_ + size_; }
    constexpr std::uint8_t operator[](const std::size_t index) const { return data_[index]; }

private:
    const std::uint8_t* data_{nullptr};
    std::size_t size_{0};
};

class MutableByteView {
public:
    constexpr MutableByteView() = default;
    constexpr MutableByteView(std::uint8_t* data, const std::size_t size) : data_(data), size_(size) {}

    constexpr std::uint8_t* data() const { return data_; }
    constexpr std::size_t size() const { return size_; }
    constexpr std::uint8_t* begin() const { return data_; }
    constexpr std::uint8_t* end() const { return data_ + size_; }
    constexpr std::uint8_t& operator[](const std::size_t index) const { return data_[index]; }

private:
    std::uint8_t* data_{nullptr};
    std::size_t size_{0};
};


inline constexpr std::array<std::uint8_t, 4> kMagic{'E', 'S', 'L', 'I'};
inline constexpr std::size_t kHeaderSize = 12;
inline constexpr std::size_t kCrcSize = 4;
inline constexpr std::size_t kMaxFrameSize = kHeaderSize + config::kMaxPayload + kCrcSize;

enum class Command : std::uint8_t {
    kHello = 0x01,
    kGetStatus = 0x02,
    kCarrierTest = 0x10,
    kSendPricerFrame = 0x11,
};

enum class Status : std::uint8_t {
    kOk = 0x00,
    kBadMagic = 0x01,
    kBadVersion = 0x02,
    kBadCrc = 0x03,
    kBadLength = 0x04,
    kUnsupportedCommand = 0x05,
    kInvalidArgument = 0x06,
    kBusy = 0x07,
    kHardwareError = 0x08,
    kNotImplemented = 0x09,
    kTimeout = 0x0A,
};

enum class TransmitterState : std::uint8_t {
    kIdle = 0,
    kBusy = 1,
    kFault = 2,
};

struct MessageView {
    std::uint8_t version{};
    Command command{};
    std::uint8_t flags{};
    Status status{};
    std::uint16_t sequence{};
    ByteView payload{};
};

struct DeviceStatus {
    Command last_command{Command::kHello};
    TransmitterState transmitter_state{TransmitterState::kIdle};
    Status last_error{Status::kOk};
    std::uint32_t tx_count{0};
};

std::uint32_t crc32(ByteView data);
std::uint16_t read_u16_le(const std::uint8_t* data);
std::uint32_t read_u32_le(const std::uint8_t* data);
void write_u16_le(std::uint8_t* data, std::uint16_t value);
void write_u32_le(std::uint8_t* data, std::uint32_t value);

class StreamParser {
public:
    enum class Result {
        kNeedMoreData,
        kMessageReady,
        kDiscardedNoise,
        kFrameError,
    };

    Result push(std::uint8_t byte, std::uint32_t now_ms);
    const MessageView& message() const { return message_; }
    Status error() const { return error_; }
    void reset();

private:
    bool decode_current_frame();
    bool magic_matches_prefix() const;

    std::array<std::uint8_t, kMaxFrameSize> buffer_{};
    std::size_t size_{0};
    std::size_t expected_size_{0};
    std::uint32_t last_byte_ms_{0};
    MessageView message_{};
    Status error_{Status::kOk};
};

std::size_t encode_response(
    MutableByteView output,
    Command command,
    Status status,
    std::uint16_t sequence,
    ByteView payload);

}  // namespace eslbridge::protocol
