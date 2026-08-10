ROUNDS = 150000


class Plain:
    def __init__(self):
        self.x = 1
        self.y = 2
        self.z = 3


class WithSlots:
    __slots__ = ("x", "y", "z")

    def __init__(self):
        self.x = 1
        self.y = 2
        self.z = 3


class WithClassAttr:
    shared = 100

    def __init__(self):
        self.value = 0


def instance_attribute_access(rounds):
    obj = Plain()
    total = 0
    for i in range(rounds):
        obj.x = obj.x + 1
        obj.y = obj.y + obj.x
        obj.z = obj.z + obj.y
        total += obj.z
    return total


def slots_attribute_access(rounds):
    obj = WithSlots()
    total = 0
    for i in range(rounds):
        obj.x = obj.x + 1
        obj.y = obj.y + obj.x
        obj.z = obj.z + obj.y
        total += obj.z
    return total


def class_attribute_access(rounds):
    obj = WithClassAttr()
    total = 0
    for i in range(rounds):
        total += WithClassAttr.shared
        obj.value += obj.shared
        total += obj.value
    return total


def main():
    result = 0
    result += instance_attribute_access(ROUNDS)
    result += slots_attribute_access(ROUNDS)
    result += class_attribute_access(ROUNDS)
    print(result)


if __name__ == "__main__":
    main()
