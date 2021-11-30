# p2ppcb_parts_resolver

**p2ppcb_parts_resolver** is a Python library for P2PPCB Composer F360.

p2ppcb_parts_resolver is independent from Autodesk Fusion 360 (F360), but designed to be used in it.
This is mainly for debugging, but good for porting of P2PPCB Composer F360 to other 3D CADs.

p2ppcb_parts_resolver resolves the design files' names, the part parameter set, and the specifier of the parts of a key.
The key is represented in a KLE file and annotated by a part description set.

## Part parameter set and design file

Many 3D CADs has parametric modeling feature. Using the feature, a design can represent a lot of fixed forms.
In other words, a design file with a parameter set is equal to a fixed form.

## Part description

Usually it is a string that indicates the type of a part, i.e. "Cherry-style plate mount", "DSA", "Choc V2".
Decal or Wiring is a different story, but it is an exception.

## From KLE file to pattern name

A KLE file doesn't contain names like "ISO Enter" or "2u", but obviously we can spot such name of a key in a KLE file.
p2ppcb_parts_resolver does. The spotted name is pattern name.

## Specifier

In some cases, a pattern name with a part description set is enough to resolve everything. But there are other cases too.
For example, row-dependent caps (Cherry, OEM, etc.) requires row information. The information should be written in "Profile / Row" of a KLE file.
A specifier is consisted by connecting "Profile / Row" string (or something like it) and a pattern name, i.e. "R4 2u" (Backspace) or "R1 2u" (Numpad 0).

## Overview of the resolving chain

- a KLE file and a part description set -> (iteration over keys)

    -  key -> 

        - "Profile / Row" string (or something like it)
        - pattern name

    - -> specifier ->

        - design file names of each part
        - parameter set

This is just an overview. There are a lot of details.

## How to write the resolving rule

Look at `p2ppcb_part_data_f360/parameters` directory. The root is `descriptions.csv`. It will look straightforward.
Let's go along DSA cap, `Cap,DSA,dsa` row.

Look at `dsa` directory (the directory name is specified in the `Cap,DSA,dsa` row), and open `mapping.csv`.
You can see the file connects specifiers to their design file names and parameter name sets.

```
1u,DSA Keycap 1u v4.f3d,Travel
\d*u,DSA Keycap v8.f3d,Width Travel
```

The row order matters. `Specifier` column is regular expression, and `\d*u` matches to "1u".
But p2ppcb_parts_resolver searches matching row from top to bottom. Once a row matches,
it stops further search. Specifier "1u" matches the `1u` row, and the `\d*u` row doesn't matter anymore.

Let's go with "2u". `\d*u` row hits, so the design file name is `DSA Keycap v8.f3d`, and the parameter name set is `Width Travel`.
We need to resolve and give those parameters to `DSA Keycap v8.f3d`. To do so, p2ppcb_parts_resolver looks at CSV files in the directory.
Open `height.csv`, see the top row, and find no `Width` or `Travel`. OK, `homing.csv`, no hit again. OK, `switch_x_y_angle.csv`...
In the end, p2ppcb_parts_resolver goes to the parent directory. Open `cap.csv`, and find `Width`, but specifier `2u` doesn't match.
`cap_wide.csv`, and find it. `Width` of "2u" is `37 mm`. Done. p2ppcb_parts_resolver resolved `Width`.

But, what is `ParameterA` in `cap_wide.csv`? We don't need it here. Moreover we haven't seen `Travel` is resolved yet,
while there is no more CSV files to see.

This is the name of the game.

`ParameterA` is the parameter for stabilizers. On the other hand, `Travel` should be resolved while resolving a switch.
p2ppcb_parts_resolver makes *a parameter set*. `ParameterA` and the value `23.8 mm` is added to the parameter set,
even it is not for `DSA Keycap v8.f3d`.

## Special parameters for part_z_pos

Key parts stack vertically (Z direction). The reference level depends on the keyboard's design. p2ppcb_parts_resolver
resolves it too.

- Cap: `TopHeight`, `StemBottomHeight`
- Switch: `StemTopHeight`, `SwitchBottomHeight`, `Travel`
- Stabilizer: ``StemTopHeight`

From these special parameters and alignment type (`StemBottom` or `TravelBottom`), p2ppcb_parts_resolver resolves
Z position of each part in a key assembly.

## Special parameter: Placeholder

`Placeholder` is another special parameter. All design files should have placeholder bodies.
Those bodies should be tagged as placeholder, and the tag have a string value which denotes the detail.
`Placeholder` value is `Placeholder` by default implicitly. You can write explicitly when you need to choose a placeholder in a design file.

## Decal and Wiring

They are not parts, but they have parts-dependent parameters.

Decal is F360's feature. We need to adjust the decal parameters to fit each cap type and specifier.
Wiring is for route data generation. See P2PPCB Composer F360 source code for details.
