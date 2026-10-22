import os
from models.enums.CodeEnums import CodeLanguage
import re
from collections import defaultdict, deque

NODE_TYPES = {"rationale", "code"}


def get_nodes_by_file(nodes: list[dict]) -> dict[str, list[dict]]:
    result = defaultdict(list)
    for node in nodes:
        if node.get("file_type") not in NODE_TYPES or not node.get("source_file"):
            continue
        m = re.search(r"\d+", str(node.get("source_location") or ""))
        if not m:
            continue
        result[node["source_file"]].append({
            "id": node.get("id"),
            "name": node.get("name"),
            "start_line": int(m.group()),
        })
    return dict(result)


def find_node_at_line(root, start_line: int, types=None, ignore_types=frozenset()):
    target = start_line - 1
    queue = deque([root])
    while queue:
        node = queue.popleft()
        if node.type in ignore_types:
            continue
        if node.start_point[0] == target and (types is None or node.type in types):
            return node
        if node.start_point[0] <= target <= node.end_point[0]:
            queue.extend(node.children)
    return None


def load_single_file(project_path,source_file: str):
    try:
        file_path=os.path.join(project_path,source_file)
        with open(file_path, "r", encoding="utf-8") as f:
            return  f.read()
    except Exception:
        return None


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


