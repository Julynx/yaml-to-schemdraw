# Important Migration Notes

The examples in `tests/TODO` use an older version of `schemdraw`. When converting to YAML tests (or updating Python code), note the following changes:

## Element Names

- `BJT_NPN_C` -> `BjtNpn` (check `schemdraw.elements.transistors`)
- `RES` -> `Resistor`
- `LINE` -> `Line`
- `DOT` -> `Dot`
- `DOT_OPEN` -> `Dot(open=True)`
- `GND` -> `Ground`
- All element names generally use CamelCase now (e.g., `SourceV` instead of `SOURCE_V`).

## Drawing Methods vs Elements

- `d.loopI(...)` has been removed. Use `d.add(elm.LoopCurrent(...))` instead.
- `d.labelI(...)` has been removed. Use `d.add(elm.CurrentLabel(...))` instead.

## Methods

- `add_label()` on elements seems to be deprecated or removed. Use `label()` instead.
- Check `schemdraw` documentation for signature changes in `label()` (e.g., `align` parameter usage).

## Flowcharts

- Flowchart elements are in `schemdraw.flow`.
- Access them via `flow.Star`, `flow.Box`, etc.
