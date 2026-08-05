#pragma once

#include <cstdint>

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
inline constexpr char kBuildGitSha[] = BUILD_GIT_SHA;
inline constexpr std::uint8_t kBuildProvenanceCode = BUILD_PROVENANCE_CODE;
inline constexpr char kPp16ProfileRevision[] = BUILD_PP16_PROFILE_REVISION;

}  // namespace eslbridge::config
