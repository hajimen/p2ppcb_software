# p2ppcb_parts_resolver

**p2ppcb_parts_resolver** is a Python library for P2PPCB Composer F360 (PC0).

p2ppcb_parts_resolver is independent of Autodesk Fusion 360 (F360), but designed to work with it.
The independence is mainly for debugging, and good for porting PC0 to other 3D CADs.

p2ppcb_parts_resolver resolves the names of the **design files**, the **part parameter set**, and the **specifier** of the parts of a key.
The key is represented in a KLE file and annotated with a **part description** set.

## Part parameter set and design file

Many 3D CADs have a parametric modeling feature. Using this feature, a design can represent many fixed forms.
In other words, a design file with a parameter set is equivalent to a fixed form.

## Part description

Usually this is a string that indicates the type of a part, e.g. "Cherry-style plate mount", "DSA", "Choc V2".
**Decal** or **Wiring** is a different story, but it is an exception.

## From KLE file to pattern name

A KLE file doesn't contain names like "ISO Enter" or "2u", but of course we can spot such name of a key in a KLE file.
p2ppcb_parts_resolver does. The spotted name is a **pattern name**.

## Specifier

In some cases, a pattern name with a part description set is enough to resolve everything. But there are other cases.
For example, row-dependent caps (Cherry, OEM, etc.) require row information. The information should be written in the "Profile / Row" of a KLE file.
A specifier consists of a "Profile / Row" string (or something similar) and a pattern name, e.g. "R4 2u" (Backspace) or "R1 2u" (Numpad 0).

## Overview of the resolving chain

- a KLE file and a part description set -> (iteration over keys)

    -  key -> 

        - "Profile / Row" string (or something similar)
        - pattern name

    - -> specifier ->

        - design file name of each part
        - parameter set

This is just an overview. There are many details.

## How to write the resolving rule

Look in the `p2ppcb_part_data_f360/parameters` directory. The root is `descriptions.csv`. It will look straightforward.
Let's go along DSA cap, `Cap,DSA,dsa` row.

Look in the `dsa` directory (the directory name is specified in the `Cap,DSA,dsa` row), and open `mapping.csv`.
You can see that the file maps the specifiers to their design file names and parameter name sets.

```
1u,DSA Keycap 1u v4.f3d,Travel
\d*u,DSA Keycap v8.f3d,Width Travel
```

Row order is important. The `Specifier` column is a regular expression, and `\d*u` matches "1u".
But p2ppcb_parts_resolver searches for matching rows from top to bottom. Once a row matches,
it stops searching. Specifier "1u" matches the `1u` row, and the `\d*u` row is ignored.

Let's go with "2u". The `\d*u` row hits, so the design file name is `DSA Keycap v8.f3d`, and the parameter name set is `Width Travel`.
We need to resolve these parameters and pass them to `DSA Keycap v8.f3d`. To do this, p2ppcb_parts_resolver looks at the CSV files in the directory.
Open `height.csv`, look at the top row, and find no `Width` or `Travel`. OK, `homing.csv`, no hit again. OK, `switch_x_y_angle.csv`...
Finally, p2ppcb_parts_resolver goes to the parent directory. Open `cap.csv`, and find `Width`, but specifier `2u` doesn't match.
`cap_wide.csv`, and find it. `Width` of "2u" is `37 mm`. Done. p2ppcb_parts_resolver resolved `Width`.

But, what is `ParameterA` in `cap_wide.csv`? We don't need it here. Also, we haven't seen `Travel` is resolved yet,
while there are no more CSV files to see.

This is the name of the game.

`ParameterA` is the parameter for stabilizers. On the other hand, `Travel` should be resolved while resolving a switch.
p2ppcb_parts_resolver makes *a parameter set*. `ParameterA` and the value `23.8 mm` will be added to the parameter set,
even it is not for `DSA Keycap v8.f3d`.

## Special parameters for part_z_pos

Key parts are stacked vertically (Z-direction). The reference level depends on the keyboard design. p2ppcb_parts_resolver
also resolves this.

- Cap: `TopHeight`, `CapStemBottomHeight`
- Switch: `SwitchStemBottomHeight`, `SwitchBottomHeight`, `Travel`
- Stabilizer: `StabilizerStemBottomHeight`

Using these special parameters and the alignment type (`StemBottom` or `TravelBottom`), p2ppcb_parts_resolver resolves
the Z position of each part in a key assembly.

## Special parameters for switch_xya

The angle, x, and y of a switch/stabilizer/PCB depends on the specifier.
For example, ISO Enter often requires a right-angled switch/stabilizer/PCB.
These are special parameters for this purpose:

- SwitchAngle
- SwitchX
- SwitchY
- StabilizerAngle
- StabilizerX
- StabilizerY

A PCB follows its switch, of course.

## Special parameter: `Placeholder`

`Placeholder` is another special parameter. All design files should have placeholder bodies.
These bodies should be tagged as placeholder, and the tag should have a string value that denotes the detail.
`Placeholder` value is `Placeholder` by default implicitly. You can write explicitly when you need to select a placeholder in a design file.

## Decal and Wiring

These are not parts, but they have part-dependent parameters.

Decal is a feature of F360. We need to adjust the decal parameters to fit each cap type and specifier.
Wiring is for route data generation. See PC0 source code for details.
