"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import importlib.util
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import microsoft.teams.apps.routing.activity_route_configs as activity_config

# Import the activity config directly without going through the package hierarchy
activity_config_path = (
    Path(__file__).parent.parent / "src" / "microsoft" / "teams" / "app" / "routing" / "activity_route_configs.py"
)

# Load the activity config module directly because we don't want to have a dependency on the package
# as it will lead to a circular dependency
# https://stackoverflow.com/questions/67631/how-can-i-import-a-module-dynamically-given-the-full-path
if not TYPE_CHECKING:
    import sys

    # Add the src directory to sys.path so relative imports work
    src_path = str(Path(__file__).parent.parent / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    spec = importlib.util.spec_from_file_location(
        "microsoft.teams.apps.routing.activity_route_configs", activity_config_path
    )
    assert spec is not None, f"Could not find activity_route_configs.py at {activity_config_path}"
    activity_config = importlib.util.module_from_spec(spec)
    assert spec.loader is not None, f"Could not load activity_route_configs.py at {activity_config_path}"
    spec.loader.exec_module(activity_config)

ACTIVITY_ROUTES = activity_config.ACTIVITY_ROUTES
ActivityConfig = activity_config.ActivityConfig


def generate_imports() -> str:
    """Generate import statements for the generated file."""
    imports = {
        "from abc import ABC, abstractmethod",
        "from typing import Callable, Optional, Union, Awaitable, overload",
        "from .activity_context import ActivityContext",
        "from .router import ActivityRouter",
        "from .type_validation import validate_handler_type",
        "from .activity_route_configs import ACTIVITY_ROUTES",
        "from microsoft.teams.models import ActivityBase",
        "from logging import Logger",
        "from microsoft.teams.api import InvokeResponse",
    }

    # Add imports for each activity class
    for config in ACTIVITY_ROUTES.values():
        # Use explicit input_type_name if provided, otherwise fall back to __name__
        class_name = config.input_model if isinstance(config.input_model, str) else config.input_model.__name__
        if class_name == "ActivityBase":
            imports.add(f"from microsoft.teams.api.models import {class_name}")
        else:
            imports.add(f"from microsoft.teams.api.activities import {class_name}")
        if config.output_model or config.output_type_name:
            # Use explicit output_type_name if provided, otherwise fall back to __name__
            output_class_name = config.output_type_name
            if not output_class_name:
                if config.output_model:
                    output_class_name = config.output_model.__name__
                else:
                    raise ValueError(f"Output type for {config.name} must be specified in the config or as a string.")
            imports.add(f"from microsoft.teams.api.models.invoke_response import {output_class_name}")

    return "\n".join(sorted(imports))


def generate_method(config: ActivityConfig, config_key: str) -> str:
    """Generate a single handler method with strict typing and runtime validation."""
    method_name = config.method_name
    activity_name = config.name

    # Use the explicit input_type_name if provided, otherwise fall back to __name__
    input_class_name = config.input_model if isinstance(config.input_model, str) else config.input_model.__name__

    # Determine output type
    if config.output_type_name or config.output_model:
        # Use explicit output_type_name if provided, otherwise fall back to __name__
        output_class_name = config.output_type_name
        if not output_class_name:
            if config.output_model:
                output_class_name = config.output_model.__name__
            else:
                raise ValueError(f"Output type for {method_name} must be specified in the config or as a string.")
        if config.is_invoke:
            output_class_name = f"Union[InvokeResponse[{output_class_name}], {output_class_name}]"
        output_type = f"Awaitable[{output_class_name}]"
    else:
        if config.is_invoke:
            output_type = "Awaitable[Union[InvokeResponse[None], None]]"
        else:
            output_type = "Awaitable[None]"

    returnTypeStr = f"Callable[[ActivityContext[{input_class_name}]], {output_type}]"
    returnTypeDecoratorStr = f"Callable[[{returnTypeStr}], {returnTypeStr}]"

    return f'''    @overload
    def {method_name}(self, handler: {returnTypeStr}) -> {returnTypeStr}: ...
        
    @overload
    def {method_name}(self) -> {returnTypeDecoratorStr}: ...
        
    def {method_name}(self, handler: Optional[{returnTypeStr}] = None) -> {returnTypeDecoratorStr} | {returnTypeStr}:
        """Register a {activity_name} activity handler."""
        def decorator(func: {returnTypeStr}) -> {returnTypeStr}:
            validate_handler_type(self.logger, func, {input_class_name}, "{method_name}", "{input_class_name}")
            config = ACTIVITY_ROUTES["{config_key}"]
            self.router.add_handler(config.selector, func)
            return func

        if handler is not None:
            return decorator(handler)
        return decorator'''  # noqa: E501, W291, W293, W391


def generate_mixin_class() -> str:
    """Generate the complete ActivityHandlerMixin class."""
    methods: list[str] = []

    for config_key, config in ACTIVITY_ROUTES.items():
        methods.append(generate_method(config, config_key))

    methods_code = "\n\n".join(methods)

    return f'''class GeneratedActivityHandlerMixin(ABC):
    """Mixin class providing typed activity handler registration methods."""

    @property
    @abstractmethod
    def router(self) -> ActivityRouter:
        """The activity router instance. Must be implemented by the concrete class."""
        pass

    @property
    @abstractmethod
    def logger(self) -> Logger:
        """The logger instance used by the app."""
        pass

{methods_code}'''


def generate_file_header() -> str:
    """Generate the file header with copyright and description."""
    return '''"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.

GENERATED FILE - DO NOT EDIT MANUALLY
This file is generated by generate_handlers.py based on activity_config.py

To regenerate, run:
uv run generate-activity-handlers
"""'''


def generate_activity_handlers():
    """Generate the complete activity handlers file."""
    print("🔧 Generating activity handlers...")

    # Build the complete file content
    content_parts = [
        generate_file_header(),
        "",
        generate_imports(),
        "",
        "",
        generate_mixin_class(),
    ]

    generated_code = "\n".join(content_parts)

    # Write to the message_handler directory in the source code
    # Use Path(__file__) to find this script's location, then navigate to the target
    script_dir = Path(__file__).parent
    source_dir = script_dir.parent / "src" / "microsoft" / "teams" / "app" / "routing"
    output_path = source_dir / "generated_handlers.py"

    # Ensure the target directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(generated_code)

    print(f"✅ Generated {len(ACTIVITY_ROUTES)} activity handlers in {output_path}")
    print("📝 Generated methods:")
    for config in ACTIVITY_ROUTES.values():
        print(f"   - {config.method_name}() for {config.name} activities")

    # execute poe fmt on the generated file
    subprocess.run(["poe", "lint", "--select", "I", "--select", "F401", "--fix"], check=True)
    subprocess.run(["poe", "fmt", str(output_path)], check=True)


if __name__ == "__main__":
    generate_activity_handlers()
