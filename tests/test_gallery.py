import os
import sys

import pytest
from ruamel.yaml import YAML

# Ensure we can import from the source directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import from the package
from yaml_to_schemdraw import from_dict

YAML_DIR = os.path.join(os.path.dirname(__file__), "yaml")
YAML_FILES = [f for f in os.listdir(YAML_DIR) if f.endswith(".yaml")]


@pytest.fixture
def yaml_parser():
    return YAML()


@pytest.mark.parametrize("filename", YAML_FILES)
def test_gallery(filename, yaml_parser):
    filepath = os.path.join(YAML_DIR, filename)
    with open(filepath, "r") as f:
        yaml_content = f.read()

    dictionary = yaml_parser.load(yaml_content)
    # Should not raise exception
    d = from_dict(dictionary)
    assert d is not None

    output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, filename.replace(".yaml", ".svg"))
    d.save(output_path)
