# P2PPCB NTCS Keyboard Overview

**P2PPCB NTCS** keyboard is a reference design of P2PPCB platform. It proofs the ability of P2PPCB platform 
to make elaborate and real-world (not mass-producing) products.

The "NTCS" is "Near TKL Conservative Split". 
It is conservative because it accepts ready-made keycap sets (should be row-independent uniform profile like XDA or DSA) 
for common US-ASCII TKL (87 keys) keyboards. It hides several obsolete keys (Pause, Scroll Lock, Print Screen, Caps Lock, Insert, Menu)
under QMK layer 1 but all other TKL keys are there, so "Near TKL".

You can use it as a reference of your design, a test specimen for evaluating P2PPCB platform in the real world, 
or just for fun.

# Covered and Naked style

P2PPCB platform is mainly for rapid prototyping, so it assumes "naked style" as its usual products. This is an example of naked style:

TODO photos

In naked style, the wires are uncovered. It is good for rapid prototyping because it is enough for testing in a laboratory.
Making a cover is a waste of time and money in this case.

The real world requires covered style. Once you get confidence of your own design in your laboratory with naked style, you can bring it 
into the real world with covered style.

TODO photos

P2PPCB NTCS keyboard shows an example of covered style. The structure is thoroughly tested by the real 3D printing results.
I recommend mimicking the structure on your own design.

# How to Assemble

## Parts List

- P2PPCB mainboard Charlotte set: 2 sets
- P2PPCB matrix wire cable for Charlotte: 2 pcs
- P2PPCB adjustable foot kit: 4 sets
- P2PPCB split keyboard kit: 1 set
- P2PPCB MX normal: 82 pcs of fragment (4 pcs of full board and 2 pcs of fragment)
- P2PPCB MX LED: 2 pcs of fragment
- M2.6 x 7 mm self-tapping screws, pan-head, for plastic: 14 pcs
- Cherry MX compatible key switch: 84 pcs
- Keycap set, row-independent uniform profile, common US-ASCII TKL (87 keys): 1 set
- Translucent 1u keycap: 2 pcs
- Blank 1.25u keycap: 2 pcs
- Cherry-style plate mount stabilizer for 2u: 4 pcs
- P2PPCB NTCS frames and covers, printed by MJF PA12: 1 set

## Precision Test

