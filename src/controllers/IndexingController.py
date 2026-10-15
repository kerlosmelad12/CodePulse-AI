import logging
from git import Repo
from pathlib import Path
from .BaseController import BaseController
from pathlib import Path
from utils.graphhiy import (find_graph_json,run_graphify,
    get_nodes_and_links
)

logger = logging.getLogger(__name__)


class IndexingController(BaseController):

    def __init__(self):
        super().__init__()


    def clone_url(self, identifier: str, project_dir: str) -> bool:
        try:
            Repo.clone_from(identifier, project_dir)
            return True
        except Exception as e:
            raise RuntimeError(f"Failed to clone repository: {e}")


    def analyze_project(self, project_path: str | Path, graphify_path: str | None = None,
                        out_dir: str | Path | None = None,
                        project_hash: str = "default",
                        no_cluster: bool = False,
                        max_workers: int | None = None, ) -> tuple[list[dict], list[dict]]:
        
        
        project_path = Path(project_path).resolve()
        if not project_path.is_dir():
            raise FileNotFoundError(f"Project not found: {project_path}")

        if out_dir is None:
            out_dir = project_path / ".graphify"
        else:
            out_dir = Path(out_dir)

        graph_path = find_graph_json(out_dir)

        if graph_path is None:
            graph_path = run_graphify(
                project_path=project_path,
                graphify_path=graphify_path,
                out_dir=out_dir,
                no_cluster=no_cluster,
                max_workers=max_workers,
            )

        return get_nodes_and_links(graph_path, project_hash)