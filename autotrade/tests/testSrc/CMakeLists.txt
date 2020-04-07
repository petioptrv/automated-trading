file(
        GLOB TEST_SRC_EXECUTABLES
        *.cpp
)
add_executable(srcTestExes ${TEST_SRC_EXECUTABLES})

target_link_libraries(srcTestExes src)

add_subdirectory(testDataStructs)
add_subdirectory(testUtils)