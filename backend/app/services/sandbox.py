import ast
import sys
import io
import traceback
import threading
import queue
from typing import Dict, Any, List, Optional

# Strict whitelist of modules that agents are permitted to import
SAFE_MODULES = {
    "math",
    "json",
    "datetime",
    "random",
    "re",
    "collections",
    "statistics",
    "itertools",
    "urllib.parse"
}

# Strict whitelist of built-in functions
SAFE_BUILTINS = {
    "abs", "all", "any", "bin", "bool", "chr", "dict", "divmod", "enumerate",
    "filter", "float", "format", "frozenset", "hash", "hex", "int", "len",
    "list", "map", "max", "min", "next", "oct", "ord", "pow", "print",
    "range", "repr", "reversed", "round", "set", "slice", "sorted", "str",
    "sum", "tuple", "type", "zip", "Exception", "ValueError", "TypeError",
    "KeyError", "IndexError", "RuntimeError"
}

class UnsafeCodeError(Exception):
    """Raised when Python code fails static AST safety analysis."""
    pass


class ASTSafetyChecker(ast.NodeVisitor):
    """
    AST Visitor that statically analyzes Python code to ensure it meets
    strict sandbox safety requirements.
    """
    def __init__(self):
        self.errors: List[str] = []

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            base_module = alias.name.split('.')[0]
            if base_module not in SAFE_MODULES:
                self.errors.append(f"Import of module '{alias.name}' is forbidden.")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if not node.module:
            self.errors.append("Relative imports are forbidden.")
            return
        
        base_module = node.module.split('.')[0]
        if base_module not in SAFE_MODULES:
            self.errors.append(f"Import from module '{node.module}' is forbidden.")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        # Prevent calling forbidden builtins like eval(), exec(), open(), etc.
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            if func_name not in SAFE_BUILTINS and func_name in __builtins__.__dict__:
                self.errors.append(f"Call to built-in function '{func_name}' is forbidden.")
        
        # Prevent indirect imports or dynamic execution hacks via getattr, setattr
        elif isinstance(node.func, ast.Attribute):
            attr_name = node.func.attr
            if attr_name in ("__import__", "eval", "exec"):
                self.errors.append(f"Call to attribute '{attr_name}' is forbidden.")
        
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        # Prevent access to private and magic variables (e.g. __class__, __subclasses__)
        if node.attr.startswith("__"):
            self.errors.append(f"Access to private attribute '{node.attr}' is forbidden.")
        self.generic_visit(node)


def check_code_safety(code: str) -> None:
    """
    Statically analyzes code. Raises UnsafeCodeError if violating rules.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise UnsafeCodeError(f"Syntax Error in Python code: {e}")

    checker = ASTSafetyChecker()
    checker.visit(tree)

    if checker.errors:
        raise UnsafeCodeError("Security Sandbox Violation: " + " | ".join(checker.errors))


def execute_restricted(code: str, inputs: Optional[Dict[str, Any]] = None, timeout: float = 5.0) -> Dict[str, Any]:
    """
    Executes Python code in a restricted AST sandbox environment.
    Captures stdout, stderr, and variables. Enforces execution timeout.
    """
    # 1. Statically verify AST safety
    check_code_safety(code)

    inputs = inputs or {}
    result_queue = queue.Queue()

    def worker():
        # Setup standard output streams redirect
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        redirected_out = io.StringIO()
        redirected_err = io.StringIO()
        sys.stdout = redirected_out
        sys.stderr = redirected_err

        # Build heavily restricted execution namespace
        exec_globals = {
            "__builtins__": {k: v for k, v in __builtins__.__dict__.items() if k in SAFE_BUILTINS}
        }
        
        # Inject inputs into locals context
        exec_locals = {k: v for k, v in inputs.items()}

        success = False
        error_msg = None
        
        try:
            # Compile and execute the code
            compiled = compile(code, "<sandbox>", "exec")
            exec(compiled, exec_globals, exec_locals)
            success = True
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        finally:
            # Restore stdout/stderr
            sys.stdout = old_stdout
            sys.stderr = old_stderr

        # Capture outputs
        captured_stdout = redirected_out.getvalue()
        captured_stderr = redirected_err.getvalue()

        # Exclude internal variables from output dict
        returned_locals = {
            k: v for k, v in exec_locals.items() 
            if not k.startswith("_") and k not in inputs
        }

        result_queue.put({
            "success": success,
            "stdout": captured_stdout,
            "stderr": captured_stderr,
            "outputs": returned_locals,
            "error": error_msg
        })

    # Run execution in a separate thread for timeout enforcement
    thread = threading.Thread(target=worker)
    thread.daemon = True
    thread.start()
    thread.join(timeout=timeout)

    if thread.is_alive():
        # Note: Thread is daemonized, so it won't block server shutdown, but we terminate early
        return {
            "success": False,
            "stdout": "",
            "stderr": "",
            "outputs": {},
            "error": f"TimeoutError: Code execution exceeded the safe limit of {timeout} seconds."
        }

    try:
        return result_queue.get_nowait()
    except queue.Empty:
        return {
            "success": False,
            "stdout": "",
            "stderr": "",
            "outputs": {},
            "error": "Unknown sandbox failure."
        }
