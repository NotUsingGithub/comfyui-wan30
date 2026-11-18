"""Offline tests for the Wan30 ComfyUI nodes.

The client is injected. Nothing in the default path confirms a spend or
opens a network session.
"""

import base64
import http.client
import importlib
import importlib.metadata
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]


def load_root_package():
    """Load this repository root as the ComfyUI node package."""
    name = "comfyui"
    for key in list(sys.modules):
        if key == name or key.startswith(name + "."):
            del sys.modules[key]
    spec = importlib.util.spec_from_file_location(
        name,
        PACKAGE / "__init__.py",
        submodule_search_locations=[str(PACKAGE)],
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


comfyui = load_root_package()
nodes = importlib.import_module("comfyui.nodes")
session = importlib.import_module("comfyui.session")

SECRET_NAMES = {
    "token",
    "access_token",
    "api_key",
    "apikey",
    "password",
    "secret",
    "credential",
    "credentials",
}


class RecordingClient:
    def __init__(self):
        self.calls = []
        self.closed = False

    def account(self):
        self.calls.append(("account",))
        return {"authenticated": True}

    def models(self):
        self.calls.append(("models",))
        return [{"id": "wan30-text-to-video"}]

    def model(self, model_id):
        self.calls.append(("model", model_id))
        return {"id": model_id}

    def estimate(self, payload):
        self.calls.append(("estimate", payload))
        return {"credits": 2}

    def generate(self, payload, request_id=None, *, confirm_spend=False):
        self.calls.append(("generate", payload, request_id, confirm_spend))
        return {"taskId": "task-1"}

    def tasks(self, limit=None):
        self.calls.append(("tasks", limit))
        return []

    def task(self, task_id):
        self.calls.append(("task", task_id))
        return {"id": task_id}

    def close(self):
        self.closed = True


class RaisingClient(RecordingClient):
    def account(self):
        raise RuntimeError("offline")


class NodeTests(unittest.TestCase):
    def setUp(self):
        self.client = RecordingClient()
        self.original = session.open_client
        session.open_client = lambda origin="": self.client
        self.previous_confirm = os.environ.pop(nodes.CONFIRM_ENV, None)

    def tearDown(self):
        session.open_client = self.original
        if self.previous_confirm is None:
            os.environ.pop(nodes.CONFIRM_ENV, None)
        else:
            os.environ[nodes.CONFIRM_ENV] = self.previous_confirm

    def test_mappings_and_defaults_do_not_spend(self):
        self.assertEqual(
            tuple(comfyui.NODE_CLASS_MAPPINGS),
            (
                "Wan30AccountStatus",
                "Wan30ListModels",
                "Wan30GetModel",
                "Wan30Estimate",
                "Wan30ListTasks",
                "Wan30GetTask",
                "Wan30GenerateVideo",
            ),
        )
        self.assertEqual(set(comfyui.NODE_CLASS_MAPPINGS), set(comfyui.NODE_DISPLAY_NAME_MAPPINGS))
        for name, cls in comfyui.NODE_CLASS_MAPPINGS.items():
            self.assertEqual(cls.CATEGORY, "Wan30")
            self.assertTrue(cls.OUTPUT_NODE)
            self.assertIn("Wan30", comfyui.NODE_DISPLAY_NAME_MAPPINGS[name])
            spec = cls.INPUT_TYPES()
            names = set()
            for group in spec.values():
                names.update(group)
            self.assertTrue(names.isdisjoint(SECRET_NAMES), names)
        generate = comfyui.NODE_CLASS_MAPPINGS["Wan30GenerateVideo"].INPUT_TYPES()
        self.assertIs(generate["required"]["confirm_spend"][1]["default"], False)
        self.assertNotIn("confirm_spend", nodes.Wan30Estimate.INPUT_TYPES()["required"])

    def test_import_does_not_open_a_client(self):
        def fail(origin=""):
            raise AssertionError("import opened a client")

        session.open_client = fail
        importlib.reload(nodes)
        self.assertIn("Wan30AccountStatus", nodes.NODE_CLASS_MAPPINGS)
        session.open_client = lambda origin="": self.client

    def test_read_nodes_call_the_matching_tool(self):
        account = json.loads(nodes.Wan30AccountStatus().execute()["result"][0])
        self.assertEqual(account["authenticated"], True)
        models = json.loads(nodes.Wan30ListModels().execute(origin="  ")["result"][0])
        self.assertEqual(models[0]["id"], "wan30-text-to-video")
        model = json.loads(
            nodes.Wan30GetModel().execute("wan30-image-to-video")["result"][0]
        )
        self.assertEqual(model["id"], "wan30-image-to-video")
        estimate = nodes.Wan30Estimate().execute(
            model_id="wan30-text-to-video",
            prompt="A paper boat",
        )
        self.assertIn("credits", json.loads(estimate["result"][0]))
        self.assertEqual(
            self.client.calls[3],
            (
                "estimate",
                {"modelId": "wan30-text-to-video", "prompt": "A paper boat"},
            ),
        )
        nodes.Wan30ListTasks().execute()
        nodes.Wan30ListTasks().execute(limit=20)
        nodes.Wan30GetTask().execute("task-1")
        self.assertEqual(self.client.calls[4:], [("tasks", None), ("tasks", 20), ("task", "task-1")])
        self.assertNotIn("generate", [call[0] for call in self.client.calls])
        self.assertTrue(self.client.closed)

    def test_estimate_keeps_explicit_fields(self):
        nodes.Wan30Estimate().execute(
            model_id="wan30-reference-to-video",
            prompt="A paper boat",
            duration_seconds=5,
            resolution="480p",
            aspect_ratio="16:9",
            has_audio="false",
            image_urls="https://cdn.example/a.png,\nhttps://cdn.example/b.png",
        )
        payload = self.client.calls[-1][1]
        self.assertEqual(
            payload,
            {
                "modelId": "wan30-reference-to-video",
                "prompt": "A paper boat",
                "durationSeconds": 5,
                "resolution": "480p",
                "aspectRatio": "16:9",
                "hasAudio": False,
                "imageUrls": [
                    "https://cdn.example/a.png",
                    "https://cdn.example/b.png",
                ],
            },
        )

    def test_generate_stays_closed_without_both_confirmations(self):
        node = nodes.Wan30GenerateVideo()
        fields = dict(
            model_id="wan30-text-to-video",
            prompt="A paper boat",
        )
        with self.assertRaises(RuntimeError) as blocked:
            node.execute(confirm_spend=False, **fields)
        self.assertIn("purchased wan30.video credits", str(blocked.exception))
        self.assertEqual(self.client.calls, [])

        with self.assertRaises(RuntimeError):
            node.execute(confirm_spend=True, **fields)
        self.assertEqual(self.client.calls, [])

        os.environ[nodes.CONFIRM_ENV] = "yes"
        with self.assertRaises(RuntimeError):
            node.execute(confirm_spend=True, **fields)
        self.assertEqual(self.client.calls, [])

        os.environ[nodes.CONFIRM_ENV] = nodes.CONFIRM_VALUE
        with self.assertRaises(RuntimeError):
            node.execute(confirm_spend=False, **fields)
        self.assertEqual(self.client.calls, [])

    def test_generate_sends_the_client_gate_after_both_confirmations(self):
        os.environ[nodes.CONFIRM_ENV] = nodes.CONFIRM_VALUE
        result = nodes.Wan30GenerateVideo().execute(
            model_id="wan30-text-to-video",
            prompt="A paper boat",
            confirm_spend=True,
            request_id="  ",
        )
        self.assertEqual(json.loads(result["result"][0])["taskId"], "task-1")
        kind, payload, request_id, confirm = self.client.calls[-1]
        self.assertEqual(kind, "generate")
        self.assertEqual(payload, {"modelId": "wan30-text-to-video", "prompt": "A paper boat"})
        self.assertNotIn("confirm_spend", payload)
        self.assertIsNone(request_id)
        self.assertIs(confirm, True)
        self.assertTrue(self.client.closed)

    def test_client_error_still_closes(self):
        self.client = RaisingClient()
        session.open_client = lambda origin="": self.client
        with self.assertRaises(RuntimeError):
            nodes.Wan30AccountStatus().execute()
        self.assertTrue(self.client.closed)

    def test_missing_package_message(self):
        saved = sys.modules.get("wan30")
        sys.modules["wan30"] = None
        try:
            with self.assertRaises(RuntimeError) as missing:
                self.original()
        finally:
            if saved is None:
                sys.modules.pop("wan30", None)
            else:
                sys.modules["wan30"] = saved
        self.assertIn("Install wan30>=0.1.0,<0.2 from PyPI", str(missing.exception))

    def test_open_client_uses_environment_without_a_widget_secret(self):
        calls = {}

        class Stub:
            @classmethod
            def from_environment(cls, origin=None):
                calls["origin"] = origin
                return "client"

        import wan30

        original = wan30.WanClient
        wan30.WanClient = Stub
        try:
            self.assertEqual(self.original(""), "client")
            self.assertIsNone(calls["origin"])
            self.assertEqual(self.original(" https://wan30.video "), "client")
            self.assertEqual(calls["origin"], "https://wan30.video")
        finally:
            wan30.WanClient = original

    def test_public_metadata(self):
        text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (
                PACKAGE / "README.md",
                PACKAGE / "pyproject.toml",
                PACKAGE / "requirements.txt",
                PACKAGE / "nodes.py",
            )
        )
        self.assertIn("purchased", text.lower())
        self.assertIn("check-in", text.lower())
        readme = (PACKAGE / "README.md").read_text(encoding="utf-8")
        self.assertIn("not an official", readme.lower())
        self.assertIn("https://pypi.org/project/wan30/0.1.0/", readme)
        self.assertNotIn("not on PyPI yet", text)
        self.assertIn('PublisherId = "notusinggithub"', (PACKAGE / "pyproject.toml").read_text())
        self.assertNotRegex(text, r"(?i)[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}")
        ignore = (PACKAGE / ".comfyignore").read_text(encoding="utf-8")
        for entry in ("tests/", ".github/", "scripts/", "node.zip"):
            self.assertIn(entry, ignore.splitlines())

    def test_registry_metadata_script(self):
        completed = subprocess.run(
            [sys.executable, str(PACKAGE / "scripts" / "check_registry_metadata.py")],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("wan30 0.1.0 registry metadata is valid.", completed.stdout)

    def test_installed_wan30_is_0_1_0(self):
        self.assertEqual(importlib.metadata.version("wan30"), "0.1.0")

    def test_public_client_uses_mocked_http_and_does_not_spend(self):
        import wan30.client
        import wan30.transport

        def fake_jwt():
            def segment(value):
                raw = json.dumps(value, separators=(",", ":")).encode("utf-8")
                return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")

            header = segment({"alg": "none", "typ": "JWT"})
            claims = segment(
                {
                    "sub": "offline-test",
                    "grant_id": "offline-grant",
                    "aud": "https://wan30.video/api/mcp",
                }
            )
            return header + "." + claims + ".sig"

        calls = []

        def fake_request(url, *, method, headers, body=None, timeout, max_bytes):
            self.assertEqual(url, "https://wan30.video/api/mcp/")
            self.assertEqual(method, "POST")
            self.assertTrue(str(headers.get("Authorization", "")).startswith("Bearer "))
            payload = json.loads(body)
            tool = None
            if payload.get("method") == "tools/call":
                tool = payload["params"]["name"]
                self.assertNotIn("confirm_spend", json.dumps(payload["params"]["arguments"]))
            calls.append((payload.get("method"), tool))
            if payload.get("method") == "notifications/initialized":
                return wan30.transport.HttpResponse(202, {"content-type": "application/json"}, b"")
            if payload.get("method") == "initialize":
                result = {"protocolVersion": "2025-11-25", "capabilities": {}}
            else:
                name = payload["params"]["name"]
                data = {"taskId": "task-mock"} if name == "generate_video" else {"authenticated": True}
                result = {"structuredContent": {"data": data}, "isError": False}
            response = {
                "jsonrpc": "2.0",
                "id": payload["id"],
                "result": result,
            }
            return wan30.transport.HttpResponse(
                200,
                {"content-type": "application/json"},
                json.dumps(response).encode("utf-8"),
            )

        def refuse_socket(*args, **kwargs):
            raise AssertionError("real HTTPS connection")

        saved_env = {
            name: os.environ.get(name)
            for name in ("WAN30_ACCESS_TOKEN", "WAN30_CONFIG_DIR", "WAN30_ORIGIN", "HOME")
        }
        saved_request = wan30.client.https_request
        saved_transport = wan30.transport.https_request
        saved_socket = http.client.HTTPSConnection
        config = tempfile.TemporaryDirectory()
        home = tempfile.TemporaryDirectory()
        try:
            wan30.client.https_request = fake_request
            wan30.transport.https_request = fake_request
            http.client.HTTPSConnection = refuse_socket
            os.environ["WAN30_ACCESS_TOKEN"] = fake_jwt()
            os.environ["WAN30_CONFIG_DIR"] = config.name
            os.environ["HOME"] = home.name
            os.environ.pop("WAN30_ORIGIN", None)
            os.environ.pop(nodes.CONFIRM_ENV, None)
            session.open_client = self.original
            fields = dict(model_id="wan30-text-to-video", prompt="A paper boat")
            with self.assertRaises(RuntimeError):
                nodes.Wan30GenerateVideo().execute(confirm_spend=False, **fields)
            with self.assertRaises(RuntimeError):
                nodes.Wan30GenerateVideo().execute(confirm_spend=True, **fields)
            self.assertEqual(calls, [])
            account = json.loads(nodes.Wan30AccountStatus().execute()["result"][0])
            self.assertEqual(account["authenticated"], True)
            self.assertIn(("tools/call", "account_status"), calls)
            self.assertNotIn("generate_video", [tool for _method, tool in calls])
            before = len(calls)
            os.environ[nodes.CONFIRM_ENV] = nodes.CONFIRM_VALUE
            generated = nodes.Wan30GenerateVideo().execute(
                confirm_spend=True,
                request_id="paper-boat-shot01",
                **fields,
            )
            self.assertEqual(json.loads(generated["result"][0])["taskId"], "task-mock")
            self.assertIn(("tools/call", "generate_video"), calls[before:])
            self.assertTrue(any(item[0] == "initialize" for item in calls))
        finally:
            wan30.client.https_request = saved_request
            wan30.transport.https_request = saved_transport
            http.client.HTTPSConnection = saved_socket
            config.cleanup()
            home.cleanup()
            for name, value in saved_env.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value


if __name__ == "__main__":
    unittest.main()
