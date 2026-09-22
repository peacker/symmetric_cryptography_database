CC := gcc
CFLAGS := -O3 -std=c99 -Wall -Wextra
LDFLAGS :=
LDLIBS :=

TARGET := gen_test_vecs
SRCS := KAT_CryptHash.c CryptHash_AlgorithmInstance.c drng.c
OBJS := $(SRCS:.c=.o)

.PHONY: all run clean

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS) $(LDLIBS)

KAT_CryptHash.o: KAT_CryptHash.c CryptHash_AlgorithmInstance.h drng.h
CryptHash_AlgorithmInstance.o: CryptHash_AlgorithmInstance.c CryptHash_AlgorithmInstance.h
drng.o: drng.c drng.h

run: $(TARGET)
	./$(TARGET)

clean:
	rm -f $(TARGET) $(OBJS)