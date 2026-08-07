#include <Arduino.h>

#include <array>

#include "app_config.hpp"
#include "bridge_protocol.hpp"
#include "build_identity.hpp"
#include "device_ui.hpp"
#include "orientation_test.hpp"
#include "ir_transmitter.hpp"

namespace {

using eslbridge::protocol::Command;
using eslbridge::protocol::Status;

eslbridge::protocol::StreamParser parser;
eslbridge::protocol::DeviceStatus device_status;
eslbridge::IrTransmitter transmitter;
eslbridge::DeviceUi ui;
std::array<std::uint8_t, eslbridge::protocol::kMaxFrameSize> response_buffer{};
const char* build_provenance_name() {
    switch (eslbridge::config::kBuildProvenanceCode) {
        case 1:
            return "clean";
        case 2:
            return "dirty";
        case 3:
            return "ci";
        default:
            return "unknown";
    }
}

void send_response(
    const Command command,
    const Status status,
    const std::uint16_t sequence,
    const eslbridge::protocol::ByteView payload = {}) {
    const auto length = eslbridge::protocol::encode_response(
        eslbridge::protocol::MutableByteView(response_buffer.data(), response_buffer.size()),
        command,
        status,
        sequence,
        payload);
    if (length > 0) {
        Serial.write(response_buffer.data(), length);
        Serial.flush();
    }
}

void handle_message(const eslbridge::protocol::MessageView& message) {
    device_status.last_command = message.command;
    device_status.last_error = Status::kOk;

    switch (message.command) {
        case Command::kHello: {
            if (!message.payload.empty()) {
                device_status.last_error = Status::kInvalidArgument;
                send_response(message.command, device_status.last_error, message.sequence);
                break;
            }
            std::array<std::uint8_t, 29> payload{};
            payload[0] = eslbridge::config::kProtocolVersion;
            payload[1] = eslbridge::config::kFirmwareVersionMajor;
            payload[2] = eslbridge::config::kFirmwareVersionMinor;
            payload[3] = eslbridge::config::kFirmwareVersionPatch;
            const std::uint32_t capabilities = (1U << 0U) | (1U << 1U) | (1U << 2U) | (1U << 3U);
            eslbridge::protocol::write_u32_le(payload.data() + 4, capabilities);
            eslbridge::protocol::write_u16_le(
                payload.data() + 8,
                static_cast<std::uint16_t>(eslbridge::config::kMaxPayload));
            payload[10] = eslbridge::config::kIrGpio;
            payload[11] = 0;
            payload[12] = eslbridge::config::kBuildIdentityVersion;
            for (std::size_t i = 0; i < 7; ++i) {
                payload[13 + i] = static_cast<std::uint8_t>(eslbridge::config::kBuildGitSha[i]);
            }
            payload[20] = eslbridge::config::kBuildProvenanceCode;
            for (std::size_t i = 0; i < 8; ++i) {
                payload[21 + i] = static_cast<std::uint8_t>(
                    eslbridge::config::kPp16ProfileRevision[i]);
            }
            send_response(
                message.command,
                Status::kOk,
                message.sequence,
                eslbridge::protocol::ByteView(payload.data(), payload.size()));
            break;
        }

        case Command::kGetStatus: {
            if (!message.payload.empty()) {
                device_status.last_error = Status::kInvalidArgument;
                send_response(message.command, device_status.last_error, message.sequence);
                break;
            }
            std::array<std::uint8_t, 8> payload{};
            payload[0] = static_cast<std::uint8_t>(device_status.last_command);
            payload[1] = static_cast<std::uint8_t>(transmitter.state());
            payload[2] = static_cast<std::uint8_t>(device_status.last_error);
            payload[3] = 0;
            eslbridge::protocol::write_u32_le(payload.data() + 4, transmitter.tx_count());
            send_response(
                message.command,
                Status::kOk,
                message.sequence,
                eslbridge::protocol::ByteView(payload.data(), payload.size()));
            break;
        }

        case Command::kCarrierTest: {
            if (message.payload.size() != 12) {
                device_status.last_error = Status::kInvalidArgument;
                send_response(message.command, device_status.last_error, message.sequence);
                break;
            }
            const auto frequency_hz = eslbridge::protocol::read_u32_le(message.payload.data());
            const auto duration_us = eslbridge::protocol::read_u32_le(message.payload.data() + 4);
            const auto duty_percent = message.payload[8];
            const auto status = transmitter.carrier_test(frequency_hz, duration_us, duty_percent);
            device_status.last_error = status;
            send_response(message.command, status, message.sequence);
            break;
        }

        case Command::kSendPricerFrame: {
            if (message.payload.size() < 10) {
                device_status.last_error = Status::kInvalidArgument;
                send_response(message.command, device_status.last_error, message.sequence);
                break;
            }
            const auto modulation = message.payload[0];
            const auto reserved = message.payload[1];
            const auto repeats = eslbridge::protocol::read_u16_le(message.payload.data() + 2);
            const auto inter_repeat_gap_us = eslbridge::protocol::read_u32_le(message.payload.data() + 4);
            const auto frame_length = eslbridge::protocol::read_u16_le(message.payload.data() + 8);

            if (message.payload.size() != 10 + frame_length || reserved != 0) {
                device_status.last_error = Status::kInvalidArgument;
                send_response(message.command, device_status.last_error, message.sequence);
                break;
            }

            const auto status = transmitter.send_pricer_frame(
                modulation,
                repeats,
                inter_repeat_gap_us,
                message.payload.data() + 10,
                frame_length);
            device_status.last_error = status;
            send_response(message.command, status, message.sequence);
            break;
        }

        default:
            device_status.last_error = Status::kUnsupportedCommand;
            send_response(message.command, device_status.last_error, message.sequence);
            break;
    }

    ui.show_command(message.command, device_status.last_error, transmitter.tx_count());
}

}  // namespace

