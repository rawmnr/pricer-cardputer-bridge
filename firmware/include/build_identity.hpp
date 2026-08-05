#pragma once

#include <cstdint>

#ifndef PROJECT_VERSION
#define PROJECT_VERSION "0.0.0"
#endif

#ifndef PROJECT_VERSION_MAJOR
#define PROJECT_VERSION_MAJOR 0
#endif

#ifndef PROJECT_VERSION_MINOR
#define PROJECT_VERSION_MINOR 0
#endif

#ifndef PROJECT_VERSION_PATCH
#define PROJECT_VERSION_PATCH 0
#endif

#ifndef BUILD_GIT_SHA
#define BUILD_GIT_SHA "unknown"
#endif

#ifndef BUILD_PROVENANCE_CODE
#define BUILD_PROVENANCE_CODE 0
#endif

#ifndef BUILD_PP16_PROFILE_REVISION
#define BUILD_PP16_PROFILE_REVISION "T006B-r1"
#endif

namespace eslbridge::config {

inline constexpr std::uint8_t kBuildIdentityVersion = 1;
inline constexpr std::uint8_t kFirmwareVersionMajor = PROJECT_VERSION_MAJOR;
inline constexpr std::uint8_t kFirmwareVersionMinor = PROJECT_VERSION_MINOR;
inline constexpr std::uint8_t kFirmwareVersionPatch = PROJECT_VERSION_PATCH;
inline constexpr char kFirmwareVersion[] = PROJECT_VERSION;
inline constexpr char kBuildGitSha[] = BUILD_GIT_SHA;
inline constexpr std::uint8_t kBuildProvenanceCode = BUILD_PROVENANCE_CODE;
inline constexpr char kPp16ProfileRevision[] = BUILD_PP16_PROFILE_REVISION;

}  // namespace eslbridge::config
