#     Copyright 2026, Kay Hayen, mailto:kay.hayen@gmail.com find license text at end of file


"""Nodes for switch-like dispatch of match statements."""

import ast

from nuitka.optimizations.TraceCollections import TraceCollectionBranch

from .NodeBases import StatementBase


class StatementSwitch(StatementBase):
    """Dispatch between mutually exclusive match case bodies."""

    kind = "STATEMENT_SWITCH"

    named_children = (
        "subject",
        "conditions|tuple+setter",
        "branches|tuple+setter",
        "default_branch|statements_or_none+setter",
    )

    __slots__ = ("case_values",)

    def __init__(
        self,
        subject,
        conditions,
        branches,
        case_values,
        source_ref,
        default_branch=None,
    ):
        assert type(conditions) is tuple
        assert type(branches) is tuple
        assert len(conditions) == len(branches) == len(case_values)
        assert all(type(values) is tuple for values in case_values)

        subject.parent = self
        for condition in conditions:
            condition.parent = self
        for branch in branches:
            branch.parent = self
        if default_branch is not None:
            default_branch.parent = self

        self.subnode_subject = subject
        self.subnode_conditions = conditions
        self.subnode_branches = branches
        self.subnode_default_branch = default_branch
        self.case_values = case_values

        StatementBase.__init__(self, source_ref)

    def setChildConditions(self, value):
        assert type(value) is tuple
        for condition in value:
            condition.parent = self
        self.subnode_conditions = value

    def getVisitableNodes(self):
        return (
            (self.subnode_subject,)
            + self.subnode_conditions
            + self.subnode_branches
            + ((self.subnode_default_branch,) if self.subnode_default_branch else ())
        )

    def getVisitableNodesNamed(self):
        return (
            ("subject", self.subnode_subject),
            ("conditions", self.subnode_conditions),
            ("branches", self.subnode_branches),
            ("default_branch", self.subnode_default_branch),
        )

    def replaceChild(self, old_node, new_node):
        if old_node is self.subnode_subject:
            new_node.parent = self
            self.subnode_subject = new_node
            return

        if old_node in self.subnode_conditions:
            conditions = list(self.subnode_conditions)
            conditions[conditions.index(old_node)] = new_node
            self.setChildConditions(tuple(conditions))
            return

        if old_node in self.subnode_branches:
            branches = list(self.subnode_branches)
            branches[branches.index(old_node)] = new_node
            self.setChildBranches(tuple(branches))
            return

        if old_node is self.subnode_default_branch:
            self.setChildDefaultBranch(new_node)
            return

        raise AssertionError("Didn't find child", old_node, "in", self)

    def setChildBranches(self, value):
        assert type(value) is tuple
        for branch in value:
            branch.parent = self
        self.subnode_branches = value

    def setChildDefaultBranch(self, value):
        if value is not None:
            value.parent = self
        self.subnode_default_branch = value

    def getDetailsForDisplay(self):
        return {"case_values": self.case_values}

    @classmethod
    def fromXML(cls, provider, source_ref, **args):
        args["case_values"] = ast.literal_eval(args["case_values"])
        return cls(source_ref=source_ref, **args)

    def computeStatement(self, trace_collection):
        conditions = []
        branches = []
        branch_collections = [trace_collection]

        for count, condition in enumerate(self.subnode_conditions):
            condition = trace_collection.onExpression(condition)
            conditions.append(condition)

            branch = self.subnode_branches[count]
            branch_collection = TraceCollectionBranch(
                parent=trace_collection, name="switch case branch"
            )
            branch = branch_collection.computeBranch(branch=branch)

            if branch is not None and branch.isStatementAborting():
                branch_collection = None

            branches.append(branch)
            if branch_collection is not None:
                branch_collections.append(branch_collection)

        self.setChildConditions(tuple(conditions))
        self.setChildBranches(tuple(branches))

        default_branch = self.subnode_default_branch
        if default_branch is not None:
            branch_collection = TraceCollectionBranch(
                parent=trace_collection, name="switch default branch"
            )
            default_branch = branch_collection.computeBranch(branch=default_branch)
            if default_branch is not None and default_branch.isStatementAborting():
                branch_collection = None
            if branch_collection is not None:
                branch_collections.append(branch_collection)
        self.setChildDefaultBranch(default_branch)

        if len(branch_collections) > 1:
            trace_collection.mergeMultipleBranches(branch_collections)

        return self, None, None

    def mayReturn(self):
        return any(branch.mayReturn() for branch in self.subnode_branches) or (
            self.subnode_default_branch is not None
            and self.subnode_default_branch.mayReturn()
        )

    def mayBreak(self):
        return any(branch.mayBreak() for branch in self.subnode_branches) or (
            self.subnode_default_branch is not None
            and self.subnode_default_branch.mayBreak()
        )

    def mayContinue(self):
        return any(branch.mayContinue() for branch in self.subnode_branches) or (
            self.subnode_default_branch is not None
            and self.subnode_default_branch.mayContinue()
        )

    def isStatementAborting(self):
        return (
            self.subnode_default_branch is not None
            and self.subnode_default_branch.isStatementAborting()
        )

    def mayRaiseException(self, exception_type):
        return (
            any(
                condition.mayRaiseException(exception_type)
                for condition in self.subnode_conditions
            )
            or any(
                branch.mayRaiseException(exception_type)
                for branch in self.subnode_branches
            )
            or (
                self.subnode_default_branch is not None
                and self.subnode_default_branch.mayRaiseException(exception_type)
            )
        )

    def needsFrame(self):
        return any(branch.needsFrame() for branch in self.subnode_branches) or (
            self.subnode_default_branch is not None
            and self.subnode_default_branch.needsFrame()
        )

    def collectVariableAccesses(self, emit_variable):
        self.subnode_subject.collectVariableAccesses(emit_variable)
        for condition in self.subnode_conditions:
            condition.collectVariableAccesses(emit_variable)
        for branch in self.subnode_branches:
            branch.collectVariableAccesses(emit_variable)
        if self.subnode_default_branch is not None:
            self.subnode_default_branch.collectVariableAccesses(emit_variable)

    def getCloneArgs(self):
        return {
            "subject": self.subnode_subject.makeClone(),
            "conditions": tuple(
                condition.makeClone() for condition in self.subnode_conditions
            ),
            "branches": tuple(branch.makeClone() for branch in self.subnode_branches),
            "case_values": self.case_values,
            "default_branch": (
                self.subnode_default_branch.makeClone()
                if self.subnode_default_branch is not None
                else None
            ),
            "source_ref": self.source_ref,
        }

    def finalize(self):
        del self.parent
        self.subnode_subject.finalize()
        del self.subnode_subject
        for condition in self.subnode_conditions:
            condition.finalize()
        del self.subnode_conditions
        for branch in self.subnode_branches:
            branch.finalize()
        del self.subnode_branches
        if self.subnode_default_branch is not None:
            self.subnode_default_branch.finalize()
        del self.subnode_default_branch
        del self.case_values
