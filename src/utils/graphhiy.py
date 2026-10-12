import json
import shutil
import subprocess
from pathlib import Path
import os


def find_graphify(graphify_path:str) -> bool:
    return os.path.exists(graphify_path)


def project_check_exist(project_path: str | Path) -> bool:
    path = Path(project_path).resolve()
    return path.is_dir()


def find_graph_json(project_path: str | Path) -> Path | None:
    project_path = Path(project_path).resolve()

    if not project_path.is_dir():
        return None

    graph_path = project_path / "graphify-out" / "graph.json"

    if graph_path.is_file():
        return graph_path

    return None


def run_graphify(project_path: str | Path , graphify_path:str) -> bool:
    project_path = Path(project_path).resolve()

    if not project_path.is_dir():
        raise NotADirectoryError(
            f"Project directory not found: {project_path}"
        )

    if not find_graphify(graphify_path):
        return None

    try:
        subprocess.run(
            [
                graphify_path,
                "extract",
                str(project_path),
                "--code-only",
            ],
            cwd=str(project_path),
            check=True,
        )
        return True

    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"Graphify extraction failed with exit code {e.returncode}"
        ) from e


def load_graph_file(project_path: str | Path) -> dict:
    graph_file = find_graph_json(project_path)

    if graph_file is None:
        raise FileNotFoundError(
            f"Graph file not found inside: {project_path}"
        )

    with graph_file.open("r", encoding="utf-8") as file:
        return json.load(file)


def get_nodes_and_links(project_path: str):
    graph = load_graph_file(project_path)

    nodes = graph.get("nodes", [])
    links = graph.get("links", graph.get("edges", []))

    if not isinstance(nodes, list):
        raise ValueError("'nodes' must be a list")

    if not isinstance(links, list):
        raise ValueError("'links' or 'edges' must be a list")

    print(f"Nodes: {len(nodes)}")
    print(f"Links: {len(links)}")

    if nodes:
        print("First node:", nodes[0])

    if links:
        print("First link:", links[0])

    return nodes, links