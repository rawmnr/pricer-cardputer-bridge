#pragma once

#include <array>
#include <cstddef>
#include <cstdint>

namespace eslbridge::pp16 {

constexpr std::size_t kMaxFrameBytes = 256;
constexpr std::size_t kMaxSymbolsPerFrame = (kMaxFrameBytes * 2) + 3;

constexpr std::uint32_t kMinCarrierHz = 500000;
constexpr std::uint32_t kMaxCarrierHz = 2000000;
constexpr std::uint8_t kMinDutyPercent = 10;
constexpr std::uint8_t kMaxDutyPercent = 60;
constexpr std::uint32_t kTicksPerMicrosecond = 10;
constexpr std::uint32_t kMaxRmtPhaseTicks = 32767;

// PrecIR prior art post-burst gaps in microseconds (0x0..0xF)
// Source: PrecIR commit b09951e2b3d2741e4ca08f929eafef849f6fc006
// (hardware/esl_blaster/FW02/Src/main.c; RE page https://www.furrtek.org/index.php?a=esl)
// GPL-3.0 license.
inline constexpr std::array<std::uint32_t, 16> kPrecirNibbleGapsUs{
    27, 51, 35, 43, 147, 123, 139, 131, 83, 59, 75, 67, 91, 115, 99, 107};
constexpr std::uint32_t kPrecirBurstUs = 21;
constexpr std::uint32_t kPrecirCarrierHz = 1250000;

enum class Status : std::uint8_t {
    kOk = 0,
    kInvalidProfile = 1,
    kEmptyPayload = 2,
    kPayloadTooLarge = 3,
    kInvalidNibble = 4,
    kDurationOverflow = 5,
};

struct Pp16Symbol {
    std::uint32_t burst_us{0};
    std::uint32_t gap_us{0};

    constexpr std::uint32_t total_us() const { return burst_us + gap_us; }
};

struct RmtPhaseTicks {
    std::uint16_t high_ticks{0};
    std::uint16_t low_ticks{0};
};

/**
 * Direct 16-entry table-driven PP16 timing profile.
 *
 * PROVISIONAL / INFERRED WARNING:
 * Default values are derived from published PrecIR prior art (GPL-3.0) and remain
 * UNTESTED against physical Pricer ESL target tags in this setup.
 * Physical carrier measurements from T005 are pending. Do NOT claim verified tag
 * or physical carrier compatibility until physical bench validation is complete.
 */
struct TimingProfile {
    std::uint32_t carrier_frequency_hz{kPrecirCarrierHz};
    std::uint8_t duty_percent{50};
    std::uint32_t symbol_burst_us{kPrecirBurstUs};
    std::array<std::uint32_t, 16> nibble_gaps_us{kPrecirNibbleGapsUs};
    std::uint32_t preamble_burst_us{0};
    std::uint32_t preamble_gap_us{0};
    std::uint32_t trailer_burst_us{0};
    std::uint32_t trailer_gap_us{0};
    bool is_provisional{true};

    constexpr bool validate() const {
        if (carrier_frequency_hz < kMinCarrierHz || carrier_frequency_hz > kMaxCarrierHz) {
            return false;
        }
        if (duty_percent < kMinDutyPercent || duty_percent > kMaxDutyPercent) {
            return false;
        }
        if (symbol_burst_us == 0 || symbol_burst_us > 1000) {
            return false;
        }
        for (std::size_t i = 0; i < 16; ++i) {
            if (nibble_gaps_us[i] == 0 || nibble_gaps_us[i] > 5000) {
                return false;
            }
        }
        if (preamble_burst_us > 5000 || preamble_gap_us > 10000) {
            return false;
        }
        if (trailer_burst_us > 5000 || trailer_gap_us > 10000) {
            return false;
        }
        return true;
    }

    constexpr std::uint32_t symbol_gap_us(std::uint8_t nibble) const {
        const std::uint8_t n = nibble & 0x0F;
        return nibble_gaps_us[n];
    }

    constexpr Pp16Symbol symbol_timing(std::uint8_t nibble) const {
        return Pp16Symbol{symbol_burst_us, symbol_gap_us(nibble)};
    }
};

constexpr TimingProfile make_precir_profile() {
    return TimingProfile{};
}

constexpr TimingProfile make_provisional_profile() {
    return make_precir_profile();
}

struct EncodedFrame {
    std::size_t symbol_count{0};
    std::uint32_t total_duration_us{0};
    std::array<Pp16Symbol, kMaxSymbolsPerFrame> symbols{};
};

Status encode_frame(
    const std::uint8_t* payload,
    std::size_t payload_len,
    const TimingProfile& profile,
    EncodedFrame& out_frame);

Status convert_symbol_to_ticks(
    const Pp16Symbol& symbol,
    RmtPhaseTicks& out_ticks);

}  // namespace eslbridge::pp16
