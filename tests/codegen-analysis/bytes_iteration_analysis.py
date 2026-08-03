from __future__ import print_function


def read_byte(data, index):
    return data[index]


def sum_bytes(data):
    result = 0
    for index in range(len(data)):
        result += data[index]
    return result


def increment_bytearray(data):
    for index in range(len(data)):
        data[index] = (data[index] + 1) & 255
    return bytes(data)


def read_bytearray(data):
    result = 0
    for index in range(len(data)):
        result += data[index]
    return result


def main():
    values = []
    iterator = iter(b"Nuitka")

    while True:
        try:
            values.append(next(iterator))
        except StopIteration:
            break

    print(values)
    print(list(iter(b"bytes")))
    print([read_byte(b"bytes", index) for index in (0, 1, -1)])
    print(sum_bytes(b"bytes"))
    print(increment_bytearray(bytearray(b"bytes")))
    print(read_bytearray(bytearray(b"bytes")))
    print(sum_bytes(memoryview(b"bytes").cast("B")))


main()
