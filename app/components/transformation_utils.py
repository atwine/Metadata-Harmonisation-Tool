import numpy as np
import ast
import operator

def generic_catagorical_conversion(x, dictionary_str):
    """
    Converts a value using a categorical dictionary.

    Args:
        x (any): The value to convert.
        dictionary_str (str): The dictionary as a string.

    Returns:
        any: The converted value or NaN if conversion fails.
    """
    dictionary_init = eval(dictionary_str)
    dictionary = {str(key): value for key, value in dictionary_init.items()} # convert all keys to string dtype
    x = str(x)
    if x in list(dictionary):
        out = dictionary[x]
        if not out == None:
            return out
        else:
            return np.nan
    else:
        return np.nan

def dtype_conversion(x, dtype):
    """
    Converts a value to a specified data type.

    Args:
        x (any): The value to convert.
        dtype (str): The target data type.

    Returns:
        any: The converted value or NaN if conversion fails.
    """
    try:
        if dtype == 'string':
            return str(x)
        elif dtype == 'str':
            return str(x)    
        elif dtype == 'float':
            return float(x)
        elif dtype == 'integer':
            return int(x)
        elif dtype == 'int':
            return int(x)
        elif dtype == 'boolean':
            return bool(x)
        elif dtype == 'other':
            return x
    except:
        return np.nan

def generic_direct_conversion(x, x_str, source_dtype, target_dtype):
    """
    Performs a direct conversion of a value.

    Args:
        x (any): The value to convert.
        x_str (str): The conversion expression as a string.
        source_dtype (str): The source data type.
        target_dtype (str): The target data type.

    Returns:
        any: The converted value.
    """
    # Convert to the expected source dtype first
    x = dtype_conversion(x, source_dtype)
    # Use SafeEvaluator to securely evaluate the user-provided expression with context variable 'x'
    evaluator = SafeEvaluator()
    x = evaluator.eval_expression(x_str, {"x": x})
    # Convert to the requested target dtype before returning
    return dtype_conversion(x, target_dtype)

# ---- Safe evaluation utilities (added to replace unsafe eval in direct conversions) ----
class SafeEvaluator:
    """
    Safely evaluate simple arithmetic expressions against a context (e.g., {'x': value}).

    Supported:
      - Binary operators: +, -, *, /
      - Unary minus: -x
      - Variable name: x
      - Numeric constants

    Everything else (function calls, attributes, subscripts, etc.) is rejected.
    """

    # Allowed operator maps
    _BINOPS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
    }
    _UNARYOPS = {
        ast.USub: operator.neg,
    }
    _ALLOWED_NAMES = {"x"}

    def eval_expression(self, expr_str: str, context: dict):
        """Parse and evaluate an expression string within a restricted AST."""
        try:
            tree = ast.parse(expr_str, mode="eval")
            return self._eval_node(tree.body, context)
        except Exception as e:
            # Raise a ValueError to surface a clear, user-facing error upstream
            raise ValueError(f"Invalid expression: {e}")

    def _eval_node(self, node, context: dict):
        # Binary operations (e.g., x/12, x*2, x + 3)
        if isinstance(node, ast.BinOp):
            left = self._eval_node(node.left, context)
            right = self._eval_node(node.right, context)
            op = self._BINOPS.get(type(node.op))
            if op is None:
                raise ValueError(f"Operator not allowed: {type(node.op).__name__}")
            return op(left, right)

        # Unary operations (e.g., -x)
        if isinstance(node, ast.UnaryOp):
            op = self._UNARYOPS.get(type(node.op))
            if op is None:
                raise ValueError(f"Unary operator not allowed: {type(node.op).__name__}")
            operand = self._eval_node(node.operand, context)
            return op(operand)

        # Variable names (only 'x' is permitted)
        if isinstance(node, ast.Name):
            if node.id not in self._ALLOWED_NAMES:
                raise ValueError(f"Name not allowed: {node.id}")
            if node.id not in context:
                raise ValueError(f"Missing variable in context: {node.id}")
            return context[node.id]

        # Numeric constants
        if isinstance(node, ast.Constant):
            return node.value

        # Disallow any other node types
        raise ValueError(f"Unsupported expression element: {type(node).__name__}")


def validate_expression(expr_str: str):
    """
    Validate an expression string using SafeEvaluator.

    Returns:
        tuple[bool, str]: (is_valid, message)
    """
    evaluator = SafeEvaluator()
    try:
        # Validate structure by parsing and a simple dry-run with x=1
        evaluator.eval_expression(expr_str, {"x": 1})
        return True, "Expression is valid (allowed: +, -, *, /; variable: x)."
    except Exception as e:
        return False, str(e)