"""
Constants and allowlists for the yaml_to_schemdraw package.

This module defines the set of allowed schemdraw methods and elements
that can be invoked through YAML definitions, ensuring a controlled
interface for circuit creation.
"""

import schemdraw

MAX_RECURSION_DEPTH = 10
MAX_COMPONENT_COUNT = 1000
MIN_SPLIT_LENGTH = 2

ALLOWED_MODULES = {
    "schemdraw": schemdraw,
    "elements": schemdraw.elements,
    "dsp": schemdraw.dsp,
    "flow": schemdraw.flow,
    "logic": schemdraw.logic,
}

ALLOWED_ELEMENT_METHODS = {
    "at",
    "to",
    "tox",
    "toy",
    "xy",
    "anchor",
    "up",
    "down",
    "left",
    "right",
    "d",
    "l",
    "theta",
    "flip",
    "reverse",
    "drop",
    "hold",
    "rotate",
    "mirror",
    "label",
    "color",
    "fill",
    "scale",
    "linestyle",
    "linewidth",
    "zorder",
    "font",
    "fontsize",
    "move_cur",
    "dot",
}

ALLOWED_DRAWING_METHODS = {
    "push",
    "pop",
    "move",
    "here",
    "add_label",
    "add",
    "loopI",
}
