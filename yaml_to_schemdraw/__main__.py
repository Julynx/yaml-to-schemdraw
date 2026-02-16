"""
Convert YAML to Schemdraw
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import schemdraw
import schemdraw.dsp
import schemdraw.flow
import schemdraw.logic
from ruamel.yaml import YAML

from .constants import ALLOWED_ATTRS

MIN_SPLIT_LENGTH = 2


def from_dict(dictionary: Dict[str, Any]) -> schemdraw.Drawing:
    """Builds a schemdraw.Drawing object from a dictionary definition.

    Args:
        dictionary: The dictionary containing the drawing definition.

    Returns:
        The configured schemdraw.Drawing object.
    """
    config = dictionary.pop("config", {})
    with schemdraw.Drawing(show=False, **config) as drawing:
        components = {}
        for key, value in dictionary.items():
            if _is_drawing_state(value):
                _handle_drawing_state(value, drawing)
                continue

            if _is_drawing_method(value):
                _handle_drawing_method(value, drawing, components)
                continue

            result = _execute_chain(value, components, drawing)
            components[key] = result

            if isinstance(result, schemdraw.elements.Element):
                drawing.add(result)

        return drawing


def from_yaml_file(file_path: str) -> schemdraw.Drawing:
    """Builds a schemdraw.Drawing object from a YAML file definition.

    Args:
        file_path: The path to the YAML file containing the drawing definition.

    Returns:
        The configured schemdraw.Drawing object.
    """
    yaml = YAML()
    return from_dict(yaml.load(Path(file_path)))


def from_yaml_string(yaml_string: str) -> schemdraw.Drawing:
    """Builds a schemdraw.Drawing object from a YAML string definition.

    Args:
        yaml_string: The YAML string containing the drawing definition.

    Returns:
        The configured schemdraw.Drawing object.
    """
    yaml = YAML()
    return from_dict(yaml.load(yaml_string))


def _safe_getattr(obj: Any, name: str) -> Any:
    """Safely gets an attribute from an object, checking against a whitelist.

    Args:
        obj: The object to get the attribute from.
        name: The name of the attribute to get.

    Returns:
        The attribute if it is allowed, None otherwise.
    """

    if name not in ALLOWED_ATTRS:
        raise ValueError(f"Attribute '{name}' not allowed")

    return getattr(obj, name)


def _is_drawing_state(value: Any) -> bool:
    """Checks if the value represents a drawing state command.

    Args:
        value: The value to check.

    Returns:
        True if the value is a drawing state command, False otherwise.
    """
    return isinstance(value, list) and len(value) > 0 and value[0] == "drawing_state"


def _handle_drawing_state(value: List[str], drawing: schemdraw.Drawing) -> None:
    """Handles drawing state commands like push and pop.

    Args:
        value: The command list (e.g., ['drawing_state', 'push']).
        drawing: The schemdraw.Drawing object.
    """
    if len(value) < MIN_SPLIT_LENGTH:
        return
    command = value[1]
    if command == "push":
        drawing.push()
    elif command == "pop":
        drawing.pop()


def _is_drawing_method(value: Any) -> bool:
    """Checks if the value represents a drawing method call.

    Args:
        value: The value to check.

    Returns:
        True if the value is a drawing method call, False otherwise.
    """
    return isinstance(value, list) and len(value) > 0 and value[0] == "drawing_method"


def _handle_drawing_method(
    value: List[Any], drawing: schemdraw.Drawing, components: Dict[str, Any]
) -> None:
    """Handles drawing methods like move.

    Args:
        value: The method call list (e.g., ['drawing_method', 'move', ...]).
        drawing: The schemdraw.Drawing object.
        components: A dictionary of existing components for reference resolution.

    Raises:
        AttributeError: If the method does not exist on the drawing object.
    """
    if len(value) < MIN_SPLIT_LENGTH:
        return
    method_name = value[1]
    args = value[2:]

    positional, keyword = _build_args_kwargs(args, method_name, components, drawing)

    if hasattr(drawing, method_name):
        method = _safe_getattr(drawing, method_name)
        method(*positional, **keyword)
    else:
        raise AttributeError(f"Drawing object has no attribute '{method_name}'")


def _resolve_reference(value: str, components: Dict[str, Any]) -> Any:
    """Resolves a component reference string (e.g. 'S1.c') to the actual object
    attribute.

    Args:
        value: The reference string.
        components: A dictionary of existing components.

    Returns:
        The resolved attribute or object.

    Raises:
        ValueError: If the component name (first part of the reference) is not found.
    """
    parts = value.split(".")
    obj = components.get(parts[0])
    if obj is None:
        raise ValueError(f"Component '{parts[0]}' not found")

    for part in parts[1:]:
        obj = _safe_getattr(obj, part)
    return obj


def _process_value(
    value: Any,
    method_name: str,
    components: Dict[str, Any],
    drawing: schemdraw.Drawing,
) -> Any:
    """Processes a single value, handling references, types, and recursive structures.

    This function handles:
    - String references to other components.
    - Numeric scaling for positioning methods.
    - Recursive processing of lists and dictionaries.
    - Nested chain execution for component definitions within dictionaries.

    Args:
        value: The value to process.
        method_name: The name of the method where this value is used (for context).
        components: A dictionary of existing components.
        drawing: The schemdraw.Drawing object.

    Returns:
        The processed value.
    """
    if isinstance(value, str):
        if value.split(".")[0] in components:
            return _resolve_reference(value, components)
        return value

    if isinstance(value, (int, float)):
        positioning_methods = {"right", "left", "up", "down"}
        if method_name in positioning_methods:
            return drawing.unit * value
        return value

    if isinstance(value, list):
        return [_process_value(val, method_name, components, drawing) for val in value]

    if isinstance(value, dict):
        if len(value) == 1:
            try:
                return _execute_chain([value], components, drawing)
            except Exception:
                pass

        return {
            key: _process_value(val, method_name, components, drawing)
            for key, val in value.items()
        }

    return value


def _build_args_kwargs(
    args: List[Any],
    method_name: str,
    components: Dict[str, Any],
    drawing: schemdraw.Drawing,
) -> Tuple[List[Any], Dict[str, Any]]:
    """Separates and processes positional and keyword arguments.

    Args:
        args: A list of mixed positional and keyword arguments (as dicts).
        method_name: The name of the method these arguments are for.
        components: A dictionary of existing components.
        drawing: The schemdraw.Drawing object.

    Returns:
        A tuple containing:
        - A list of processed positional arguments.
        - A dictionary of processed keyword arguments.
    """
    args = args or []
    positional = []
    keyword = {}

    for arg in args:
        if isinstance(arg, dict):
            keyword.update(arg)
        else:
            positional.append(arg)

    processed_positional = [
        _process_value(arg, method_name, components, drawing) for arg in positional
    ]
    processed_keyword = {
        key: _process_value(val, method_name, components, drawing)
        for key, val in keyword.items()
    }

    return processed_positional, processed_keyword


def _resolve_object(name: str) -> Any:
    """Resolves a dot-notation string to a Python object.

    Args:
        name: The dot-notation string (e.g., 'schemdraw.elements.Resistor').

    Returns:
        The resolved Python object.

    Raises:
        AttributeError: If any part of the path cannot be resolved.
    """
    obj = schemdraw
    for part in name.split("."):
        obj = _safe_getattr(obj, part)
    return obj


def _execute_chain(
    component_def: List[Any], components: Dict[str, Any], drawing: schemdraw.Drawing
) -> Optional[Any]:
    """Executes a chain of method calls to instantiate and configure a component.

    This function handles two main formats:
    1. [ModulePath, ClassName, Method1, ...] -> e.g. ['elements', 'Resistor', ...]
    2. [ClassPath, Method1, ...] -> e.g. ['elements.Gap', ...]

    Args:
        component_def: A list defining the component and associated method calls.
        components: A dictionary of existing components for reference resolution.
        drawing: The schemdraw.Drawing object.

    Returns:
        The instantiated and configured component object, or None if the definition is
        empty.

    Raises:
        ValueError: If an invalid method name is encountered.
        AttributeError: If a class or method cannot be found.
    """
    if len(component_def) == 0:
        return None

    # 1. Process first item (Module or Class)
    item = component_def[0]
    if isinstance(item, dict):
        name = list(item.keys())[0]
        args = item[name]
        if isinstance(args, dict):
            args = [args]
        elif not isinstance(args, list):
            args = [args]
    else:
        name = item
        args = []

    obj = _resolve_object(name)

    start_index = 1

    if callable(obj):
        positional, keyword = _build_args_kwargs(args, name, components, drawing)
        obj = obj(*positional, **keyword)
    elif len(component_def) > 1:
        start_index = 2
        class_item = component_def[1]

        if isinstance(class_item, dict):
            class_name = list(class_item.keys())[0]
            class_args = class_item[class_name]
            if isinstance(class_args, dict):
                class_args = [class_args]
            elif not isinstance(class_args, list):
                class_args = [class_args]
        else:
            class_name = class_item
            class_args = []

        if hasattr(obj, class_name):
            obj_class = _safe_getattr(obj, class_name)
            if callable(obj_class):
                positional, keyword = _build_args_kwargs(
                    class_args, class_name, components, drawing
                )
                obj = obj_class(*positional, **keyword)
            else:
                obj = obj_class
        else:
            raise AttributeError(f"Module {name} has no attribute {class_name}")

    # 3. Process remaining items as methods on the instance
    for item in component_def[start_index:]:
        if isinstance(item, dict):
            method_name = list(item.keys())[0]
            args = item[method_name]
        else:
            method_name = item
            args = []

        if isinstance(args, dict):
            args = [args]
        elif not isinstance(args, list):
            args = [args]

        positional, keyword = _build_args_kwargs(args, method_name, components, drawing)

        if hasattr(obj, method_name):
            method = _safe_getattr(obj, method_name)
            result = method(*positional, **keyword)
            if result is not None:
                obj = result
        else:
            raise AttributeError(f"Object {obj} has no attribute {method_name}")

    return obj
