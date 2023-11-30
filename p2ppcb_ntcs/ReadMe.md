# P2PPCB NTCS keyboard overview

![NTCS left](https://gist.github.com/assets/1212166/32299ca1-f364-4737-9eea-4bd8399780eb)

![NTCS right](https://gist.github.com/assets/1212166/e9124f41-d4e5-4bbc-bf16-de905afbb88d)


**P2PPCB NTCS** keyboard is a reference design of P2PPCB platform. It demonstrates the ability of P2PPCB platform 
to produce elaborate and real-world (not mass-produced) products.

The "NTCS" stands for "Near TKL Conservative Split". 
It is conservative because it accepts ready-made keycap sets (should be row-independent uniform profile like XDA or DSA) 
for common US-ASCII TKL (87-keys) keyboards. It hides several obsolete keys (Pause, Scroll Lock, Print Screen, Caps Lock, Insert, Menu)
under QMK layer, but all other TKL keys are there, so "Near TKL".

You can use it as a reference for your design, as a test specimen to evaluate P2PPCB platform in the real world, 
or just for fun.

# Covered and naked style

P2PPCB platform is mainly for rapid prototyping, so it adopts "naked style" as its usual products. This is an example of the naked style:

![Naked style 1](https://user-images.githubusercontent.com/1212166/223884622-39fb7f13-f122-4abf-98a7-62fd1bab328f.jpg)

![Naked style 2](https://user-images.githubusercontent.com/1212166/223884690-81c0ba6f-90c2-4a8e-ae31-295ae04dcca4.jpg)

In naked style, the wires are exposed. It is good for rapid prototyping because it is enough for testing in a lab.
Making a cover is a waste of time and money in this case.

The real world requires a covered style. Once you are confident with your own design in your lab with the naked style, you can bring it 
into the real world with the covered style.

![Covered style](https://user-images.githubusercontent.com/1212166/223887875-9ccec73b-69ee-4c0e-9a9c-8b3fb7aff4e8.jpg)

P2PPCB NTCS keyboard shows an example of covered style. The structure is thoroughly tested by the real 3D printing results.
I recommend you to imitate the structure on your own design.

# How to assemble

If you feel hard to prepare all parts / components and assemble them, please ask me via email.
The price is $1000 without switches, keycaps, and the shipping charge.

## Parts list

- P2PPCB mainboard Charlotte set: 2 sets
- P2PPCB matrix wire cable for Charlotte: 2 pcs
- P2PPCB adjustable foot kit: 4 sets
- P2PPCB split keyboard kit: 1 set
- P2PPCB MX normal: 82 pcs of fragment (4 pcs of full board and 2 pcs of fragment)
- P2PPCB MX LED: 2 pcs of fragment
- M2.6 x 7 mm pan-head self-tapping screws for plastic: 16 pcs
- Cherry MX compatible key switch: 84 pcs
- Keycap set, row-independent uniform profile, common US layout TKL (87-key): 1 set
- Translucent 1u keycap: 2 pcs
- Blank 1u keycap: 2 pcs
- Cherry-style plate mount stabilizer for 2u: 4 pcs
- P2PPCB NTCS frames and covers, printed by Somos LEDO 6060: 1 set
- (Optional) Kyocera AVX single IDC contact accessory cap 609176001415000: 168 pcs

## Precision check

![Precision checker](https://user-images.githubusercontent.com/1212166/209415583-0d614ed5-e443-4265-84e2-5a9159c72551.PNG)

You can find these indentations on the covers of NTCS. They are precision checkers for verifying the precision of 3D printing results.
Get an M3 screw or a 3.0 mm drill bit, and try to push it (chuck side or tail) into a gap between three indentations, 
as shown in the figure below.

<img width="398" alt="Precision check" src="https://user-images.githubusercontent.com/1212166/209415763-1a1ac968-f855-432b-82f8-1d7e7763d093.PNG">

Seven indentations consist a section, and two sections are paired side-by-side. 
The diameter of the green translucent cylinder shown in the figure above is 2.9 mm, or 3.1 mm in the drawings. 
One of the section of a pair is 2.9 mm, and the other is 3.1 mm. Therefore, if a 3D printing 
result is enough precise, you can easily insert a 3.0 mm cylinder into all six gaps of the 3.1 mm section, 
and feel difficult to insert into any gaps of the 2.9 mm section.

The section pairs are installed on the XY, XZ, and YZ planes of a cover because many 3D printers have anisotropy. 
If your 3D printing result fails the test, you may face a problem during assembling. Actually 2.9 mm gaps
can accept 3.0 mm (3D printers tend to have minus tolerance, -20 to -50 μm), but all 3.1 mm gaps must accept 3.0 mm.

## Writing firmware

At the time of shipment, the mainboards' firmware is starter kit's. You need to write the NTCS firmware to the mainboards.
The firmware file is `p2ppcb_charlotte_ntcs.uf2` in this directory.

Unplug the USB, press the BOOTSEL button, and plug USB. You'll find the `RPI RP2` drive on your PC.
Copy the firmware file into the drive. The mainboard will automatically reset itself and become NTCS.

You should write it on both left and right, of course.

## Single IDC contact accessory cap

For P2PPCB starter kit, there are no covers on single IDC contacts. This is reliable enough 
while the keyboard is in the lab. If you find a disconnection, just fix it with the tool.
It is quite rare.

But in the real world, sometimes "quite rare" is not enough. The accessory cap ensures the reliability. 
When you finish an operation test successfully, apply the caps on the contacts. Long nose pliers will help you.

CAUTION: Once you apply a cap, you cannot remove it without damaging the contact-to-socket assembly. 
Check the operation carefully before applying.

CAUTION: If you are using non-genuine matrix wire, the cap may not be applicable. 1.2 mm diameter is the upper limit of the thickness.
The peel-offed wire of a common ribbon cable (1.27 mm pitch) exceeds the limit.

## Tightening screws and warp correction

First of all: Please note that **3D printing material is fragile against small screws such as M2.6**. 
The tightening force should be much less than for normal screws. Just stopping the rattling is enough. 
It cannot withstand too many tightening-loosening iterations. 

I assume that you have already assembled a P2PPCB starter kit. There will be no hard part before
fastening the frame to the cover (please check the operation before fastening). 
The fastening is a bit tricky, because the design is the countermeasure of the warping of the 3D printing results.

Put the frame into the cover, and:

1. Put M2.6 x 7 mm screws into the holes of the cover wall. Don't tighten them, just screw them in a little.
2. Put a M2.6 x 7 mm screw into the hole in the center of the cover bottom. Tighten it mildly.
3. Make sure that the cover bottom is completely flat. If it is not flat, the feet will rattle. 
This is very common because 3D-printing results are always warped.
4. By pushing or pulling the frame to the cover, make the cover bottom flat, and tighten mildly the screws of the wall.

# How to use

The keycaps are row-independent uniform profile. So you can reallocate all 1u keycaps as you like.
Of course you can remap keycode using VIA. The draft definition file for VIA can be found here: 
<https://github.com/hajimen/p2ppcb_software/blob/main/p2ppcb_ntcs/via_keymap.json>

The left and right bodies both have a Micro USB type-B connector. You can choose one whichever you like and connect it to your PC.

The hole on the cover near the USB connector is for BOOTSEL button of Raspberry Pi Pico. You can press BOOTSEL button via the hole
to write new firmware.

The LED keys in front of the space keys are for Caps Lock / Scroll Lock indicator. 
I map LANG2 / LANG1 on them (useful keys for Japanese input) in QMK layer 0. 

The finger assignment shown in the figure below may look strange. 
The "Typing Method" says that you should press the "1/!" key by your pinky finger,
but I think this is outdated rubbish from the age of non-electric typewriters and professional typists. They didn't use wrist rests 
because they had to hit the keys with an adequate even force, like a pianist. If the hitting force is uneven, the thickness of the letters 
will be uneven. This was not considered the workmanship of a professional typist. So they hit the keys with their shoulders and arms, 
not with palms and fingers. In this case, the shortness of the pinky finger is not a 
problem because the upper arm moves and covers all the keys on a keyboard. 
Also, professional typists didn't develop sentences in front of a typewriter because there was a manuscript to type. 
No revising or editing, of course. In front of a typewriter, they just typed without stopping. 
There was no room for wrist rests, like on a piano.

Today we live on another planet. 
NTCS has built-in wrist rests. It doesn't assume shoulder-and-arm typing. Long fingers should press distant keys.

![Finger Assignment](https://gist.github.com/assets/1212166/765ac001-6a24-4a5b-9e1b-88803966ebfe)

# The design process of NTCS

P2PPCB platform is for rapid prototyping. So I guess you are going to start a design process with it.
The F3D files show the final result, not the process. Let's see the story.

## Starting point 1: TRON keyboard TK1

The 1980s was the golden age of bizarre keyboards. The pinnacle is TRON keyboard TK1, 1991.

![TK1](https://user-images.githubusercontent.com/1212166/207522147-169f17b4-5e90-4ddc-b5a0-c8648aa0439f.jpg)

![Cited from SAKAMURA Ken, Keyboard Dangi 7, bit (1990) Vol. Dec.](https://user-images.githubusercontent.com/1212166/207523753-d67a0784-211e-408c-b4dd-8eed3ca3c4a1.jpg)

TK1 has its long story. I only enumerate the ideas what I stole from it.

- 10° twist along front-back direction and built-in wrist rests

These two ideas are closely related. 10° twist along front-back direction requires uncommonly high-profile wrist rests 
because the keytop altitude of the inner area is much higher than common keyboards.
Built-in wrist rests can be uncommonly high-profile.

- Wedge-shaped gaps between keytops

My dear keyboard people, please stop filling a keyboard with keytops. This is a quite common mistake
in the industry. Key separation (the ability to press a key without interfering with other keys) is much more 
important than keytop largeness, and key separation requires gaps between keytops.
Your habit may say "Gaps between keytops are ugly". Please break that habit now.

NTCS's wedge angle is much sharper than TK1's. TK1's angle is more bizarre and attractive, but I've come to 
the conclusion that it is not good for typing.

- Small space key and Shift keys with thumbs

These ideas were very common even before TK1. Maltron's keyboard in 1980 had a small space key.
Fujitsu's "親指シフト" (Thumb Shift) keyboard in 1980 had Shift keys with thumbs (the space key was also small). 

- Arrow keys under the main cluster (right side only)

Symmetrical arrow keys are the great charm of TK1. I tried to mimic this by placing Home / End / PgUp / PgDn instead of 
red arrows on the left hand part, but when I tested the layout with several prototypes, I realized that this is a bad idea. 
All navigation keys should be assigned to the right hand, because the left hand should focus on copy / paste.

- How about other ideas?

As you can see, I didn't adopt many ideas in TK1. Symmetrical and column-staggered layout, 
built-in drawing tablet, 3-bank typewriter style shift (left and right Shift keys work differently), 
16 mm pitch, etc. Yeah TK1 is the pinnacle of the bizarre keyboards of the 1980s. 
I miss these ideas, but this is a design process.

## Starting point 2: Ready-made keycap set

I am running a custom keycap shop [DecentKeyboards](https://www.etsy.com/shop/DecentKeyboards). 
I can print any legends on white PBT blank keycaps. But such custom keycaps can distract 
attention from the capabilities of P2PPCB platform. NTCS is a reference design for P2PPCB platform, 
not an ultimate keyboard.

(Besides, an ultimate keyboard requires a new ecosystem. OS, applications, common practice, 
users, developers, hardware and its supply chain. 
TRON keyboard TK1 was a part of such a new ecosystem "BTRON", but it failed. From this experience, 
I think that an ultimate keyboard will not be profitable, not widely available, not even very good for most people in the real world, 
even if it is mass-produced and its price is around ordinary keyboards. An ultimate keyboard is like 
an exotic car. Its price may be several hundred times of ordinary products, but it is inferior to ordinary products 
in most respects, even without taking the price into account.)

Swapping keycaps is a great hobby. It is much harder with custom keycap-based keyboards. 
A ready-made keycap set is a great product of the existing ecosystem.

## Starting point 3: Keyboard shortcuts of Windows applications

Actually, I'm not a big fan of keyboard shortcuts. Of course I use them heavily, but because of that, 
my pinky finger hurt often (now I am free of the pain with NTCS). From a productivity standpoint, 
keyboard shortcuts are negligible IMHO. I use them just because I'm impatient with using a mouse.

Not all the people (including keyboard people) are so impatient. Prioritizing keyboard shortcuts is an important 
decision, because it completely changes the design.

For example, by prioritizing keyboard shortcuts, all modifier keys should be easy to press simultaneously, 
in any combination, with one hand.
(I think multiple pressing of modifier keys is 
a bad idea in the existing ecosystem. Commands should be invoked when the keys are released, just like mice and touchscreens. 
But NTCS is not an ultimate keyboard).
Because of this requirement, 
yet another modifier key (i.e. QMK layer) is hard to use heavily. Ctrl+Shift+F5 is a very familiar shortcut in Visual Studio, 
but if F5 is hidden by yet another modifier (YAM) key, Ctrl+Shift+YAM+5 should be easy to press. 
In Japanese typing, F7 is a very frequently used key. YAM+7 should be as easy to press as Shift+7. 
I think it is impossible to fulfill all of these requirements under all of the prerequisites above.

Under different prerequisites, heavy use of YAM key can be a good design because it can reduce the number of keys on a keyboard. 

## Starting point 4: Stateless (as far as I can)

I hate intangible states. The downfall of keyboards started when the latching mechanism of Caps Lock key was substituted by LEDs.
One-shot modifier of QMK is a kind of intangible states.

## Other ideas stolen from various keyboards

- Del key at the left edge

The idea comes from Symbolics keyboard (namely Space-cadet). The RUB OUT key is a legend.

- Esc key at the left top corner of the main cluster

This was common before the dominance of IBM Model M layout. I'd like to name HHKB as the resistance movement against
the dominance.

## Iteration 1

https://user-images.githubusercontent.com/1212166/207766975-fe80b625-9c89-4bb3-ab00-f115f13a7b42.mp4

The first trial. Left hand only, naked style, custom keycap based. In this iteration, I didn't adopt the start point 2.

I got a lot of findings in this iteration. 

- Thumb keys should be tilted in the opposite direction of the other keys.
- Wrist rests should be uncommonly high-profile, because the keytop altitude of the inner area is 
much higher than common keyboards.
- Pinky finger keys should be more front.

## Iteration 2

https://user-images.githubusercontent.com/1212166/207769963-8871a65c-baf6-4fd5-8fc1-cc160b2b6ee9.mp4

The first trial of the covered style. I adopted the start point 2 from this iteration.

- Small space key should be in front of V. Shift key should be the right neighbor of the space key.
- Q should be pressed by a ring finger.
- Thumb keys should be lower.
- Ctrl key should be a thumb key.

I don't mention the problem of the covered style. Just imitate the conclusion shown in the F3D files of NTCS.
And I don't mention the right hand part too. It will be redundant.

## Iteration 3

https://user-images.githubusercontent.com/1212166/207800112-49950f18-dee0-47fb-89b6-9756c5d27d19.mp4

https://user-images.githubusercontent.com/1212166/207801987-bb7279e0-d1bd-43f7-8470-23f2b017d544.mp4

The first trial of built-in wrist rests. I thought of taking a video at this time.
The material is SLA of WENEXT. Built-in wrist rests take up a lot of space,
and it makes 3D printing much more expensive.

- The position of the Alt key is not a good idea.
- Pressing the space key interferes with End key.
- The wrist rests are too long in front-back direction.
- Shift and Ctrl keys should be a bit further back.
- Ctrl key should be 1 mm higher.
- Q row of pinky finger section should be slightly higher for key separation.
- Tab key is too far for pinky finger.

## Iteration 4

https://user-images.githubusercontent.com/1212166/207805898-d4af1ae7-47c4-46dc-a097-f8915beb6a94.mp4

https://user-images.githubusercontent.com/1212166/207806336-694a83c3-6f9b-410a-8993-eb757cfd567e.mp4

- Shift key should be further front.
- LANG1 should be lower. Pressing the Ctrl key interferes.
- Symmetrical layout of arrow keys (Home / End / PgUp / PgDn - Left / Right / Up / Down) is a bad idea.

## Iteration 5

https://user-images.githubusercontent.com/1212166/207811766-837e6841-0c39-4954-b991-4490d437edb7.mp4

https://user-images.githubusercontent.com/1212166/207813334-f48241b7-b52c-4ad7-b488-d3c9fbc1e20a.mp4

In this iteration, the material is MJF PA12 black.

- Function keys interfere with my palm. The function key cluster should not tilt.

## Iteration 6

This is the last iteration worth mentioning. I have done many more, but the findings are trivial.
This iteration is not the final result, but it is close enough for the purpose of this story.

https://user-images.githubusercontent.com/1212166/207817193-05dbc5cd-c3d1-442c-9eca-ad06bcb6c566.mp4

https://user-images.githubusercontent.com/1212166/207817925-683ccf40-5cc8-40d5-9adb-0121a6b742cf.mp4

- The key angle surface should be finely tuned.

# How to imitate the structure of NTCS

It is far from straightforward. If you feel it is too tedious, please ask me. I can make a covered style 
from your naked style F3D file. It costs, of course.

The basic story is the Fill/Hole method. You should do the method manually to the cover.
In the F3D file of NTCS, on the object browser, expand `P2PPCB Internal/Foot Placeholders mU0jU/Foot A_FL:1/Foot_P:2/Bodies`.
You'll find a `Foot Fill Cover` body. `Cover Boss.*/Bodies` and `Adjust Boss.*/Bodies` also have bodies with such names. 

The **Regex Select** command will help you. You can see the results of the command 
in the "Selection Sets" of the object browser.

`P2PPCB Internal/Depot Parts mU0jU/Switch MX_P:1/Bodies/MF/Switch Fill.*` is a very important trick that is hard to 
comprehend. See the timeline of the F3D file step by step. The fill body of `Switch MX_P` is modified from the original 
before the **Fill** command is executed. The modification makes it possible to connect a bridge body to a switch 
fill body using the **Extrude** command.