![Precision Marks](https://user-images.githubusercontent.com/1212166/209415583-0d614ed5-e443-4265-84e2-5a9159c72551.PNG)

You can find these bulges on the covers of NTCS. They are precision marks to verify the precision of 3D printing results.
If you use MJF, nothing to care about it. But if not, the marks are useful. 
Get a M3 screw or 3.0 mm drill bit, and try to push it (the chuck side or the tail) into a gap between three bulges, 
like the figure below.

<img width="398" alt="Capture" src="https://user-images.githubusercontent.com/1212166/209415763-1a1ac968-f855-432b-82f8-1d7e7763d093.PNG">

Seven bulges consist a section, and two sections are paired side-by-side. 
The diameter of the green translucent cylinder shown in the figure above is 2.9 mm or 3.1 mm in the drawings. 
One of the section of a pair is 2.9 mm, and the other is 3.1 mm. Therefore, if a 3D printing 
result is enough precise, you can easily push 3.0 mm cylinder into all six gaps of 3.1 mm section, 
and cannot put into any gaps of 2.9 mm section.

The section pairs are installed on XY, XZ, and YZ planes of a cover because many 3D printers have anisotropy. 
If your 3D printing result fails the test, you might be going to face a problem while assembling.

## Tightening Screws and Warp Countermeasure

First of all: Please note that MJF is fragile against small screws like M2.6. 
The tightening force should be much smaller than common screws. Just stopping rattling is enough. 
It cannot bear too many tightening-loosening iterations. 
(BTW in this aspect SLA is better than MJF.)

I assume that you have already assembled a P2PPCB starter kit. There will be no hard part before
fastening the frame with the cover (please check the operation before fastening). 
The fastening is a bit tricky, because the design is the countermeasure of the warping of 3D printing results.

Put the frame in the cover, and:

1. Put M2.6 x 7 mm screws on the holes of the cover wall. Don't tighten, just drive a bit.
2. Put a M2.6 x 7 mm screw on the hole at the center of the cover bottom. Tighten it.
3. See if the cover bottom is entirely flat. If not flat, the feet will rattle. It is very common because 3D-printing results always warp.
4. By pushing or pulling the frame to the cover, make the cover bottom flat, and tighten the screws of the wall.

# How to Use

The keycaps are row-independent uniform profile. So you can reallocate all 1u keycaps as you like.
You can remap keycode by VIA, of course.

Left and right bodies both have a Micro USB type-B connector. You can choose one whichever you like and connect it to your PC.

The hole on the cover near the USB connector is for BOOTSEL button of Raspberry Pi Pico. You can press BOOTSEL button via the hole
to write new firmware.

The LED keys in front of the space keys are for Caps Lock / Scroll Lock indicator. 
I map LANG2 / LANG1 on them (useful keys for Japanese input) in QMK layer 0. 

The finger assignment shown in the figure below might look odd. 
"Typing method" says that you should press "1/!" key by your pinky finger,
but I think it is outdated rubbish from the age of non-electric typewriters and professional typists. They didn't use wrist rests 
because they should hit keys with adequate even force, like a pianist. If the hitting force is uneven, the thickness of the letters 
becomes uneven. It was considered not the workmanship of a professional typist. So they hit keys by their shoulders and arms, 
not palms and fingers. In this case, the shortness of the pinky finger is not a 
problem because the upper arm moves and covers all the keys on a keyboard. 
Moreover, professional typists didn't develop sentences in front of a typewriter because there was a manuscript to type. 
No revising nor editing, of course. In front of a typewriter, they just typed without stopping. 
There was no room for wrist rests, like a piano.

Today we live on another planet. 
NTCS has built-in wrist rests. It doesn't assume shoulder-and-arm typing. Long fingers should press distant keys.

![Finger Assignment](https://user-images.githubusercontent.com/1212166/208791474-8c6c3ea0-70e5-4856-b384-1191193a8042.png)

# The Design Process of NTCS

P2PPCB platform is for rapid prototyping. So I guess you are going to start a design process with it.
The F3D files show the final result, not the process. Let's see the story.

## Starting Point 1: TRON Keyboard TK1

1980s was the golden era of bizarre keyboards. The pinnacle is TRON keyboard TK1, 1991.

![TK1](https://user-images.githubusercontent.com/1212166/207522147-169f17b4-5e90-4ddc-b5a0-c8648aa0439f.jpg)

![Cited from SAKAMURA Ken, Keyboard Dangi 7, bit (1990) Vol. Dec.](https://user-images.githubusercontent.com/1212166/207523753-d67a0784-211e-408c-b4dd-8eed3ca3c4a1.jpg)

TK1 has its long story. I just enumerate the ideas what I stole from it.

- 10° twist along front-back direction and built-in wrist rests

These two ideas are closely related. 10° twist along front-back direction requires uncommonly high-profile wrist rests 
because the keytop altitude of the inner area is much higher than common keyboards.
Built-in wrist rests can be uncommonly high-profile.

- Wedge-shaped gaps between keytops

My dear keyboard people, please stop filling a keyboard with keytops. It is a quite common mistake
in this industry. Key separation (pushing down a key without interfering with other keys) is much more 
important than keytop largeness, and key separation requires gaps between keytops.
Your habit might say "Gaps between keytops are ugly". Please break the habit now.

NTCS's wedge angle is much acuter than TK1's. TK1's angle is more bizarre and attractive, but I've come to 
the conclusion that it is not good for typing.

- Small space key and Shift keys by thumbs

These ideas are very common even before TK1. Maltron's keyboard in 1980 had a small space key.
Fujitsu's "親指シフト" (Thumb Shift) keyboard in 1980 had Shift keys by thumbs (the space key was small too). 
I feel curious why these ideas are rarely seen in a (bizarre) keyboard today.

- Arrow keys under main cluster (right hand only)

Symmetric arrow keys are the big charm of TK1. I tried to mimic it by placing Home / End / PgUp / PgDn instead of 
red arrows on the left hand part, but when I tested the layout with several prototypes, I realized it is a bad idea. 
All navigation keys should be assigned to the right hand because the left hand should focus copy paste.

- How about other ideas?

As you can see, I didn't adopt many ideas in TK1. Symmetric and column-staggered layout, 
built-in drawing tablet, 3-bank shift (left and right Shift key works differently), 
16 mm pitch, etc. Yeah TK1 is the pinnacle of 1980s' bizarre keyboards. 
I miss them, but this is a design process.

## Starting Point 2: Ready-Made Keycap Set

I am running a custom keycap shop [DecentKeyboards](https://www.etsy.com/shop/DecentKeyboards). 
I can print any legends on any (white PBT) blank keycaps. But such custom keycaps can distract 
attention from the ability of P2PPCB platform. NTCS is a reference design of P2PPCB platform, 
not an ultimate keyboard.

(BTW an ultimate keyboard requires a new ecosystem. OS, applications, common practice, 
users, developers, hardwares and its supply chain. 
TRON keyboard TK1 was a part of a such new ecosystem "BTRON", but it failed. From this experience, 
I think an ultimate keyboard will be not profitable, not widely available, not even very good for most people in the real world, 
even if it is mass-produced and its price is around common keyboards'. An ultimate keyboard is the same kind of 
exotic cars. Its price can be several hundred times of common products', but it is inferior to common products 
in most aspects even without counting the price.)

Swapping keycaps is a great recreation. It is much harder with custom keycap based keyboards. 
A ready-made keycap set is a great product of the existing ecosystem.

## Starting Point 3: Keyboard Shortcuts of Windows Applications

Actually, I'm not a big fan of keyboard shortcuts. Of course I use them heavily, but because of that, 
my pinky finger hurt often (now I am free from the pain with NTCS). In the viewpoint of productivity, 
keyboard shortcuts are negligible IMHO. I use them just because I'm impatient of using a mouse.

Not all the people (including keyboard people) are so impatient. Prioritizing keyboard shortcuts is an important 
decision because it changes the design completely.

For example, by prioritizing keyboard shortcuts, all modifier keys should be easy to press simultaneously, 
easily, with any combination, by one hand. (I think multi-pressing of modifier keys is 
a bad idea of the existing ecosystem, but NTCS is not an ultimate keyboard.) Because of this requirement, 
yet another modifier key (i.e. QMK layer) is hard to use heavily. Ctrl+Shift+F5 is a very familiar shortcut in Visual Studio, 
but if F5 is hidden by yet another modifier (YAM) key, Ctrl+Shift+YAM+5 should be easy to press. 
In typing Japanese, F7 is a very frequently used key. YAM+7 should be easy to press like Shift+7. 
I think it is impossible to fulfill all requirements like them under all the prerequisites above.

Under different prerequisites, heavy use of YAM key can be a good design because it can reduce keys on a keyboard. 

## Other Ideas Stolen From Various Keyboards

- Del key at left edge

The idea came from Symbolics keyboard (namely Space-cadet). The RUB OUT key is a legend.

- Esc key at left top corner of the main cluster

It was common before the dominance of IBM Model M layout. I'd like to name HHKB as the resistance movement against
the dominance.

## Iteration 1

https://user-images.githubusercontent.com/1212166/207766975-fe80b625-9c89-4bb3-ab00-f115f13a7b42.mp4

The first trial. Left hand only, naked style, custom keycap based. In this iteration, I didn't adopt the start point 2.

I got a lot of findings in this iteration. 

- Thumb keys should be tilted in the opposite direction of other keys.
- Wrist rests should be uncommonly high-profile because the keytop altitude of the inner area is 
much higher than common keyboards.
- Pinky finger keys should be more front.

## Iteration 2

https://user-images.githubusercontent.com/1212166/207769963-8871a65c-baf6-4fd5-8fc1-cc160b2b6ee9.mp4

The first trial of covered style. I adopted the start point 2 from this iteration.

- Small space key should be in front of V. Shift key should be the right neighbor of the space key.
- Q should be pressed by a ring finger.
- Thumb keys should be lower.
- Ctrl key should be a thumb key.

I don't mention the problem of covered style. Just mimic the conclusion shown in the F3D files of NTCS.
And I don't mention the right hand part too. It will be redundant.

## Iteration 3

https://user-images.githubusercontent.com/1212166/207800112-49950f18-dee0-47fb-89b6-9756c5d27d19.mp4

https://user-images.githubusercontent.com/1212166/207801987-bb7279e0-d1bd-43f7-8470-23f2b017d544.mp4

The first trial of built-in wrist rests. I thought of taking a video at this time.
The material is SLA of WENEXT. It is much cheaper than MJF. Built-in wrist rests takes up much space,
and it makes 3D printing much more pricey.

- The position of the Alt key is not a good idea.
- Pressing the space key interferes End key.
- Wrist rests are too long in front-back direction.
- Shift and Ctrl keys should be more back a bit.
- Ctrl key should be 1 mm higher.
- Q row of pinky finger section should be higher a bit for key separation.
- Tab key is too far for pinky finger.

## Iteration 4

https://user-images.githubusercontent.com/1212166/207805898-d4af1ae7-47c4-46dc-a097-f8915beb6a94.mp4

https://user-images.githubusercontent.com/1212166/207806336-694a83c3-6f9b-410a-8993-eb757cfd567e.mp4

- Shift key should be more front a bit.
- LANG1 should be lower. Pressing the Ctrl key interferes.
- Symmetric layout of arrow keys (Home / End / PgUp / PgDn - Left / Right / Up / Down) is a bad idea.

## Iteration 5

https://user-images.githubusercontent.com/1212166/207811766-837e6841-0c39-4954-b991-4490d437edb7.mp4

https://user-images.githubusercontent.com/1212166/207813334-f48241b7-b52c-4ad7-b488-d3c9fbc1e20a.mp4

In this iteration, the material is MJF PA12 black.

- Function keys interfere my palm. The function key cluster should not tilt.

## Iteration 6

This is the final noteworthy iteration. I did much more, but the findings are trivial.
This iteration is not the final result, but close enough from the viewpoint of this story.

https://user-images.githubusercontent.com/1212166/207817193-05dbc5cd-c3d1-442c-9eca-ad06bcb6c566.mp4

https://user-images.githubusercontent.com/1212166/207817925-683ccf40-5cc8-40d5-9adb-0121a6b742cf.mp4

- Key angle surface should be adjusted finely.

# How to Mimic the Structure of NTCS

It is far from straightforward. If you feel it is too tedious, please ask me. I can make a covered style 
from your naked style F3D file. It costs, of course.

The basic story is the Fill/Hole method. You should do the method manually to the cover.
In the F3D file of NTCS, on the object browser, expand `P2PPCB Internal/Foot Placeholders mU0jU/Foot A_FL:1/Foot_P:2/Bodies`.
You'll find a `Foot Fill Cover` body. `Cover Boss.*/Bodies` and `Adjust Boss.*/Bodies` also has bodies with such names. 

**Regex Select** command in **Select** panel in SOLID tab will help you. You can see the results of the command 
in "Selection Sets" of the object browser.

`P2PPCB Internal/Depot Parts mU0jU/Switch MX_P:1/Bodies/MF/Switch Fill.*` is a quite important trick which is hard to 
comprehend. See the timeline of the F3D file step by step. The fill body of `Switch MX_P` is modified from the original 
before running **Fill** command. The modification makes possible to connect a bridge body to a switch fill body by **Extrude** command.
