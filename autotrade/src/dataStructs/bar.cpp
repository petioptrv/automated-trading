//
// Created by petioptrv on 2020-04-03.
//

#include "bar.h"

#include <utility>

using namespace bar;

BarSize::BarSize(timeUtils::time_duration barSize) :
        barSize_(std::move(barSize)) {
    validateBarSize(barSize_);
}

BarSize::BarSize(const bar::BarSize &barSize) : barSize_(barSize.barSize_) {
    validateBarSize(barSize_);
}

void BarSize::validateBarSize(const timeUtils::time_duration &barSize) {
    if (barSize > timeUtils::hours(24)) {
        throw std::invalid_argument("barSize must be less than 24 hours.");
    }
}

std::string BarSize::operator+(const std::string &other) const {
    return toString() + other;
}

std::string bar::operator+(const std::string &first, const BarSize &second) {
    return first + second.toString();
}

void bar::operator+=(std::string &first, const BarSize &second) {
    first = first + second;
}

bool BarSize::operator<(const timeUtils::time_duration &duration) const {
    return barSize_ < duration;
}

bool BarSize::operator<=(const timeUtils::time_duration &duration) const {
    return barSize_ <= duration;
}

bool BarSize::operator>(const timeUtils::time_duration &duration) const {
    return barSize_ > duration;
}

bool BarSize::operator>=(const timeUtils::time_duration &duration) const {
    return barSize_ >= duration;
}

bool BarSize::operator==(const timeUtils::time_duration &duration) const {
    return barSize_ == duration;
}

bool BarSize::operator<(const BarSize &other) const {
    return barSize_ < other.barSize_;
}

bool BarSize::operator<=(const BarSize &other) const {
    return barSize_ <= other.barSize_;
}

bool BarSize::operator>(const BarSize &other) const {
    return barSize_ > other.barSize_;
}

bool BarSize::operator>=(const BarSize &other) const {
    return barSize_ >= other.barSize_;
}

bool BarSize::operator==(const BarSize &other) const {
    return barSize_ == other.barSize_;
}

std::string BarSize::toString() const {
    std::string sizeString;

    if (barSize_ == timeUtils::seconds(1)) {
        sizeString = "1 sec";
    } else if (barSize_ < timeUtils::minutes(1)) {
        sizeString = std::to_string(barSize_.seconds()) + " secs";
    } else if (barSize_ == timeUtils::minutes(1)) {
        sizeString = "1 min";
    } else if (barSize_ < timeUtils::hours(1)) {
        sizeString = std::to_string(barSize_.minutes()) + " mins";
    } else if (barSize_ == timeUtils::hours(1)) {
        sizeString = "1 hour";
    } else if (barSize_ < timeUtils::hours(24)) {
        sizeString = std::to_string(barSize_.hours()) + " hours";
    } else {
        sizeString = "1 day";
    }

    return sizeString;
}

BarData::BarData(const timeUtils::time_duration &barSize) : barSize_(barSize) {
}

BarData::BarData(const bar::BarSize &barSize) : barSize_(barSize) {}

void BarData::addBar(Bar bar) {
    bars[bar.dateTime] = bar;
}

size_t BarData::size() {
    return bars.size();
}

const BarSize &BarData::barSize() {
    return barSize_;
}
