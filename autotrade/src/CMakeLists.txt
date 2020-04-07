add_subdirectory(dataStructs)
add_subdirectory(utils)

add_library(
        src
        HistoricalRetriever.cpp
        HistoricalRetriever.h)

target_link_libraries(src ibapi utils dstructs)
