"""
Module for converting YAML to SchemDraw.
"""

import types
from typing import Any, Dict, List, Optional, Tuple

import schemdraw
import schemdraw.dsp
import schemdraw.elements
import schemdraw.flow
import schemdraw.logic

from .constants import (
    ALLOWED_DRAWING_METHODS,
    ALLOWED_ELEMENT_METHODS,
    ALLOWED_MODULES,
    MAX_COMPONENT_COUNT,
    MAX_RECURSION_DEPTH,
    MIN_SPLIT_LENGTH,
)


class SecurityError(Exception):
    """Raised when a security constraint is violated."""


def _safe_getattr(obj: Any, name: str) -> Any:
    if not hasattr(obj, name) or name.startswith("_"):
        raise SecurityError(f"Object '{obj}' has no attribute '{name}'")
    return getattr(obj, name)


def _validate_method_name(name: str, allowlist: set) -> None:
    if name not in allowlist:
        raise SecurityError(f"Method '{name}' is not allowed.")
    if name.startswith("_"):
        raise SecurityError(f"Access to private attribute '{name}' is forbidden.")


def _resolve_allowlisted_component(name: str) -> Any:
    parts = name.split(".")

    if len(parts) < 1 or len(parts) > MIN_SPLIT_LENGTH:
        raise SecurityError(
            f"Invalid component reference '{name}'. Must be 'module.Class' or 'module'."
        )

    module_name = parts[0]

    if module_name not in ALLOWED_MODULES:
        raise SecurityError(f"Module '{module_name}' is not in the allowlist.")

    obj = ALLOWED_MODULES[module_name]

    if len(parts) == MIN_SPLIT_LENGTH:
        class_name = parts[1]
        if class_name.startswith("_"):
            raise SecurityError(
                f"Access to private attribute '{class_name}' forbidden."
            )

        if not hasattr(obj, class_name):
            raise AttributeError(
                f"Module '{module_name}' has no attribute '{class_name}'"
            )

        obj = _safe_getattr(obj, class_name)

    if not (isinstance(obj, (type, types.ModuleType)) or callable(obj)):
        raise SecurityError(
            f"Resolved object '{name}' is not a valid component class or module."
        )

    return obj


def from_dict(dictionary: Dict[str, Any]) -> schemdraw.Drawing:
    """
    Convert a dictionary (YAML or JSON spec) to a SchemDraw drawing.
    """
    if len(dictionary) > MAX_COMPONENT_COUNT:
        raise SecurityError("Input dictionary exceeds maximum component count.")

    config = dictionary.pop("config", {})
    if not isinstance(config, dict):
        config = {}

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


def _is_drawing_state(value: Any) -> bool:
    return (
        isinstance(value, (list, tuple))
        and len(value) > 0
        and str(value[0]) == "drawing_state"
    )


def _handle_drawing_state(value: List[str], drawing: schemdraw.Drawing) -> None:
    if len(value) < MIN_SPLIT_LENGTH:
        return
    command = str(value[1])

    _validate_method_name(command, ALLOWED_DRAWING_METHODS)

    if hasattr(drawing, command):
        _safe_getattr(drawing, command)()


def _is_drawing_method(value: Any) -> bool:
    return (
        isinstance(value, (list, tuple))
        and len(value) > 0
        and str(value[0]) == "drawing_method"
    )


def _handle_drawing_method(
    value: List[Any], drawing: schemdraw.Drawing, components: Dict[str, Any]
) -> None:
    if len(value) < MIN_SPLIT_LENGTH:
        return
    method_name = str(value[1])
    args = value[2:]

    _validate_method_name(method_name, ALLOWED_DRAWING_METHODS)
    positional, keyword = _build_args_kwargs(
        args, method_name, components, drawing, depth=0
    )

    if hasattr(drawing, method_name):
        method = _safe_getattr(drawing, method_name)
        method(*positional, **keyword)
    else:
        raise AttributeError(f"Drawing object has no attribute '{method_name}'")


def _resolve_reference(value: str, components: Dict[str, Any]) -> Any:
    parts = value.split(".")
    if any(part.startswith("_") for part in parts):
        raise SecurityError("References cannot contain private attributes.")

    obj = components.get(parts[0])
    if obj is None:
        raise ValueError(f"Component '{parts[0]}' not found")

    for part in parts[1:]:
        if not hasattr(obj, part):
            raise AttributeError(f"Object has no attribute '{part}'")
        obj = _safe_getattr(obj, part)

    return obj


