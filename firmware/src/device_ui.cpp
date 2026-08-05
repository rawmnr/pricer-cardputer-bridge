#include "device_ui.hpp"

#include <M5Cardputer.h>

#include "orientation_test.hpp"

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

void DeviceUi::show_orientation_test(
    const OrientationTest test,
    const protocol::Status status,
    const std::uint32_t tx_count) {
    M5Cardputer.Display.fillRect(0, 88, M5Cardputer.Display.width(), 47, TFT_BLACK);
    M5Cardputer.Display.setCursor(8, 88);
    M5Cardputer.Display.printf("KEY TEST: %s\n", orientation_test_name(test));
    M5Cardputer.Display.printf("STATUS: 0x%02X TX:%lu\n",
                               static_cast<unsigned>(status),
                               static_cast<unsigned long>(tx_count));
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
