#include "device_ui.hpp"

#include <M5Cardputer.h>

namespace eslbridge {

void DeviceUi::begin() {
    auto config = M5.config();
    M5Cardputer.begin(config, true);
    M5Cardputer.Display.setRotation(1);
    M5Cardputer.Display.setTextSize(1);
    M5Cardputer.Display.setTextColor(TFT_GREEN, TFT_BLACK);
    M5Cardputer.Display.fillScreen(TFT_BLACK);
}

void DeviceUi::show_ready(const std::uint8_t ir_gpio) {
    M5Cardputer.Display.fillScreen(TFT_BLACK);
    M5Cardputer.Display.setCursor(8, 8);
    M5Cardputer.Display.println("Pricer ESL Bridge");
    M5Cardputer.Display.println("USB: waiting");
    M5Cardputer.Display.printf("IR GPIO: %u\n", ir_gpio);
    M5Cardputer.Display.println("PP16: pending");
}

void DeviceUi::show_command(
    const protocol::Command command,
    const protocol::Status status,
    const std::uint32_t tx_count) {
    M5Cardputer.Display.fillRect(0, 48, M5Cardputer.Display.width(), 70, TFT_BLACK);
    M5Cardputer.Display.setCursor(8, 48);
    M5Cardputer.Display.printf("CMD: 0x%02X\n", static_cast<unsigned>(command));
    M5Cardputer.Display.printf("STATUS: 0x%02X\n", static_cast<unsigned>(status));
    M5Cardputer.Display.printf("TX count: %lu\n", static_cast<unsigned long>(tx_count));
}

void DeviceUi::update() {
    M5Cardputer.update();
}

}  // namespace eslbridge