void setup() {
    ui.begin();
    ui.show_ready(
        eslbridge::config::kIrGpio,
        eslbridge::config::kFirmwareVersion,
        eslbridge::config::kBuildGitSha,
        build_provenance_name(),
        eslbridge::config::kPp16ProfileRevision);

    Serial.begin(115200);
    const auto init_status = transmitter.begin();
    if (init_status != Status::kOk) {
        device_status.last_error = init_status;
        ui.show_command(Command::kCarrierTest, init_status, 0);
    }
}

void loop() {
    const auto key_test = ui.update();
    if (key_test != eslbridge::OrientationTest::kNone) {
        const auto status = eslbridge::run_orientation_test(transmitter, key_test);
        device_status.last_command = Command::kSendPricerFrame;
        device_status.last_error = status;
        ui.show_orientation_test(key_test, status, transmitter.tx_count());
    }

    const auto now_ms = millis();
    const auto poll_res = parser.poll(now_ms);
    if (poll_res == eslbridge::protocol::StreamParser::Result::kFrameError ||
        poll_res == eslbridge::protocol::StreamParser::Result::kTimeout) {
        if (parser.has_error_context()) {
            send_response(parser.error_command(), parser.error(), parser.error_sequence());
        }
        parser.reset();
    }

    while (Serial.available() > 0) {
        const auto byte = static_cast<std::uint8_t>(Serial.read());
        const auto result = parser.push(byte, millis());
        if (result == eslbridge::protocol::StreamParser::Result::kMessageReady) {
            handle_message(parser.message());
            parser.reset();
        } else if (result == eslbridge::protocol::StreamParser::Result::kFrameError ||
                   result == eslbridge::protocol::StreamParser::Result::kTimeout) {
            if (parser.has_error_context()) {
                send_response(parser.error_command(), parser.error(), parser.error_sequence());
            }
            parser.reset();
        }
    }

    delay(1);
}
