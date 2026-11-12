"""T10b2: what ships the application to the host: the start script, the container image, the
Render blueprint, the keep-alive workflow and the operations guide stay consistent with the code
and with each other. The image itself is built by the CI (no Docker daemon in every session)."""

import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import pytest

ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / "backend"
GUIDE = ROOT / "docs" / "04-operacion" / "guia-de-despliegue.md"
SCRIPT = BACKEND / "start.sh"
SECRETS = ("ROYEXA_LEDGER_URL", "ROYEXA_MIGRATOR_URL", "ROYEXA_APP_PASSWORD")


def _env_vars_in_code() -> set[str]:
    found: set[str] = set()
    for path in (BACKEND / "src").rglob("*.py"):
        found |= set(re.findall(r"ROYEXA_[A-Z_]+", path.read_text()))
    return found


def test_t10b2_every_variable_the_code_reads_is_in_the_guide():
    guide = GUIDE.read_text()

    missing = sorted(name for name in _env_vars_in_code() if f"`{name}`" not in guide)

    assert missing == [], f"undocumented: {missing}"


def test_t10b2_the_blueprint_runs_the_docker_image_on_the_free_plan_with_a_health_check():
    blueprint = (ROOT / "render.yaml").read_text()

    assert "runtime: docker" in blueprint and "plan: free" in blueprint
    assert "healthCheckPath: /health" in blueprint
    assert "dockerfilePath: ./backend/Dockerfile" in blueprint and "dockerContext: ./backend" in blueprint
    assert "autoDeploy: false" in blueprint, "a deploy is a decision, not a side effect of a merge"


def test_t10b2_the_blueprint_sets_the_production_mode_and_keeps_secrets_out_of_the_repository():
    blueprint = (ROOT / "render.yaml").read_text()

    for line in ("key: ROYEXA_SEED\n        value: pilot", 'key: ROYEXA_REQUIRE_CHANGED_PASSWORDS\n        value: "1"'):
        assert line in blueprint, line
    for name in SECRETS:
        assert re.search(rf"key: {name}\n\s+sync: false", blueprint), f"{name} must be set by hand"
    declared = set(re.findall(r"key: (ROYEXA_[A-Z_]+)", blueprint))
    assert declared <= _env_vars_in_code(), declared - _env_vars_in_code()
    assert not re.search(r"postgres(ql)?://\S+:\S+@", blueprint), "no connection string with a password"


def test_t10b2_the_image_is_small_unprivileged_and_carries_what_the_code_reads_from_disk():
    dockerfile = (BACKEND / "Dockerfile").read_text()

    assert re.search(r"^FROM python:3\.14-slim", dockerfile, re.M)
    assert re.search(r"^USER (?!root)\S+", dockerfile, re.M)
    for path in ("src", "migrations", "pilot", "start.sh"):
        assert re.search(rf"^COPY .*{re.escape(path)}", dockerfile, re.M), path
    assert "uv sync --locked --no-dev" in dockerfile
    assert not re.search(r"PASSWORD|://\S+:\S+@", dockerfile), "no secret in the image"
    assert (BACKEND / ".dockerignore").read_text().split().count(".venv") == 1


def _start(env: dict[str, str], seconds: float = 20.0):
    clean = {k: v for k, v in os.environ.items() if not k.startswith("ROYEXA_")}
    return subprocess.Popen(
        ["sh", str(SCRIPT)],
        cwd=BACKEND,
        env={**clean, "ROYEXA_PYTHON": sys.executable, **env},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def test_t10b2_a_database_without_a_migrator_url_stops_the_start_with_a_message():
    process = _start({"ROYEXA_LEDGER_URL": "postgresql://royexa_app:x@localhost:1/royexa"})
    output, _ = process.communicate(timeout=20)

    assert process.returncode != 0 and "ROYEXA_MIGRATOR_URL" in output


def test_t10b2_the_script_serves_on_the_port_the_host_gives_it():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    process = _start({"PORT": str(port), "ROYEXA_SEED": "pilot", "ROYEXA_DISPATCH_SECONDS": "0"})
    try:
        deadline = time.monotonic() + 20
        body = None
        while time.monotonic() < deadline and body is None:
            try:
                body = urlopen(f"http://127.0.0.1:{port}/health", timeout=1).read()
            except (URLError, ConnectionError):
                time.sleep(0.2)
        assert body == b'{"status":"ok"}'
    finally:
        process.terminate()
        process.wait(timeout=10)


def test_t10b2_the_keep_alive_workflow_pings_health_every_ten_minutes_only_when_configured():
    workflow = (ROOT / ".github" / "workflows" / "keepalive.yml").read_text()

    assert 'cron: "*/10 * * * *"' in workflow
    assert "workflow_dispatch" in workflow
    assert "vars.ROYEXA_HEALTH_URL" in workflow and "!= ''" in workflow
    assert "curl --fail" in workflow and "--retry" in workflow
    assert "secrets." not in workflow, "the health route is public: nothing to hide"


def test_t10b2_the_ci_builds_the_image_and_starts_it_in_the_production_shape():
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text()

    assert "docker build" in ci and "backend" in ci
    assert ci.index('uv run pytest -m ""') < ci.index("docker build"), "the smoke test changes the app role's password"
    assert "ROYEXA_REQUIRE_CHANGED_PASSWORDS=1" in ci and "ROYEXA_SEED=pilot" in ci
    assert "/health" in ci


@pytest.mark.parametrize("fragment", ["set_password", "sslmode=require", "ROYEXA_HEALTH_URL", "pooler"])
def test_t10b2_the_guide_covers_the_manual_steps(fragment):
    assert fragment in GUIDE.read_text()
