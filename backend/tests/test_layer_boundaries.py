import ast
from pathlib import Path


def test_support_business_service_has_no_framework_or_database_imports():
    source_path = Path(__file__).parents[1] / "src" / "services" / "support_chat.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imported_roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])

    assert "fastapi" not in imported_roots
    assert "sqlalchemy" not in imported_roots
