#ifndef AUTOMATED_TRADING_HISTORICALRETRIEVER_H
#define AUTOMATED_TRADING_HISTORICALRETRIEVER_H

#include "dataStructs/bar.h"

/**
 * Historical data is kept in the `histData` folder at the root level of the
 * project. The data is then split by symbol. Daily data for each symbol is
 * kept in a CSV called `daily.csv`. Intraday data is further subdivided in
 * one folder per bar size and one CSV per day for each bar size.
 *
 * .
 * +-- SPY
 *     +-- daily.csv
 *     +-- 1 sec/
 *     |   +-- 20100101.csv
 *     |   +-- 20100102.csv
 *     |   +-- ...
 *     |   +-- 20200406.csv
 *     +-- 2 sec/
 *     |   +-- 20100101.csv
 *     |   +-- 20100102.csv
 *     |   +-- ...
 *     |   +-- 20200406.csv
 *     +-- ...
 *     +-- 4 hours/
 *         +-- 20100101.csv
 *         +-- 20100102.csv
 *         +-- ...
 *         +-- 20200406.csv
 */
namespace histRetriever {
    /**
     * Retrieves historical bar data.
     *
     * @param symbol The symbol for which to retrieve data.
     * @param startDateTime Start date and time for the historical
     *     data (inclusive).
     * @param endDateTime End date and time for the historical
     *     data (exclusive).
     * @param barSize The bar size for the historical data.
     * @param includeAfterHours If `true`, after hours data is included.
     * @param searchCache If `true`, the cache will be searched before
     *     retrieving the data online.
     * @param storeToCache If `true`, the data will be cached.
     * @return The requested historical bars.
     */
    bar::BarData retrieveBarData(
            const std::string &symbol,
            const timeUtils::ptime &startDateTime,
            const timeUtils::ptime &endDateTime,
            const bar::BarSize &barSize,
            const bool &includeAfterHours = false,
            const bool &searchCache = true,
            const bool &storeToCache = true
    );
}

#endif //AUTOMATED_TRADING_HISTORICALRETRIEVER_H
