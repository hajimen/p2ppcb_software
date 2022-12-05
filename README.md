# P2PPCB Platform Overview

**P2PPCB platform** is a software / hardware complex for rapid prototyping of 3D-shaped PC keyboards,
offered by [DecentKeyboards](https://www.etsy.com/shop/DecentKeyboards).

With P2PPCB platform, you can design your own 3D-shaped keyboards, like this:

![NTCS](https://user-images.githubusercontent.com/1212166/204071963-3679261d-637c-492d-8b60-ddd91955e88e.png)

The image above is not an easy one. It requires several hours by a highly skilled operator (me).

But the below can be done in several hours by a newbie who has a Windows PC (English) and a broadband connection, without any charge:

![Starter Kit Bob](https://user-images.githubusercontent.com/1212166/204072408-b945348d-184f-4f22-bea4-f73e1ffc0fbf.png)

You can build your own design with a 3D printing service, P2PPCB components, and switches / keycaps / stabilizers / etc. as you like.

https://user-images.githubusercontent.com/1212166/204074347-09d51a74-aeb3-4d89-92ee-5701aa64c457.mp4

## Soldering free

P2PPCB platform uses single IDC contacts for wiring, like this:

![Single IDC Contacts](https://user-images.githubusercontent.com/1212166/204113500-06845de2-328b-4cc9-8748-06a3c7bbc6a0.jpg)

Just push a wire into a contact by a specialty hand tool.

![Specialty Hand Tool](https://user-images.githubusercontent.com/1212166/204113537-69a5786f-f7b6-4ace-96e6-4cebf9549b30.jpg)

Kyocera AVX provides them. The details are here:
<https://www.kyocera-avx.com/products/connectors/wire-to-board/single-idc-contact-22-28-awg-9176-400/>

Point-to-point wiring with PCB without soldering, so the name is "P2PPCB".

Point-to-point wiring is far more flexible than usual PCB. 3D-shape is the best example.
Rapid and easy prototyping of usual keyboards is also a happy usage.
With P2PPCB platform, you don't need to build a dedicated PCB for each design.
Just a 3D-printed frame, and the software helps your CAD operation much.

[Kailh socket](https://www.aliexpress.com/item/32959301642.html) connects switch to PCB.
There is nothing to solder by yourself, even in the case of split keyboards.
(But if you need to connect a debugger, soldering is required.)

## All softwares are open-source or charge-free for hobbyists

- [keyboard-layout-editor.com](https://keyboard-layout-editor.com) : Open-source
- [Autodesk Fusion 360](https://www.autodesk.com/products/fusion-360/overview): Charge-free for hobbyists
- [P2PPCB Composer F360](https://github.com/hajimen/p2ppcb_software/tree/dev/p2ppcb_composer_f360): Open-source
- [QMK firmware](https://qmk.fm/): Open-source

As long as your project stays on a PC screen, there is no charge.

## Switch LED is available

![Switch LED](https://user-images.githubusercontent.com/1212166/204113696-83d9a5dd-3236-453e-aa4f-98871a75f9c4.jpg)

Up to six per keyboard usually.

## MX / Choc V1 / Choc V2 switches are available

Available switches:

- MX ([Kailh MX](https://www.aliexpress.com/item/32966071689.html) and many other Cherry MX compatibles)
- [Kailh Choc V1](https://www.aliexpress.com/item/32959996455.html)
- [Kailh Choc V2](https://www.aliexpress.com/item/4000803757746.html)

Available stabilizers:

- Cherry-style plate-mount (for MX)
- Coaster (for MX)
- [Kailh Choc V1 stabilizer](https://www.aliexpress.com/item/33039182740.html) (for Choc V1)

Stabilizer for Choc V2 is not available yet because there is no such item in the market. I hope it appears in the market.
But by modifying a Cherry-style plate-mount stabilizer with a knife, it works (very geeky way).

# P2PPCB Composer F360

**P2PPCB Composer F360 (PC0)** is an add-in of Autodesk Fusion 360 (F360). Install F360 first. 
More details are here: <https://github.com/hajimen/p2ppcb_software/tree/dev/p2ppcb_composer_f360>

## Keycaps

PC0 handles keycaps to check interference and to help your design process.
The below are available on PC0. You can put other keycaps on your 3D-printed keyboards, of course.

- XDA (not very good category for precise design, so use this for a rough estimate)
- DSA
- Cherry profile
- OEM profile
- [Kailh Choc V1](https://www.aliexpress.com/item/32979973961.html)
- Junana for MX (New keycap from DecentKeyboards. Now getting ready)

Only Junana for MX can mate with Choc V2, usually. Actually DSA 1u can do by deep geeky way.
Dig `P2PPCB Internal/Depot Parts mU0jU/Cap DSA 1u.*` component of your F360 file, find what to do,
and use **Set Attribute** command of PC0.

# P2PPCB Components

There are many dedicated components for P2PPCB platform. It requires general-purpose parts too, like switches and keycaps.

[DecentKeyboards](https://www.etsy.com/shop/DecentKeyboards) sells P2PPCB components.
General-purpose parts are at your own choice.

## Mainboard

A mainboard connects USB to matrix wires. Comparison table of the three mainboards:

|    |Alice|Bob |Charlotte|
|----|-----|----|---------|
|Cost|Bad  |Cheapest|Good |
|Size|Bad  |Smallest|Good |
|Split Keyboard|USART|N/A      |Qwiic|
|Qwiic|Yes  |No      |Yes  |
|Matrix Size|8x24 + 2x6|12x16|12x16 + 2x3|
|Matrix Wire|Dupont|30 pin ribbon|36 pin ribbon|
|Switch LED|12 |N/A      |6  |
|Underglow|Yes|No|No|
|USART|Yes|No|No|
|Complexity|Bad|Simplest|Good|

### Alice

![Alice](https://user-images.githubusercontent.com/1212166/204481367-1596c8bf-62f4-4363-a5c8-b038445ec9e7.jpg)

I don't recommend **Alice** in most cases. It is only good for R&D laboratories which have HP's MJF 3D printer.
If you use a 3D printing service, go Bob or Charlotte.

![Alice Wire Harness Set](https://user-images.githubusercontent.com/1212166/204482063-080e00e3-34a9-44c6-9837-83c2bb0c8a61.jpg)

Alice accepts female Dupont wire as matrix wire. It is cheaper and more convenient than IDC ribbon cable of **Bob** / **Charlotte**.
Dupont wire is not very reliable, but enough for trial-and-error iterations of a design process.
A wire harness set (the image above) is available for high reliability, but it is quite expensive.

You might think IDC ribbon cable is available for Alice. I thought so too.
But 1.27 mm pitch cable (common thing) is too thick for a single IDC contact. I failed to make it reliable.
(This is a big reason why I need to make Bob and Charlotte.)

### Bob

![Bob](https://user-images.githubusercontent.com/1212166/204481608-7f183b4c-1801-4136-88ea-a06abbbf45b7.jpg)

**Bob** is the smallest and cheapest but lacks many functions.

### Charlotte

![Charlotte](https://user-images.githubusercontent.com/1212166/204481740-dc1d4314-9420-4dec-b742-34981c9d06d9.jpg)

If you need split keyboard / switch LED / Qwiic connector, **Charlotte** is recommended.

(You might wonder how Charlotte uses I2C for split keyboards. I implemented I2C slave mode
which ChibiOS doesn't have. The code is RP2040 only, sorry.)

## Matrix Wire

![36-pin 1.00 mm pitch IDC ribbon rainbow cable](https://user-images.githubusercontent.com/1212166/204482169-f5ddf0f1-f670-47e1-9cb6-9a9a42c60313.jpg)

A matrix wire connects a mainboard to contacts.

Alice accepts a female Dupont wire as a matrix wire. It is a general-purpose part, not a P2PPCB component.
A wire harness set for Alice is available as a P2PPCB component, but it is not recommended in most cases.

Bob and Charlotte accept 1.00 mm pitch IDC ribbon rainbow cable as matrix wire. The pitch is not very common.
These are P2PPCB components. When you build a keyboard, tear off bonding of wires (easily tearable), and use it as single wires.

## Contact-to-Socket Assembly

MX socket and Choc socket are available. LED and normal for each socket. So:

- MX LED
- MX normal
- Choc LED
- Choc normal

are available.

![Contact-to-Socket](https://user-images.githubusercontent.com/1212166/204484257-108bf20a-2522-4053-b8ea-9a14f05be936.jpg)

(You might wonder how LED and switch both are driven / read by only a pair of wires.
By utilizing the forward voltage (Vf) of LEDs. Under its Vf, a LED does not flow current (no light, of course).
We can read a switch by giving voltage lower than the Vf. About driving, a resistor is connected in series to a switch.
Even when the switch is close, the resistor makes enough voltage to drive the LED which is connected
in parallel to the switch-resistor. Reading and driving are multiplexed by time division in high frequency like PWM.)

### Single IDC Contact Push Mount

<img width="704" alt="Single IDC Contact Push Mount" src="https://user-images.githubusercontent.com/1212166/205607683-697694b7-b2b8-42c0-b508-0daa7677686f.PNG">

To Push a wire to a single IDC contact, this mount helps you. Insert the cuboid end to the switch hole of a frame.
You can get this component by printing the F3D file: `p2ppcb_component_reference/contact-to-socket/Single IDC Contact Push Mount.f3d`.

## Qwiic-to-TRRS Assembly

![Qwiic-to-TRRS](https://user-images.githubusercontent.com/1212166/204488371-f274d0c1-be72-4f98-81a5-a561463c563b.jpg)

Charlotte uses Qwiic (3.3V I2C with Vdd on JST-SH 4-pin connector) for split keyboards.
Qwiic-to-TRRS assembly is available as a P2PPCB component. TRRS cable is a general-purpose part.

(No P2PPCB component for USART split keyboards of Alice. Connect by female / female Dupont wire or solder a terminal which you like.)

## Foot Kit

![Foot Spacers](https://user-images.githubusercontent.com/1212166/204488560-f9f35b51-4cd7-4369-bd15-2f8b73eed9d3.jpg)

![Height Comparison](https://user-images.githubusercontent.com/1212166/204489172-3572e1eb-9682-45ff-8fd9-cbaf93daf2f4.jpg)

Even in the case of 3D-shaped keyboards, height-adjustable feet are indispensable for many reasons.
Rubber sole is also indispensable. P2PPCB platform has a dedicated foot kit.

# Starter Kit

P2PPCB platform requires so many parts for building a real keyboard.

- Specialty hand tool for single IDC contact (special bit and common handle)
- Mainboard (with screws)
- Contact-to-socket assembly
- Single IDC contact push mount
- Matrix wire
- Foot kit
- Key switch
- Keycap
- 3D-printed frame
- Philips screwdriver :-)

In these parts, difficult-to-reuse is only matrix wire and frame. You can reuse Contact-to-socket assembly
up to three times (according to Kyocera AVX. I guess a lot more actually).

So DecentKeyboards combined them into P2PPCB Starter Kit (except screwdriver). Just getting this kit,
you can build and test a P2PPCB-based keyboard by hand.

TODO link to item

# Technical Details

This repository contains a lot of technical details of P2PPCB platform. You'll need them when you go deep.

`p2ppcb_component_reference`: P2PPCB component

`p2ppcb_starter_kit_reference`: P2PPCB Starter Kit

# Discussions

If you have any questions, or require anything further of me, please feel free to join the discussions:
<https://github.com/hajimen/p2ppcb_software/discussions>
