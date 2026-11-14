import hashlib
import importlib
import logging
from pathlib import Path
from typing import List
from git import Repo
from tree_sitter import Language, Parser

from models.db_schemas.ChunkRelation import ChunkLink

from .BaseController import BaseController
from utils.graphhiy import find_graph_json, run_graphify, get_nodes_and_links
from utils.Chunking import (
    extract_subtrees, get_nodes_by_file, load_single_file, get_file_langeauge, find_node_at_line, residual_text,
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
            Repo.clone_from(identifier, project_dir, depth=1, single_branch=True, branch=branch)
            repo = Repo(project_dir)
            indexed_branch = repo.active_branch.name
            indexed_commit = repo.head.commit.hexsha
            return True,indexed_branch, indexed_commit
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

    def chuncking_code(self, code_nodes, project_path, project_hash):
        chunks, links = [], []

        for source_file, file_nodes in get_nodes_by_file(code_nodes).items():
            try:
                code_content = load_single_file(project_path, source_file)
                language = get_file_langeauge(source_file)
                parser = self.parsers.get(language)
                if code_content is None or parser is None:
                    continue

                source = code_content.encode("utf-8")
                tree = parser.parse(source)
                file_hash = hashlib.sha256(source).hexdigest()
                file_path = f"{project_hash}/{source_file}"
                types = language.chunk_node_types

                def make_chunk(ts_node, text, name, kind):
                    s, e = ts_node.start_point[0] + 1, ts_node.end_point[0] + 1
                    raw = f"{file_path}:{s}:{e}:{ts_node.type}:{kind}"
                    return CodeChunk(
                        project_hash=project_hash, name=name, chunk_type=ts_node.type,
                        language=language.value, file_path=file_path,
                        node_id=hashlib.sha256(raw.encode()).hexdigest(),
                        file_hash=file_hash, text=text, start_line=s, end_line=e,
                    )

                # 1) كل graphify node -> ts_node (owner). أكتر من node ممكن يشاركوا نفس الـ ts_node
                owners = {}
                for item in file_nodes:
                    ts_node = find_node_at_line(tree.root_node, item["start_line"],
                                                types=types, ignore_types=IGNORE_TYPES)
                    if ts_node is None:
                        continue
                    key = (ts_node.start_byte, ts_node.end_byte, ts_node.type)
                    owners.setdefault(key, (ts_node, []))[1].append(item)

                # 2) chunk لكل owner بعد استبعاد الأولاد
                for ts_node, items in owners.values():
                    kids = [k for ch in ts_node.children
                            for k in extract_subtrees(ch, types, IGNORE_TYPES)]
                    text = residual_text(ts_node, source, kids)
                    chunk = make_chunk(ts_node, text, items[0]["name"], "body")
                    chunks.append(chunk)
                    links += [ChunkLink(source=i["id"], target=chunk.node_id,
                                        source_file=source_file) for i in items]   # كلهم يتربطوا

                # 3) chunk للـ file header (imports + top-level code)
                top = [k for ch in tree.root_node.children
                    for k in extract_subtrees(ch, types, IGNORE_TYPES)]
                header = residual_text(tree.root_node, source, top).strip()
                file_node = next((n for n in file_nodes if n["name"] == Path(source_file).name), None)
                if header and file_node:
                    chunk = make_chunk(tree.root_node, header, file_node["name"], "file_header")
                    chunks.append(chunk)
                    links.append(ChunkLink(source=file_node["id"], target=chunk.node_id,
                                        source_file=source_file))
            except Exception:
                logger.exception(f"Error while chunking {source_file}")

        return chunks, links