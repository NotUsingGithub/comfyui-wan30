# Wan30 ComfyUI nodes

Nodes for a [wan30.video](https://wan30.video/) account. They call the same
hosted tools as `@wan30/cli` 0.1.0 through the Python package `wan30`:
account status, models, estimation, task list, task status, and an explicit
opt-in generation.

Purchased wan30.video credits are required for generation. Sign-up, check-in
and gift credits alone do not qualify. Estimation does not spend credits.

This is not an official Alibaba, DashScope, or Tongyi client. It does not
generate video on your machine and it does not offer free generation.

The Python dependency `wan30>=0.1.0,<0.2` is published on PyPI as
[wan30 0.1.0](https://pypi.org/project/wan30/0.1.0/).

## Nodes

| Node | Tool | Spends |
| --- | --- | --- |
| Wan30 Account Status | `account_status` | no |
| Wan30 List Models | `list_models` | no |
| Wan30 Get Model | `get_model` | no |
| Wan30 Estimate | `estimate_generation` | no |
| Wan30 List Tasks | `list_tasks` | no |
| Wan30 Get Task | `get_task` | no |
| Wan30 Generate Video | `generate_video` | only after both confirmations |

Models are `wan30-reference-to-video`, `wan30-text-to-video`, and
`wan30-image-to-video`. Optional duration, resolution, aspect ratio, and audio
are left unset when you keep the `omit` or `0` widgets. The node does not
fill in server defaults. Image inputs are existing HTTPS URLs. The node does
not upload local files.

`Wan30 Generate Video` does not call the service unless both of these are true:

1. The node widget `confirm_spend` is enabled.
2. The ComfyUI process has `WAN30_CONFIRM_SPEND=spend-purchased-credits`.

The environment value is not a workflow input, so it is not saved in workflow
JSON. A shared workflow with the widget enabled still does not spend until
that process environment is set. There is no token, password, or API-key
widget.

## Authentication

Sign in with the Wan30 CLI or the Python client before starting ComfyUI, or
export a process environment the client already understands:

- `WAN30_ACCESS_TOKEN` — bearer token for this process
- `WAN30_CONFIG_DIR` — directory of an existing file session (default `~/.wan30`)
- `WAN30_ORIGIN` — optional origin, default `https://wan30.video`

An optional `origin` widget overrides `WAN30_ORIGIN` for that node. Leave it
empty to use the environment. Do not put a token in the widget or in the
workflow. These nodes do not read `.env` files and do not start a login flow.

## Install

Clone https://github.com/NotUsingGithub/comfyui-wan30 into
`ComfyUI/custom_nodes/comfyui-wan30`, or copy this repository so `__init__.py`
is directly inside that folder. Restart ComfyUI.

`requirements.txt` installs `wan30>=0.1.0,<0.2` from PyPI. That requirement
resolves to wan30 0.1.0.

## Comfy Registry

Registry metadata is in `pyproject.toml`. The node id is `wan30`, the version
is `0.1.0`, and `PublisherId` is `notusinggithub`. The expected listing is
https://registry.comfy.org/nodes/wan30. This package does not create the
publisher. The listing is not live until a maintainer dispatches the manual
workflow from `main`.

`.github/workflows/publish_action.yml` is manual only. The `publish` input
must be the word `publish`, the ref must be `main`, and the repository must
be `NotUsingGithub/comfyui-wan30`. It does not run on a push, a tag, or a
pull request. The publish job reads the repository Actions secret
`REGISTRY_ACCESS_TOKEN` and does not print it. The key is not stored in this
repository.

`comfy node pack` zips git-tracked files from this repository root.
`.comfyignore` drops `tests/`, `scripts/`, `.github/`, and `node.zip`. From a committed
checkout, before a manual dispatch:

```sh
comfy node validate
```

Do not commit a Registry key. The published version is `0.1.0` in
`pyproject.toml`.

Authors recorded here are Wan30 and NotUsingGithub.
