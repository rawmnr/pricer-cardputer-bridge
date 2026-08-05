#include <unity.h>

#include <cstdint>

#include "ir_transmitter.hpp"

using namespace eslbridge;
using namespace eslbridge::detail;

void setUp(void) {}
void tearDown(void) {}

void test_valid_carrier_request_accepted_min_max(void) {
    TEST_ASSERT_TRUE(valid_carrier_request(500000, 1, 10));
    TEST_ASSERT_TRUE(valid_carrier_request(2000000, 5000, 60));
    TEST_ASSERT_TRUE(valid_carrier_request(1245000, 2000, 50));
}

void test_valid_carrier_request_invalid_boundaries(void) {
    // Frequency boundaries (500 kHz .. 2 MHz)
    TEST_ASSERT_FALSE(valid_carrier_request(499999, 2000, 50));
    TEST_ASSERT_FALSE(valid_carrier_request(2000001, 2000, 50));

    // Duration boundaries (1 us .. 5000 us)
    TEST_ASSERT_FALSE(valid_carrier_request(1245000, 0, 50));
    TEST_ASSERT_FALSE(valid_carrier_request(1245000, 5001, 50));

    // Duty percent boundaries (10% .. 60%)
    TEST_ASSERT_FALSE(valid_carrier_request(1245000, 2000, 9));
    TEST_ASSERT_FALSE(valid_carrier_request(1245000, 2000, 61));
}

void test_carrier_burst_plan_exact_totals(void) {
    // 1 us -> 10 ticks total (10, 0)
    {
        CarrierBurstPlan plan = make_carrier_burst_plan(1);
        TEST_ASSERT_EQUAL_UINT16(10, plan.first_ticks);
        TEST_ASSERT_EQUAL_UINT16(0, plan.second_ticks);
        TEST_ASSERT_EQUAL_UINT32(10, plan.total_ticks());
    }

    // 3276 us -> 32760 ticks total (32760, 0)
    {
        CarrierBurstPlan plan = make_carrier_burst_plan(3276);
        TEST_ASSERT_EQUAL_UINT16(32760, plan.first_ticks);
        TEST_ASSERT_EQUAL_UINT16(0, plan.second_ticks);
        TEST_ASSERT_EQUAL_UINT32(32760, plan.total_ticks());
    }

    // 3277 us -> 32770 ticks total (32767, 3)
    {
        CarrierBurstPlan plan = make_carrier_burst_plan(3277);
        TEST_ASSERT_EQUAL_UINT16(32767, plan.first_ticks);
        TEST_ASSERT_EQUAL_UINT16(3, plan.second_ticks);
        TEST_ASSERT_EQUAL_UINT32(32770, plan.total_ticks());
    }

    // 5000 us -> 50000 ticks total (32767, 17233)
    {
        CarrierBurstPlan plan = make_carrier_burst_plan(5000);
        TEST_ASSERT_EQUAL_UINT16(32767, plan.first_ticks);
        TEST_ASSERT_EQUAL_UINT16(17233, plan.second_ticks);
        TEST_ASSERT_EQUAL_UINT32(50000, plan.total_ticks());
    }
}

void test_carrier_burst_plan_max_phase_width(void) {
    for (std::uint32_t duration_us = 1; duration_us <= 5000; ++duration_us) {
        CarrierBurstPlan plan = make_carrier_burst_plan(duration_us);
        TEST_ASSERT_TRUE(plan.first_ticks <= 32767);
        TEST_ASSERT_TRUE(plan.second_ticks <= 32767);
        TEST_ASSERT_EQUAL_UINT32(duration_us * 10, plan.total_ticks());
    }
}

void test_carrier_burst_plan_uninterrupted_high_phases_when_split(void) {
    // When duration > 3276 us (e.g. 3277 us and 5000 us), the burst is split across two phases.
    // Both first_ticks and second_ticks must be > 0 and their sum must equal the total envelope ticks
    // so carrier modulation remains uninterrupted without zero/idle gaps between phases.
    {
        CarrierBurstPlan plan = make_carrier_burst_plan(3277);
        TEST_ASSERT_TRUE(plan.first_ticks > 0);
        TEST_ASSERT_TRUE(plan.second_ticks > 0);
        TEST_ASSERT_EQUAL_UINT32(32770, plan.first_ticks + plan.second_ticks);
    }
    {
        CarrierBurstPlan plan = make_carrier_burst_plan(5000);
        TEST_ASSERT_TRUE(plan.first_ticks > 0);
        TEST_ASSERT_TRUE(plan.second_ticks > 0);
        TEST_ASSERT_EQUAL_UINT32(50000, plan.first_ticks + plan.second_ticks);
    }
}
void test_valid_pricer_frame_request_boundaries(void) {
    // Valid requests
    TEST_ASSERT_TRUE(valid_pricer_frame_request(16, 1, 0, 10));
    TEST_ASSERT_TRUE(valid_pricer_frame_request(4, 100, 1000000, 256));
    TEST_ASSERT_TRUE(valid_pricer_frame_request(16, 50, 500, 1));

    // Invalid modulation
    TEST_ASSERT_FALSE(valid_pricer_frame_request(0, 1, 0, 10));
    TEST_ASSERT_FALSE(valid_pricer_frame_request(5, 1, 0, 10));
    TEST_ASSERT_FALSE(valid_pricer_frame_request(255, 1, 0, 10));

    // Invalid repeats (0 or > 400)
    TEST_ASSERT_FALSE(valid_pricer_frame_request(16, 0, 0, 10));
    TEST_ASSERT_FALSE(valid_pricer_frame_request(16, 401, 0, 10));

    // Invalid gap (> 1,000,000 us)
    TEST_ASSERT_FALSE(valid_pricer_frame_request(16, 1, 1000001, 10));

    // Invalid frame length (0 or > 256 bytes)
    TEST_ASSERT_FALSE(valid_pricer_frame_request(16, 1, 0, 0));
    TEST_ASSERT_FALSE(valid_pricer_frame_request(16, 1, 0, 257));
}

void run_all_tests(void) {
    UNITY_BEGIN();
    RUN_TEST(test_valid_carrier_request_accepted_min_max);
    RUN_TEST(test_valid_carrier_request_invalid_boundaries);
    RUN_TEST(test_carrier_burst_plan_exact_totals);
    RUN_TEST(test_carrier_burst_plan_max_phase_width);
    RUN_TEST(test_carrier_burst_plan_uninterrupted_high_phases_when_split);
    RUN_TEST(test_valid_pricer_frame_request_boundaries);
    UNITY_END();
}

#ifdef ARDUINO
#include <Arduino.h>
void setup() {
    run_all_tests();
}
void loop() {}
#else
int main(int argc, char** argv) {
    (void)argc;
    (void)argv;
    run_all_tests();
    return 0;
}
#endif
