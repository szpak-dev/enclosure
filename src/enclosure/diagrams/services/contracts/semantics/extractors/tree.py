from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import cast

import mermaiden.diagrams.treeview.diagram
from mermaiden.diagrams import domain
from mermaiden.diagrams.treeview.elements import TreeItem
from mermaiden.diagrams.treeview.relations import TreeBranch
from wireup import injectable

from ..model import DiagramContractPath, DiagramContractSemantics
from .base import DiagramSemanticExtractor


@injectable(as_type=DiagramSemanticExtractor, qualifier="tree-contract")
@dataclass(frozen=True)
class TreeSemanticExtractor(DiagramSemanticExtractor):
    kind: str = field(default="treeView-beta", init=False)
    order: int = field(default=10, init=False)

    def extract(self, diagram: domain.DiagramModel) -> DiagramContractSemantics:
        tree = cast(mermaiden.diagrams.treeview.diagram.TreeView, diagram)
        items = tuple(cast(TreeItem, item) for item in tree.walk_elements(""))
        branches = tuple(cast(TreeBranch, relation) for relation in tree.find_relations(""))
        parents = {branch.child_id: branch.parent_id for branch in branches}
        labels = {item.id: item.label for item in items}
        paths: list[DiagramContractPath] = []
        for item in items:
            components = [item.label]
            parent_id = parents.get(item.id, "")
            while parent_id:
                components.insert(0, labels[parent_id])
                parent_id = parents.get(parent_id, "")
            paths.append(
                DiagramContractPath(
                    element_id=item.id,
                    path=str(PurePosixPath(*components)),
                    kind=item.item_type.value,
                )
            )
        return DiagramContractSemantics(
            kind=self.kind,
            paths=tuple(sorted(paths, key=lambda item: (item.path, item.element_id))),
            symbols=(),
            relations=(),
        )
