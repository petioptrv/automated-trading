//
// Created by petioptrv on 2020-04-03.
//

#ifndef AUTOMATED_TRADING_BAR_H
#define AUTOMATED_TRADING_BAR_H

#include <boost/date_time/gregorian/gregorian.hpp>

#include "../utils/timeUtils.h"

namespace bar {
    struct Bar {
        timeUtils::ptime dateTime;
        double high{};
        double low{};
        double open{};
        double close{};
        double wap{};
        long long volume{};
        int count{};
    };

    class BarSize {
    public:
        explicit BarSize(timeUtils::time_duration barSize);

        BarSize(const BarSize &barSize);

        std::string operator+(const std::string &other) const;

        friend std::string
        operator+(const std::string &first, const BarSize &second);

        friend void
        operator+=(std::string &first, const BarSize &second);

        bool operator<(const timeUtils::time_duration &duration) const;

        bool operator<=(const timeUtils::time_duration &duration) const;

        bool operator>(const timeUtils::time_duration &duration) const;

        bool operator>=(const timeUtils::time_duration &duration) const;

        bool operator==(const timeUtils::time_duration &duration) const;

        bool operator<(const BarSize &other) const;

        bool operator<=(const BarSize &other) const;

        bool operator>(const BarSize &other) const;

        bool operator>=(const BarSize &other) const;

        bool operator==(const BarSize &other) const;

    private:
        timeUtils::time_duration barSize_;

        static void validateBarSize(const timeUtils::time_duration &barSize);

        std::string toString() const;
    };

    std::string operator+(const std::string &first, const BarSize &second);

    void operator+=(std::string &first, const BarSize &second);

    class BarData {
    public:
        explicit BarData(const timeUtils::time_duration &barSize);

        explicit BarData(const BarSize &barSize);

        void addBar(Bar bar);

        size_t size();

        const BarSize &barSize();

    private:
        std::map<timeUtils::ptime, Bar> bars;
        BarSize barSize_;
    };
}

#endif //AUTOMATED_TRADING_BAR_H
