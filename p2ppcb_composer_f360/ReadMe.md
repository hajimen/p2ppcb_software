# P2PPCB Composer F360

**P2PPCB Composer F360** is an add-in of Autodesk Fusion 360 (F360). It helps you design your own keyboard which is built on P2PPCB platform.

DISCLAIMER: P2PPCB Composer F360 is extraordinarily slow for a large keyboard, so far.

DISCLAIMER: So far, P2PPCB Composer F360 remains at sketchy quality. In some cases, you'll get stuck into F360's critical bug and waste much time to get around it.

## Requirements: Just designing a keyboard

- Windows PC

F360 runs on Mac too, but P2PPCB Composer F360 uses RPA to get over the lack of F360 API features.

By leaving all top legends empty, you can get around the problem, I guess (I haven't test it yet).
But without legends, your work may be a bit hard.

- Autodesk Fusion 360 (F360)

F360 is a proprietary 3D CAD. Autodesk generously offers free plan for hobbyists so far.

- QMK firmware <https://qmk.fm/>

You need your own firmware for your own design. P2PPCB Composer F360 helps you, but you need to be well informed about QMK.

The official codebase lacks RP2040 (Raspberry Pi Pico's MPU) support yet, so you need to use a fork like this: <https://github.com/sekigon-gonnoc/qmk_firmware/tree/rp2040>.

## Requirements: Building your own design

- A 3D printing service of HP Multi Jet Fusion (MJF) <https://www.hp.com/us-en/printers/3d-printers/products/multi-jet-technology.html>

You might know the quality of 3D printers for hobbyists. MJF is in another league.

There are a lot of 3D printing services of MJF in the world. Shapeways (North America and Europe), DMM.make (Japan), etc.
Pick a good one for you.

- P2PPCB parts from DecentKeyboards <https://www.etsy.com/shop/DecentKeyboards>

P2PPCB Composer F360 is free, but the parts aren't :-)

- Switches, caps, stabilizers

If you need custom caps for your own design, ask DecentKeyboards <https://www.etsy.com/shop/DecentKeyboards>.
I can make custom printed PBT keycaps. The total charge is from around $30.

## Installation

Download a latest release file from here: <https://github.com/hajimen/p2ppcb_software/releases>

Unzip the release file, run F360, type Shift-S. Click "Add-Ins" tab, click **+** at the right of "My Add-Ins".
Choose `p2ppcb_composer` directory in the unzipped release file. Choose `P2PPCB Composer` in "Add-Ins" tab and click "Run".
Now "P2PPCB" tab should appear on F360 main window.

## Overview of the design process by P2PPCB Composer F360

1. Design your own key layout by KLE <http://www.keyboard-layout-editor.com/> and download the deliverable by JSON. The file is KLE file.

You can include QMK keycodes in your KLE file. The detail is later.

2. Design the height/angle of keys by F360 surface.

The F360 surface is **skeleton surface**. You need a F360 construction plane as **layout plane** too.

You can see how they work by a scaffold set which is built in P2PPCB Composer F360.
Click green **P2P/PCB** icon and enable 'Generate a scaffold set' checkbox in the command dialog.

3. Start a P2PPCB project

Specify the main preference of key switch, cap, stabilizer, vertical alignment, etc.
F360 file holds the preference.

You can run this command more than once.

4. Load KLE file

It can consume tens of minutes. F360 isn't very suitable to P2PPCB Composer, but you don't want to pay thousands of USD for CATIA, I guess.

5. Adjust each key

You can move each key, or change switch/cap/stabilizer of each key.

6. Generate a frame

A generated frame doesn't have holes for keys yet. It is for fill/hole method. The detail is later.

7. Place a mainboard and feet

You can run this command more than once. To place feet, you need to do so in most cases.

8. Connect bosses of the mainboard/feet to a frame

You need to do this step by F360's features like loft, extrude, etc.

9. Finish

It makes a 3D printable solid body. Run **Save As Mesh**, choose STL and OK. Send the STL file to 3D printing service of MJF.

10. There is isolated thin wall? Oh...

MJF cannot print isolated thin wall around under 0.8 mm. If it occurs, you need to remove them by F360's features by yourself.

## Bridge and fill/hole - MF/MEV method

Key switches, stabilizers, and screws should be fixed on their holes. Such holes must be void without defect, otherwise parts will be stuck.

On the other hand, a frame is not so rigorous about "defect". Frame should be strong, stiff, and have essential areas to hold parts (internal screw thread, for example).
Except for essential areas, a frame can have void to some extent.

P2PPCB Composer F360 adopts fill/hole method to form a frame. Fill: make a block. Hole: cut the block.

Make a block, how? By connecting essential areas. Where key layout is dense, essential areas overlap each other. In this case, simply do "join" operation.
Where key layout is sparse, a bridge connects between essential areas. Bridge is a board parallel to the skeleton surface. 
By joining essential areas and a bridge, a block has been made. This is **Fill**.

Cutting the block will be obvious. Holes must be void without defect, so fill/hole method doesn't allow fill-after-hole. This is **Hole**.

After fill/hole, we must check whether essential areas are filled without defect. The must-be-filled area is **MF** (must-filled).

Hole areas don't always equal to their parts. Two parts cannot occupy a same area, but two insert paths can do. An insert path is occupied by a part while assembly,
but it is left void after once the part has been assembled. A typical case is Cherry-style stabilizer's wire. Thus a hole area can be larger than its part.
To know the area of a part itself, and to check the interference of parts each other, we need **MEV** (must-exclusively-void) area, in addition to hole area.

To reduce inference check range, there is **Territory**. It declares the outer edge of fill-hole areas of a part. **Placeholder** will be obvious.

## QMK keycodes in your KLE file

QMK keycodes are here: <https://beta.docs.qmk.fm/using-qmk/simple-keycodes/keycodes>

By including the keycodes on your KLE file, P2PPCB can help you much. Just write the keycode on the key's front-left legend.

## Keyboard matrix

Keyboard matrix: <https://beta.docs.qmk.fm/developing-qmk/for-a-deeper-understanding/how_a_matrix_works>

By assigning a matrix, and by including the keycodes on your KLE file, you can generate route data (QMK keymap and wiring diagrams).
Without route data generation, your life will be much harder.

# For developers

If you are familiar with F360 add-in development, you'll find P2PPCB Composer F360 uses a bunch of bizarre hacks.
Let's see the hacks.

## RPA for decals

F360 API cannot handle decals so far. Thus I need to get over the limitation by RPA.
The hack is modularized as **f360_insert_decal_rpa** <https://github.com/hajimen/f360_insert_decal_rpa>.

## Unit tests

F360 script in `composer_test` does unit tests. Please carefully look at `sys.path.append()` and `reimport.py` hack. 

The unit tests don't have good granularity. In reality, they are just regression tests (in preparation for F360's update) and command launchers for debugging.

## Lazy binding by surrogate

F360 command cannot import F360 components during from the end of a create event to the end of an execute event. 
Importing should be done in a create event handler or after an execute event.
Importing in a create event handler breaks the cancel button's behavior (I did it in "Load KLE" command). 
Importing after an execute event is done by F360 custom event: <https://help.autodesk.com/view/fusion360/ENU/?guid=GUID-EC785EB6-22A8-4932-B362-395262D802CF>

Anyway, F360 cannot import anything while a command dialog is shown. We need to build/manipulate an object tree before the objects become available.
In other words, we need lazy binding. Thus I adopted surrogate. Objects-in-the-future are represented by surrogates.
After importing, surrogates are replaced by real objects.

## How to build `app-packages`

Prepare `%PATH%` for F360's `python.exe` and its `Scripts` directory.

```
python -m pip install --upgrade pip
pip install piprepo setuptools wheel
mkdir repos
cd repos
mkdir pep503
git clone https://github.com/hajimen/f360_insert_decal_rpa
cd f360_insert_decal_rpa
python setup.py bdist_wheel
cp dist/*.whl ../pep503
cd ..
git clone https://github.com/hajimen/pykle_serial
cd pykle_serial
python setup.py bdist_wheel
cp dist/*.whl ../pep503
cd ..
git clone https://github.com/hajimen/kle_scraper
cd kle_scraper
python setup.py bdist_wheel
cp dist/*.whl ../pep503
cd ..
git clone https://github.com/hajimen/p2ppcb_software
cd p2ppcb_software/p2ppcb_parts_resolver
python setup.py bdist_wheel
cp dist/*.whl ../../pep503
cd ..
piprepo build ../pep503
cd p2ppcb_composer_f360
mkdir app-packages
pip install -r requirements.txt -t app-packages --extra-index-url ../../pep503/simple
```

# Further development

So far, P2PPCB Composer F360 remains at sketchy quality. It helps you design your own keyboard *in many cases*. In some cases, it annoys you rather than helps you.
In other cases, it gets stuck in F360's bugs. We need further development for better quality of P2PPCB Composer F360.

## Why so extraordinarily slow for a large keyboard?

There are two reasons.

1. F360 API cannot handle decals.

I need to get over the limitation by RPA (extraordinarily slow by its nature) and by manipulating bodies in units of F360 components.
It causes a lot of redundant F360 components. However it doesn't cause O(n^2) complexity, so our common sense says "no problem", but Autodesk doesn't.

2. F360 becomes extraordinarily slow when there are 100 or above F360 components in a file.

I don't know why. Autodesk doesn't expect such usage, I guess.

## F360's bugs which annoy you or make you get stuck

In some cases, interference check doesn't work:
<https://forums.autodesk.com/t5/fusion-360-support/obvious-interference-was-not-detected/m-p/10633251>

In some cases, `importToTarget()` corrupts the imported component. See `p2ppcb_parts_depot.depot.prepare()`.
The bug is erratic and not reproducible. I guess it has a deal with CPU usage.
Once it occurs, `P2PPCB Cache` file is corrupted. Remove the file and try again.
But it can be hard to recognize the phenomenon.

## Custom features

So far, P2PPCB Composer F360 doesn't support parametric modeling. I wish I could edit a skeleton surface and key angle surfaces by parametric modeling.
Now (Apr. 2022) Autodesk is testing custom features: <https://help.autodesk.com/view/fusion360/ENU/?guid=GUID-FA7EF128-1DE0-4115-89A3-795551E2DEF2>
I don't expect much, but I'll take a look when it turned into GA.

## Mac

So far, P2PPCB Composer F360 runs on Windows only. The limitation comes from RPA of decals. If Autodesk prepares APIs for decals,
Mac will be supported too. Contributions on f360_insert_decal_rpa <https://github.com/hajimen/f360_insert_decal_rpa> will make us happy too.
