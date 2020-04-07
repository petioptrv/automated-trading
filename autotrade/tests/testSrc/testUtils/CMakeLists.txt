file(
        GLOB UTILS_TEST_EXECUTABLES
        *.cpp
)
add_executable(utilsTestExes ${UTILS_TEST_EXECUTABLES})

target_link_libraries(utilsTestExes utils)

find_package(Boost REQUIRED COMPONENTS date_time)
include_directories(${Boost_INCLUDE_DIRS})
target_link_libraries(utilsTestExes ${Boost_LIBRARIES})