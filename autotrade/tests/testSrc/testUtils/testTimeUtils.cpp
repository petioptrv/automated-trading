#define CATCH_CONFIG_MAIN

#include "../../catch.h"
#include "../../../src/utils/timeUtils.h"

TEST_CASE("General datetime string parsing.", "[datetime]") {
    REQUIRE_THROWS(
            timeUtils::timeStringParser(
                    "%Y-%m-%d %H-%M-%S",
                    "1993098-09-11 11-12-13"
            )
    );
    REQUIRE_NOTHROW(
            timeUtils::timeStringParser(
                    "%Y-%m-%d %H-%M-%S",
                    "1993-09-11 11-12-13"
            )
    );

    // TODO: should throw on format mismatch.

    timeUtils::ptime res = timeUtils::timeStringParser(
            "%Y-%m-%d %H-%M-%S",
            "1993-09-11 11-12-13"
    );
    timeUtils::date targetDate(1993, 9, 11);
    timeUtils::time_duration targetTime(11, 12, 13);

    REQUIRE(res.date() == targetDate);
    REQUIRE(res.time_of_day() == targetTime);
}

TEST_CASE("Generate dates ranges", "[datetime]") {
    timeUtils::ptime start = timeUtils::timeStringParser(
            "%Y-%m-%d",
            "2010-09-10"
    );
    timeUtils::ptime end = timeUtils::timeStringParser(
            "%Y-%m-%d",
            "2010-09-20"
    );
    std::vector<timeUtils::date> datesRange = timeUtils::getDatesRange(
            start, end
    );

    REQUIRE(datesRange.size() == 10);
    REQUIRE(datesRange[0] == start.date());
    REQUIRE(datesRange[9] == end.date() - timeUtils::days(1));

    timeUtils::date dStart(2010, 9, 10);
    timeUtils::date dEnd(2010, 9, 20);

    std::vector<timeUtils::date> anotherDatesRange = timeUtils::getDatesRange(
            dStart, dEnd
    );

    REQUIRE(anotherDatesRange.size() == 10);
    REQUIRE(anotherDatesRange[0] == datesRange[0]);
    REQUIRE(anotherDatesRange[9] == datesRange[9]);
}