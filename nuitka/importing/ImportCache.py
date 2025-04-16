#     Copyright 2025, Kay Hayen, mailto:kay.hayen@gmail.com find license text at end of file


""" Import cache.

This is not about caching the search of modules in the file system, but about
maintaining a cache of module trees built.

It can happen that modules become unused, and then dropped from active modules,
and then later active again, via another import, and in this case, we should
not start anew, but reuse what we already found out about it.
"""

# from nuitka.ModuleCollector import module_collector


# def addImportedModule(imported_module):
#     module_collector.addImportedModule(imported_module)


# def isImportedModuleByName(full_name):
#     return module_collector.isImportedModuleByName(full_name)


# def getImportedModuleByName(full_name):
#     return module_collector.getImportedModuleByName(full_name)


# def getImportedModuleByNameAndPath(full_name, module_filename):
#     return module_collector.getImportedModuleByNameAndPath(full_name, module_filename)


# def replaceImportedModule(old, new):
#     module_collector.replaceImportedModule(old, new)


#     Part of "Nuitka", an optimizing Python compiler that is compatible and
#     integrates with CPython, but also works on its own.
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.