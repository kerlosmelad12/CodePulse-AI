import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from helper.config import get_settings
app_settings=get_settings()

logger = logging.getLogger(__name__)




def resolve_graphify(graphify_path: str | None) -> str:
    if graphify_path and os.path.isfile(graphify_path):
        return graphify_path

    found = shutil.which(graphify_path or "graphify")
    if found:
        return found

    raise FileNotFoundError(
        f"graphify executable not found (GRAPHIFY_PATH={graphify_path!r}). "
        "Install it with: uv tool install graphifyy"
    )


def find_graph_json(out_dir: str | Path) -> Path | None:
    candidates = []
    for root, _, files in os.walk(out_dir):
        if "graph.json" in files:
            candidates.append(Path(root) / "graph.json")

    return max(candidates, key=lambda p: p.stat().st_mtime) if candidates else None


def run_graphify(project_path: str | Path,graphify_path: str | None,
                 out_dir: str | Path,timeout: int = app_settings.DEFAULT_TIMEOUT,
                 no_cluster: bool = False, 
                 max_workers: int | None = None) -> Path:

    project_path = Path(project_path).resolve()
    if not project_path.is_dir():
        raise NotADirectoryError(f"Project directory not found: {project_path}")

    executable = resolve_graphify(graphify_path)
    os.makedirs(out_dir, exist_ok=True)

    command = [executable, "extract", str(project_path), "--code-only", "--out", str(out_dir), "--timing"]
    if no_cluster:
        command.append("--no-cluster")
    if max_workers:
        command += ["--max-workers", str(max_workers)]

    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"graphify timed out after {timeout} seconds")

    if completed.returncode != 0:
        details = (completed.stderr or completed.stdout or "").strip()[-800:]
        raise RuntimeError(f"graphify failed (exit code {completed.returncode}): {details}")

    logger.info("graphify output:\n%s", (completed.stdout or "").strip()[-1500:])

    graph_path = find_graph_json(out_dir)
    if graph_path is None:
        raise FileNotFoundError(f"graphify finished but no graph.json was found under {out_dir}")

    return graph_path


def load_graph_file(graph_path: str | Path) -> dict:
    with open(graph_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("graph.json must contain a JSON object")

    return data


def get_nodes_and_links(graph_path: str | Path, project_hash: str) -> tuple[list[dict], list[dict]]:

    graph = load_graph_file(graph_path)

    nodes = graph.get("nodes") or []
    links = graph.get("links") or graph.get("edges") or []

    if not isinstance(nodes, list) or not isinstance(links, list):
        raise ValueError("'nodes' and 'links'/'edges' must be lists")

    prefixed_nodes = []
    for node in nodes:
        if node.get("id") is None:
            continue
        prefixed_nodes.append({**node, "id": f"{project_hash}:{node['id']}", "project_hash": project_hash})

    prefixed_links = []
    for link in links:
        if link.get("source") is None or link.get("target") is None:
            continue
        prefixed_links.append(
            {
                **link,
                "source": f"{project_hash}:{link['source']}",
                "target": f"{project_hash}:{link['target']}",
                "project_hash": project_hash,
            }
        )

    logger.info("graph loaded: %d nodes, %d links", len(prefixed_nodes), len(prefixed_links))
    return prefixed_nodes, prefixed_links