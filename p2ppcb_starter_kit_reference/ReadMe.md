# P2PPCB Starter Kit Bob / Charlotte

P2PPCB Starter Kit Bob / Charlotte are starter kits of P2PPCB platform. You can test the real 
quality and experience of P2PPCB platform through these kits.

## How to assemble

### 1. Prepare tools at your own

Hand tools:

- Philips screwdriver, PH1 size
- Flat screwdriver, 3.5 mm wide, 0.6 mm thick, on the edge (smaller is OK)
- Scissors or cutting pliers
- (Optional) Key switch puller
- (Optional) Digital multimeter

![Hand tools](https://user-images.githubusercontent.com/1212166/223644826-3b770b9c-8dd4-4a55-8b35-bde6ccc00fea.jpg)

VIA: <https://www.caniusevia.com/>

### 2. Check the contents of the kit

Please check the contents of the kit with the included paper manuals.

### 3. Assemble contact-to-socket assemblies to the frame

DISCLAIMER: The videos show gray frame (MJF). The actual product is white (Somos Ledo 6060).

Tear a fragment of a contact-to-socket assembly from a full board.

https://user-images.githubusercontent.com/1212166/223646746-8ab56e6a-60d3-4587-8ffc-27e4f80802d5.mov

Insert the fragment into the hole in the frame.

CAUTION (Charlotte): Look at the wiring diagram! There is an LED fragment. Don't insert 
the normal fragment into the hole.

https://user-images.githubusercontent.com/1212166/223647008-41a2cce3-f3a8-4095-b10f-7d3f8a6ce913.mov

Push it into the hole with the flat screwdriver.

https://user-images.githubusercontent.com/1212166/223648865-bf569a75-6fc2-442b-8305-fc646b1283ee.mov

The result should be like this:

https://user-images.githubusercontent.com/1212166/223649365-13185463-47a5-4ad2-a7eb-a47b0a8cba95.mov

### 4. Assemble a mainboard to the frame

Pay attention to the direction.

https://user-images.githubusercontent.com/1212166/223650886-23f14d98-9855-4501-9a1c-a5af57097b62.mov

**CAUTION: Somos Ledo 6060 (the material of the frame) is fragile against small screws!** 
The tightening force should be much less than for normal screws. Just enough to stop rattling. 
It cannot withstand too many tightening-loosening iterations.

### 5. Put matrix wiring cable to the mainboard

### 6. Peel the matrix wiring cable and cut the unused wires

Look carefully at the wiring diagram on the paper manual. If you feel hard to read it, use the digital images below.

- Starter Kit Bob: <https://github.com/hajimen/p2ppcb_software/blob/main/p2ppcb_starter_kit/bob/wiring_D.png> <https://github.com/hajimen/p2ppcb_software/blob/main/p2ppcb_starter_kit/bob/wiring_S.png>
- Starter Kit Charlotte: <https://github.com/hajimen/p2ppcb_software/blob/main/p2ppcb_starter_kit/charlotte/wiring_D.png> <https://github.com/hajimen/p2ppcb_software/blob/main/p2ppcb_starter_kit/charlotte/wiring_S.png>

### 7. Install wires into the contacts

Again, look carefully at the wiring diagram. But it is difficult. So the kit bundles two 
matrix wiring cables :-).

https://user-images.githubusercontent.com/1212166/223652054-34629ded-7a83-4f41-a15c-5276e1920c53.mov

The jig helps you.

https://user-images.githubusercontent.com/1212166/223654861-1e51b0ce-4438-439f-9aec-14645ebf921c.mov

If you find that you go wrong, carefully pull out the wire, and strengthen the damaged points of the wire 
with Scotch tape or something.

Damaged wires will unexpectedly withstand tension, but are vulnerable to bending. This is true for normal installed points.
Don't bend wires at contacts.

### 8. Assemble key switches to the frame

Just push it.

https://user-images.githubusercontent.com/1212166/223880715-38a6497c-7b95-4a4e-988e-679835631a97.mov

It may look easy, but sometimes it fails like below. Please make sure that the leads of the key switches are straight before assembling.

