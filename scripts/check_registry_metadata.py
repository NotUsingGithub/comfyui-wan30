#!/usr/bin/env python3
"""Check wan30 0.1.0 metadata before a manual Comfy Registry publish.

This script reads the repository files only. It does not read environment
secrets or contact the Registry.
"""

import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKOUT = "3d3c42e5aac5ba805825da76410c181273ba90b1"
PUBLISH_ACTION = "d2366e7abb6ab16f3bb03e3520ae25c8cf749bc9"
EMAIL = re.compile(r"(?i)[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}")
TEXT_SUFFIXES = {".py", ".md", ".toml", ".txt", ".yml", ".yaml"}
SKIP_DIRS = {".git", "__pycache__"}
TRIGGER_KEYS = (
    "push:",
    "pull_request:",
    "pull_request_target:",
    "release:",
    "schedule:",
    "workflow_run:",
    "workflow_call:",
    "repository_dispatch:",
    "create:",
    "delete:",
)


def fail(message):
    print(message, file=sys.stderr)
    raise SystemExit(1)


def tracked_text():
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix in TEXT_SUFFIXES or path.name in {"LICENSE", ".comfyignore"}:
            yield path


def check_project():
    project_file = ROOT / "pyproject.toml"
    data = tomllib.loads(project_file.read_text(encoding="utf-8"))
    project = data.get("project")
    comfy = data.get("tool", {}).get("comfy")
    if not isinstance(project, dict) or not isinstance(comfy, dict):
        fail("pyproject.toml is missing [project] or [tool.comfy].")
    if project.get("name") != "wan30":
        fail("project name must be wan30.")
    if project.get("version") != "0.1.0":
        fail("project version must be 0.1.0.")
    if project.get("license") != {"file": "LICENSE"}:
        fail("license must reference the LICENSE file.")
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    if not license_text.startswith("MIT License\n"):
        fail("LICENSE must be the MIT license.")
    if project.get("requires-python") != ">=3.10":
        fail("requires-python must be >=3.10.")
    if project.get("dependencies") != ["wan30>=0.1.0,<0.2"]:
        fail("dependency must be wan30>=0.1.0,<0.2.")
    authors = project.get("authors")
    if authors != [{"name": "Wan30"}, {"name": "NotUsingGithub"}]:
        fail("authors must be Wan30 and NotUsingGithub, with no email addresses.")
    urls = project.get("urls")
    if not isinstance(urls, dict):
        fail("project.urls is missing.")
    if urls.get("Repository") != "https://github.com/NotUsingGithub/comfyui-wan30":
        fail("Repository URL must be https://github.com/NotUsingGithub/comfyui-wan30.")
    if comfy.get("PublisherId") != "notusinggithub":
        fail("PublisherId must be notusinggithub.")
    if comfy.get("DisplayName") != "Wan30":
        fail("DisplayName must be Wan30.")
    requirement = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    if "wan30>=0.1.0,<0.2" not in requirement.splitlines():
        fail("requirements.txt must require wan30>=0.1.0,<0.2.")
    ignore = (ROOT / ".comfyignore").read_text(encoding="utf-8")
    for entry in ("tests/", ".github/", "scripts/", "node.zip"):
        if entry not in ignore.splitlines():
            fail(f".comfyignore must exclude {entry}.")


def check_workflow():
    path = ROOT / ".github" / "workflows" / "publish_action.yml"
    text = path.read_text(encoding="utf-8")
    if "workflow_dispatch:" not in text:
        fail("The publish workflow must be manual.")
    for key in TRIGGER_KEYS:
        if re.search(rf"(?m)^[ ]{{2}}{re.escape(key)}", text):
            fail(f"The publish workflow must not declare {key}")
    if text.count("secrets.REGISTRY_ACCESS_TOKEN") != 1:
        fail("REGISTRY_ACCESS_TOKEN must be referenced once.")
    if "secrets." in text.replace("secrets.REGISTRY_ACCESS_TOKEN", ""):
        fail("The workflow must not reference another secret.")
    if "contents: write" in text or "id-token:" in text or "pull-requests:" in text:
        fail("The workflow permissions are broader than contents read.")
    if text.count("contents: read") != 3:
        fail("The workflow must grant contents read at the workflow and both jobs.")
    if f"actions/checkout@{CHECKOUT}" not in text:
        fail("actions/checkout is not pinned to the reviewed release.")
    if f"Comfy-Org/publish-node-action@{PUBLISH_ACTION}" not in text:
        fail("publish-node-action is not pinned to the reviewed commit.")
    if "skip_checkout: true" not in text or "persist-credentials: false" not in text:
        fail("Checkout must drop credentials, and the action must not checkout again.")
    required = (
        "github.event_name == 'workflow_dispatch'",
        "github.repository == 'NotUsingGithub/comfyui-wan30'",
        "github.ref == 'refs/heads/main'",
        "github.event.inputs.publish == 'publish'",
        "required: true",
    )
    for item in required:
        if text.count(item) < 1:
            fail(f"Missing publish guard: {item}")
    if text.count("github.event.inputs.publish == 'publish'") != 2:
        fail("Both jobs must require the publish confirmation.")
    if re.search(r"(?m)^[ ]+default:", text):
        fail("The publish input must not have a default.")
    if "echo " in text:
        fail("The workflow must not echo shell values.")


def check_public_text():
    stale = "not on PyPI " + "yet"
    docs = (
        ROOT / "README.md",
        ROOT / "requirements.txt",
        ROOT / "session.py",
        ROOT / "nodes.py",
        ROOT / "pyproject.toml",
        ROOT / ".github" / "workflows" / "publish_action.yml",
    )
    for path in docs:
        if stale in path.read_text(encoding="utf-8"):
            fail(f"{path.relative_to(ROOT)} still says the dependency is absent from PyPI.")
    for path in tracked_text():
        if EMAIL.search(path.read_text(encoding="utf-8")):
            fail(f"{path.relative_to(ROOT)} contains an email address.")


def main():
    check_project()
    check_workflow()
    check_public_text()
    print("wan30 0.1.0 registry metadata is valid.")


if __name__ == "__main__":
    main()
