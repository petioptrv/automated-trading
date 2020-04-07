//
// Created by petioptrv on 2020-04-03.
//

#include "timeUtils.h"

timeUtils::ptime timeUtils::timeStringParser(
        const std::string &format,
        const std::string &timeString
) {
    std::locale dtFormat(
            std::locale::classic(),
            new timeUtils::time_input_facet(format)
    );
    std::istringstream is(timeString);
    is.exceptions(std::ios_base::failbit);
    is.imbue(dtFormat);
    timeUtils::ptime pt;
    is >> pt;
    return pt;
}

timeUtils::ptime timeUtils::ibTimeStrParser(const std::string &timeString) {
    timeUtils::ptime pt = timeUtils::timeStringParser(
            "%Y%m%d %H:%M:%S",
            timeString
    );
    return pt;
}

std::vector<timeUtils::date> timeUtils::getDatesRange(
        const timeUtils::date &start,
        const timeUtils::date &end
) {
    std::vector<timeUtils::date> datesRange;
    timeUtils::date currentDate(start);
    while (currentDate < end) {
        datesRange.push_back(currentDate);
        currentDate += timeUtils::days(1);
    }

    return datesRange;
}

std::vector<timeUtils::date> timeUtils::getDatesRange(
        const timeUtils::ptime &start,
        const timeUtils::ptime &end
) {
    timeUtils::date startDate = start.date();
    timeUtils::date endDate = end.date();

    return timeUtils::getDatesRange(startDate, endDate);
}
