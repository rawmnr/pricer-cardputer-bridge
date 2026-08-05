#include "pp16_encoder.hpp"

namespace eslbridge::pp16 {

Status encode_frame(
    const std::uint8_t* payload,
    const std::size_t payload_len,
    const TimingProfile& profile,
    EncodedFrame& out_frame) {
    if (!profile.validate()) {
        return Status::kInvalidProfile;
    }
    if (payload == nullptr || payload_len == 0) {
        return Status::kEmptyPayload;
    }
    if (payload_len > kMaxFrameBytes) {
        return Status::kPayloadTooLarge;
    }

    out_frame.symbol_count = 0;
    out_frame.total_duration_us = 0;

    // Optional preamble
    if (profile.preamble_burst_us > 0) {
        const Pp16Symbol preamble{profile.preamble_burst_us, profile.preamble_gap_us};
        out_frame.symbols[out_frame.symbol_count++] = preamble;
        out_frame.total_duration_us += preamble.total_us();
    }

    // PrecIR's transmitter emits the low nibble before the high nibble.
    // The target ESL consumes each byte least-significant nibble first.
    for (std::size_t i = 0; i < payload_len; ++i) {
        const std::uint8_t byte_val = payload[i];
        const std::uint8_t low_nibble = byte_val & 0x0F;
        const std::uint8_t high_nibble = (byte_val >> 4) & 0x0F;

        const Pp16Symbol s_low = profile.symbol_timing(low_nibble);
        out_frame.symbols[out_frame.symbol_count++] = s_low;
        out_frame.total_duration_us += s_low.total_us();

        const Pp16Symbol s_high = profile.symbol_timing(high_nibble);
        out_frame.symbols[out_frame.symbol_count++] = s_high;
        out_frame.total_duration_us += s_high.total_us();
    }

    // Required terminal carrier burst marks the end of the final nibble.
    const Pp16Symbol terminal{profile.symbol_burst_us, 0};
    out_frame.symbols[out_frame.symbol_count++] = terminal;
    out_frame.total_duration_us += terminal.total_us();


    return Status::kOk;
}

Status convert_symbol_to_ticks(
    const Pp16Symbol& symbol,
    RmtPhaseTicks& out_ticks) {
    const std::uint32_t high_ticks = symbol.burst_us * kTicksPerMicrosecond;
    const std::uint32_t low_ticks = symbol.gap_us * kTicksPerMicrosecond;

    if (high_ticks > kMaxRmtPhaseTicks || low_ticks > kMaxRmtPhaseTicks) {
        return Status::kDurationOverflow;
    }

    out_ticks.high_ticks = static_cast<std::uint16_t>(high_ticks);
    out_ticks.low_ticks = static_cast<std::uint16_t>(low_ticks);
    return Status::kOk;
}

}  // namespace eslbridge::pp16
