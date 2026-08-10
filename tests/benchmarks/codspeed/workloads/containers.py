ROUNDS = 60000


def list_manipulation(rounds):
    total = 0
    for i in range(rounds):
        items = [1, 2, 3, 4, 5]
        items.append(i % 7)
        items[0] = items[-1]
        items.reverse()
        total += sum(items)
        sliced = items[1:4]
        total += len(sliced)
    return total


def dict_manipulation(rounds):
    total = 0
    d = {}
    for i in range(rounds):
        key = i % 500
        d[key] = d.get(key, 0) + 1
        if key in d:
            total += d[key]
    return total


def tuple_unpacking(rounds):
    total = 0
    for i in range(rounds):
        a, b, c = i, i + 1, i + 2
        (x, y), z = (a, b), c
        total += x + y + z
        first, *rest = [a, b, c, x, y, z]
        total += first + len(rest)
    return total


def comprehensions(rounds):
    total = 0
    for i in range(rounds // 10):
        squares = [x * x for x in range(20)]
        evens = {x for x in squares if x % 2 == 0}
        mapping = {x: x + 1 for x in range(10)}
        total += sum(squares) + len(evens) + sum(mapping.values())
    return total


def main():
    result = 0
    result += list_manipulation(ROUNDS)
    result += dict_manipulation(ROUNDS)
    result += tuple_unpacking(ROUNDS)
    result += comprehensions(ROUNDS)
    print(result)


if __name__ == "__main__":
    main()
