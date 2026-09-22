CC ?= gcc
CFLAGS ?= -std=c99 -O2 -Wall -Wextra -pedantic
LDFLAGS ?=

PERF_SPLIT_ROUNDS ?= 6
PERF_CFLAGS ?= $(CFLAGS) -DAFS_TREDM_PERFORMANCE_PROFILE=1 -DAFS_TREDM_TIERED_SPLIT_ROUNDS=$(PERF_SPLIT_ROUNDS)
PERF_KAT_CFLAGS ?= $(PERF_CFLAGS)

COMMON_SRCS = CryptHash_AlgorithmInstance.c afs_sbox64.c afs_lmds1600_s6.c afs_p1600.c afs_tredm.c
KAT_SRCS = KAT_CryptHash.c drng.c $(COMMON_SRCS)
QUICK_SRCS = quick_test.c $(COMMON_SRCS)
HASHCLI_SRCS = hash_cli.c $(COMMON_SRCS)
BENCH_SRCS = benchmark.c $(COMMON_SRCS)
PROFILE_SRCS = profile_info.c

.PHONY: all clean kat quick run-quick kat-2-12 benchmark run-benchmark \
    quick_test_perf hash_cli_perf benchmark_perf kat_perf run-quick-perf run-benchmark-perf kat-2-12-perf \
    profile-info profile-info-perf

all: kat quick_test hash_cli benchmark

kat: $(KAT_SRCS)
	$(CC) $(CFLAGS) -o $@ $(KAT_SRCS) $(LDFLAGS)

quick_test: $(QUICK_SRCS)
	$(CC) $(CFLAGS) -o $@ $(QUICK_SRCS) $(LDFLAGS)

hash_cli: $(HASHCLI_SRCS)
	$(CC) $(CFLAGS) -o $@ $(HASHCLI_SRCS) $(LDFLAGS)

benchmark: $(BENCH_SRCS)
	$(CC) $(CFLAGS) -o $@ $(BENCH_SRCS) $(LDFLAGS)

profile_info: $(PROFILE_SRCS)
	$(CC) $(CFLAGS) -o $@ $(PROFILE_SRCS) $(LDFLAGS)

profile_info_perf: $(PROFILE_SRCS)
	$(CC) $(PERF_CFLAGS) -o $@ $(PROFILE_SRCS) $(LDFLAGS)

kat_perf: $(KAT_SRCS)
	$(CC) $(PERF_KAT_CFLAGS) -o $@ $(KAT_SRCS) $(LDFLAGS)

quick_test_perf: $(QUICK_SRCS)
	$(CC) $(PERF_CFLAGS) -o $@ $(QUICK_SRCS) $(LDFLAGS)

hash_cli_perf: $(HASHCLI_SRCS)
	$(CC) $(PERF_CFLAGS) -o $@ $(HASHCLI_SRCS) $(LDFLAGS)

benchmark_perf: $(BENCH_SRCS)
	$(CC) $(PERF_CFLAGS) -o $@ $(BENCH_SRCS) $(LDFLAGS)

run-quick: quick_test
	./quick_test

run-benchmark: benchmark
	./benchmark

run-quick-perf: quick_test_perf
	./quick_test_perf

run-benchmark-perf: benchmark_perf
	./benchmark_perf

kat-2-12: kat
	./kat

kat-2-12-perf: kat_perf
	./kat_perf

profile-info: profile_info
	./profile_info

profile-info-perf: profile_info_perf
	./profile_info_perf

clean:
	rm -f kat kat_perf quick_test quick_test_perf hash_cli hash_cli_perf \
		benchmark benchmark_perf profile_info profile_info_perf *.o *.su
	rm -rf output output_performance output_*
