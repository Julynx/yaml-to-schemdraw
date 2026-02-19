"""
Convert YAML to Schemdraw.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import schemdraw
import schemdraw.dsp
import schemdraw.flow
import schemdraw.logic
from ruamel.yaml import YAML

from .constants import ALLOWED_ATTRS


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
            if isinstance(value, dict) and "drawing_state" in value:
                _handle_drawing_state(value["drawing_state"], drawing)
                continue

            if isinstance(value, dict) and "drawing_method" in value:
                _handle_drawing_method(value["drawing_method"], drawing, components)
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
    """Safely gets an attribute from an object, checking against an allowlist.

    Checks the static allowlist first. If the name is not found, falls back
    to checking whether the object exposes it as a dynamic anchor (e.g.,
    user-defined Ic pin names or element position attributes).

    Args:
        obj: The object to get the attribute from.
        name: The name of the attribute to get.

    Returns:
        The attribute value.

    Raises:
        ValueError: If the attribute name is not in the allowlist and is not
            a recognized dynamic anchor on the object.
    """
    if name not in ALLOWED_ATTRS:
        if name in getattr(obj, "absanchors", {}):
            return getattr(obj, name)
        raise ValueError(f"Attribute '{name}' not allowed")
    return getattr(obj, name)


def _handle_drawing_state(command: str, drawing: schemdraw.Drawing) -> None:
    """Handles drawing state commands like push and pop.

    Args:
        command: The state command string (e.g., 'push' or 'pop').
        drawing: The schemdraw.Drawing object.
    """
    if command == "push":
        drawing.push()
    elif command == "pop":
        drawing.pop()


def _handle_drawing_method(
    method_def: Dict[str, Any], drawing: schemdraw.Drawing, components: Dict[str, Any]
) -> None:
    """Handles drawing method calls like move.

    Args:
        method_def: A dict mapping method name to its arguments
            (e.g., {'move': [0, -3]}).
        drawing: The schemdraw.Drawing object.
        components: A dictionary of existing components for reference resolution.

    Raises:
        AttributeError: If the method does not exist on the drawing object.
    """
    method_name = next(iter(method_def))
    args = method_def[method_name]
    if not isinstance(args, list):
        args = [args]

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
    """Resolves a dot-notation string to a schemdraw object.

    Args:
        name: The dot-notation string (e.g., 'elements.Resistor').

    Returns:
        The resolved Python object.

    Raises:
        AttributeError: If any part of the path cannot be resolved.
    """
    obj = schemdraw
    for part in name.split("."):
        obj = _safe_getattr(obj, part)
    return obj


def _parse_chain_item(item: Any) -> Tuple[str, List[Any]]:
    """Extracts the name and argument list from a chain item.

    Handles both dict items (e.g., {'label': ['5V']}) and bare string items
    (e.g., 'down'). Normalizes the args to always be a list.

    Args:
        item: A chain item, either a dict or a string.

    Returns:
        A tuple of (name, args_list).
    """
    if isinstance(item, dict):
        name = next(iter(item))
        args = item[name]
    else:
        name = item
        args = []

    if isinstance(args, dict):
        args = [args]
    elif not isinstance(args, list):
        args = [args]

    return name, args


def _execute_chain(
    component_def: List[Any], components: Dict[str, Any], drawing: schemdraw.Drawing
) -> Optional[Any]:
    """Executes a chain of method calls to instantiate and configure a component.

    The first item specifies the component class using dot-notation
    (e.g., 'elements.Resistor'). Remaining items are method calls on the instance.

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
    if not component_def:
        return None

    name, args = _parse_chain_item(component_def[0])
    obj = _resolve_object(name)

    if callable(obj):
        positional, keyword = _build_args_kwargs(args, name, components, drawing)
        obj = obj(*positional, **keyword)

    for item in component_def[1:]:
        method_name, args = _parse_chain_item(item)
        positional, keyword = _build_args_kwargs(args, method_name, components, drawing)

        if hasattr(obj, method_name):
            method = _safe_getattr(obj, method_name)
            result = method(*positional, **keyword)
            if result is not None:
                obj = result
        else:
            raise AttributeError(f"Object {obj} has no attribute {method_name}")

    return obj
