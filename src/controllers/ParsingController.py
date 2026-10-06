import ast
import builtins
 
BUILTIN_NAMES = set(dir(builtins))

class CodeVisitor(ast.NodeVisitor):

    def __init__(self, module_name: str):
        self.module_name = module_name
        self.functions = []
        self.classes = []
        self.imports = []  
        self.calls = []    
        self.current_function = None
 
    def visit_ClassDef(self, node):
        self.classes.append(node.name)
        self.generic_visit(node)
 
    def visit_FunctionDef(self, node):
        full_name = f"{self.module_name}.{node.name}"
        self.functions.append(node.name)
 
        previous_function = self.current_function
        self.current_function = full_name
        self.generic_visit(node)
        self.current_function = previous_function
 
    def visit_ImportFrom(self, node):

        if node.module:
            for alias in node.names:

                self.imports.append(
                    {
                        "imported_name": alias.name,
                        "alias": alias.asname,
                        "source_module": (
                            "." * node.level + node.module
                            if node.level > 0
                            else node.module
                        )
                    }
                )

        self.generic_visit(node)
    
    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and self.current_function:
            called_name = node.func.id
 
            if called_name in self.imports:
                confidence = "EXTRACTED"
                source_module = self.imports[called_name]
            elif called_name in BUILTIN_NAMES:
                confidence = "BUILTIN"
                source_module = "python.builtins"
            else:
                confidence = "INFERRED"
                source_module = self.module_name
 
            self.calls.append({
                "caller": self.current_function,
                "callee": called_name,
                "confidence": confidence,
                "source_module": source_module
            })
        self.generic_visit(node)
 
 
