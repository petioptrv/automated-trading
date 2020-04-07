//
// Created by petioptrv on 2020-04-01.
//

#include <iostream>

#include "HistoricalRetriever.h"

namespace histRetriever {
    namespace {
        std::vector<std::string> getFilePaths(
                const std::string &symbol,
                const timeUtils::ptime &startDateTime,
                const timeUtils::ptime &endDateTime,
                const bar::BarSize &barSize
        ) {
            std::vector<std::string> paths;
            std::string basePath = "../histData/" + symbol + "/";

            // TODO: check if this should not be less than 24 hours
            if (barSize >= timeUtils::hours(24)) {
                paths.push_back(basePath + "daily.csv");
            } else {
                throw std::logic_error(
                        "Retrieving intraday historical bar"
                        " data is not yer implemented."
                );
            }
        }
    }

    bar::BarData retrieveBarData(
            const std::string &symbol,
            const timeUtils::ptime &startDateTime,
            const timeUtils::ptime &endDateTime,
            const bar::BarSize &barSize,
            const bool &includeAfterHours,
            const bool &searchCache,
            const bool &storeToCache
    ) {

    }
}