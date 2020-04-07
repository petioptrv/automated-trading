file(
        GLOB DATA_STRUCTS_TEST_EXECUTABLES
        *.cpp
)
add_executable(dataStructsTestExes ${DATA_STRUCTS_TEST_EXECUTABLES})

target_link_libraries(dataStructsTestExes dstructs)

find_package(Boost REQUIRED COMPONENTS date_time)
include_directories(${Boost_INCLUDE_DIRS})
target_link_libraries(dataStructsTestExes ${Boost_LIBRARIES})