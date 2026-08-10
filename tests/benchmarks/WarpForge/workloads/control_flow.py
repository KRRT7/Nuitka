ROUNDS = 250000


def nested_loops(rounds):
    total = 0
    outer = 0
    while outer < rounds:
        for inner in range(8):
            if inner % 2 == 0:
                total += inner
            else:
                total -= inner
        outer += 1
    return total


def if_else_chain(rounds):
    total = 0
    for i in range(rounds):
        v = i % 5
        if v == 0:
            total += 1
        elif v == 1:
            total += 2
        elif v == 2:
            total += 3
        elif v == 3:
            total += 4
        else:
            total += 5
    return total


def exception_handling(rounds):
    total = 0
    for i in range(rounds // 5):
        try:
            if i % 3 == 0:
                raise ValueError("boom")
            total += 1
        except ValueError:
            total += 2
        finally:
            total += 1
    return total


def main():
    result = 0
    result += nested_loops(ROUNDS)
    result += if_else_chain(ROUNDS)
    result += exception_handling(ROUNDS)
    print(result)


if __name__ == "__main__":
    main()
