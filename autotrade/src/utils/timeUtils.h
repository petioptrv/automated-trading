//
// Created by petioptrv on 2020-04-03.
//

#ifndef SCRATCHES_TIMEUTILS_H
#define SCRATCHES_TIMEUTILS_H

#include <boost/date_time/posix_time/posix_time.hpp>
#include <boost/date_time/gregorian/gregorian.hpp>

namespace timeUtils {
    using namespace boost::posix_time;
    using namespace boost::gregorian;

    /**
     * Parses the time from a string according to a predefined format.
     *
     * @param format The format for string parsing.
     * @param timeString The string to parse.
     * @return The parsed time.
     */
    ptime timeStringParser(
            const std::string &format,
            const std::string &timeString
    );

    /**
     * Parses the time from a string following IBAPI's string format for
     * date-time (YYYYmmdd HH:MM:SS).
     *
     * @param timeString The IBAPI-generated date-time string.
     * @return The parsed date-time.
     */
    ptime ibTimeStrParser(const std::string &timeString);

    /**
     * Generates a range of dates between the supplied start and end points.
     *
     * @param start Start date (inclusive).
     * @param end End date (exclusive).
     * @return The range of dates.
     */
    std::vector<date> getDatesRange(const date &start, const date &end);

    /**
     *  Generates a range of dates between the supplied start and end points.
     *
     * @param start Start date-time (inclusive).
     * @param end End date-time (exclusive).
     * @return The range of dates.
     */
    std::vector<date> getDatesRange(const ptime &start, const ptime &end);
};


#endif //SCRATCHES_TIMEUTILS_H
