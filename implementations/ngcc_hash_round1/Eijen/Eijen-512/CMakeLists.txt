cmake_minimum_required(VERSION 3.11.4)
project(eijen_crypt_hash_reference C)

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS OFF)

add_executable(kat
    KAT_CryptHash.c
    CryptHash_AlgorithmInstance.c
    eijen_ref.c
    drng.c)

target_include_directories(kat PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
target_compile_options(kat PRIVATE -std=c99 -Wpedantic -Wall -Wextra -O2)
