#include "pp4_encoder.hpp"

namespace eslbridge::pp4 {

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

    // TagTinker emits each byte least-significant 2-bit pair first.
    for (std::size_t i = 0; i < payload_len; ++i) {
        const auto byte_value = payload[i];
        for (std::uint8_t pair = 0; pair < kSymbolsPerByte; ++pair) {
            const auto raw_symbol = static_cast<std::uint8_t>((byte_value >> (pair * 2U)) & 0x03U);
            const auto symbol = profile.symbol_timing(raw_symbol);
            out_frame.symbols[out_frame.symbol_count++] = symbol;
            out_frame.total_duration_us += symbol.total_us();
        }
    }

    // The terminal burst is mandatory and carries no encoded symbol.
    const Pp4Symbol terminal{
        0, profile.symbol_burst_us, 0, profile.symbol_burst_rmt_ticks, 0};
    out_frame.symbols[out_frame.symbol_count++] = terminal;
    out_frame.total_duration_us += terminal.total_us();

    return Status::kOk;
}

Status convert_symbol_to_ticks(
    const Pp4Symbol& symbol,
    RmtPhaseTicks& out_ticks) {
    const auto high_ticks = symbol.rmt_high_ticks != 0
                                ? symbol.rmt_high_ticks
                                : symbol.burst_us * kTicksPerMicrosecond;
    const auto low_ticks = symbol.rmt_low_ticks != 0
                               ? symbol.rmt_low_ticks
                               : symbol.gap_us * kTicksPerMicrosecond;
    if (high_ticks > kMaxRmtPhaseTicks || low_ticks > kMaxRmtPhaseTicks) {
        return Status::kDurationOverflow;
    }

    out_ticks.high_ticks = static_cast<std::uint16_t>(high_ticks);
    out_ticks.low_ticks = static_cast<std::uint16_t>(low_ticks);
    return Status::kOk;
}

}  // namespace eslbridge::pp4
