#     Copyright 2025, Kay Hayen, mailto:kay.hayen@gmail.com find license text at end of file


""" Module collection for Nuitka.

This class encapsulates the logic for collecting and managing modules during the
compilation process. It replaces the global state previously used in ModuleRegistry
and consolidates module collection logic from various parts of the codebase.
"""

import os
import collections

from nuitka.containers.Namedtuples import makeNamedtupleClass
from nuitka.containers.OrderedSets import OrderedSet
from nuitka.utils.CStrings import decodePythonIdentifierFromC
from nuitka.utils.Importing import hasPackageDirFilename


class Registry:
    """Class responsible for collecting and managing modules during compilation.

    This class replaces the global state previously used in ModuleRegistry and
    consolidates module collection logic from various parts of the codebase.
    """

    def __init__(self):
        # One or more root modules, i.e. entry points that must be there.
        self.root_modules = OrderedSet()

        # To be traversed modules
        self.active_modules = OrderedSet()

        # Information about why a module became active.
        self.active_modules_info = {}

        # Already traversed modules
        self.done_modules = set()
        
        # Index of done modules by name for faster lookups
        self.done_modules_by_name = {}

        # Cache of imported modules by name and path
        self.imported_modules = {}
        self.imported_by_name = {}

        # Information about how modules were influenced by plugins
        self.module_influencing_plugins = {}

        # Information about how long the optimization took
        self.module_timing_infos = {}

        # Cache for recursion decisions
        self.recursion_decision_cache = {}

        # Define named tuples
        self.ActiveModuleInfo = collections.namedtuple(
            "ActiveModuleInfo", ("using_module", "usage_tag", "reason", "source_ref")
        )

        self.ModuleOptimizationTimingInfo = makeNamedtupleClass(
            "ModuleOptimizationTimingInfo",
            ("pass_number", "time_used", "micro_passes", "merge_counts"),
        )

    def addRootModule(self, module):
        """Add a root module to the collection."""
        self.root_modules.add(module)

    def getRootModules(self):
        """Get all root modules."""
        return self.root_modules

    def getRootTopModule(self):
        """Get the top-level root module."""
        top_module = next(iter(self.root_modules))
        assert top_module.isTopModule(), top_module
        return top_module

    def hasRootModule(self, module_name):
        """Check if a module with the given name is a root module."""
        for module in self.root_modules:
            if module.getFullName() == module_name:
                return True
        return False

    def replaceRootModule(self, old, new):
        """Replace a root module with another one."""
        new_root_modules = OrderedSet()

        for module in self.root_modules:
            new_root_modules.add(module if module is not old else new)

        assert len(self.root_modules) == len(new_root_modules)
        self.root_modules = new_root_modules

    def getUncompiledModules(self):
        """Get all uncompiled modules."""
        result = set()

        for module in self.getDoneModules():
            if module.isUncompiledPythonModule():
                result.add(module)

        return tuple(sorted(result, key=lambda module: module.getFullName()))

    def getCompiledModules(self):
        """Get all compiled modules."""
        result = set()

        for module in self.getDoneModules():
            if module.isCompiledPythonModule():
                result.add(module)

        return tuple(sorted(result, key=lambda module: module.getFullName()))

    def getUncompiledTechnicalModules(self):
        """Get all uncompiled technical modules."""
        result = set()

        for module in self.getDoneModules():
            if module.isUncompiledPythonModule() and module.isTechnical():
                result.add(module)

        return tuple(sorted(result, key=lambda module: module.getFullName()))

    def getUncompiledNonTechnicalModules(self):
        """Get all uncompiled non-technical modules."""
        result = set()

        for module in self.getDoneModules():
            if module.isUncompiledPythonModule():
                result.add(module)

        return tuple(sorted(result, key=lambda module: module.getFullName()))

    def startTraversal(self):
        """Start the module traversal process."""
        # Create a new OrderedSet with the root modules
        self.active_modules = OrderedSet(self.root_modules)

        # Reset the active modules info dictionary
        self.active_modules_info = {}
        
        # Initialize active_modules_info for root modules
        for root_module in self.root_modules:
            self.active_modules_info[root_module] = self.ActiveModuleInfo(
                using_module=None,
                usage_tag="root_module",
                reason="Root module",
                source_ref=None,
            )
            
        # Reset the done modules set and index
        self.done_modules = set()
        self.done_modules_by_name = {}

        # Start traversal for all active modules
        for active_module in self.active_modules:
            active_module.startTraversal()

    def addUsedModule(self, module, using_module, usage_tag, reason, source_ref):
        """Add a module to the active modules list."""
        if module not in self.done_modules and module not in self.active_modules:
            self.active_modules.add(module)

            self.active_modules_info[module] = self.ActiveModuleInfo(
                using_module=using_module,
                usage_tag=usage_tag,
                reason=reason,
                source_ref=source_ref,
            )

            module.startTraversal()

    def nextModule(self):
        """Get the next module to process and mark it as done."""
        if self.active_modules:
            result = self.active_modules.pop()
            self.done_modules.add(result)
            # Update the name index for faster lookups
            self.done_modules_by_name[result.getFullName()] = result
            return result
        else:
            return None

    def getRemainingModulesCount(self):
        """Get the count of remaining modules to process."""
        return len(self.active_modules)

    def getDoneModulesCount(self):
        """Get the count of processed modules."""
        return len(self.done_modules)

    def getDoneModules(self):
        """Get all processed modules, sorted by name and kind."""
        return sorted(self.done_modules, key=lambda module: (module.getFullName(), module.kind))

    def hasDoneModule(self, module_name):
        """Check if a module with the given name has been processed."""
        # Use the name index for O(1) lookup instead of O(n) search
        return module_name in self.done_modules_by_name

    def getModuleInclusionInfoByName(self, module_name):
        """Get inclusion info for a module by name."""
        # First check if the module exists in done modules
        if module_name in self.done_modules_by_name:
            module = self.done_modules_by_name[module_name]
            if module in self.active_modules_info:
                return self.active_modules_info[module]
                
        # Fallback to the original search if needed
        for module, info in self.active_modules_info.items():
            if module.getFullName() == module_name:
                return info
                
        return None

    def getModuleFromCodeName(self, code_name):
        """Get a module from its code name."""
        module_name = decodePythonIdentifierFromC(code_name)

        # TODO: We need something to just load modules.
        for module in self.root_modules:
            if module.getCodeName() == module_name:
                return module

        assert False, code_name

    def getOwnerFromCodeName(self, code_name):
        """Get the owner (module or function) from a code name."""
        code_name = decodePythonIdentifierFromC(code_name)

        if "$$$" in code_name:
            module_code_name, _function_code_name = code_name.split("$$$", 1)

            module = self.getModuleFromCodeName(module_code_name)
            return module.getFunctionFromCodeName(code_name)
        else:
            return self.getModuleFromCodeName(code_name)

    def getModuleByName(self, module_name):
        """Get a module by its name."""
        # First check the done modules index for O(1) lookup
        if module_name in self.done_modules_by_name:
            return self.done_modules_by_name[module_name]
            
        # Then check active modules
        for module in self.active_modules:
            if module.getFullName() == module_name:
                return module

        return None

    def addModuleInfluencingCondition(
        self, module_name, plugin_name, condition, control_tags, result
    ):
        """Add information about a plugin condition influencing a module."""
        if module_name not in self.module_influencing_plugins:
            self.module_influencing_plugins[module_name] = OrderedSet()
        self.module_influencing_plugins[module_name].add(
            (plugin_name, "condition-used", (condition, tuple(control_tags), result))
        )

    def addModuleInfluencingVariable(
        self, module_name, config_module_name, plugin_name, variable_name, control_tags, result
    ):
        """Add information about a plugin variable influencing a module."""
        if module_name not in self.module_influencing_plugins:
            self.module_influencing_plugins[module_name] = OrderedSet()
        self.module_influencing_plugins[module_name].add(
            (
                plugin_name,
                "variable-used",
                (variable_name, tuple(control_tags), repr(result), config_module_name),
            )
        )

    def addModuleInfluencingParameter(
        self, module_name, plugin_name, parameter_name, condition_tags_used, result
    ):
        """Add information about a plugin parameter influencing a module."""
        if module_name not in self.module_influencing_plugins:
            self.module_influencing_plugins[module_name] = OrderedSet()
        self.module_influencing_plugins[module_name].add(
            (
                plugin_name,
                "parameter-used",
                (parameter_name, tuple(condition_tags_used), result),
            )
        )

    def addModuleInfluencingDetection(
        self, module_name, plugin_name, detection_name, detection_value
    ):
        """Add information about a plugin detection influencing a module."""
        if module_name not in self.module_influencing_plugins:
            self.module_influencing_plugins[module_name] = OrderedSet()
        self.module_influencing_plugins[module_name].add(
            (plugin_name, "detection", (detection_name, detection_value))
        )

    def getModuleInfluences(self, module_name):
        """Get all plugin influences for a module."""
        return self.module_influencing_plugins.get(module_name, ())

    def addModuleOptimizationTimeInformation(
        self, module_name, pass_number, time_used, micro_passes, merge_counts
    ):
        """Add timing information for module optimization."""
        # Get existing timing info or initialize an empty list
        if module_name in self.module_timing_infos:
            module_timing_info = list(self.module_timing_infos[module_name])
        else:
            module_timing_info = []

        # Do not record cached bytecode loaded timing information, not useful
        # and duplicate, we want the original values.
        if pass_number == 1 and len(module_timing_info) == 1:
            assert micro_passes == 0
            return

        # Create the timing info object
        timing_info = self.ModuleOptimizationTimingInfo(
            pass_number=pass_number,
            time_used=time_used,
            micro_passes=micro_passes,
            merge_counts=merge_counts,
        )
        
        # Append to the list and store back as tuple for immutability
        module_timing_info.append(timing_info)
        self.module_timing_infos[module_name] = tuple(module_timing_info)

    def getModuleOptimizationTimingInfos(self, module_name):
        """Get timing information for module optimization."""
        return self.module_timing_infos.get(module_name, ())

    def setModuleOptimizationTimingInfos(self, module_name, timing_infos):
        """Set timing information for module optimization."""
        self.module_timing_infos[module_name] = [
            self.ModuleOptimizationTimingInfo(*timing_info) for timing_info in timing_infos
        ]

    def getImportedModuleNames(self):
        """Get names of all imported modules."""
        result = OrderedSet()

        for module in self.getDoneModules():
            for used_module in module.getUsedModules():
                module_name = used_module.module_name

                if self.hasDoneModule(module_name):
                    continue

                result.add(module_name)

        return result

    def addImportedModule(self, imported_module):
        """Add a module to the import cache."""
        # Get the absolute path of the module filename
        module_filename = os.path.abspath(imported_module.getFilename())
        full_name = imported_module.getFullName()

        # Handle package directory filenames
        if hasPackageDirFilename(module_filename):
            module_filename = os.path.dirname(module_filename)

        # Create the key for the imported_modules dictionary
        key = (module_filename, full_name)

        # Only notify plugins if this is a new module
        if key not in self.imported_modules:
            from nuitka.plugins.Plugins import Plugins
            Plugins.onModuleDiscovered(imported_module)
        else:
            # Sanity check: the module should be the same object
            assert imported_module is self.imported_modules[key], key

        # Update both caches
        self.imported_modules[key] = imported_module
        self.imported_by_name[full_name] = imported_module

        # We don't expect that to happen.
        assert not imported_module.isMainModule()

    def isImportedModuleByName(self, full_name):
        """Check if a module with the given name is in the import cache."""
        return full_name in self.imported_by_name

    def getImportedModuleByName(self, full_name):
        """Get a module from the import cache by name."""
        return self.imported_by_name[full_name]

    def getImportedModuleByNameAndPath(self, full_name, module_filename):
        """Get a module from the import cache by name and path."""
        if module_filename is None:
            # pyi deps only
            return self.getImportedModuleByName(full_name)

        # For caching we use absolute paths only.
        module_filename = os.path.abspath(module_filename)

        if hasPackageDirFilename(module_filename):
            module_filename = os.path.dirname(module_filename)

        # KeyError is valid result.
        return self.imported_modules[module_filename, full_name]

    def replaceImportedModule(self, old, new):
        """Replace a module in the import cache with another one."""
        for key, value in self.imported_by_name.items():
            if value == old:
                self.imported_by_name[key] = new
                break
        else:
            assert False, (old, new)

        for key, value in self.imported_modules.items():
            if value == old:
                self.imported_modules[key] = new
                break
        else:
            assert False, (old, new)

    def getRecursionDecisions(self):
        """Get all recursion decisions."""
        return self.recursion_decision_cache

    def cacheRecursionDecision(self, key, decision):
        """Cache a recursion decision."""
        self.recursion_decision_cache[key] = decision
        return decision

    def getRecursionDecision(self, key):
        """Get a cached recursion decision."""
        return self.recursion_decision_cache.get(key)


module_registry = Registry()


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