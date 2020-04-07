add_library(utils timeUtils.cpp timeUtils.h pathUtils.cpp pathUtils.h)

find_package(Boost REQUIRED COMPONENTS date_time)
include_directories(${Boost_INCLUDE_DIRS})
target_link_libraries(utils ${Boost_LIBRARIES})