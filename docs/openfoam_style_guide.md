# OpenFOAM Style Guidelines

OpenFOAM dictionaries (`system/*`, `constant/*`, `0/*`) use a specific C++-like syntax. Adhering to these guidelines ensures files are parsed correctly and remain readable.

## 1. Syntax & Whitespace
OpenFOAM parsers can be sensitive to whitespace around delimiters.

### Do:
*   **Always** put a space before opening parentheses/braces.
*   **Always** use newlines for complex lists.

```cpp
// Correct
vertices
(
    (0 0 0)
    (1 0 0)
);

boundary
(
    inlet
    {
        type patch;
    }
);
```

### Don't:
*   Avoid compact, "function-call" style syntax without spaces. It often causes strict parsing errors ("ill defined primitiveEntry").

```cpp
// Incorrect - May cause parsing errors
vertices((0 0 0)(1 0 0));
boundary(inlet{type patch;});
```

## 2. Lists
*   Use Round brackets `( ... )` for ordered lists (points, faces).
*   Use Curly braces `{ ... }` for dictionaries/sub-blocks.

## 3. Comments
*   Use `//` for single line comments.
*   Use `/* ... */` for block comments.
*   Annotate identifying indices (e.g., vertex numbers) to aid debugging.

```cpp
vertices
(
    (0 0 0)  // 0: Aft Bottom Port
    (10 0 0) // 1: Fwd Bottom Port
);
```
