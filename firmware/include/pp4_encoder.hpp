#pragma once

#include <array>
#include <cstddef>
#include <cstdint>

namespace eslbridge::pp4 {

constexpr std::size_t kMaxFrameBytes = 256;
constexpr std::size_t kSymbolsPerByte = 4;
constexpr std::size_t kMaxSymbolsPerFrame =
    (kMaxFrameBytes * kSymbolsPerByte) + 1;  // includes terminal burst

constexpr std::uint32_t kMinCarrierHz = 500000;
constexpr std::uint32_t kMaxCarrierHz = 2000000;
constexpr std::uint8_t kMinDutyPercent = 10;
constexpr std::uint8_t kMaxDutyPercent = 60;
constexpr std::uint32_t kTicksPerMicrosecond = 10;
constexpr std::uint32_t kMaxRmtPhaseTicks = 32767;
constexpr std::uint32_t kApbClockHz = 80'000'000;

// TagTinker measures PP4 phases from a 64 MHz timer. Preserve those source
// cycles when converting to the ESP32-S3 RMT's 10 MHz item clock.
constexpr std::uint32_t kTagTinkerTimingClockHz = 64'000'000;
constexpr std::uint32_t kTagTinkerBurstCycles = 2581;
inline constexpr std::array<std::uint32_t, 4> kTagTinkerSymbolGapCycles{
    3871, 15483, 7741, 11612};

constexpr std::uint16_t reference_cycles_to_rmt_ticks(const std::uint32_t cycles) {
    return static_cast<std::uint16_t>(
        (cycles * kTicksPerMicrosecond + (kTagTinkerTimingClockHz / 2U)) /
        kTagTinkerTimingClockHz);
}

constexpr std::uint16_t kTagTinkerBurstRmtTicks =
    reference_cycles_to_rmt_ticks(kTagTinkerBurstCycles);
inline constexpr std::array<std::uint16_t, 4> kTagTinkerSymbolGapRmtTicks{
    reference_cycles_to_rmt_ticks(kTagTinkerSymbolGapCycles[0]),
    reference_cycles_to_rmt_ticks(kTagTinkerSymbolGapCycles[1]),
    reference_cycles_to_rmt_ticks(kTagTinkerSymbolGapCycles[2]),
    reference_cycles_to_rmt_ticks(kTagTinkerSymbolGapCycles[3])};

// Rounded display values; conversion to RMT uses the cycle-derived ticks above.
constexpr std::uint32_t kTagTinkerCarrierHz = 1'254'902;
constexpr std::uint32_t kTagTinkerEffectiveCarrierHz = 1'250'000;
constexpr std::uint8_t kTagTinkerDutyPercent = 50;
constexpr std::uint32_t kTagTinkerBurstUs = 40;

// Indexed directly by the raw 2-bit symbol value.
inline constexpr std::array<std::uint32_t, 4> kTagTinkerSymbolGapsUs{
    61, 242, 121, 181};

enum class Status : std::uint8_t {
    kOk = 0,
    kInvalidProfile = 1,
    kEmptyPayload = 2,
    kPayloadTooLarge = 3,
    kInvalidSymbol = 4,
    kDurationOverflow = 5,
};

struct Pp4Symbol {
    std::uint8_t value{0};
    std::uint32_t burst_us{0};
    std::uint32_t gap_us{0};
    std::uint16_t rmt_high_ticks{0};
    std::uint16_t rmt_low_ticks{0};

    constexpr std::uint32_t total_us() const { return burst_us + gap_us; }
};

struct RmtPhaseTicks {
    std::uint16_t high_ticks{0};
    std::uint16_t low_ticks{0};
};

struct TimingProfile {
    std::uint32_t carrier_frequency_hz{kTagTinkerCarrierHz};
    std::uint8_t duty_percent{kTagTinkerDutyPercent};
    std::uint32_t symbol_burst_us{kTagTinkerBurstUs};
    std::array<std::uint32_t, 4> symbol_gaps_us{kTagTinkerSymbolGapsUs};
    std::uint16_t symbol_burst_rmt_ticks{kTagTinkerBurstRmtTicks};
    std::array<std::uint16_t, 4> symbol_gap_rmt_ticks{kTagTinkerSymbolGapRmtTicks};
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
        for (const auto gap_us : symbol_gaps_us) {
            if (gap_us == 0 || gap_us > 5000) {
                return false;
            }
        }
        return true;
    }

    constexpr std::uint32_t symbol_gap_us(const std::uint8_t symbol) const {
        return symbol_gaps_us[symbol & 0x03U];
    }

    constexpr Pp4Symbol symbol_timing(const std::uint8_t symbol) const {
        const auto raw_symbol = static_cast<std::uint8_t>(symbol & 0x03U);
        return Pp4Symbol{
            raw_symbol,
            symbol_burst_us,
            symbol_gap_us(raw_symbol),
            symbol_burst_rmt_ticks,
            symbol_gap_rmt_ticks[raw_symbol]};
    }

    constexpr std::uint32_t effective_carrier_frequency_hz() const {
        if (carrier_frequency_hz == 0) {
            return 0;
        }
        const auto period_ticks = (kApbClockHz + (carrier_frequency_hz / 2U)) /
                                  carrier_frequency_hz;
        return kApbClockHz / period_ticks;
    }
};

constexpr TimingProfile make_tagtinker_profile() {
    return TimingProfile{};
}

struct EncodedFrame {
    std::size_t symbol_count{0};
    std::uint32_t total_duration_us{0};
    std::array<Pp4Symbol, kMaxSymbolsPerFrame> symbols{};
};

Status encode_frame(
    const std::uint8_t* payload,
    std::size_t payload_len,
    const TimingProfile& profile,
    EncodedFrame& out_frame);

Status convert_symbol_to_ticks(
    const Pp4Symbol& symbol,
    RmtPhaseTicks& out_ticks);

}  // namespace eslbridge::pp4
