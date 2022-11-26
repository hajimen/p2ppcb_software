# P2PPCB Composer F360

**P2PPCB Composer F360 (PC0)** is an add-in of Autodesk Fusion 360 (F360). It helps you design your own keyboard
which is built on P2PPCB platform.
I, DecentKeyboards <https://www.etsy.com/shop/DecentKeyboards>, offer P2PPCB platform.

DISCLAIMER: PC0 is extraordinarily slow for a large keyboard, so far. Around 60 keys is the upper limit in common sense.
You cannot accelerate PC0 by expensive hardware, because F360's computation is done by only CPU never GPU,
only single-thread never multi-thread.

DISCLAIMER: So far, PC0 remains at sketchy quality. In some cases, you'll get stuck into F360's critical bug
and waste much time getting around it.

## Requirements: Just designing a keyboard

- Windows PC, English

F360 runs on Mac too, but PC0 uses RPA to get over the lack of F360 API features. Windows' language should be english
for RPA. In this case, RPA is platform-dependent.

Moreover, PC0 uses [`cefpython3`](https://pypi.org/project/cefpython3/) package which doesn't run on Mac.

- Autodesk Fusion 360 (F360)

F360 is a proprietary 3D CAD. Autodesk generously offers free plans for hobbyists so far.

- QMK firmware <https://qmk.fm/>

You need your own firmware for your own design. PC0 helps you, but you need to be well informed about QMK.

The official codebase of master branch lacks RP2040 (Raspberry Pi Pico's MPU) support now, so you need to use develop branch at least. Moreover, P2PPCB platform's mainboards require special codes for custom hardware. I prepared the codebase which have handles the custom hardware: <https://github.com/hajimen/qmk_firmware/tree/p2ppcb>. Fork it for your own design.

## Requirements: Building your own design

- A 3D printing service of HP Multi Jet Fusion (MJF) <https://www.hp.com/us-en/printers/3d-printers/products/multi-jet-technology.html>

Some SLA also does a good job, but some doesn't. The price is very attractive compared to MJF, so it's worth a try if you are going to do
a lot of trial-and-error iterations. Anyway I recommend you to have a MJF output in your hand to evaluate the quality of others.

There are a lot of 3D printing services of MJF in the world. Shapeways (North America and Europe), DMM.make (Japan), WENEXT (China) etc.
Pick a good one for you. I always use WENEXT.

- P2PPCB components from DecentKeyboards <https://www.etsy.com/shop/DecentKeyboards>

PC0 is free, but P2PPCB components aren't :-)

- Switches, caps, stabilizers

If you need custom printed caps for your own design, ask DecentKeyboards <https://www.etsy.com/shop/DecentKeyboards>.
I can make custom printed PBT keycaps. The total charge is from around $30 when COVID-19 went away (nowadays the shipping charge is quite expensive).

## Installation

Download a latest release file from here: <https://github.com/hajimen/p2ppcb_software/releases>

Unzip the release file, run F360, type Shift-S. Click "Add-Ins" tab, click **+** at the right of "My Add-Ins".
Choose `p2ppcb_composer_f360` directory in the unzipped release file. Choose `P2PPCB Composer` in "Add-Ins" tab and click "Run".
Now "P2PPCB" tab should appear on F360 main window.

## Overview of the design process

1. Design your own key layout by KLE <http://www.keyboard-layout-editor.com/> and download the deliverable by JSON. The file is KLE file.

You can include QMK keycodes in your KLE file. The details are later.

2. Design the height/angle of keys by F360 surface.

The F360 surface is **skeleton surface**. You need a F360 construction plane as **layout plane** too.
You can specify **key angle surface** to make a stepped ("staircase") profile keyboard with uniform profile keycaps (DSA/XDA etc.).

You can see how they work by a scaffold set which is built in PC0.
Click green **P2P/PCB** command icon in P2PPCB tab and enable 'Generate a scaffold set' checkbox in the command dialog.

3. Start a P2PPCB project

Specify the main preference of key switch, cap, stabilizer, vertical alignment, etc.
F360 file holds the preference.

You can run this command more than once.

4. Load KLE file

It can consume tens of minutes for a large keyboard. F360 isn't very suitable to P2PPCB Composer, but you don't want to pay
thousands of USD for CATIA, I guess.

5. Adjust each key

You can move each key, or change the switch/cap/stabilizer of each key.

6. **Fill** command

A generated frame doesn't have holes for keys yet. It is for the fill/hole method. The details are later.

7. Place a mainboard and feet

You can run this command more than once. To place feet, you'll need to do so in most cases.

8. Connect bosses of the mainboard/feet to a frame

You need to do this step by F360's features like loft, extrude, etc.

9. **Hole** command

It makes a 3D printable solid body. Right-click the body in the browser, choose **Save As Mesh**, choose STL, and OK.
Send the STL file to your 3D printing service.

10. There is an isolated thin wall? Oh...

MJF cannot print isolated thin walls under 0.8 mm. It often occurs on elaborate designs.
Some 3D printing services accept such STL file if you take on all risks. Some doesn't.
In the case, you need to remove them by F360's features by yourself.

## Bridge and fill/hole - MF/MEV method

Switches, stabilizers, and screws should be fixed on their holes on the frame. Such holes must be free of obstruction,
otherwise parts will be stuck.

On the other hand, a frame itself is not so rigorous about defects. A frame should be strong, stiff,
and have essential areas to hold parts (internal screw thread, for example).
Except for essential areas, a frame can have defects (voids) to some extent. Let's call such
non-essential areas which surround essential areas as "supporting areas".

PC0 adopts the fill/hole method to form a frame. Fill: make a block. Hole: cut the block.

Make a block, how? By connecting essential+supporting areas to each other. Where key layout is dense,
keys' essential+supporting areas overlap each other. In this case, a simple "join" operation is enough.
Where key layout is sparse, a bridge should connect between essential+supporting areas.
A bridge is a board parallel to the skeleton surface. 
By joining essential+supporting areas and a bridge, a block has been made. This is **Fill**.

Cutting the block will be obvious. Holes must be void without defect, so the fill/hole method doesn't allow fill-after-hole. This is **Hole**.

After fill/hole, we must check whether essential areas are filled without defects. The must-be-filled area is **MF** (must-filled).

Hole areas don't always equal to their parts. Two parts cannot occupy the same area, but two insert paths can do. 
An insert path is occupied by a part while assembly, but it is left void after once the part has been assembled.
A typical case is Cherry-style stabilizer's wire. Thus a hole area can be larger than its part.
To know the area of a part itself, and to check the interference of parts each other,
we need **MEV** (must-exclusively-void) area, in addition to hole area.

To reduce inference check range, there is **Territory**. It declares the outer edge of fill-hole areas of a part.

**Placeholder** will be obvious.

## QMK keycodes in your KLE file

QMK keycodes are here: <https://github.com/hajimen/qmk_firmware/blob/p2ppcb/docs/keycodes.md>

By including the keycodes on your KLE file, P2PPCB can help you much. Just write the keycode (of layer 0) on the key's front-left legend.
Front-center legend is layer 1, and front-right legend is layer 2.

## Keyboard matrix

Keyboard matrix: <https://github.com/qmk/qmk_firmware/blob/master/docs/how_a_matrix_works.md>

P2PPCB Bob/Charlotte uses S and D instead of row and col. QMK's row and col are dependent from the direction of current
(ROW2COL and COL2ROW are both capable), but S and D are always S to D.

By assigning a matrix, and by including the keycodes on your KLE file, you can generate route data (QMK keymap and wiring diagrams).
Without route data generation, your life will be much harder. Use **Assign Matrix** command and **Generate Route** command in P2PPCB tab.

### The limitation of VIA

VIA <https://www.caniusevia.com/> is a useful tool and the P2PPCB codebase is compatible with VIA.
But there is a limitation: VIA cannot handle the rows and cols above 8. So you should not use D8/S8 or above
if you are going to use VIA.

## Advanced features and design

### 'Regex Select' command

You can make a fully operating keyboard which have just a frame, no cover.
It looks geeky and good enough for prototyping. But in some cases, you may need a cover.

PC0 is not very helpful for the case, but there is a tool which may help you. While running PC0, You can find
'Regex Select' command in 'Select' panel. You can make a selection set by regex of the entities' full path name.
You can do the fill/hole method with the tool, without 'Fill' and 'Hole' commands.

### 'Set Attribute' and 'Check Key Assembly' commands

Look at the tooltips of each command. Making a part's data requires deep knowledge, including F360's bug.
You should be a developer of PC0 itself if you are going to make a part's data.

# For developers

If you are familiar with F360 add-in development, you'll find PC0 uses a bunch of bizarre hacks.
Let's see the hacks.

## RPA for decals

F360 API cannot handle decals so far. Thus I need to get over the limitation by RPA.
The hack is modularized as **f360_insert_decal_rpa** <https://github.com/hajimen/f360_insert_decal_rpa>.

## Unit tests

The F360 script in `composer_test` does unit tests. Please look at `sys.path.append()` and `reimport.py`
hack carefully.

The unit tests don't have good granularity. In reality, they are just regression tests
(in preparation for F360's update) and command launchers for debugging.

`test_generate_route` is quite slow while the VSCode debugger is attached.
It comes from cefpython3's behavior under F360 + VSCode debugger. I don't know why.

## Lazy binding by surrogate

F360 command cannot import F360 components, from the end of a create event to the end of an execute event. 
Importing should be done in a create event handler or after an execute event.
Importing in a create event handler breaks the cancel button's behavior (I did it in "Load KLE" command). 
Importing after an execute event is done by F360 custom event: <https://help.autodesk.com/view/fusion360/ENU/?guid=GUID-EC785EB6-22A8-4932-B362-395262D802CF>

Anyway, F360 cannot import anything while a command dialog is shown.
We need to build/manipulate an object tree before the objects become available.
In other words, we need lazy binding. Thus I adopted the surrogate method.
Objects-in-the-future are represented by surrogates.
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

So far, PC0 remains at sketchy quality. It helps you design your own keyboard *in many cases*.
In some cases, it annoys you rather than helps you.
In other cases, it gets stuck in F360's bugs. We need further development for better quality of PC0.

## Why so extraordinarily slow, especially for a large keyboard?

There are several reasons.

1. F360 API cannot handle decals.

I need to get over the limitation by RPA (extraordinarily slow by its nature) and
by manipulating bodies in units of F360 components.
It causes a lot of redundant F360 components. However it doesn't cause O(n^2) complexity,
so our common sense says "no problem", but Autodesk doesn't.

2. F360 becomes extraordinarily slow when there are 100 or above F360 components in a file.

I don't know why. Autodesk doesn't expect such usage, I guess.
Especially `findBRepUsingRay()` function can consume several seconds, so `Move Key` command
is nearly impossible.

3. F360 API's `attributes` scanning is extraordinarily slow.

I tried to find a good workaround, but failed.

## F360's bugs which annoy you or make you get stuck

In some cases, interference check doesn't work:
<https://forums.autodesk.com/t5/fusion-360-support/obvious-interference-was-not-detected/m-p/10633251>

In some cases, `importToTarget()` corrupts the imported component. See `p2ppcb_parts_depot.depot.prepare()`.
The bug is erratic and not reproducible. I guess it has a deal with CPU usage.
Once it occurs, `P2PPCB Cache` file is corrupted. Remove the file and try again.
But it can be hard to recognize the phenomenon.

## Custom features

So far, PC0 doesn't support parametric modeling. I wish I could edit a skeleton surface and key angle surfaces by parametric modeling.
Now (Dec 2022) Autodesk is testing custom features: <https://help.autodesk.com/view/fusion360/ENU/?guid=GUID-FA7EF128-1DE0-4115-89A3-795551E2DEF2>
I don't expect much, but I'll take a look when it turns into GA.

## Mac

So far, PC0 runs on Windows only. The limitation comes from decals. The codes relating to decals are hard to decouple.