def _process_value(
    value: Any,
    method_name: str,
    components: Dict[str, Any],
    drawing: schemdraw.Drawing,
    depth: int,
) -> Any:
    if depth > MAX_RECURSION_DEPTH:
        raise SecurityError("Maximum recursion depth exceeded.")

    if isinstance(value, str):
        if value.split(".")[0] in components:
            return _resolve_reference(value, components)
        return value

    if isinstance(value, (int, float)):
        positioning_methods = {"right", "left", "up", "down", "tox", "toy"}
        if method_name in positioning_methods:
            return drawing.unit * value
        return value

    if isinstance(value, list):
        return [
            _process_value(val, method_name, components, drawing, depth + 1)
            for val in value
        ]

    if isinstance(value, dict):
        if len(value) == 1:
            try:
                return _execute_chain([value], components, drawing, depth + 1)
            except (ValueError, AttributeError, SecurityError):
                pass

        return {
            key: _process_value(val, method_name, components, drawing, depth + 1)
            for key, val in value.items()
        }

    return value


def _build_args_kwargs(
    args: List[Any],
    method_name: str,
    components: Dict[str, Any],
    drawing: schemdraw.Drawing,
    depth: int = 0,
) -> Tuple[List[Any], Dict[str, Any]]:
    args = args or []
    positional = []
    keyword = {}

    for arg in args:
        if isinstance(arg, dict):
            keyword.update(arg)
        else:
            positional.append(arg)

    processed_positional = [
        _process_value(arg, method_name, components, drawing, depth)
        for arg in positional
    ]
    processed_keyword = {
        key: _process_value(val, method_name, components, drawing, depth)
        for key, val in keyword.items()
    }

    return processed_positional, processed_keyword


def _execute_chain(
    component_def: List[Any],
    components: Dict[str, Any],
    drawing: schemdraw.Drawing,
    depth: int = 0,
) -> Optional[Any]:
    if len(component_def) == 0:
        return None

    item = component_def[0]
    args = []

    if isinstance(item, dict):
        name = list(item.keys())[0]
        raw_args = item[name]
        args = (
            [raw_args]
            if isinstance(raw_args, dict)
            else (raw_args if isinstance(raw_args, list) else [raw_args])
        )
    else:
        name = item
        args = []

    obj = _resolve_allowlisted_component(name)
    start_index = 1

    # Case 1: Callable/Class (e.g. elements.Resistor if imported as class)
    if callable(obj):
        positional, keyword = _build_args_kwargs(args, name, components, drawing, depth)
        obj = obj(*positional, **keyword)

    # Case 2: Module + Class (e.g. ['elements', 'Resistor'])
    elif len(component_def) > 1:
        if isinstance(obj, types.ModuleType):
            start_index = 2
            class_item = component_def[1]

            if isinstance(class_item, dict):
                class_name = list(class_item.keys())[0]
                class_args = class_item[class_name]
                class_args = (
                    [class_args]
                    if isinstance(class_args, dict)
                    else (class_args if isinstance(class_args, list) else [class_args])
                )
            else:
                class_name = class_item
                class_args = []

            if class_name.startswith("_"):
                raise SecurityError(f"Private class '{class_name}' forbidden.")

            if hasattr(obj, class_name):
                obj_class = _safe_getattr(obj, class_name)
                if callable(obj_class):
                    positional, keyword = _build_args_kwargs(
                        class_args, class_name, components, drawing, depth
                    )
                    obj = obj_class(*positional, **keyword)
                else:
                    obj = obj_class
            else:
                raise AttributeError(f"Module {name} has no attribute {class_name}")

    # Case 3: Method Chaining
    for item in component_def[start_index:]:
        if isinstance(item, dict):
            method_name = list(item.keys())[0]
            raw_args = item[method_name]
            args = (
                [raw_args]
                if isinstance(raw_args, dict)
                else (raw_args if isinstance(raw_args, list) else [raw_args])
            )
        else:
            method_name = item
            args = []

        _validate_method_name(method_name, ALLOWED_ELEMENT_METHODS)
        positional, keyword = _build_args_kwargs(
            args, method_name, components, drawing, depth
        )

        if hasattr(obj, method_name):
            method = _safe_getattr(obj, method_name)
            result = method(*positional, **keyword)
            if result is not None:
                obj = result
        else:
            raise AttributeError(f"Object {obj} has no attribute {method_name}")

    return obj
