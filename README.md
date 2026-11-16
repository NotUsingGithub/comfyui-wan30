# Wan30 ComfyUI nodes

Nodes for a [wan30.video](https://wan30.video/) account. They call the same
hosted tools as `@wan30/cli` 0.1.0 through the Python package `wan30`:
account status, models, estimation, task list, task status, and an explicit
opt-in generation.

Purchased wan30.video credits are required for generation. Sign-up, check-in
and gift credits alone do not qualify. Estimation does not spend credits.

This is not an official Alibaba, DashScope, or Tongyi client. It does not
generate video on your machine and it does not offer free generation.

The Python dependency `wan30>=0.1.0,<0.2` is **not on PyPI yet**. ComfyUI-Manager
will fail `pip install -r requirements.txt` until that release exists. Install
the reviewed wheel first, then install this folder.

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

`requirements.txt` asks pip for `wan30>=0.1.0,<0.2`. That package is not on
PyPI yet, so a Manager install still fails at the pip step. Install the
reviewed wheel first. This repository is not a Comfy Registry listing.

## Comfy Registry and Manager

Checked against the current Comfy docs and `comfy-cli`:

- Registry metadata lives in this `pyproject.toml`. The node id is `wan30`.
  On 2026-11-11, `GET https://api.comfy.org/nodes/wan30` returned 404.
- `PublisherId` is `notusinggithub`. That publisher id already exists at
  `https://registry.comfy.org`. This package does not create it. You still
  need a Registry publishing API key from that publisher. Create the key at
  the registry while logged in, and keep it outside this repo.
- `comfy node pack` and `comfy node publish` zip git-tracked files from this
  repository root (`git -C . ls-files`). `.comfyignore` drops `tests/`.
- `Comfy-Org/publish-node-action` checks out the repository root and has no
  subdirectory input. Point it at `NotUsingGithub/comfyui-wan30`, not at
  `NotUsingGithub/wan30-mcp`. This import does not run that action.
- Manager installs a registry zip into `custom_nodes/<node-id>/`, then runs
  `requirements.txt`. Do not open a `custom-node-list.json` pull request.
  The Registry upload is not done. PyPI package `wan30` is still blocked, and
  no Registry publishing key is stored in this repository.

Publish only after `wan30` is on PyPI and a Registry key exists outside this
repo. Otherwise Manager installs the node and then fails its dependency. From
a committed checkout:

```sh
comfy node validate
comfy node publish
```

`comfy node publish` uploads. The API key is prompted, or passed with
`--token` from a secret store. Do not commit the key. The published version
is `0.1.0` in `pyproject.toml`.

Authors recorded here are Wan30 and NotUsingGithub.
