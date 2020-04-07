file(
        GLOB IBAPI_SOURCES
        *.cpp
        *.h
)

add_library(ibapi ${IBAPI_SOURCES})

find_package(Threads REQUIRED)
target_link_libraries(ibapi ${CMAKE_THREAD_LIBS_INIT})
