CC = gcc
CFLAGS = -std=c99 -Wpedantic -Wall -Wextra -O2
ifdef DEBUG
CFLAGS += -DDEBUG -g
endif
KAT = KAT_CryptHash
SRC = KAT_CryptHash.c drng.c CryptHash_AlgorithmInstance.c wish.c

.PHONY: kat run-kat clean

kat: $(KAT)

$(KAT): $(SRC)
	$(CC) $(CFLAGS) -o $@ $^

run-kat: $(KAT)
	./$(KAT)

clean:
	rm -f $(KAT) *.txt