![Bad switch](https://user-images.githubusercontent.com/1212166/223880997-2dc6577d-440c-463e-bc9c-94f3d4491235.jpg)

### 9. Assemble feet to the frame

https://user-images.githubusercontent.com/1212166/223882839-7949211d-c44f-41d8-993c-a2fe876bee1c.mov

### 9. Check the operation with VIA

Load the draft definition file of your mainboard into VIA.

- Starter Kit Bob: <https://github.com/hajimen/p2ppcb_software/blob/main/p2ppcb_starter_kit/bob/via_keymap.json>
- Starter Kit Charlotte: <https://github.com/hajimen/p2ppcb_software/blob/main/p2ppcb_starter_kit/charlotte/via_keymap.json>

If you find non-operating key switches, check the wire-to-socket conduct. If it fails, press the contact again with the tool.
Otherwise, pull the key switch off and look at the contacts.

### 10. Assemble feet to the frame

Again, **CAUTION: Somos Ledo 6060 (the material of the frame) is fragile against small screws!** 
The tightening force should be much less than for normal screws. Just enough to stop rattling. 
It cannot withstand too many tightening-loosening iterations.

For the combination of screws and spacers, please refer to the paper manual included with the foot kit.

### 11. Install keycaps to the key switches

Just push it to the switch. In Charlotte, OSM-Ctrl is a translucent keycap.

![Starter-Kit-Bob](https://gist.github.com/assets/1212166/8dfbbca7-be66-4ea9-aa9c-559b533a91ab)

## How to use

### Inspecting the F3D file to compare with the real object

Prepare [Autodesk Fusion 360](https://www.autodesk.com/products/fusion-360/overview) on your 
Windows PC or Mac (just for the inspection, Mac is OK, non-English language is OK), and open the F3D file below.

- Starter Kit Bob: <https://github.com/hajimen/p2ppcb_software/blob/main/p2ppcb_starter_kit/bob/Starter Kit Bob.f3d>
- Starter Kit Charlotte: <https://github.com/hajimen/p2ppcb_software/blob/main/p2ppcb_starter_kit/charlotte/Starter Kit Charlotte.f3d>

`P2PPCB Internal:1` in the object browser is an important one. Expand it and inspect it. Toggling the eye icons is also useful.

### Compiling and modifying the firmware

VIA can configure almost everything about Bob. About Charlotte,
you will need your own firmware for your own design.

The codebase is here: <https://github.com/hajimen/qmk_firmware/tree/p2ppcb>
`git clone -b p2ppcb https://github.com/hajimen/qmk_firmware` and see `keyboards/p2ppcb/charlotte`.

### Swapping and testing key switches

Somos Ledo 6060 frames have inherent stiffness and acoustics. They are very different from them of steel, alloy, or FR-4 (common PCB).

### See 3D printing quality, precision, and tolerance

You can see the overall quality by your eyes and fingers.

There are indentations on the frame, as shown in below:

![Precision checker](https://gist.github.com/assets/1212166/ee06529b-bf28-4a9b-a856-8bf5e53e0886)

These indentations are precision checkers for verifying the precision of 3D printing results.
Get an M3 screw or a 3.0 mm drill bit, and try to push it (chuck side or tail) into a gap between three indentations, 
as shown in the figure below.

<img width="398" alt="Precision check" src="https://user-images.githubusercontent.com/1212166/209415763-1a1ac968-f855-432b-82f8-1d7e7763d093.PNG">

Seven indentations consist a section, and there are two sections per XY, XZ, and YZ planes. 
The diameter of the green translucent cylinder shown in the figure above is 2.9 mm, or 3.1 mm in the drawings. 
One of the section of a pair is 2.9 mm, and the other is 3.1 mm. Therefore, if a 3D printing 
result is enough precise, you can easily insert a 3.0 mm cylinder into all six gaps of the 3.1 mm section, 
and feel difficult to insert into any gaps of the 2.9 mm section.

The section pairs are installed on the XY, XZ, and YZ planes of a frame because many 3D printers have anisotropy. 
If your 3D printing result fails the test, you may face a problem during assembling. Actually 2.9 mm gaps
can accept 3.0 mm (3D printers tend to have minus tolerance, -20 to -50 μm), but all 3.1 mm gaps must accept 3.0 mm.
