#     Copyright 2026, Kay Hayen, mailto:kay.hayen@gmail.com find license text at end of file


class Plain:
    def __init__(self):
        self.value = "initial"


plain = Plain()
assert plain.value == "initial"
assert hasattr(plain, "value")
assert not hasattr(plain, "missing")

plain.value = "updated"
assert plain.value == "updated"

del plain.value
try:
    plain.value
except AttributeError:
    pass
else:
    raise AssertionError("deleted attribute was returned from cache")

assert not hasattr(plain, "value")


class WithProperty:
    @property
    def value(self):
        return "property"


with_property = WithProperty()
with_property.__dict__["value"] = "instance"
assert with_property.value == "property"

WithProperty.value = "class value"
del with_property.__dict__["value"]
assert with_property.value == "class value"


class Growing:
    pass


growing = Growing()
growing.target = "before growth"
assert growing.target == "before growth"

for index in range(1000):
    setattr(growing, "attribute_%d" % index, index)

assert growing.target == "before growth"
growing.target = "after growth"
assert growing.target == "after growth"

print("AttributeCacheTest: OK")
