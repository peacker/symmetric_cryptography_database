CC = gcc
CFLAGS = -std=c99 -O2 -Wall -Wextra

INSTANCES = Neulaser-512 Neulaser-768 Neulaser-1024
TARGETS = $(addsuffix /KAT_CryptHash.exe,$(INSTANCES))

.PHONY: all kat clean

all: $(TARGETS)

%/KAT_CryptHash.exe: %/KAT_CryptHash.c %/CryptHash_AlgorithmInstance.c %/CryptHash_AlgorithmInstance.h %/drng.c %/drng.h
	$(CC) $(CFLAGS) -I$* -o $@ $*/KAT_CryptHash.c $*/CryptHash_AlgorithmInstance.c $*/drng.c

kat: all
	for d in $(INSTANCES); do (cd $$d && ./KAT_CryptHash.exe); done

clean:
	rm -f $(TARGETS)
