def is_number(value):
    return type(value) in (int, float)


class IntegerSubclass(int):
    pass


print(is_number(1))
print(is_number(1.0))
print(is_number(IntegerSubclass(1)))
print(type("x") in (int, float))
