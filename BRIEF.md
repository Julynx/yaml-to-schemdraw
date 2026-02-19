# BRIEF: yaml-to-schemdraw

> Generate schemdraw diagrams from YAML files or Python dictionaries.

## 1. Overview (README)

```markdown
# yaml-to-schemdraw

Generate schemdraw diagrams from YAML files or Python dictionaries.

`pip install yaml-to-schemdraw`

- [yaml-to-schemdraw](#yaml-to-schemdraw)
  - [Usage](#usage)
  - [Why?](#why)
  - [How it works](#how-it-works)

The following YAML spec:

'''yaml
V1:
  - elements.SourceV
  - label: ["5V"]

line1:
  - elements.Line
... (truncated) [Read more](file:///D:/_DISK_/_Documentos_/Mis_repositorios/yaml-to-schemdraw/README.md)
```

## 2. Dependencies

```text
ruamel-yaml
schemdraw
```

## 3. Directory Structure

```text
yaml-to-schemdraw/
├── scripts
├── yaml_to_schemdraw
    ├── __init__.py
    ├── __main__.py
    └── constants.py
├── .gitignore
├── .python-version
├── README.md
├── pyproject.toml
└── uv.lock
```

## 4. Import Tree

```text
- yaml_to_schemdraw\__init__.py
  - yaml_to_schemdraw\__main__.py
    - yaml_to_schemdraw\constants.py
```

## 5. Module Definitions

### yaml_to_schemdraw\__main__.py

```text
- def from_dict(dictionary: Dict[str, Any]) -> schemdraw.Drawing
- def from_yaml_file(file_path: str) -> schemdraw.Drawing
- def from_yaml_string(yaml_string: str) -> schemdraw.Drawing
```
