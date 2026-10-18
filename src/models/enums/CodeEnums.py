from enum import Enum
from pathlib import Path
from typing import Optional


class CodeLanguage(Enum):
    PYTHON = "python"
    JAVA = "java"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    GO = "go"
    RUST = "rust"
    C = "c"
    CPP = "cpp"
    CSHARP = "csharp"
    PHP = "php"
    RUBY = "ruby"

    @property
    def extensions(self) -> tuple[str, ...]:
        return _EXTENSIONS[self]

    @property
    def chunk_node_types(self) -> frozenset[str]:
        return _CHUNK_NODE_TYPES[self]

    @property
    def grammar_module(self) -> str:
        return _GRAMMAR_MODULES[self]

    @classmethod
    def from_path(cls, file_path: str) -> Optional["CodeLanguage"]:
        return _EXT_TO_LANGUAGE.get(Path(file_path).suffix.lower())


_EXTENSIONS = {
    CodeLanguage.PYTHON: (".py",),
    CodeLanguage.JAVA: (".java",),
    CodeLanguage.JAVASCRIPT: (".js", ".jsx", ".mjs", ".cjs"),
    CodeLanguage.TYPESCRIPT: (".ts",),
    CodeLanguage.GO: (".go",),
    CodeLanguage.RUST: (".rs",),
    CodeLanguage.C: (".c", ".h"),
    CodeLanguage.CPP: (".cpp", ".cc", ".cxx", ".hpp", ".hh"),
    CodeLanguage.CSHARP: (".cs",),
    CodeLanguage.PHP: (".php",),
    CodeLanguage.RUBY: (".rb",),
}

_CHUNK_NODE_TYPES = {
    CodeLanguage.PYTHON: frozenset({"function_definition", "class_definition","decorated_definition"}),
    CodeLanguage.JAVA: frozenset({
        "class_declaration", "interface_declaration", "enum_declaration",
        "method_declaration", "constructor_declaration",
    }),
    CodeLanguage.JAVASCRIPT: frozenset({
        "function_declaration", "class_declaration", "method_definition",
        "generator_function_declaration",
    }),
    CodeLanguage.TYPESCRIPT: frozenset({
        "function_declaration", "class_declaration", "method_definition",
        "interface_declaration",
    }),
    CodeLanguage.GO: frozenset({
        "function_declaration", "method_declaration", "type_declaration",
    }),
    CodeLanguage.RUST: frozenset({
        "function_item", "impl_item", "struct_item", "enum_item", "trait_item",
    }),
    CodeLanguage.C: frozenset({"function_definition", "struct_specifier"}),
    CodeLanguage.CPP: frozenset({
        "function_definition", "class_specifier", "struct_specifier",
    }),
    CodeLanguage.CSHARP: frozenset({
        "class_declaration", "interface_declaration",
        "method_declaration", "constructor_declaration",
    }),
    CodeLanguage.PHP: frozenset({
        "function_definition", "class_declaration", "method_declaration",
    }),
    CodeLanguage.RUBY: frozenset({"method", "class", "module"}),
}

_GRAMMAR_MODULES = {
    CodeLanguage.PYTHON: "tree_sitter_python",
    CodeLanguage.JAVA: "tree_sitter_java",
    CodeLanguage.JAVASCRIPT: "tree_sitter_javascript",
    CodeLanguage.TYPESCRIPT: "tree_sitter_typescript",
    CodeLanguage.GO: "tree_sitter_go",
    CodeLanguage.RUST: "tree_sitter_rust",
    CodeLanguage.C: "tree_sitter_c",
    CodeLanguage.CPP: "tree_sitter_cpp",
    CodeLanguage.CSHARP: "tree_sitter_c_sharp",
    CodeLanguage.PHP: "tree_sitter_php",
    CodeLanguage.RUBY: "tree_sitter_ruby",
}

_EXT_TO_LANGUAGE = {
    ext: lang for lang, exts in _EXTENSIONS.items() for ext in exts
}