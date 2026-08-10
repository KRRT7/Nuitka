ROUNDS = 400000


def int_arithmetic(rounds):
    c = 0
    for i in range(rounds):
        a = i % 7 + 2
        b = i % 5 + 3
        c = a + b
        c = b + c
        c = c + a
        c = c - a
        c = a - b
        c = b - c
        c = c * b
        c = b * a
        c = a * c
    return c


def int_comparisons(rounds):
    total = 0
    for i in range(rounds):
        a = i % 17
        b = i % 42
        if a < b:
            total += 1
        if a > b:
            total -= 1
        if a == b - 25:
            total += 1
        if a != b:
            total += 1
        if i < rounds - 1:
            total += 1
        if i >= 0:
            total += 1
    return total


def float_arithmetic(rounds):
    c = 0.0
    for i in range(rounds):
        a = (i % 11) + 2.5
        b = (i % 13) + 3.25
        c = a + b
        c = b + c
        c = c - a
        c = c * b
        c = c / b
    return c


def min_max_pairs(rounds):
    total = 0
    for i in range(rounds):
        a = i % 97
        b = (i * 7) % 89
        total += min(a, b)
        total += max(a, b)
    return total


def main():
    result = 0
    result += int_arithmetic(ROUNDS)
    result += int_comparisons(ROUNDS)
    result += int(float_arithmetic(ROUNDS))
    result += min_max_pairs(ROUNDS)
    print(result)


if __name__ == "__main__":
    main()
