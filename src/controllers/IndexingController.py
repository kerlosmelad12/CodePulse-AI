import hashlib
import importlib
import logging
from pathlib import Path
from typing import List

from git import Repo
from tree_sitter import Language, Parser

from .BaseController import BaseController
from utils.graphhiy import find_graph_json, run_graphify, get_nodes_and_links
from utils.Chunking import (
    get_nodes_file_paths, load_single_file, get_file_langeauge, extract_subtrees,
)
from models.enums.CodeEnums import CodeLanguage
from models.db_schemas.ChunkDataNode import CodeChunk
from models.db_schemas.Neo4jNode import CodeNode


logger = logging.getLogger(__name__)

IGNORE_TYPES = frozenset({"comment", "line_comment", "block_comment"})


class IndexingController(BaseController):

    def __init__(self):
        super().__init__()
        self.parsers = self._build_parsers()

    @staticmethod
    def _build_parsers() -> dict:
        parsers = {}
        for lang in CodeLanguage:
            try:
                module = importlib.import_module(lang.grammar_module)
                parsers[lang] = Parser(Language(module.language()))
            except ImportError:
                logger.info(f"Grammar not installed, skipping: {lang.name}")
            except Exception:
                logger.exception(f"Failed to load grammar: {lang.name}")
        return parsers

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
                        max_workers: int | None = None) -> tuple[list[dict], list[dict]]:

        project_path = Path(project_path).resolve()
        if not project_path.is_dir():
            raise FileNotFoundError(f"Project not found: {project_path}")

        out_dir = project_path / ".graphify" if out_dir is None else Path(out_dir)

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

    def chuncking_code(self, code_nodes: List[dict], project_path: str, project_hash: str) -> dict:
        chunks = []
        for path in get_nodes_file_paths(project_path, code_nodes):
            try:
                file_path, code_content = load_single_file(path)
                if code_content is None:
                    logger.warning(f"Could not read file: {file_path}")
                    continue

                language = get_file_langeauge(file_path)
                parser = self.parsers.get(language)
                if parser is None:
                    logger.debug(f"Skipping unsupported file: {file_path}")
                    continue

                source = code_content.encode("utf-8")
                tree = parser.parse(source)

                nodes = extract_subtrees(
                    tree.root_node,
                    terminal=language.chunk_node_types,
                    ignore_types=IGNORE_TYPES,
                )

                seen_text = set()
                for node in nodes:
                    text = source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
                    if text in seen_text:
                        continue
                    
                    seen_text.add(text)

                    name_node = node.child_by_field_name("name")
                    
                    # Generate a deterministic, non-null unique string ID
                    start_line = node.start_point[0] + 1
                    end_line = node.end_point[0] + 1
                    raw_id_str = f"{file_path}:{start_line}:{end_line}:{node.type}"
                    node_id = hashlib.sha256(raw_id_str.encode("utf-8")).hexdigest()

                    chunks.append(CodeChunk(
                        project_hash=project_hash,
                        name=source[name_node.start_byte:name_node.end_byte]
                        .decode("utf-8", errors="replace") if name_node else None,
                        chunk_type=node.type,
                        language=language.value,
                        file_path=file_path,
                        node_id=node_id,  # Guaranteed unique string, never null
                        file_hash=hashlib.sha256(source).hexdigest(),
                        text=text,
                        end_line=end_line,
                        start_line=start_line,
                    ))

            except Exception:
                logger.exception(f"Error while chunking {path}")

        return chunks

    def create_chunks_links(self,code_nodes:CodeNode,chunk_nodes:CodeChunk):
        for code_node in code_nodes:
            pass
