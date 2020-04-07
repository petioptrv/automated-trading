//
// Created by petioptrv on 2020-04-03.
//
#define CATCH_CONFIG_MAIN

#include <random>
#include <boost/date_time/posix_time/posix_time.hpp>

#include "../../../src/dataStructs/bar.h"
#include "../../catch.h"

TEST_CASE("BarSize constructors", "[BarSize]") {
    timeUtils::minutes validTimeM(5);
    timeUtils::hours invalidTime(25);

    REQUIRE_NOTHROW(bar::BarSize(validTimeM));

    bar::BarSize validBarSize = bar::BarSize(validTimeM);

    REQUIRE_NOTHROW(bar::BarSize(validBarSize));

    REQUIRE_THROWS(bar::BarSize(invalidTime));
}

TEST_CASE("BarSize + operator with string", "[BarSize]") {
    timeUtils::seconds time1S(1);
    timeUtils::seconds time5S(5);

    std::string baseStr = " time ";

    REQUIRE(bar::BarSize(time1S) +baseStr == "1 sec time ");
    REQUIRE(baseStr + bar::BarSize(time5S) == " time 5 secs");
}

TEST_CASE("BarSize += operator with string", "[BarSize]") {
    timeUtils::minutes time1M(1);
    timeUtils::minutes time5M(5);

    std::string baseStr = " time ";
    baseStr += bar::BarSize(time5M);

    REQUIRE(baseStr == " time 5 mins");
}

TEST_CASE("BarSize comparison operators time_duraiton", "[BarSize]") {
    timeUtils::hours time1H(1);
    timeUtils::hours time2H(2);
    timeUtils::hours time4H(4);

    bar::BarSize targetBar(timeUtils::hours(2));

    REQUIRE(targetBar > time1H);
    REQUIRE(targetBar >= time2H);
    REQUIRE(targetBar <= time2H);
    REQUIRE(targetBar < time4H);
}

TEST_CASE("BarData size", "[BarData]") {
    bar::BarData bars(timeUtils::minutes(5));

    REQUIRE(bars.size() == 0);
}

TEST_CASE("BarData addBar", "[BarData]") {
    bar::BarData bars(timeUtils::minutes(5));

    bars.addBar(
            bar::Bar{
                    boost::posix_time::ptime(
                            boost::posix_time::microsec_clock::local_time()
                    ),
                    180,
                    179,
                    179.5,
                    179.6,
                    179.3,
                    12341234,
                    10
            }
    );

    REQUIRE(bars.size() == 1);
}

bar::BarData generateBars(int nBars) {
    bar::BarData bars(timeUtils::minutes(5));

    std::random_device rd;
    std::mt19937 gen(rd());
    float baseVal = 100;

    for (int i = 0; i != nBars; ++i) {
        std::uniform_real_distribution<> dis(
                baseVal + (float) i, baseVal + 5 + (float) i
        );
        bars.addBar(
                bar::Bar{
                        boost::posix_time::ptime(
                                boost::posix_time::microsec_clock::local_time()
                        ),
                        dis(gen),
                        dis(gen),
                        dis(gen),
                        dis(gen),
                        dis(gen),
                        static_cast<long long>(gen()),
                        static_cast<int>(gen()) % 100
                }
        );
    }
}

