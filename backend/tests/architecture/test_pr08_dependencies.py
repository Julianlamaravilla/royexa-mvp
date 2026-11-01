"""PR-08, static dependency check. EV-09, ADR-002, AD-02."""

import ast
from pathlib import Path

import royexa

ROOT = Path(royexa.__file__).parent
BUSINESS_MODULES = {"cash_box", "clients", "identity_access", "ledger", "loans", "sales"}
FRAMEWORKS = {"fastapi", "starlette", "pydantic", "uvicorn", "psycopg", "httpx"}
OUTER_LAYER = {"adapters", "api", "bootstrap", "main", "migrate", "seed"}


def _imports(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def _module_of(path: Path) -> str:
    return path.relative_to(ROOT).parts[0].removesuffix(".py")


def _graph() -> dict[str, set[str]]:
    graph: dict[str, set[str]] = {}
    for path in ROOT.rglob("*.py"):
        module = _module_of(path)
        if module == "__init__":
            continue
        targets = graph.setdefault(module, set())
        for name in _imports(path):
            parts = name.split(".")
            if parts[0] == "royexa" and len(parts) > 1 and parts[1] != module:
                targets.add(parts[1])
    return graph


def _find_cycle(graph: dict[str, set[str]]) -> list[str] | None:
    done: set[str] = set()

    def visit(node: str, path: list[str]) -> list[str] | None:
        if node in path:
            return path[path.index(node) :] + [node]
        if node in done:
            return None
        for target in sorted(graph.get(node, ())):
            cycle = visit(target, [*path, node])
            if cycle:
                return cycle
        done.add(node)
        return None

    for node in sorted(graph):
        cycle = visit(node, [])
        if cycle:
            return cycle
    return None


def test_pr08_module_graph_is_acyclic():
    """PR-08 / EV-09 / AD-02: dependencies between modules form no cycle."""
    assert _find_cycle(_graph()) is None


def test_pr08_cycle_detector_reports_a_cycle():
    """PR-08 / EV-09: the check above can actually fail."""
    assert _find_cycle({"a": {"b"}, "b": {"a"}}) == ["a", "b", "a"]


def test_pr08_domain_code_imports_no_framework_or_adapter():
    """PR-08 / EV-09: business modules know neither the framework nor the adapters."""
    offenders = []
    for path in ROOT.rglob("*.py"):
        if _module_of(path) not in BUSINESS_MODULES:
            continue
        for name in _imports(path):
            parts = name.split(".")
            if parts[0] in FRAMEWORKS or (
                parts[0] == "royexa" and len(parts) > 1 and parts[1] in OUTER_LAYER
            ):
                offenders.append(f"{path.relative_to(ROOT)} -> {name}")
    assert offenders == []


def test_pr08_business_modules_never_call_notifications():
    """PR-08 / EV-09 / ADR-002: business modules reach notices through the outbox only."""
    graph = _graph()
    assert not {m for m in BUSINESS_MODULES if "notifications" in graph.get(m, set())}
