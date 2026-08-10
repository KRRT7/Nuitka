ROUNDS = 150000


def add_one(x):
    return x + 1


def add_args(a, b, c=1, *, d=2):
    return a + b + c + d


class Counter:
    def __init__(self, value=0):
        self.value = value

    def increment(self):
        self.value += 1
        return self.value

    def add(self, amount):
        self.value += amount
        return self.value


def fib(n):
    if n < 2:
        return n
    return fib(n - 1) + fib(n - 2)


def plain_function_calls(rounds):
    total = 0
    for i in range(rounds):
        total = add_one(total)
        total = add_args(total, 1, c=2, d=3)
    return total


def method_calls(rounds):
    counter = Counter()
    for i in range(rounds):
        counter.increment()
        counter.add(2)
    return counter.value


def recursive_calls():
    return fib(24)


def main():
    result = 0
    result += plain_function_calls(ROUNDS)
    result += method_calls(ROUNDS)
    result += recursive_calls()
    print(result)


if __name__ == "__main__":
    main()
