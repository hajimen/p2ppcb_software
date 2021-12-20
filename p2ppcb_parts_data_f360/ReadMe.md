# p2ppcb_parts_data

## Important bug of Autodesk Fusion 360

Fusion 360 (F360) often overlooks `SwitchAngle` rotation. To get around the bug,
we need to erase design history (Disable capturing and Enable it again) and prepare
`SwitchAngle` `SwitchX` `SwitchY` for each exporting of F3D.

## `UseStabilizer` parameter

It just shows as the name. If the value exists and is nonzero, it is true.
