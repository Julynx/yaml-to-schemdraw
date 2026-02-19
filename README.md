# yaml-to-schemdraw

Generate schemdraw diagrams from YAML files or Python dictionaries.

`pip install yaml-to-schemdraw`

- [yaml-to-schemdraw](#yaml-to-schemdraw)
  - [Usage](#usage)
  - [Why?](#why)
  - [How it works](#how-it-works)

The following YAML spec:

```yaml
V1:
  - elements.SourceV
  - label: ["5V"]

line1:
  - elements.Line
  - right: [0.75]

S1:
  - elements.SwitchSpdt2: [{ action: close }]
  - up
  - anchor: ["b"]
  - label: ["$t=0$", { loc: rgt }]

line2:
  - elements.Line
  - right: [0.75]
  - at: ["S1.c"]

R1:
  - elements.Resistor
  - down
  - label: ["$100\\Omega$"]
  - label: [["+", "$v_o$", "-"], { loc: bot }]

line3:
  - elements.Line
  - to: ["V1.start"]

C1:
  - elements.Capacitor
  - at: ["S1.a"]
  - toy: ["V1.start"]
  - label: ["1$\\mu$F"]
  - dot
```

Represents the equivalent Python code:

```python
with schemdraw.Drawing() as d:
    V1 = elm.SourceV().label('5V')
    elm.Line().right(d.unit*.75)
    S1 = elm.SwitchSpdt2(action='close').up().anchor('b').label('$t=0$', loc='rgt')
    elm.Line().right(d.unit*.75).at(S1.c)
    elm.Resistor().down().label(r'$100\Omega$').label(['+','$v_o$','-'], loc='bot')
    elm.Line().to(V1.start)
    elm.Capacitor().at(S1.a).toy(V1.start).label(r'1$\mu$F').dot()
```

And can be loaded with this library as follows:

## Usage

```python
from yaml_to_schemdraw import from_yaml_file
# "from_yaml_string" and "from_dict" are also available

diagram = from_yaml_file("diagram.yaml")
```

You can now call `diagram.draw()` or `diagram.save("diagram.svg")` as usual.

![diagram](https://i.imgur.com/89mZNP1.png)

## Why?

Schemdraw was always intended to be used as a Python library, with developers manually writing diagrams in code.

However, when it comes to accepting diagram definitions provided by clients through the network or originating from an untrusted environment, the naive approach of running arbitrary Python code with a function like `exec()` poses a significant security risk.

This module proposes an alternative, declarative way to represent Schemdraw diagrams as a YAML file or a Python dictionary.

## How it works

The module parses the dictionary and resolves the function calls against the schemdraw library.

Internally, it uses `getattr()` to resolve function calls, with an attribute allowlist to prevent module escalation.

It can easily and safely parse most of the [schemdraw circuit gallery](https://schemdraw.readthedocs.io/en/stable/gallery/index.html).

If you encounter any valid diagrams that cannot be parsed (or easily adapted into something that this module can parse), please open an issue.
