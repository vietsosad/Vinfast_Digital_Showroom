"""Enforce the layered dependency rule across the whole backend.

    api  ──▶  application  ──▶  domain  ◀──  infrastructure

* domain/ and application/ are plain Python: no web framework, ORM, DB driver,
  JWT/crypto library or validation framework, and no import of api/infrastructure.
* api/ never touches SQLAlchemy; only api/dependencies.py (the composition
  root) may import infrastructure to wire repositories into use cases.
* infrastructure/ never imports the API layer or FastAPI.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from fastapi.routing import APIRoute, APIWebSocketRoute

SRC = Path(__file__).resolve().parents[1] / "src"

FRAMEWORKS = {"fastapi", "starlette", "pydantic", "pydantic_settings", "uvicorn"}
DATABASE_LIBRARIES = {"sqlalchemy", "aiosqlite", "asyncpg", "sqlite3", "psycopg", "psycopg2"}
INFRA_LIBRARIES = {"jwt", "passlib", "requests", "httpx"}


def python_files(layer: str) -> list[Path]:
    return sorted((SRC / layer).rglob("*.py"))


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            modules.add(node.module)
    return modules


def roots(modules: set[str]) -> set[str]:
    return {module.split(".")[0] for module in modules}


def violations(layer: str, forbidden_roots: set[str], forbidden_prefixes: tuple[str, ...], allow: set[str] = frozenset()):
    found = []
    for path in python_files(layer):
        relative = path.relative_to(SRC).as_posix()
        if relative in allow:
            continue
        modules = imported_modules(path)
        bad = sorted(roots(modules) & forbidden_roots) + sorted(
            module for module in modules if module.startswith(forbidden_prefixes)
        )
        if bad:
            found.append(f"{relative}: {', '.join(bad)}")
    return found


@pytest.mark.parametrize("layer", ["domain", "application"])
def test_business_layers_are_framework_and_database_free(layer):
    assert python_files(layer), f"{layer}/ must contain modules"
    assert violations(
        layer,
        FRAMEWORKS | DATABASE_LIBRARIES | INFRA_LIBRARIES,
        ("src.api", "src.infrastructure", "src.main", "src.config"),
    ) == []


def test_domain_does_not_depend_on_application():
    assert violations("domain", set(), ("src.application",)) == []


def test_api_layer_never_touches_the_database():
    assert violations("api", DATABASE_LIBRARIES, ()) == []


def test_only_the_composition_root_imports_infrastructure():
    assert violations("api", set(), ("src.infrastructure",), allow={"api/dependencies.py"}) == []


def test_infrastructure_does_not_depend_on_the_web_layer():
    assert violations("infrastructure", {"fastapi", "starlette"}, ("src.api", "src.main")) == []


def test_legacy_mixed_layer_packages_are_gone():
    for legacy in ("models", "services", "repositories"):
        assert not (SRC / legacy).exists(), f"src/{legacy} mixes layers and must not return"


def iter_endpoints(routes):
    """Yield every HTTP/WebSocket route, descending into included routers.

    Recent FastAPI versions keep included routers nested instead of flattening
    them into ``app.routes``.
    """
    for route in routes:
        nested = getattr(route, "original_router", None)
        if nested is not None:
            yield from iter_endpoints(nested.routes)
        elif isinstance(route, (APIRoute, APIWebSocketRoute)):
            yield route


def test_every_route_is_served_by_an_api_module():
    from src.main import app

    endpoints = list(iter_endpoints(app.routes))
    # 46 documented operations + WebSocket, mounted under /api/v1 and the /api alias,
    # plus /health. A low count means routes are being missed, not that all is well.
    assert len(endpoints) >= 2 * 47 + 1
    for route in endpoints:
        module = route.endpoint.__module__
        assert module.startswith("src.api.") or module == "src.main", f"{route.path} served by {module}"
