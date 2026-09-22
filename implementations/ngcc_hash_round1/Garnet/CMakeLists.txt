add_library(garnet_512 Garnet/Garnet_512_896.c)

add_library(garnet_768
    Garnet/Garnet_768.c
)

add_library(garnet_1024
    Garnet/Garnet_1024.c
)

target_include_directories(garnet_512 PUBLIC
    Garnet/include/Garnet_512.h
)

target_include_directories(garnet_768 PUBLIC
    Garnet/include/Garnet_768.h
)

target_include_directories(garnet_1024 PUBLIC
    Garnet/include/Garnet_1024.h
)

