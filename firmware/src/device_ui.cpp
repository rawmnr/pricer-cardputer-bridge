#include "device_ui.hpp"

#include <M5Cardputer.h>

#include "orientation_test.hpp"
#include "build_identity.hpp"

namespace {

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

unsigned orientation_test_key(const eslbridge::OrientationTest test) {
    return static_cast<unsigned>(test);
}

void render_orientation_test_screen(
    const eslbridge::OrientationTest test,
    const eslbridge::protocol::Status status,
    const std::uint32_t tx_delta,
    const bool sending) {
    const auto summary = eslbridge::orientation_test_summary(test);
    auto& display = M5Cardputer.Display;
    display.fillScreen(TFT_BLACK);
    display.setCursor(4, 4);
    display.printf(
        "KEY %u %s\n",
        orientation_test_key(test),
        eslbridge::orientation_test_name(test));
    display.printf(
        "FRAMES:%lu AIRFRAMES:%lu\n",
        static_cast<unsigned long>(summary.frame_count),
        static_cast<unsigned long>(summary.airframe_count));
    display.printf(
        "BYTES:%lu GPIO:%u\n",
        static_cast<unsigned long>(summary.encoded_byte_count),
        static_cast<unsigned>(summary.ir_gpio));
    display.printf(
        "PP%u:%lu.%03lu->%lu.%03lu D:%u%%\n",
        static_cast<unsigned>(summary.modulation),
        static_cast<unsigned long>(summary.requested_carrier_hz / 1000U),
        static_cast<unsigned long>(summary.requested_carrier_hz % 1000U),
        static_cast<unsigned long>(summary.effective_carrier_hz / 1000U),
        static_cast<unsigned long>(summary.effective_carrier_hz % 1000U),
        static_cast<unsigned>(summary.duty_percent));
    if (sending) {
        display.println("STATE: SENDING");
    } else {
        const char* result = status == eslbridge::protocol::Status::kOk ? "OK" : "ERROR";
        display.printf(
            "%s 0x%02X TX:+%lu\n",
            result,
            static_cast<unsigned>(status),
            static_cast<unsigned long>(tx_delta));
    }
    display.printf("GIT: %s\n", eslbridge::config::kBuildGitSha);
    display.printf("BUILD: %s\n", build_provenance_name());
}

}  // namespace

namespace eslbridge {

void DeviceUi::begin() {
    auto config = M5.config();
    M5Cardputer.begin(config, true);
    M5Cardputer.Display.setRotation(1);
    M5Cardputer.Display.setTextSize(1);
    M5Cardputer.Display.setTextColor(TFT_GREEN, TFT_BLACK);
    M5Cardputer.Display.fillScreen(TFT_BLACK);
}

void DeviceUi::show_ready(
    const std::uint8_t ir_gpio,
    const char* firmware_version,
    const char* git_sha,
    const char* build_provenance,
    const char* pp16_profile_revision) {
    M5Cardputer.Display.fillScreen(TFT_BLACK);
    M5Cardputer.Display.setCursor(8, 8);
    M5Cardputer.Display.println("Pricer ESL Bridge");
    M5Cardputer.Display.printf("FW: %s\n", firmware_version);
    M5Cardputer.Display.printf("GIT: %s\n", git_sha);
    M5Cardputer.Display.printf("BUILD: %s\n", build_provenance);
    M5Cardputer.Display.printf("PP16: %s\n", pp16_profile_revision);
    M5Cardputer.Display.printf("IR GPIO: %u\n", ir_gpio);
    M5Cardputer.Display.println("USB: waiting");
}

void DeviceUi::show_command(
    const protocol::Command command,
    const protocol::Status status,
    const std::uint32_t tx_count) {
    M5Cardputer.Display.fillRect(0, 104, M5Cardputer.Display.width(), 31, TFT_BLACK);
    M5Cardputer.Display.setCursor(8, 104);
    M5Cardputer.Display.printf("CMD: 0x%02X\n", static_cast<unsigned>(command));
    M5Cardputer.Display.printf("STATUS: 0x%02X TX:%lu\n",
                               static_cast<unsigned>(status),
                               static_cast<unsigned long>(tx_count));
}

void DeviceUi::show_orientation_test_start(const OrientationTest test) {
    render_orientation_test_screen(
        test,
        protocol::Status::kOk,
        0,
        true);
}

void DeviceUi::show_orientation_test_result(
    const OrientationTest test,
    const protocol::Status status,
    const std::uint32_t tx_delta) {
    render_orientation_test_screen(test, status, tx_delta, false);
}

OrientationTest DeviceUi::update() {
    M5Cardputer.update();
    if (!M5Cardputer.Keyboard.isChange()) {
        return OrientationTest::kNone;
    }
    if (M5Cardputer.Keyboard.isKeyPressed('1')) {
        return OrientationTest::kOne;
    }
    if (M5Cardputer.Keyboard.isKeyPressed('2')) {
        return OrientationTest::kTwo;
    }
    if (M5Cardputer.Keyboard.isKeyPressed('3')) {
        return OrientationTest::kThree;
    }
    if (M5Cardputer.Keyboard.isKeyPressed('4')) {
        return OrientationTest::kFour;
    }
    return OrientationTest::kNone;
}
}  // namespace eslbridge
