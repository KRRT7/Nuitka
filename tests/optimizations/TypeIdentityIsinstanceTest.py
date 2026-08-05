#     Test for type(x) is T and isinstance optimizations

def type_identity_is(x=None):
    if type(x) is tuple:
        return 1
    return 2


def type_identity_is_not(x=None):
    if type(x) is not list:
        return 1
    return 2


def isinstance_single(x=None):
    if isinstance(x, int):
        return 1
    return 2


def isinstance_tuple(x=None):
    if isinstance(x, (int, float)):
        return 1
    return 2


def isinstance_bool(x=None):
    if isinstance(x, bool):
        return 1
    return 2


def type_identity_with_none(x=None):
    if type(x) is type(None):
        return 1
    return 2


def isinstance_none_tuple(x=None):
    if isinstance(x, (type(None), str)):
        return 1
    return 2


def isinstance_notimplemented(x=None):
    if isinstance(x, type(NotImplemented)):
        return 1
    return 2


def type_identity_with_bool(x=None):
    if type(x) is bool:
        return 1
    return 2


print(type_identity_is())
print(type_identity_is_not())
print(isinstance_single())
print(isinstance_tuple())
print(isinstance_bool())
print(type_identity_with_none())
print(isinstance_none_tuple())
print(isinstance_notimplemented())
print(type_identity_with_bool())

#     Python test originally created or extracted from other peoples work. The
#     parts from me are licensed as below. The parts from other people are
#     licensed as well.
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
