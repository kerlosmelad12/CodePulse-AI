import os
from collections import deque
from pathlib import Path

from models.enums.CodeEnums import CodeLanguage


def get_nodes_file_paths(project_path, nodes: list[dict]) -> list[str]:
    node_labels = {"rationale", "code"}
    paths = (
        os.path.join(project_path, node["source_file"])
        for node in nodes
        if node.get("file_type") in node_labels and node.get("source_file")
    )
    return [p for p in dict.fromkeys(paths) if os.path.isfile(p)]


def load_single_file(file_path: str):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return file_path, f.read()
    except Exception:
        return file_path, None


def get_file_langeauge(file_path: str):
    return CodeLanguage.from_path(file_path)


def extract_subtrees(root, terminal, ignore_types=frozenset(), nested: bool = False):

    results = []
    queue = deque([root])

    while queue:
        node = queue.popleft()

        if node.type in ignore_types:
            continue

        if node.type in terminal:
            results.append(node)
            if not nested:
                continue

        queue.extend(node.children)

    results.sort(key=lambda n: n.start_byte)
    return results

def split_large_node(node, source: bytes, max_chars: int = 1500):
    text = source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
    if len(text) <= max_chars:
        return [node]

    children = node.named_children
    if not children:
        return [node]

    parts = []
    for child in children:
        parts.extend(split_large_node(child, source, max_chars))
    return parts


