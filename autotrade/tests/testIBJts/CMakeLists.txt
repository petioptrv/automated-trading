file(
        GLOB IBAPI_TEST_EXECUTABLES
        *.cpp
)
add_executable(ibapiTestExes ${IBAPI_TEST_EXECUTABLES})

target_link_libraries(ibapiTestExes ibapi)

find_package(Boost REQUIRED COMPONENTS date_time)
include_directories(${Boost_INCLUDE_DIRS})
target_link_libraries(ibapiTestExes ${Boost_LIBRARIES})
