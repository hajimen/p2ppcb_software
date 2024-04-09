# P2PPCB Composer F360

**P2PPCB Composer F360 (PC0)** is an add-in of Autodesk Fusion 360 (F360). It helps you to design your own keyboard
based on P2PPCB platform <https://github.com/hajimen/p2ppcb_software>.
I, DecentKeyboards <https://www.etsy.com/shop/DecentKeyboards>, provide P2PPCB platform.

DISCLAIMER: PC0 is slow for a large keyboard, so far. Initial "Load KLE" command can take several minutes.
Please start with making small studies and get a good grasp of the time consumption.

DISCLAIMER: So far, PC0 remains at sketchy quality. In some cases, you'll get stuck into F360's critical bug
and waste a lot of time to get around it.

## Requirements: Just design a Keyboard

- Windows PC, English

PC0 uses RPA to get around the lack of F360 API features (Windows only). Windows' language should be English
for RPA. In this case, RPA is platform-dependent.

Also, PC0 uses [`cefpython3`](https://github.com/hajimen/cefpython) package. It doesn't run on Apple Silicon Mac.

Mac can do most of PC0 features. But it lacks decals (key top images). Apple Silicon Mac lacks wire route generation too.

- Autodesk Fusion 360 (F360) <https://www.autodesk.com/products/fusion-360/overview>

F360 is a proprietary 3D CAD. Autodesk generously offers charge-free plans for hobbyists so far.

- QMK Firmware <https://qmk.fm/>

You need your own firmware for your own design. PC0 will help you, but you need to be well informed about QMK.

P2PPCB mainboards require special code for their own hardware. I have prepared the codebase which handles the custom hardware:
<https://github.com/hajimen/qmk_firmware/tree/p2ppcb>. Fork the `p2ppcb` branch for your own design.

## Requirements: Create your own design

- A 3D printing service shop

As the printing material, HP Multi Jet Fusion (MJF) <https://www.hp.com/us-en/printers/3d-printers/products/multi-jet-technology.html> and
Somos® Ledo 6060 with sanding are well tested. In many cases, the latter is much cheaper.

IMPORTANT: The modeling assumes -20 to -50 μm tolerance. MJFs are made with this tolerance.
Ledo 6060s with sanding also. But Ledo 6060s **without sanding** has almost zero tolerance.
It doesn't fit. Choose "Surface finish: Sanding" if you use Ledo 6060.

There are many 3D printing service shops of MJF or Ledo 6060 in the world. 
[Shapeways](https://www.shapeways.com/) (North America and Europe), 
[DMM.make](https://make.dmm.com/) (Japan), [WENEXT](https://www.wenext.com/) (China),
[JLCPCB](https://jlcpcb.com/) (China) etc.
Pick a good one for you. I always use JLCPCB.

In most cases, 3D printing service shop will give you a warning about too thin walls. In most cases,
I don't recommend you to fix it. You must have the ability to identify real limits if you want to make
an elaborated design. Failure teaches success.

- P2PPCB components by DecentKeyboards <https://www.etsy.com/shop/DecentKeyboards>

PC0 is free, but P2PPCB components aren't :-).

- Switches, keycaps, stabilizers

If you need custom printed keycaps for your own design, contact DecentKeyboards <https://www.etsy.com/shop/DecentKeyboards>.
I can make custom printed PBT keycaps. The total cost will be from about $30.

## Installation

Download the latest release file from here: <https://github.com/hajimen/p2ppcb_software/releases>

Unzip the release file, run F360, click the **UTILITIES** tab -> **Scripts and Add-ins** command icon on the F360 menu (or type Shift-S).
In the command dialog, click the **Add-Ins** tab, click **+** at the right of **My Add-Ins**.
Select the `p2ppcb_composer_f360` directory in the unzipped release file.
Select `P2PPCB Composer F360` in the **Add-Ins** tab and click **Run**.
Now the "P2PPCB" tab should appear in the F360 menu.

https://user-images.githubusercontent.com/1212166/205190084-6b400099-2b3c-4de8-aa02-cd9ade1af381.mp4

## Overview of operation

1. Design your own key layout using KLE <http://www.keyboard-layout-editor.com/> and download the result in JSON. The file is a KLE file.

You can include QMK keycodes in your KLE file. The details are later.

2. Design the height/angle of the keys using F360 surface(s).

The F360 surface is a **skeleton surface**. You also need a F360 construction plane as a **layout plane**.
You can specify a **key angle surface** to create a stepped ("staircase") profile keyboard with uniform profile keycaps (DSA/XDA, etc.).
A **main surface** in the **Initialize** command dialog is both skeleton and angle.

You can get an example set of them from a scaffold set built in PC0.
Click the green **P2P/PCB** command icon in the P2PPCB tab and check the **Generate a scaffold set** checkbox in the command dialog.

https://user-images.githubusercontent.com/1212166/205190284-dbbb6a80-51aa-4bd7-b1e0-33d8e4ddc5c1.mp4

3. Start a P2PPCB project

Specify the main preference of key switch, cap, stabilizer, vertical alignment, etc.
The F360 file holds the preference.

You can run this command more than once.

https://user-images.githubusercontent.com/1212166/205190521-6bdee0ec-76c7-4ee5-b622-5411ba3257b6.mp4

4. Load KLE file

This can take tens of minutes for a large keyboard. F360 is not very suitable for P2PPCB Composer, but you don't want to pay
thousands of USD for CATIA, I guess.

This command uses RPA when the cache is not enough. You cannot use the mouse/keyboard while running RPA.

https://user-images.githubusercontent.com/1212166/205190601-aa501d4e-4c94-4c00-b48b-c263d903dbeb.mp4

DISCLAIMER: Key decals will be odd if the display scale is not 150%. It comes from the bizarre behavior of F360.
F360 lacks decal API.

5. Adjust any key

Of course you can move any key.

https://user-images.githubusercontent.com/1212166/205190738-955e6beb-f937-490e-a4c4-32c4ce18899b.mp4

You can also change the switch / cap / stabilizer / etc. of each key by using the **Change Key** command.
A bit bizarre behavior can occur in this command. See the video below.

https://user-images.githubusercontent.com/1212166/205191054-84a16ef2-c920-4fa9-a5d0-66a4c00a2914.mp4

6. **Fill** command

A generated frame doesn't have holes for keys yet. It is intended for the Fill/Hole method. The details are later.

https://user-images.githubusercontent.com/1212166/205191342-d7a71c5c-0b93-40e0-bb5d-ce35f1fff37d.mp4

7. Place mainboard and feet

You can run this command more than once. In most cases, you'll need to do many to place the feet.

In most cases, you will need to check for interference. It is extraordinarily slow. Use it carefully.

https://user-images.githubusercontent.com/1212166/205191446-48d868da-c83e-4557-8093-cd8c0a0816a8.mp4

8. Connect mainboard/feet bosses to a frame

You need to do this step through F360's features like loft, extrude, etc.

https://user-images.githubusercontent.com/1212166/205191579-d20d2189-508d-4ecd-a077-7d0353ef2241.mp4

9. **Hole** command

It creates a 3D printable solid body. Right-click the body in the browser, select **Save As Mesh**, select STL and click OK.
Send the STL file to your 3D printing service shop.

https://user-images.githubusercontent.com/1212166/205191677-80e63a34-99b5-444a-b3b5-ab5381502606.mp4

10. There is a thin wall? Oh...

3D printing cannot print thin walls. This often occurs in elaborated designs.
Some 3D printing service shops will accept such STL files if you take on all the risks. Some don't.
In that case, you have to remove them yourself (or ask another shop).

## Bridge and Fill/Hole - MF/MEV method

Switches, stabilizers, and screws should be fastened to their holes in the frame. Such holes must be free of obstructions,
otherwise parts will get stuck.

On the other hand, a frame itself is not so strict about defects. A frame should be strong, rigid,
and have essential areas to hold parts (such as internal screw threads).
Except for the essential areas, a frame can have some defects (voids) to some extent. Let's call such
non-essential areas which surrounding essential areas as "support areas".

PC0 adopts the Fill/Hole method to form a frame. Fill: create a solid. Hole: cut the solid.

How to create a solid? By connecting essential+support areas to each other. Where the key layout is dense,
the essential+support areas of the keys overlap. In this case, a simple "join" operation is sufficient.
Where the key layout is sparse, a **bridge** should connect the essential+support areas.
A bridge is a board parallel to the skeleton surface. 
By joining essential+support areas and a bridge, a solid is created. This is **Fill**.

Cutting the solid will be obvious. Holes must be void without obstructions,
so the Fill/Hole method doesn't allow fill-after-hole. This is **Hole**.

After Fill/Hole, we need to check that essential areas are filled without defects. The area that must be filled is **MF** (must-filled).

Hole areas don't always match their parts. Two parts cannot occupy the same area, but two insert paths can do. 
An insert path is occupied by a part during assembly, but is empty after the part is assembled.
A typical case is Cherry-style stabilizer's wire. Thus, a hole area can be larger than its part.
To know the area of a part itself, and to check the interference of parts with each other,
we need the **MEV** (must-exclusively-void) area in addition to the hole area.

To reduce the inference check computation, there is **Territory**. It declares the outer edge of fill-hole areas of a part.
You won't find it in normal operation.

**Placeholder** will be obvious. It is for developers only too.

## QMK keycodes in your KLE file

QMK keycodes can be found here: <https://github.com/hajimen/qmk_firmware/blob/p2ppcb/docs/keycodes.md>

By including the keycodes in your KLE file, P2PPCB can help you a lot. Just write the keycode (of layer 0) in the the front-left legend of the key.
The front-center legend is layer 1, and the front-right legend is layer 2. You can see the example in
`scaffold_data/starter-kit.json`.

## Keyboard matrix

Keyboard matrix: <https://github.com/hajimen/qmk_firmware/blob/p2ppcb/docs/how_a_matrix_works.md>

P2PPCB Bob/Charlotte uses S and D instead of row and col. QMK's row and col are independent of the current direction 
(ROW2COL and COL2ROW are both capable), but S and D are always S to D.

By assigning a matrix, and by including the keycodes in your KLE file, you can generate route data
(QMK keymap and wiring diagrams) and VIA keymap.
Without them, your life will be much harder. Use the **Assign Matrix** command and the **Generate Route** command in the P2PPCB tab.

Generating route data for split keyboards is not supported. You need to combine two keymaps into one by yourself.
The example is shown at <https://github.com/hajimen/qmk_firmware/blob/p2ppcb/keyboards/p2ppcb/charlotte/keymaps/ntcs/keymap.c>.

## Show all available caps

There are several `test.json` files in `p2ppcb_parts_data_f360/parameters/*/`. They are KLE files
and contain all available caps for each profile. Load them with the **Load KLE** command and see the result.

By inspecting `test.json` with KLE, you can grab how to specify row (in case of row-dependent profile) and special
caps like ISO Enter.

## F360's bug in parametric modeling

In some cases, parametric modeling is better than direct modeling, especially for making a cover. In parametric modeling mode, 
the placeholders of keys sometimes slip. This is F360's bug. In this case, use the **Sync Key** command.

## Advanced features and design

### 'Place Misc' command

This command places a F3D file for miscellaneous parts and components.
So far this command is for:

- trackpads and its Qwiic-to-FFC adapters
- cover bosses

The F3D files should provide Placeholder / Fill / Hole / MF / MEV / Territory bodies.

After **Fill** command and before **Hole** command,
run the **Place Misc** command (should be found under the **PLACE PARTS**) in the P2PPCB tab.
It opens a file dialog. Choose an appropriate F3D file. Adjust the place. You can run the command
repeatedly on the same F3D file.

The inserted component should be found in **P2PPCB Internal/Misc Placeholders mU0jU**.
If you need multiple occurrences, copy it and paste.

Once the place is adjusted perfectly,
copy the Fill body to the root component and connect it to the frame body.
Hole will be done by running **Hole** command.

### 'Regex Select' command

You can create a fully functional keyboard that has only a frame, no cover.
This is good enough for prototyping. But in some cases you may need a cover.

PC0 is not very helpful for making a cover, but there are some tools that can help you. 
With **Regex Select** command, you can make a F360 selection set by regex of the full path name of the entities.
You can do Fill/Hole method manually with this tool, without using **Fill** / **Hole** commands.

CAUTION: For a bug of Fusion 360, you cannot repeat **Search** now. If you failed to type right regex in the first trial,
press **Cancel** button and run **Regex Select** command again. You will see 'Selection Set n' after **OK** button.
You cannot name the created F360 selection set in the command dialog for the bug.
The bug: <https://forums.autodesk.com/t5/fusion-360-api-and-scripts/selectionsets-add-doesn-t-work-when-the-entity-is-proxy/m-p/11914208>

CAUTION: Unselect all objects before running the command.

### 'Remove Undercut' command

Covers should be assemblable with their frames. You will encounter undercuts by running 'Combine' command.
They will make a cover impossible to assemble.
To remove undercuts, run 'Remove Undercut' command, select surfaces and a cover body.

### 'Set Attribute' and 'Check Key Assembly' commands

See the tooltips for each command. Creating a part's data requires deep knowledge, including F360's bug.
You should be a developer of PC0 if you want to create a part's data.

# For developers

If you are familiar with F360 add-in development, you'll notice that PC0 uses a bunch of bizarre hacks.
Let's see the hacks.

## RPA for decals

F360 API cannot handle decals yet. So I need to get around the limitation by using RPA.
The hack is modularized as **f360_insert_decal_rpa** <https://github.com/hajimen/f360_insert_decal_rpa>.

## Regression tests

The F360 script in `composer_test` runs regression tests. Please take a close look at `sys.path.append()` and `reimport.py`
hacks.

Convenient command launchers for debugging are available in `composer_test`. See the code.

`test_generate_route` is quite slow while the VSCode debugger is attached.
This is due to the behavior of cefpython3 under F360 + VSCode debugger. I don't know why.

## Lazy binding through surrogate

From the end of a create event to the end of an execute event, the F360 command cannot import F360 components. 
Importing should be done in a create event handler or after an execute event.
Importing in a create event handler breaks the cancel button behavior (I did it in the **Load KLE** command). 
Importing after an execute event is done by F360 custom event: <https://help.autodesk.com/view/fusion360/ENU/?guid=GUID-EC785EB6-22A8-4932-B362-395262D802CF>

Anyway, F360 cannot import anything while a command dialog is displayed.
We need to build/manipulate an object tree before the objects become available.
In other words, we need lazy binding. So I adopted the surrogate method.
Objects-in-the-future are represented by surrogates.
After importing, the surrogates are replaced by real objects.

## Magic string 'mU0jU'

F360 doesn't allow name collision of F360 components. All F360 components should have unique name.
To avoid name collision with user's components, I add magic string 'mU0jU' to most components' name.
(The exception is 'P2PPCB Internal'.)

## How to build `app-packages-win_amd64` (Windows)

Prepare `%PATH%` for F360's `python.exe` and its `Scripts` directory.

```
python -m pip install --upgrade pip
pip install piprepo setuptools wheel build
mkdir repos
cd repos
mkdir pep503
git clone https://github.com/hajimen/f360_insert_decal_rpa
cd f360_insert_decal_rpa
python -m build --wheel
cp dist/*.whl ../pep503
cd ..
git clone https://github.com/hajimen/pykle_serial
cd pykle_serial
python -m build --wheel
cp dist/*.whl ../pep503
cd ..
git clone https://github.com/hajimen/kle_scraper
cd kle_scraper
python -m build --wheel
cp dist/*.whl ../pep503
cd ..
git clone https://github.com/hajimen/p2ppcb_software
cd p2ppcb_software/p2ppcb_parts_resolver
python -m build --wheel
cp dist/*.whl ../../pep503
cd ..
piprepo build ../pep503
cd p2ppcb_composer_f360
pip install -r requirements.txt -t app-packages-win_amd64 --extra-index-url ../../pep503/simple
```

## How to build `app-packages-macosx_*` (Mac)

Use python.org's or Homebrew's python 3.11 because Mac F360's python lacks `pip` module.
If you run on Apple Silicon, you can choose Intel or Apple Silicon by `arch` command.
It is true for F360 itself.

Architecture independent part:

```
pip install --upgrade pip
pip install piprepo setuptools wheel build
mkdir repos
cd repos
mkdir pep503
git clone https://github.com/hajimen/f360_insert_decal_rpa
cd f360_insert_decal_rpa
python -m build --wheel
cp dist/*.whl ../pep503
cd ..
git clone https://github.com/hajimen/pykle_serial
cd pykle_serial
python -m build --wheel
cp dist/*.whl ../pep503
cd ..
git clone https://github.com/hajimen/p2ppcb_software
cd p2ppcb_software/p2ppcb_parts_resolver
python -m build --wheel
cp dist/*.whl ../../pep503
cd ..
piprepo build ../pep503
cd p2ppcb_composer_f360
```

Architecture dependent part:

```
tag='macosx_10_10_x86_64'  # or 'macosx_11_0_arm64'
pip install -r requirements.txt -t app-packages-$tag --extra-index-url ../../pep503/simple
```

# Further development

So far, PC0 remains in sketchy quality. *In many cases*, it helps you to design your own keyboard.
In some cases, it annoys you more than it helps.
In other cases, it gets stuck in F360's bugs. We need further development to improve the quality of PC0.

## F360's bugs that can annoy you or get you stuck

In some cases, interference check doesn't work:
<https://forums.autodesk.com/t5/fusion-360-support/obvious-interference-was-not-detected/m-p/10633251>

In some cases, `importToTarget()` corrupts the imported component. See `p2ppcb_parts_depot.depot.prepare()`.
The bug is erratic and non-reproducible. I suspect it has something to do with CPU usage.
When it occurs, `P2PPCB Cache` file is corrupted. Remove the file and try again.
But it can be difficult to detect the phenomenon.

Attributes of native objects can be destruct by some irrelevant operations: 
<https://forums.autodesk.com/t5/fusion-360-support/attributes-of-native-objects-corrupt-by-removing-a-component/m-p/11909404>
You cannot import `P2PPCB Internal` component from other files for this reason. Import will corrupt attributes.

Intel Mac F360 has a bug in floating point operation:
<https://forums.autodesk.com/t5/fusion-360-api-and-scripts/python-bug-of-ieee-754-subnormal-number-on-intel-mac/td-p/12133211>
I think we should forget Intel Mac. It is going to be obsolete.

A component by Insert Derive goes wrong about decal:
<https://forums.autodesk.com/t5/fusion-360-support/a-component-by-insert-derive-goes-wrong-about-decal/m-p/11913925>

## Mac and decals

We can make f360_insert_decal_rpa functional on Mac, but I think we should wait for Autodesk adds decal API.

Moreover, `cefpython3` is going to be obsolete. It haven't be updated from 2021 and I need to build it for Python 3.11.
It can be a big problem for Windows someday.

(Why using CEF, instead of custom rendering? Because a web browser is a super font resolver and text renderer.
The resolution and rendering is almost impossible to mimic.)

## Route generation on Apple Silicone

Actually we can make it work by building the COIN-OR CBC source and setting the environment variables.
But I think we should wait for Python-MIP project make it available.
