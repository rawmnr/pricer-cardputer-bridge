"""Windows host library for the Pricer Cardputer Bridge."""

from .pp16 import (
    MAX_FRAME_BYTES,
    PRECIR_CARRIER_HZ,
    PRECIR_NIBBLE_GAPS_US,
    PRECIR_PROVENANCE,
    PP16EncoderError,
    PP16TimingProfile,
    SymbolTiming,
    calculate_frame_duration_us,
    encode_pp16_rmt_ticks,
    encode_pp16_symbols,
    precir_pp16_profile,
    provisional_pp16_profile,
)
from .precir import (
    CRC16_INITIAL,
    CRC16_POLYNOMIAL,
    PRECIR_ADAPTER_PROVENANCE,
    PRECIR_PP4_HEADER,
    PRECIR_PP16_HEADER,
    PRECIR_UPSTREAM_COMMIT,
    PRECIR_UPSTREAM_FILE,
    PrecIRAdapterError,
    build_pricer_frame_request,
    calculate_precir_crc16,
    finalize_precir_frame,
)

__version__ = "0.1.0"

__all__ = [
    "CRC16_INITIAL",
    "CRC16_POLYNOMIAL",
    "MAX_FRAME_BYTES",
    "PRECIR_ADAPTER_PROVENANCE",
    "PRECIR_CARRIER_HZ",
    "PRECIR_NIBBLE_GAPS_US",
    "PRECIR_PP4_HEADER",
    "PRECIR_PP16_HEADER",
    "PRECIR_PROVENANCE",
    "PRECIR_UPSTREAM_COMMIT",
    "PRECIR_UPSTREAM_FILE",
    "PP16EncoderError",
    "PP16TimingProfile",
    "PrecIRAdapterError",
    "SymbolTiming",
    "build_pricer_frame_request",
    "calculate_frame_duration_us",
    "calculate_precir_crc16",
    "encode_pp16_rmt_ticks",
    "encode_pp16_symbols",
    "finalize_precir_frame",
    "precir_pp16_profile",
    "provisional_pp16_profile",
]
