#define CATCH_CONFIG_MAIN

#include <boost/date_time/posix_time/posix_time.hpp>

#include "../../src/HistoricalRetriever.cpp"
#include "../../src/dataStructs/bar.h"

#include "../catch.h"

typedef boost::gregorian::date date;
typedef boost::posix_time::time_duration td;
typedef boost::posix_time::ptime ptime;

TEST_CASE("Retrieve cached historical bar data", "[bar data]") {
    ptime startDataTime(date(2020, 03, 30), td(9, 0, 0));
    ptime endDateTime(date(2020, 4, 3), td(16, 30, 0));
    bar::BarSize barSize(td(24, 0, 0));

    bar::BarData data = histRetriever::retrieveBarData(
            "SPY",
            startDataTime,
            endDateTime,
            barSize
    );

    REQUIRE(data.size() == 4)
}