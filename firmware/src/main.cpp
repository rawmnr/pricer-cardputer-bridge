#include <Arduino.h>

#include <array>

#include "app_config.hpp"
#include "bridge_protocol.hpp"
#include "device_ui.hpp"
#include "ir_transmitter.hpp"

#ifndef PROJECT_VERSION
#define PROJECT_VERSION "0.0.0"
#endif

namespace {

using eslbridge::protocol::Command;
using eslbridge::protocol::Status;

eslbridge::protocol::StreamParser parser;
eslbridge::protocol::DeviceStatus device_status;
eslbridge::IrTransmitter transmitter;
eslbridge::DeviceUi ui;
std::array<std::uint8_t, eslbridge::protocol::kMaxFrameSize> response_buffer{};

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
            std::array<std::uint8_t, 12> payload{};
            payload[0] = eslbridge::config::kProtocolVersion;
            payload[1] = 0;
            payload[2] = 1;
            payload[3] = 0;
            const std::uint32_t capabilities = (1U << 0U) | (1U << 3U);
            eslbridge::protocol::write_u32_le(payload.data() + 4, capabilities);
            eslbridge::protocol::write_u16_le(
                payload.data() + 8,
                static_cast<std::uint16_t>(eslbridge::config::kMaxPayload));
            payload[10] = eslbridge::config::kIrGpio;
            payload[11] = 0;
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

        case Command::kSendPricerFrame:
            device_status.last_error = transmitter.send_pricer_frame();
            send_response(message.command, device_status.last_error, message.sequence);
            break;

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
    ui.show_ready(eslbridge::config::kIrGpio);

    Serial.begin(115200);
    const auto init_status = transmitter.begin();
    if (init_status != Status::kOk) {
        device_status.last_error = init_status;
        ui.show_command(Command::kCarrierTest, init_status, 0);
    }
}

void loop() {
    ui.update();

    while (Serial.available() > 0) {
        const auto byte = static_cast<std::uint8_t>(Serial.read());
        const auto result = parser.push(byte, millis());
        if (result == eslbridge::protocol::StreamParser::Result::kMessageReady) {
            handle_message(parser.message());
            parser.reset();
        }
    }

    delay(1);
}
