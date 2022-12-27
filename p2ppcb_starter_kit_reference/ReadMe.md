# P2PPCB Starter Kit Bob / Charlotte

P2PPCB Starter Kit Bob / Charlotte is a starter kit of P2PPCB platform. You can test the actual 
quality and experience of P2PPCB platform by this kit.

## How to Assemble

### 1. Prepare tools at your own

Hand tools:

- Philips screwdriver, PH1 size
- Slotted screwdriver, 3.5 mm width, 0.6 mm thick, at the edge (smaller is OK)
- Scissors or cutting pliers
- (Optional) Key switch puller
- (Optional) Digital multimeter

TODO photo

VIA: <https://www.caniusevia.com/>

### 2. Check the content of the kit

Please check the content of the kit with the included paper manuals.

### 3. Assemble contact-to-socket assemblies to the frame

Tear a fragment of contact-to-socket assembly from a full board.

TODO movie

Insert the fragment into the hole of the frame.

CAUTION (Charlotte): Look at the wiring diagram! There is a LED fragment. Don't insert 
normal fragment into the hole.

TODO movie

Push it in the hole by the slotted screwdriver.

TODO movie

### 4. Assemble a mainboard to the frame

Be careful of the direction.

TODO photo

**CAUTION: MJF (the material of the frame) is fragile against small screws!** 
The tightening force should be much smaller than common screws. Just stopping rattling is enough. 
It cannot bear too many tightening-loosening iterations.

### 5. Put matrix wiring cable to the mainboard

### 6. Tear the matrix wiring cable and cut unused wires

Look at the wiring diagram on the paper manual carefully. If you feel hard to read it, use the digital images below.

- Starter Kit Bob: <https://github.com/hajimen/p2ppcb_software/blob/main/p2ppcb_starter_kit/bob/wiring_D.png> <https://github.com/hajimen/p2ppcb_software/blob/main/p2ppcb_starter_kit/bob/wiring_S.png>
- Starter Kit Charlotte: <https://github.com/hajimen/p2ppcb_software/blob/main/p2ppcb_starter_kit/charlotte/wiring_D.png> <https://github.com/hajimen/p2ppcb_software/blob/main/p2ppcb_starter_kit/charlotte/wiring_S.png>

TODO photo

### 7. Install wires into the contacts

Again, look at the wiring diagram carefully. But it is difficult. So the kit bundles three 
matrix wiring cables :-)

TODO movie

If you find that you go wrong, extract the wire carefully, and strengthen the damaged points of the wire 
by scotch tape or something.

Damaged wires unexpectedly bear tension, but are vulnerable to folding. This is true for normally installed points.
Don't fold wires at contacts.

### 8. Assemble key switches to the frame

Just push it.

TODO movie

It might look quite easy, but sometimes fails like below. Please push it perpendicularly.

TODO photo

### 9. Check the operation by VIA

Load the draft definition file of your mainboard into VIA.

- Starter Kit Bob: <https://github.com/hajimen/p2ppcb_software/blob/main/p2ppcb_starter_kit/bob/via_keymap.json>
- Starter Kit Charlotte: <https://github.com/hajimen/p2ppcb_software/blob/main/p2ppcb_starter_kit/charlotte/via_keymap.json>

If you find non-operating key switches, check the conduct of wire-to-socket. If it fails, push the contact by the tool again.
Otherwise, pull the key switch off and see the contacts.

### 10. Assemble feet to the frame

Again, **CAUTION: MJF (the material of the frame) is fragile against small screws!** 
The tightening force should be much smaller than common screws. Just stopping rattling is enough. 
It cannot bear too many tightening-loosening iterations.

About the combination of screws and spacers, please look at the included paper manual of the foot kit.

### 11. Install keycaps to the key switches

Just push it to the switch. In Charlotte, OSM-Ctrl is a translucent keycap.

![Starter-Kit-Bob](https://user-images.githubusercontent.com/1212166/209491521-de1addab-7ca9-49f6-8644-644fdeb20af5.jpg)

## How to Use

### Inspect the F3D file comparing with the real item

Prepare [Autodesk Fusion 360](https://www.autodesk.com/products/fusion-360/overview) on your 
Windows PC or Mac (just for the inspection, Mac is OK, non-English language is OK), and open the F3D file below.

- Starter Kit Bob: <https://github.com/hajimen/p2ppcb_software/blob/main/p2ppcb_starter_kit/bob/Starter Kit Bob.f3d>
- Starter Kit Charlotte: <https://github.com/hajimen/p2ppcb_software/blob/main/p2ppcb_starter_kit/charlotte/Starter Kit Charlotte.f3d>

`P2PPCB Internal:1` in the object browser is an important one. Unfold it and inspect. Toggling the eye icons is also meaningful.

### Compile and modify the firmware

VIA can configure almost everything about Bob. About Charlotte,
you will need your own firmware for your own design.

The codebase is here: <https://github.com/hajimen/qmk_firmware/tree/p2ppcb>
`git clone -b p2ppcb https://github.com/hajimen/qmk_firmware` and see `keyboards/p2ppcb/charlotte`.

### Swap key switches and test them

MJF frame has intrinsic stiffness and acoustics. They are very different from steel. 
If you are interested in them, test it by yourself.

If you need stiffer material, SLA can be a good choice.
