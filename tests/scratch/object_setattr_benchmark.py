from time import perf_counter


class Record:
    def __setattr__(self, name, value):
        object.__setattr__(self, name, value)


def main():
    record = Record()
    count = 200000
    started = perf_counter()
    for index in range(count):
        record.value = index
    elapsed = perf_counter() - started
    print("mean_ns=%.1f value=%d" % (elapsed * 1000000000.0 / count, record.value))


if __name__ == "__main__":
    main()
