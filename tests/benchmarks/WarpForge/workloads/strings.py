ROUNDS = 60000


def string_concat(rounds):
    total = 0
    for i in range(rounds):
        s = "prefix-" + str(i) + "-suffix"
        s = s + "!"
        total += len(s)
    return total


def string_formatting(rounds):
    total = 0
    for i in range(rounds):
        s = f"item-{i}-value-{i * 2}"
        total += len(s)
    return total


def string_predicates_and_search(rounds):
    total = 0
    needle = "value"
    for i in range(rounds):
        s = f"item-{i}-value-{i * 2}"
        if needle in s:
            total += 1
        if s.startswith("item"):
            total += 1
        if s.endswith(str(i * 2)):
            total += 1
        total += s.count("-")
        parts = s.split("-")
        total += len(parts)
    return total


def main():
    result = 0
    result += string_concat(ROUNDS)
    result += string_formatting(ROUNDS)
    result += string_predicates_and_search(ROUNDS)
    print(result)


if __name__ == "__main__":
    main()
