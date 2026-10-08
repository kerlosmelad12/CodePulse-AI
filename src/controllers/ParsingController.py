import ast
import builtins

BUILTIN_NAMES = set(dir(builtins))


class CodeVisitor(ast.NodeVisitor):

    def __init__(self, module_name: str):
        self.module_name = module_name
        self.functions = []
        self.classes = []
        self.class_bases = {}
        self.methods = []
        self.imports = []
        self.import_lookup = {}
        self.calls = []
        self.scope = []

    def _qualname(self, name: str) -> str:
        return ".".join([scope_name for _, scope_name in self.scope] + [name])

    def _current_function(self) -> str | None:
        for i in range(len(self.scope) - 1, -1, -1):
            if self.scope[i][0] == "function":
                return ".".join(scope_name for _, scope_name in self.scope[: i + 1])
        return None

    def visit_ClassDef(self, node):
        qualname = self._qualname(node.name)
        self.classes.append(qualname)
        self.class_bases[qualname] = [ast.unparse(base) for base in node.bases]

        self.scope.append(("class", node.name))
        self.generic_visit(node)
        self.scope.pop()

    def visit_FunctionDef(self, node):
        qualname = self._qualname(node.name)
        self.functions.append(qualname)

        if self.scope and self.scope[-1][0] == "class":
            self.methods.append(
                {
                    "class": ".".join(scope_name for _, scope_name in self.scope),
                    "method": qualname,
                }
            )

        self.scope.append(("function", node.name))
        self.generic_visit(node)
        self.scope.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Import(self, node):
        for alias in node.names:
            imported_name = alias.name.split(".")[-1]

            self.imports.append(
                {
                    "imported_name": imported_name,
                    "alias": alias.asname,
                    "source_module": alias.name,
                }
            )

            self.import_lookup[
                alias.asname or imported_name
            ] = (
                alias.name,
                imported_name,
            )

        self.generic_visit(node)

    def visit_Call(self, node):
        caller = self._current_function()

        if isinstance(node.func, ast.Name) and caller:
            called_name = node.func.id

            if called_name in self.import_lookup:
                source_module, callee = self.import_lookup[called_name]
                confidence = "EXTRACTED"
            elif called_name in BUILTIN_NAMES:
                source_module, callee = "python.builtins", called_name
                confidence = "BUILTIN"
            else:
                source_module, callee = self.module_name, called_name
                confidence = "INFERRED"

            self.calls.append(
                {
                    "caller": caller,
                    "callee": callee,
                    "confidence": confidence,
                    "source_module": source_module,
                }
            )
        self.generic_visit(node)