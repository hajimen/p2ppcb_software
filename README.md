# P2PPCB platform overview

**P2PPCB platform** is a software / hardware complex for rapid prototyping of 3D-shaped PC keyboards,
offered by [DecentKeyboards](https://www.etsy.com/shop/DecentKeyboards).

With P2PPCB platform, you can design your own 3D-shaped keyboards, like this one:

![NTCS](https://user-images.githubusercontent.com/1212166/204071963-3679261d-637c-492d-8b60-ddd91955e88e.png)

The above is not easy. It takes several hours by a highly skilled operator (me).

But the one below can be done in a few hours by a newbie who has a Windows PC (English) and a broadband connection, without any charge:

![Starter Kit Bob](https://user-images.githubusercontent.com/1212166/204072408-b945348d-184f-4f22-bea4-f73e1ffc0fbf.png)

You can build your own design using a 3D printing service, P2PPCB components, and switches / keycaps / stabilizers / etc. as you like.

https://user-images.githubusercontent.com/1212166/204074347-09d51a74-aeb3-4d89-92ee-5701aa64c457.mp4

## No soldering

P2PPCB platform uses single IDC contacts for wiring, as shown here:

![Single IDC Ccntacts](https://user-images.githubusercontent.com/1212166/204113500-06845de2-328b-4cc9-8748-06a3c7bbc6a0.jpg)

Simply push a wire into a contact by a special hand tool.

![Special hand tool](https://user-images.githubusercontent.com/1212166/204113537-69a5786f-f7b6-4ace-96e6-4cebf9549b30.jpg)

Kyocera AVX provides them. Details can be found here:
<https://www.kyocera-avx.com/products/connectors/wire-to-board/single-idc-contact-22-28-awg-9176-400/>

Point-to-point wiring with PCB without soldering, hence the name is "P2PPCB".

Point-to-point wiring is much more flexible than ordinary PCB. 3D-shape is the best example.
Rapid and easy prototyping of ordinary keyboards is also a happy use.
With P2PPCB platform, you don't need to build a dedicated PCB for each design.
Just a 3D-printed frame, and the software helps your CAD operation a lot.

[Kailh socket](https://www.aliexpress.com/item/32959301642.html) connects the switch to the PCB.
There is nothing to solder, even in the case of split keyboards.
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

- MX ([Kailh MX](https://www.aliexpress.com/item/32966071689.html) and many other Cherry MX compatible)
- [Kailh Choc V1](https://www.aliexpress.com/item/32959996455.html)
- [Kailh Choc V2](https://www.aliexpress.com/item/4000803757746.html)
- [GATERON Low Profile](https://gateron.com/collections/low-profile-series)

Available stabilizers:

- Cherry-style plate-mount (for MX)
- Coaster (for MX)
- [Kailh Choc V1 stabilizer](https://www.aliexpress.com/item/33039182740.html) (for Choc V1)
- [Gateron Low Profile](https://gateron.com/products/gateron-low-profile-plate-mounted-stabilizer?VariantsId=10478)

Stabilizer for Choc V2 is not available yet because there is no such item in the market yet. I hope it will appear on the market.
But by modifying a Cherry-style plate-mount stabilizer with a knife, it works (very geeky way).

# P2PPCB Composer F360

**P2PPCB Composer F360 (PC0)** is an add-in of Autodesk Fusion 360 (F360). F360 runs on Mac too, but PC0 is Windows only.
More details can be found here: <https://github.com/hajimen/p2ppcb_software/tree/dev/p2ppcb_composer_f360>

## Keycaps

PC0 handles keycaps to check interference and to help your design process.
The following are available on PC0. You can of course put other keycaps on your 3D-printed keyboards.

- XDA (9.5 mm height. CAUTION: There are a lot of "XDA" profiles in the market)
- DSA
- Cherry profile
- OEM profile
- [Kailh Choc V1](https://www.aliexpress.com/item/32979973961.html)
- Junana for MX (New keycap from DecentKeyboards. Now in preparation)

Only Junana for MX can mate with Choc V2, normally. In fact DSA 1u can do it in a deep geeky way.
Dig into `P2PPCB Internal/Depot Parts mU0jU/Cap DSA 1u.*` component of your F360 file, and find what to do.

# P2PPCB Components

There are many dedicated components for P2PPCB platform. It also requires general-purpose parts like switches and keycaps.

[DecentKeyboards](https://www.etsy.com/shop/DecentKeyboards) is selling P2PPCB components.
General-purpose parts are at your own choice.

## Mainboard

A mainboard connects the USB to the matrix wires. Comparison chart of the three mainboards:

|    |Alice|Bob |Charlotte|
|----|-----|----|---------|
|Cost|Bad  |Cheapest|Good |
|Size|Bad  |Smallest|Good |
|Split Keyboard|USART|N/A      |Qwiic|
|Qwiic|Yes  |No      |Yes  |
|Matrix Size|8x24 + 2x6|12x16|12x16 + 2x3|
|Matrix Wire|Dupont|30 pin ribbon|36 pin ribbon|
|Switch LED|12 |0      |6  |
|Underglow|Yes|No|No|
|USART|Yes|No|No|
|Complexity|Bad|Simplest|Good|

### Alice

![Alice](https://user-images.githubusercontent.com/1212166/204481367-1596c8bf-62f4-4363-a5c8-b038445ec9e7.jpg)

I don't recommend **Alice** in most cases. It is only good for R&D labs that have a high precision and large size 3D printer.
If you use a 3D printing service, go with Bob or Charlotte.

![Alice harness kit](https://user-images.githubusercontent.com/1212166/204482063-080e00e3-34a9-44c6-9837-83c2bb0c8a61.jpg)

Alice accepts female Dupont wire as matrix wire. It is cheaper and more convenient than **Bob** / **Charlotte**'s IDC ribbon cable.
A Dupont wire is not very reliable, but sufficient for trial-and-error iterations of a design process.
A harness kit (the picture above) is available for high reliability, but it is quite expensive.

You might think that IDC ribbon cable is available for Alice. I thought so, too.
But 1.27 mm pitch ribbon cable (common thing) is too thick for a single IDC contact. I could not make it reliable.
(This is a big reason why I made Bob and Charlotte.)

### Bob

![Bob](https://user-images.githubusercontent.com/1212166/204481608-7f183b4c-1801-4136-88ea-a06abbbf45b7.jpg)

**Bob** is the smallest and cheapest but lacks a lot of features.
You can configure most things with VIA <https://www.caniusevia.com/>.
With Bob, you can live without QMK firmware configuration in most cases.

### Charlotte

![Charlotte](https://user-images.githubusercontent.com/1212166/204481740-dc1d4314-9420-4dec-b742-34981c9d06d9.jpg)

If you need a split keyboard / switch LED / Qwiic connector, **Charlotte** is recommended.
If you go with Charlotte, QMK firmware is a must.

(You may wonder how Charlotte uses I2C for split keyboards. I implemented I2C slave mode
that ChibiOS doesn't have. The code is RP2040 only, sorry.)

## Matrix wire cable

![36-pin 1.00 mm pitch IDC ribbon rainbow cable](https://user-images.githubusercontent.com/1212166/204482169-f5ddf0f1-f670-47e1-9cb6-9a9a42c60313.jpg)

A matrix wire connects a mainboard to contacts.

Alice accepts a female Dupont wire as a matrix wire. It is a general-purpose part, not a P2PPCB component.
A harness kit for Alice is available as a P2PPCB component, but it is not recommended in most cases.

Bob and Charlotte accept 1.00 mm pitch IDC ribbon rainbow cable as matrix wire. This pitch is not very common.
These are P2PPCB components. When you build a keyboard, peel off the bonds of wires (easy to peel)
and use them as single wires.

## Contact-to-socket assembly

MX, Choc, and Gateron LP socket are available. LED and normal for each socket. So:

- MX LED
- MX normal
- Choc LED
- Choc normal
- Gateron LP LED
- Gateron LP normal

are available.

![Contact-to-socket](https://user-images.githubusercontent.com/1212166/204484257-108bf20a-2522-4053-b8ea-9a14f05be936.jpg)

(You may wonder how an LED and a switch both can be driven / read by only one pair of wires.
By utilizing the forward voltage (Vf) of LEDs. Below its Vf, an LED has no current flow (no light, of course).
We can read a switch by applying a voltage lower than the Vf. To drive an LED, a resistor is connected in series with the switch.
Even when the switch is closed, the resistor produces enough voltage to drive the LED which is connected
in parallel to the switch-resistor. Reading and driving are multiplexed by time division in high frequency like PWM.)

### Single IDC contact push mount

<img width="704" alt="Single IDC Contact Push Mount" src="https://user-images.githubusercontent.com/1212166/205607683-697694b7-b2b8-42c0-b508-0daa7677686f.PNG">

To push a wire to a single IDC contact, use this mount. Insert the cuboid end into the switch hole of a frame.
You can get this component by printing the F3D file: `p2ppcb_component_reference/contact-to-socket/Single IDC Contact Push Mount.f3d`.

## Qwiic-to-TRRS assembly

![Qwiic-to-TRRS](https://user-images.githubusercontent.com/1212166/204488371-f274d0c1-be72-4f98-81a5-a561463c563b.jpg)

Charlotte uses Qwiic (3.3V I2C with Vdd on JST-SH 4-pin connector) for split keyboards.
The Qwiic-to-TRRS assembly is available as a P2PPCB component. TRRS cable is a general-purpose part.

(No P2PPCB component for USART split keyboards of Alice. Connect by female / female Dupont wire or solder a terminal of your own choice.)

## Adjustable foot kit

![Foot spacers](https://user-images.githubusercontent.com/1212166/204488560-f9f35b51-4cd7-4369-bd15-2f8b73eed9d3.jpg)

![Height comparison](https://user-images.githubusercontent.com/1212166/204489172-3572e1eb-9682-45ff-8fd9-cbaf93daf2f4.jpg)

Even with 3D-shaped keyboards, height-adjustable feet are indispensable for many reasons.
Rubber sole is also indispensable. P2PPCB platform has its own foot kit.

# Starter kit

P2PPCB platform requires so many parts to build a real keyboard.

- Special hand tool for single IDC contact (special bit and common handle)
- Mainboard (with screws)
- Contact-to-socket assembly
- Single IDC contact push mount
- Matrix wire cable
- Adjustable foot kit
- Key switch
- Keycap
- 3D-printed frame
- One Philips and one flat screwdriver :-)

In these parts, difficult-to-reuse is only matrix wire and frame. You can reuse contact-to-socket assembly
up to three times (according to Kyocera AVX. I guess much more actually).

So DecentKeyboards combined them into P2PPCB Starter Kit (except screwdriver). Just by getting this kit,
you can build and test a P2PPCB-based keyboard by hand.

TODO link to item

# Technical Details

This repository contains a lot of technical details about P2PPCB platform. You'll need it if you want to go deep.

`p2ppcb_component_reference`: P2PPCB component

`p2ppcb_starter_kit_reference`: P2PPCB Starter Kit

# Discussions

If you have any questions, please feel free to join the discussions:
<https://github.com/hajimen/p2ppcb_software/discussions>
