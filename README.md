> [!CAUTION]
> This project is in active development and not ready for production use. It has not been publicly announced yet.

## Getting Started

### Prerequisites

Note: Ensure uv version is >= 0.8.11
Install [uv](https://docs.astral.sh/uv/getting-started/installation/)

### Installing

1. `uv sync --all-packages --group dev` - it installs the virtual env and dependencies
   - If you are using Windows, you may need to manually install [cargo](https://doc.rust-lang.org/cargo/getting-started/installation.html)
2. Activate virtual env

- Mac: `source .venv/bin/activate`
- Windows: `.venv\Scripts\Activate`

> **Note:** After the initial setup, you need to activate the virtual environment each time you start a new terminal session

3. Install pre-commit hooks: `pre-commit install`

## Creating a new package

We use [cookiecutter](https://cookiecutter.readthedocs.io/en/latest/README.html) to create new packages. To create a new package, run:

```bash
cookiecutter templates/package -o packages
```

Follow the prompts to name the package and the directory. It should create the package folder in the `packages` directory.

## Creating a new test package

Similarly, to create a new test package, run:

```bash
cookiecutter templates/test -o tests
```