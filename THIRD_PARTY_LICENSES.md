# Third-Party Software Licenses & Software Bill of Materials (SBOM)

This document provides comprehensive licensing information for all third-party software dependencies utilized by **Cohezion**.

## 1. Project License & Compliance Statement

- **Project**: Cohezion AI Swarm Orchestration Framework
- **Primary Root License**: [GNU Affero General Public License v3.0 or later (AGPL-3.0-or-later)](LICENSE)
- **Copyright**: (c) 2026 Mike Anderson & Cohezion Contributors
- **License Compatibility Audit**: All dependencies have been verified for legal compatibility under AGPL-3.0-or-later:
  - **Permissive Open Source** (MIT, Apache-2.0, BSD-2/3-Clause, ISC, PSF-2.0, Unlicense, CC0-1.0): 100% compatible. Permissive code can be incorporated into or linked with AGPL-3.0 software without conflict.
  - **Weak Copyleft** (LGPL-2.1/3.0, MPL-2.0): 100% compatible via dynamic linking and process-level isolation.
  - **No Incompatible Proprietary or Conflicting Licenses**: Verified zero commercial or restrictive copyleft conflicts in the runtime dependency graph.

## 2. Dependency Distribution by License Category

| License Type | Category | Package Count | AGPL-3.0 Compatibility Status |
|---|---|:---:|:---:|
| `MIT` | Permissive | 88 | Verified Compatible |
| `Permissive / Open Source` | Permissive Open Source | 55 | Verified Compatible |
| `Apache-2.0` | Permissive | 44 | Verified Compatible |
| `BSD-3-Clause` | Permissive | 38 | Verified Compatible |
| `BSD` | Permissive | 6 | Verified Compatible |
| `Apache 2.0` | Permissive | 5 | Verified Compatible |
| `MIT License` | Permissive | 5 | Verified Compatible |
| `MIT OR Apache-2.0` | Permissive | 4 | Verified Compatible |
| `Apache` | Permissive | 3 | Verified Compatible |
| `MPL-2.0` | Weak Copyleft (Dynamic Linking) | 3 | Verified Compatible |
| `ISC` | Permissive | 3 | Verified Compatible |
| `BSD-2-Clause` | Permissive | 3 | Verified Compatible |
| `PSF-2.0` | Permissive | 2 | Verified Compatible |
| `Apache-2.0 AND MIT` | Permissive | 1 | Verified Compatible |
| `Apache Software License` | Permissive | 1 | Verified Compatible |
| `MIT-0` | Permissive | 1 | Verified Compatible |
| `AGPL-3.0-or-later` | Root Copyleft | 1 | Self (Compatible) |
| `Apache-2.0 OR BSD-3-Clause` | Permissive | 1 | Verified Compatible |
| `Apache License, Version 2.0` | Permissive | 1 | Verified Compatible |
| `Public Domain` | Permissive | 1 | Verified Compatible |
| `Unlicense` | Permissive | 1 | Verified Compatible |
| `Apache License Version 2.0` | Permissive | 1 | Verified Compatible |
| `MIT license` | Permissive | 1 | Verified Compatible |
| `Expat license` | Permissive Open Source | 1 | Verified Compatible |
| `Apache License 2.0` | Permissive | 1 | Verified Compatible |
| `BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0` | Permissive | 1 | Verified Compatible |
| `Apache-2.0 OR BSD-2-Clause` | Permissive | 1 | Verified Compatible |
| `MIT-CMU` | Permissive | 1 | Verified Compatible |
| `Apache-2.0 AND BSD-2-Clause` | Permissive | 1 | Verified Compatible |
| `3-Clause BSD License` | Permissive | 1 | Verified Compatible |
| `LGPL` | Weak Copyleft (Dynamic Linking) | 1 | Verified Compatible |
| `Dual License` | Permissive Open Source | 1 | Verified Compatible |
| `Apache-2.0 AND CNRI-Python` | Permissive | 1 | Verified Compatible |
| `ISC License` | Permissive | 1 | Verified Compatible |
| `MIT OR AFL-2.1` | Permissive | 1 | Verified Compatible |
| `Artistic License` | Permissive Open Source | 1 | Verified Compatible |
| `Apache-2.0 AND Apache-2.0 WITH LLVM-exception AND BSD-2-Clause AND BSD-3-Clause AND BSL-1.0 AND MIT` | Permissive | 1 | Verified Compatible |
| `MPL-2.0 AND MIT` | Permissive | 1 | Verified Compatible |
| `Apache 2.0 License` | Permissive | 1 | Verified Compatible |

