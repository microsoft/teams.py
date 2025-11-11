# Microsoft Teams SDK for Python

Microsoft Teams SDK for Python is a comprehensive SDK for building Microsoft Teams applications, bots, and AI agents using Python. This is a monorepo with workspace structure containing core packages and test applications.

**Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.**

## Working Effectively

### Prerequisites and Setup
- Install UV: `python -m pip install uv` (curl method fails due to network restrictions)
- Python version: 3.12+ (confirmed working with 3.12.3)
- Verify versions: `uv --version && python --version`

### Bootstrap, Build, and Test Repository
**CRITICAL TIMING NOTES: NEVER CANCEL any build or test commands. Set timeouts appropriately:**

1. **Install dependencies** (8 seconds - set timeout to 60+ seconds):
   ```bash
   uv sync --all-packages --group dev
   ```

2. **Activate virtual environment** (instant) or use `uv run` for commands:
   ```bash
   # On Linux/Mac
   source .venv/bin/activate

   # On Windows
   .venv\Scripts\Activate

   # Alternative: Use uv run (no activation needed)
   # Example: uv run pytest packages
   ```

3. **Install pre-commit hooks** (<1 second):
   ```bash
   pre-commit install
   ```

4. **Run linting** (<1 second - 376 files checked):
   ```bash
   ruff check
   ```

5. **Run formatting check** (<1 second):
   ```bash
   ruff format --check
   ```

6. **Run type checking** (9 seconds - set timeout to 30+ seconds):
   ```bash
   pyright
   ```

7. **Run tests** (18 seconds - 337 tests - set timeout to 60+ seconds):
   ```bash
   pytest packages
   ```

8. **Build all packages** (3 seconds - set timeout to 60+ seconds):
   ```bash
   uv build --all-packages
   ```

### Quick Development Commands
- **Combined format + lint**: `poe check` (<1 second)
- **Format code**: `poe fmt` or `ruff format`
- **Lint only**: `poe lint` or `ruff check`
- **Test only**: `poe test` or `pytest packages`

## Validation Scenarios

**ALWAYS manually validate changes by running at least one complete test application scenario:**

### Basic Teams App Validation
1. Navigate to test app: `cd tests/echo`
2. Start the app: `python src/main.py`
3. **Expected output**: App starts on ports 3978 and 3979 with logs:
   ```
   [INFO] @teams/app.HttpPlugin listening on port 3978 🚀
   [INFO] @teams/app.DevToolsPlugin listening on port 3979 🚀
   ```
4. **Test endpoints**:
   - Health check: `curl http://localhost:3978/` (returns `{"status":"healthy","port":3978}`)
   - DevTools UI: `curl http://localhost:3979/devtools` (returns HTML page)
5. Stop with Ctrl+C

### Required Pre-commit Validation
**ALWAYS run before committing changes or CI will fail:**
```bash
# These commands must pass:
ruff format --check  # Format validation
ruff check          # Linting validation
pyright             # Type checking validation
```

## Repository Structure and Navigation

### Core Packages (`/packages`)
- **microsoft-teams-apps**: Main application framework
- **microsoft-teams-ai**: AI integration functionality
- **microsoft-teams-api**: Teams API client
- **microsoft-teams-cards**: Adaptive cards support
- **microsoft-teams-common**: Shared utilities
- **microsoft-teams-devtools**: Development and debugging tools
- **microsoft-teams-graph**: Microsoft Graph integration
- **microsoft-teams-openai**: OpenAI integration
- **microsoft-teams-mcpplugin**: MCP protocol integration

### Test Applications (`/tests`)
Available test apps for development and validation:
- **echo**: Basic message echo bot (recommended for quick validation)
- **ai-test**: AI functionality testing
- **dialogs**: Dialog handling examples
- **message-extensions**: Message extension samples
- **oauth**: OAuth authentication examples
- **graph**: Microsoft Graph integration examples
- **stream**: Streaming functionality examples

### Creating New Components
- **New package**: `cookiecutter templates/package -o packages`
- **New test app**: `cookiecutter templates/test -o tests`

## Common Development Tasks

### Testing Changes
1. **Run commands with UV** (recommended): Use `uv run pytest packages/[package-name]` or **activate virtual environment**: `source .venv/bin/activate`
2. **Run affected tests**: `pytest packages/[package-name]` for specific package (or `uv run pytest packages/[package-name]`)
3. **Validate with test app**: Use `tests/echo` for basic functionality validation (starts a blocking server process)
4. **Check DevTools web app**: Access http://localhost:3979/devtools when app is running

### Debugging and Development
- **DevTools Web App**: Available at port 3979 when running any test app
- **Logging**: Apps provide structured logging for debugging
- **Hot reload**: No hot reload - restart apps after changes
- **Port conflicts**: Default ports are 3978 (main) and 3979 (devtools)

### CI/CD Integration
The CI pipeline (`.github/workflows/ci.yml`) runs:
1. Dependency installation with UV
2. Ruff linting and formatting validation
3. PyRight type checking
4. Full test suite execution

**Match CI requirements locally with**: `poe check && pyright && pytest packages`

## Troubleshooting

### Known Issues
- **generate-activity-handlers command fails**: Path bug exists but doesn't affect normal development workflow
- **Network restrictions**: Use `python -m pip install uv` instead of curl-based installation
- **Build timeouts**: UV operations are fast (3-18 seconds) but use generous timeouts for reliability
- **Pre-commit hook installation may timeout**: If `pre-commit install` fails with PyPI timeout, use `git commit --no-verify` for urgent commits

### Common Problems
- **Import errors**: Ensure virtual environment is activated (`source .venv/bin/activate`) or use `uv run` commands
- **UV not found**: Install with pip: `python -m pip install uv`
- **Test failures**: Run `uv sync --all-packages --group dev` to update dependencies
- **Type errors**: Run `pyright` to catch type issues before CI
- **Format issues**: Run `ruff format` to auto-fix formatting
- **Pre-commit hook timeouts**: Use `git commit --no-verify` to bypass hooks temporarily during network issues

## Critical Reminders

- **NEVER CANCEL builds or tests** - Commands complete in 3-18 seconds but network delays may occur
- **ALWAYS use timeouts of 60+ seconds** for any UV or build commands
- **ALWAYS activate virtual environment or use uv run** before running Python commands
- **ALWAYS validate with a test app** after making changes to core packages
- **ALWAYS run pre-commit validation** (`poe check && pyright`) before committing
- **NEVER skip manual testing** - Automated tests don't cover integration scenarios

## Repository Quick Reference

### Package Root Structure
```
.
├── .github/          # GitHub workflows and configs
├── packages/         # Core SDK packages
├── tests/           # Test applications
├── templates/       # Cookiecutter templates
├── scripts/         # Build and release scripts
├── pyproject.toml   # Workspace and tool configuration
├── uv.lock         # Dependency lock file
└── README.md       # Main documentation
```

### Essential Files
- **pyproject.toml**: Workspace configuration, dependencies, tool settings
- **uv.lock**: Locked dependency versions (do not edit manually)
- **.pre-commit-config.yaml**: Git hook configuration
- **.github/workflows/ci.yml**: CI pipeline definition