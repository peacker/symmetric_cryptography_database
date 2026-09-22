# Makefile for Reference_Implementation/JuziHash-1024
# Build the ICCS KAT generator on Linux/GCC.

CC ?= gcc
CSTD ?= -std=c99
WARN ?= -Wall -Wextra
OPTFLAGS ?= -O2
CFLAGS ?= $(CSTD) $(OPTFLAGS) $(WARN)
LDFLAGS ?=
TARGET := KAT_CryptHash
SRC := KAT_CryptHash.c drng.c CryptHash_AlgorithmInstance.c

.PHONY: all kat run clean

all: $(TARGET)

$(TARGET): $(SRC) CryptHash_AlgorithmInstance.h drng.h
	$(CC) $(CFLAGS) $(SRC) -o $(TARGET) $(LDFLAGS)

# Build and run the ICCS KAT generator. This may take a long time for large tests.
kat run: $(TARGET)
	./$(TARGET)

clean:
	rm -f $(TARGET) *.o *.obj *.exe
	rm -rf output
