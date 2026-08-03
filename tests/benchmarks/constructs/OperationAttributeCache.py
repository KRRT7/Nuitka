#     Copyright 2026, Kay Hayen, mailto:kay.hayen@gmail.com find license text at end of file


class Bench:
    def __init__(self):
        self.value = 1


bench = Bench()

for _ in range(50000):
    # construct_begin
    result = bench.value
    # construct_alternative
    result = bench.value + 0
    # construct_end

assert result == 1
print("OK.")
