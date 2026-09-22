cmake_minimum_required(VERSION 3.10)

set(MCUBE_IMPL "reference" CACHE STRING "Build the MasterCube reference implementation" FORCE)
add_subdirectory("${CMAKE_CURRENT_LIST_DIR}/.." "${CMAKE_BINARY_DIR}/MasterCubeReference")