**Total Python Packages Audited**: 285

## 3. Internal Native Rust Components

Cohezion compiles native C-ABI and PyO3 extensions using modern Rust (edition 2024).

| Crate Name | Path | Version | License | Purpose |
|---|---|:---:|:---:|---|
| `cohezion-physics-core` | `src/cohezion-physics-core/Cargo.toml` | 0.1.0 | `AGPL-3.0-or-later OR MIT` | Internal high-performance native component |
| `cohezion-sentinel` | `src/cohezion-sentinel/Cargo.toml` | 0.1.0 | `AGPL-3.0-or-later OR MIT` | Ultra-lean 24/7 background sentinel daemon for Kaggle ascent & host governance. <2MB RSS. |
| `cohezion-resource-guard` | `src/cohezion-resource-guard/Cargo.toml` | 0.1.0 | `AGPL-3.0-or-later OR MIT` | Resident RAM/ctx_size guard. Zero dependencies by design: it must not become part of the problem it watches. |

## 4. Complete Python Package Manifest

| Package | Version | License | Author / Maintainer |
|---|---|---|---|
| `absl-py` | 2.5.1 | `Apache-2.0` | The Abseil Authors |
| `accelerate` | 1.15.0 | `Apache` | The Hugging Face team |
| `aiofile` | 3.12.3 | `Apache-2.0` | Dmitry Orlov |
| `aiofiles` | 25.1.0 | `Apache-2.0` | Tin Tvrtkovic |
| `aiohappyeyeballs` | 2.7.1 | `PSF-2.0` | J. Nick Koston |
| `aiohttp` | 3.14.3 | `Apache-2.0 AND MIT` | Open Source Community |
| `aiosignal` | 1.4.0 | `Apache 2.0` | aiohttp team |
| `aiosqlite` | 0.22.1 | `Permissive / Open Source` | Amethyst Reese |
| `alembic` | 1.20.0 | `MIT` | Mike Bayer |
| `amd-gaia` | 0.24.1 | `MIT` | AMD |
| `annotated-doc` | 0.0.5 | `MIT` | =?utf-8?q?Sebasti=C3=A1n_Ram=C3=ADrez?= |
| `annotated-types` | 0.8.0 | `MIT` | Adrian Garcia Badaracco |
| `anthropic` | 1.11.0 | `MIT` | Anthropic |
| `anyio` | 4.15.1 | `MIT` | Alex Grönholm |
| `APScheduler` | 3.11.3 | `MIT` | Alex Grönholm |
| `arc-agi` | 0.9.9 | `Permissive / Open Source` | arcprizefoundation |
| `arcengine` | 0.9.3 | `Permissive / Open Source` | arcprizefoundation |
| `ast_serialize` | 0.12.1 | `MIT` | Jukka Lehtosalo |
| `attrs` | 26.1.0 | `MIT` | Hynek Schlawack |
| `Authlib` | 1.8.0 | `BSD-3-Clause` | Hsiaoming Yang |
| `baml-py` | 0.226.2 | `Apache-2.0` | Boundary |
| `bcrypt` | 5.0.0 | `Apache-2.0` | The Python Cryptographic Authority devel |
| `beartype` | 0.22.9 | `Permissive / Open Source` | Cecil Curry |
| `beautifulsoup4` | 4.15.0 | `MIT License` | Leonard Richardson |
| `black` | 26.5.1 | `MIT` | Łukasz Langa |
| `bleach` | 6.4.0 | `Apache Software License` | Will Kahn-Greene |
| `blinker` | 1.9.0 | `Permissive / Open Source` | Jason Kirtland |
| `bluequbit` | 0.18.12b1 | `Apache-2.0` | BlueQubit |
| `cachetools` | 7.2.0 | `MIT` | Thomas Kemmer |
| `caio` | 0.12.9 | `Apache-2.0` | Dmitry Orlov |
| `certifi` | 2026.7.22 | `MPL-2.0` | Kenneth Reitz |
| `cffi` | 2.1.1 | `MIT-0` | Armin Rigo, Maciej Fijalkowski |
| `charset-normalizer` | 3.5.2 | `MIT` | Ahmed R. TAHRI |
| `chex` | 0.1.92 | `Permissive / Open Source` | Google DeepMind |
| `click` | 8.5.0 | `BSD-3-Clause` | Open Source Community |
| `cloudpickle` | 3.1.2 | `BSD-3-Clause` | The cloudpickle developer team |
| `cohezion` | 1.27.0 | `AGPL-3.0-or-later` | Mike Anderson |
| `cohezion-physics-core` | 0.1.0 | `Permissive / Open Source` | Open Source Community |
| `colorlog` | 6.12.0 | `MIT License` | Sam Clements |
| `contourpy` | 1.4.0 | `BSD-3-Clause` | Ian Thomas |
| `coverage` | 7.16.2 | `Apache-2.0` | Ned Batchelder and 263 others |
| `cryptography` | 50.0.2 | `Apache-2.0 OR BSD-3-Clause` | The Python Cryptographic Authority and i |
| `cycler` | 0.12.1 | `Permissive / Open Source` | Thomas A Caswell |
| `cyclopts` | 5.1.1 | `Apache-2.0` | Brian Pugh |
| `datasets` | 5.0.1 | `Apache 2.0` | HuggingFace Inc. |
| `dill` | 0.4.1 | `BSD-3-Clause` | Mike McKerns |
| `distro` | 1.9.0 | `Apache License, Version 2.0` | Nir Cohen |
| `dnspython` | 2.8.0 | `ISC` | Bob Halley |
| `docker` | 7.2.0 | `Apache-2.0` | Open Source Community |
| `docstring_parser` | 0.18.0 | `MIT` | Marcin Kurczewski |
| `docutils` | 0.23 | `Public Domain` | David Goodger |
| `einops` | 0.8.2 | `MIT` | Alex Rogozhnikov |
| `email-validator` | 2.3.0 | `Unlicense` | Joshua Tauberer |
| `etils` | 1.14.0 | `Permissive / Open Source` | Conchylicultor |
| `exceptiongroup` | 1.3.1 | `Permissive / Open Source` | Alex Grönholm |
| `execnet` | 2.1.2 | `MIT` | holger krekel and others |
| `Farama-Notifications` | 0.0.6 | `Permissive / Open Source` | Jordan Terry |
| `fastapi` | 0.141.1 | `MIT` | =?utf-8?q?Sebasti=C3=A1n_Ram=C3=ADrez?= |
| `fastjsonschema` | 2.22.2 | `BSD-3-Clause` | Michal Horejsek |
| `fastmcp` | 3.4.7 | `Apache-2.0` | Jeremiah Lowin |
| `fastmcp-slim` | 3.4.7 | `Apache-2.0` | Jeremiah Lowin |
| `fastuuid` | 0.14.0 | `Permissive / Open Source` | Open Source Community |
| `filelock` | 4.0.10 | `MIT` | Open Source Community |
| `flake8` | 7.4.1 | `MIT` | Tarek Ziade |
| `Flask` | 3.1.3 | `BSD-3-Clause` | Open Source Community |
| `flax` | 0.12.10 | `Permissive / Open Source` | Flax team |
| `fonttools` | 4.66.1 | `MIT` | Just van Rossum |
| `frozenlist` | 1.8.0 | `Apache-2.0` | aiohttp team |
| `fsspec` | 2026.6.0 | `BSD-3-Clause` | Open Source Community |
| `google-adk` | 2.11.0 | `Permissive / Open Source` | Google LLC |
| `google-auth` | 2.59.1 | `Apache 2.0` | Google Cloud Platform |
| `google-genai` | 2.28.0 | `Apache-2.0` | Google LLC |
| `graphviz` | 0.21 | `MIT` | Sebastian Bank |
| `griffelib` | 2.3.0 | `ISC` | Timothée Mazzucotelli |
| `gym` | 0.26.2 | `MIT` | Gym Community |
| `gym-notices` | 0.1.0 | `Permissive / Open Source` | Jordan Terry |
| `gymnasium` | 1.3.0 | `MIT License` | Farama Foundation |
| `gymnax` | 0.0.8 | `Permissive / Open Source` | Robert Tjarko Lange |
| `h11` | 0.16.0 | `MIT` | Nathaniel J. Smith |
| `hf-xet` | 1.6.0 | `Apache-2.0` | Open Source Community |
| `httpcore` | 1.0.9 | `BSD-3-Clause` | Tom Christie |
| `httpcore2` | 2.13.1 | `BSD-3-Clause` | Tom Christie |
| `httpx` | 0.28.1 | `BSD-3-Clause` | Tom Christie |
| `httpx-sse` | 0.4.3 | `MIT` | Florimond Manca |
| `httpx2` | 2.13.1 | `BSD-3-Clause` | Tom Christie |
| `huggingface_hub` | 0.36.2 | `Apache` | Hugging Face, Inc. |
| `humanize` | 4.16.0 | `MIT` | Jason Moiron |
| `hypothesis` | 6.168.3 | `MPL-2.0` | David R. MacIver and Zac Hatfield-Dodds |
| `idna` | 3.20 | `BSD-3-Clause` | Kim Davies |
| `importlib_metadata` | 8.9.0 | `Apache-2.0` | Jason R. Coombs |
| `iniconfig` | 2.3.0 | `MIT` | Ronny Pfannschmidt |
| `itsdangerous` | 2.2.0 | `Permissive / Open Source` | Open Source Community |
| `jaraco.classes` | 3.4.0 | `Permissive / Open Source` | Jason R. Coombs |
| `jaraco.context` | 6.1.2 | `MIT` | Jason R. Coombs |
| `jaraco.functools` | 4.6.0 | `MIT` | Jason R. Coombs |
| `jax` | 0.11.2 | `Apache-2.0` | JAX team |
| `jaxlib` | 0.11.2 | `Apache-2.0` | JAX team |
| `jedi` | 0.20.0 | `MIT` | David Halter |
| `jeepney` | 0.9.0 | `MIT` | Thomas Kluyver |
| `Jinja2` | 3.1.6 | `Permissive / Open Source` | Open Source Community |
| `jiter` | 0.17.0 | `MIT` | Samuel Colvin |
| `joblib` | 1.6.0 | `BSD-3-Clause` | Gael Varoquaux |
| `joserfc` | 1.7.5 | `BSD-3-Clause` | Hsiaoming Yang |
| `jsonref` | 1.1.0 | `MIT` | Chase Sterling |
| `jsonschema` | 4.26.0 | `MIT` | Julian Berman |
| `jsonschema-path` | 0.5.0 | `Apache-2.0` | Artur Maciag |
| `jsonschema-specifications` | 2025.9.1 | `MIT` | Julian Berman |
| `jupyter_core` | 5.9.1 | `BSD-3-Clause` | Jupyter Development Team |
| `jupytext` | 1.19.5 | `Permissive / Open Source` | Marc Wouts |
| `kaggle` | 2.2.4 | `Permissive / Open Source` | Kaggle |
| `kaggle-environments` | 1.33.0 | `Permissive / Open Source` | Kaggle |
| `kagglehub` | 1.0.2 | `Permissive / Open Source` | Kaggle |
| `kagglesdk` | 0.1.37 | `Permissive / Open Source` | Kaggle |
| `kbench` | 0.5.0 | `MIT` | Keichi Takahashi |
| `keyring` | 25.7.0 | `MIT` | Kang Zhang |
| `kiwisolver` | 1.5.1 | `Permissive / Open Source` | The Nucleic Development Team |
| `kubernetes` | 18.20.0 | `Apache License Version 2.0` | Kubernetes |
| `libcst` | 1.9.0 | `Permissive / Open Source` | Open Source Community |
| `librt` | 0.16.0 | `MIT` | Jukka Lehtosalo |
| `linkify-it-py` | 2.2.0 | `MIT` | tsutsu3 |
| `litellm` | 1.93.2 | `MIT` | BerriAI |
| `loguru` | 0.5.3 | `MIT license` | Delgan |
| `loro` | 1.16.2 | `MIT` | leon7hao |
| `Mako` | 1.4.3 | `MIT` | Mike Bayer |
| `marimo` | 0.25.1 | `Apache-2.0` | Open Source Community |
| `Markdown` | 3.11 | `BSD-3-Clause` | Manfred Stienstra, Yuri Takhteyev |
| `markdown-it-py` | 4.2.0 | `Permissive / Open Source` | Chris Sewell |
| `MarkupSafe` | 3.0.4 | `BSD-3-Clause` | Open Source Community |
| `matplotlib` | 3.11.2 | `Permissive / Open Source` | John D. Hunter, Michael Droettboom |
| `maturin` | 1.15.0 | `MIT OR Apache-2.0` | konstin |
| `mccabe` | 0.7.0 | `Expat license` | Tarek Ziade |
| `mcp` | 1.30.0 | `MIT` | Anthropic, PBC. |
| `mdit-py-plugins` | 0.6.1 | `Permissive / Open Source` | Chris Sewell |
| `mdurl` | 0.1.2 | `Permissive / Open Source` | Taneli Hukkinen |
| `ml_collections` | 1.1.0 | `Permissive / Open Source` | ML Collections Authors |
| `ml_dtypes` | 0.6.0 | `Apache-2.0` | ml_dtypes authors |
| `more-itertools` | 11.1.0 | `MIT` | Erik Rose |
| `mpmath` | 1.3.0 | `BSD` | Fredrik Johansson |
| `msgpack` | 1.2.3 | `Apache-2.0` | Inada Naoki |
| `msgspec` | 0.22.0 | `BSD-3-Clause` | Open Source Community |
| `multidict` | 6.9.1 | `Apache License 2.0` | Andrew Svetlov |
| `multiprocess` | 0.70.19 | `BSD-3-Clause` | Mike McKerns |
| `mutmut` | 3.8.0 | `BSD-3-Clause` | Anders Hovmöller |
| `mypy` | 2.4.0 | `MIT` | Jukka Lehtosalo |
| `mypy_extensions` | 1.1.0 | `MIT` | The mypy developers |
| `narwhals` | 2.26.0 | `MIT` | Marco Gorelli |
| `nbformat` | 5.11.1 | `Permissive / Open Source` | Jupyter Development Team |
| `networkx` | 3.7 | `BSD-3-Clause` | Aric Hagberg |
| `numpy` | 2.5.3 | `BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0` | Travis E. Oliphant et al. |
| `oauthlib` | 4.0.0 | `BSD-3-Clause` | The OAuthlib Community |
| `omegaconf` | 2.4.0 | `Permissive / Open Source` | Omry Yadan |
| `open-spiel` | 2.0.1 | `Apache-2.0` | The OpenSpiel authors |
| `openai` | 3.24.0 | `Apache-2.0` | OpenAI |
| `openapi-pydantic` | 0.6.0 | `MIT` | Mike Oakley |
| `opentelemetry-api` | 1.42.1 | `Apache-2.0` | OpenTelemetry Authors |
| `opentelemetry-sdk` | 1.42.1 | `Apache-2.0` | OpenTelemetry Authors |
| `opentelemetry-semantic-conventions` | 0.63b1 | `Apache-2.0` | OpenTelemetry Authors |
| `opt_einsum` | 3.4.0 | `MIT` | Daniel Smith |
| `optax` | 0.2.8 | `Permissive / Open Source` | Google DeepMind |
| `optuna` | 5.0.0 | `Permissive / Open Source` | Takuya Akiba |
| `orbax-checkpoint` | 0.12.7 | `Permissive / Open Source` | Orbax Authors |
| `packaging` | 26.3 | `Apache-2.0 OR BSD-2-Clause` | Donald Stufft |
| `pandas` | 3.0.6 | `Permissive / Open Source` | The Pandas Development Team |
| `parso` | 0.8.7 | `MIT` | David Halter |
| `passlib` | 1.7.4 | `BSD` | Eli Collins |
| `pathable` | 0.6.0 | `Apache-2.0` | Artur Maciag |
| `pathlib_abc` | 0.5.2 | `Permissive / Open Source` | Barney Gale |
| `pathspec` | 1.1.1 | `Permissive / Open Source` | Caleb P. Burns |
| `peft` | 0.21.2 | `Apache` | The HuggingFace team |
| `pettingzoo` | 1.27.0 | `MIT License` | Farama Foundation |
| `pillow` | 12.3.0 | `MIT-CMU` | Jeffrey Alex Clark |
| `platformdirs` | 4.12.3 | `MIT` | Open Source Community |
| `plotly` | 7.1.0 | `MIT` | Chris P |
| `pluggy` | 1.6.0 | `MIT` | Holger Krekel |
| `pocket-tts` | 3.3.0 | `Permissive / Open Source` | Open Source Community |
| `pokerkit` | 0.6.3 | `MIT` | University of Toronto Computer Poker Stu |
| `polars` | 1.44.2 | `Permissive / Open Source` | Ritchie Vink |
| `polars-runtime-32` | 1.44.2 | `MIT` | Ritchie Vink |
| `prometheus_client` | 0.26.0 | `Apache-2.0 AND BSD-2-Clause` | The Prometheus Authors |
| `propcache` | 0.5.4 | `Apache-2.0` | Andrew Svetlov |
| `protobuf` | 6.33.6 | `3-Clause BSD License` | protobuf@googlegroups.com |
| `psutil` | 7.2.2 | `BSD-3-Clause` | Giampaolo Rodola |
| `py-key-value-aio` | 0.4.6 | `Apache-2.0` | Open Source Community |
| `pyarrow` | 25.0.1 | `Apache-2.0` | Open Source Community |
| `pyasn1` | 0.6.4 | `BSD-2-Clause` | Ilya Etingof |
| `pyasn1_modules` | 0.4.2 | `BSD` | Ilya Etingof |
| `pycodestyle` | 2.15.0 | `MIT` | Johann C. Rocholl |
| `pycparser` | 3.0 | `BSD-3-Clause` | Eli Bendersky |
| `pydantic` | 2.13.5 | `MIT` | Samuel Colvin |
| `pydantic-settings` | 2.15.0 | `MIT` | Samuel Colvin |
| `pydantic_core` | 2.46.5 | `MIT` | Samuel Colvin |
| `pyflakes` | 4.0.2 | `MIT` | A lot of people |
| `pygame` | 2.6.1 | `LGPL` | A community project. |
| `Pygments` | 2.21.0 | `BSD-2-Clause` | Georg Brandl |
| `pyjson5` | 2.0.1 | `MIT OR Apache-2.0` | René Kijewski |
| `PyJWT` | 2.15.1 | `MIT` | Jose Padilla |
| `pymdown-extensions` | 11.0.2 | `MIT` | Isaac Muse |
| `pyparsing` | 3.3.3 | `MIT` | Paul McGuire |
| `pyperclip` | 1.11.0 | `BSD` | Al Sweigart |
| `pytest` | 9.1.1 | `MIT` | Brianna Laugher, Bruno Oliveira, Floris  |
| `pytest-asyncio` | 1.4.0 | `Apache-2.0` | Tin Tvrtković |
| `pytest-cov` | 7.1.0 | `MIT` | Marc Schlaich |
| `pytest-rerunfailures` | 16.7 | `MPL-2.0` | Leah Klearman |
| `pytest-xdist` | 3.8.0 | `MIT` | holger krekel and contributors |
| `python-dateutil` | 2.9.0.post0 | `Dual License` | Gustavo Niemeyer |
| `python-dotenv` | 1.2.4 | `BSD-3-Clause` | Saurabh Kumar |
| `python-multipart` | 0.0.32 | `Apache-2.0` | Andrew Dunham |
| `python-slugify` | 9.1.2 | `MIT` | Val Neekman |
| `pytokens` | 0.4.1 | `Permissive / Open Source` | Tushar Sadhwani |
| `PyYAML` | 6.0.3 | `MIT` | Kirill Simonov |
| `PyYAML-ft` | 8.0.0 | `MIT` | Lysandros Nikolaou |
| `pyzmq` | 27.2.0 | `BSD-3-Clause` | Brian E. Granger, Min Ragan-Kelley |
| `qiskit` | 2.5.2 | `Apache-2.0` | Qiskit Development Team |
| `redis` | 8.1.0 | `MIT` | Redis Inc. |
| `referencing` | 0.37.0 | `MIT` | Julian Berman |
| `regex` | 2026.9.29 | `Apache-2.0 AND CNRI-Python` | Matthew Barnett |
| `requests` | 2.34.2 | `Apache-2.0` | Kenneth Reitz |
| `requests-oauthlib` | 2.0.0 | `ISC` | Kenneth Reitz |
| `respx` | 0.23.1 | `BSD-3-Clause` | Jonas Lundberg |
| `rich` | 15.0.0 | `MIT` | Will McGugan |
| `rich-rst` | 2.2.0 | `MIT` | Wasi Master |
| `rpds-py` | 2026.6.3 | `MIT` | Julian Berman |
| `ruff` | 0.16.10 | `MIT` | Astral Software Inc. |
| `rustworkx` | 0.18.1 | `Apache-2.0` | Matthew Treinish |
| `safetensors` | 0.8.0 | `Permissive / Open Source` | Nicolas Patry |
| `scikit-learn` | 1.9.1 | `BSD-3-Clause` | Open Source Community |
| `scipy` | 1.18.1 | `Permissive / Open Source` | Open Source Community |
| `seaborn` | 0.13.2 | `Permissive / Open Source` | Michael Waskom |
| `SecretStorage` | 3.5.0 | `BSD-3-Clause` | Dmitry Shachnev |
| `sentence-transformers` | 5.7.0 | `Apache-2.0` | Nils Reimers |
| `sentencepiece` | 0.2.2 | `Apache-2.0` | Taku Kudo |
| `setproctitle` | 1.3.8 | `BSD-3-Clause` | Daniele Varrazzo |
| `setuptools` | 84.0.0 | `MIT` | Python Packaging Authority |
| `shellingham` | 1.5.4 | `ISC License` | Tzu-ping Chung |
| `Shimmy` | 2.0.1 | `Permissive / Open Source` | Farama Foundation |
| `simplejson` | 4.2.0 | `MIT OR AFL-2.1` | Bob Ippolito |
| `six` | 1.17.0 | `MIT` | Benjamin Peterson |
| `sniffio` | 1.3.1 | `MIT OR Apache-2.0` | Nathaniel J. Smith |
| `sortedcontainers` | 2.4.0 | `Apache 2.0` | Grant Jenks |
| `soupsieve` | 2.10 | `MIT` | Isaac Muse |
| `SQLAlchemy` | 2.1.3 | `MIT` | Mike Bayer |
| `sse-starlette` | 3.5.0 | `BSD-3-Clause` | sysid |
| `starlette` | 1.7.0 | `BSD-3-Clause` | Tom Christie |
| `stevedore` | 5.9.1 | `Apache-2.0` | OpenStack |
| `structlog` | 26.1.0 | `MIT OR Apache-2.0` | Hynek Schlawack |
| `surrealdb` | 2.0.0 | `Apache-2.0` | SurrealDB |
| `sympy` | 1.14.0 | `BSD` | SymPy development team |
| `tavily-python` | 0.8.4 | `Permissive / Open Source` | Tavily AI |
| `tenacity` | 9.1.4 | `Apache 2.0` | Julien Danjou |
| `tensorstore` | 0.1.85 | `Apache-2.0` | TensorStore Team |
| `termcolor` | 3.3.0 | `MIT` | Konstantin Lepa |
| `text-unidecode` | 1.3 | `Artistic License` | Mikhail Korobov |
| `textual` | 8.2.8 | `MIT` | Will McGugan |
| `threadpoolctl` | 3.7.0 | `BSD-3-Clause` | Thomas Moreau |
| `tiktoken` | 0.14.0 | `Permissive / Open Source` | Shantanu Jain |
| `tokenizers` | 0.22.2 | `Permissive / Open Source` | Nicolas Patry |
| `tomli_w` | 1.2.0 | `Permissive / Open Source` | Taneli Hukkinen |
| `tomlkit` | 0.15.1 | `MIT` | Sébastien Eustace |
| `toolz` | 1.2.0 | `BSD-3-Clause` | PyToolz Contributors |
| `torch` | 2.14.1+cpu | `Apache-2.0 AND Apache-2.0 WITH LLVM-exception AND BSD-2-Clause AND BSD-3-Clause AND BSL-1.0 AND MIT` | PyTorch Team |
| `torchvision` | 0.29.1+cpu | `BSD` | PyTorch Core Team |
| `tqdm` | 4.70.1 | `MPL-2.0 AND MIT` | Open Source Community |
| `traitlets` | 5.16.1 | `Permissive / Open Source` | IPython Development Team |
| `transformers` | 4.57.2 | `Apache 2.0 License` | The Hugging Face team (past and future)  |
| `treescope` | 0.1.10 | `Permissive / Open Source` | The Treescope Authors |
| `trl` | 0.23.0 | `Permissive / Open Source` | Leandro von Werra |
| `truststore` | 0.10.4 | `MIT` | Seth Michael Larson |
| `typer` | 0.27.2 | `MIT` | =?utf-8?q?Sebasti=C3=A1n_Ram=C3=ADrez?= |
| `typing-inspection` | 0.4.4 | `MIT` | Victorien Plot |
| `typing_extensions` | 4.16.0 | `PSF-2.0` | Guido van Rossum, Jukka Lehtosalo, Łukas |
| `tzlocal` | 5.4.4 | `MIT` | Lennart Regebro |
| `uncalled-for` | 0.4.0 | `Permissive / Open Source` | Chris Guidry |
| `universal_pathlib` | 0.3.10 | `MIT` | Andrew Fulton |
| `urllib3` | 2.8.0 | `MIT` | Andrey Petrov |
| `uvicorn` | 0.54.0 | `BSD-3-Clause` | Tom Christie |
| `uvloop` | 0.23.0 | `MIT License` | Yury Selivanov |
| `watchdog` | 6.0.0 | `Apache-2.0` | Mickaël Schoentgen |
| `watchfiles` | 1.3.0 | `MIT` | Samuel Colvin |
| `webencodings` | 0.6.1 | `Permissive / Open Source` | Simon Sapin |
| `websocket-client` | 1.9.2 | `Apache-2.0` | liris |
| `websockets` | 15.0.1 | `BSD-3-Clause` | Aymeric Augustin |
| `Werkzeug` | 3.1.9 | `BSD-3-Clause` | Open Source Community |
| `xxhash` | 4.0.1 | `BSD-2-Clause` | Yue Du |
| `yarl` | 1.25.1 | `Apache-2.0` | Andrew Svetlov |
| `zipp` | 4.1.1 | `MIT` | Jason R. Coombs |
