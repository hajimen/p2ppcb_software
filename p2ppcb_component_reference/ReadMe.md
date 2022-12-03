# P2PPCB Component Reference

Mainly it contains schematic diagrams of the components.

# Mainboards

The dimension is shown in `p2ppcb_composer_f360/*.f3d`.

## Alice

- MPU: STM32F072C8U6
- USB type-C
- All IDC terminals are shrouded headers, 2.54 mm pitch.

## Bob / Charlotte

- MPU: RP2040
- Micro USB type-B
- The IDC terminal is a shrouded header, 2.00 mm pitch.

Bob's shrouded header: <https://lcsc.com/product-detail/IDC-Connectors_Wcon-3111-30SG0BK00T1_C783804.html>

Charlotte's: <https://lcsc.com/product-detail/IDC-Connectors_Wcon-3111-36SG0BK00T1_C920868.html>

- The pin header J1 for debugger is not implemented. Solder 1x5 pin header if you need it.

# Matrix Wire

## Wire Harness for Alice

Length: 1 m

Connector: <https://www.digikey.com/en/products/detail/hirose-electric-co-ltd/HIF3BA-30D-2-54C-63/12758629>

## IDC ribbon cable for Bob / Charlotte

Length: 60 cm

Connector of Bob: <https://lcsc.com/product-detail/IDC-Connectors_Wcon-5222-30YPS0BW01_C843027.html>

Connector of Charlotte: <https://lcsc.com/product-detail/IDC-Connectors_span-style-background-color-ff0-Wcon-span-5222-36YPS0BW01_C843029.html>

# Contact-to-Socket Assembly

Single IDC Contact: <https://www.digikey.com/en/products/detail/avx-corporation/709176001443006/3074530>

LED: <https://www.digikey.com/en/products/detail/lite-on-inc/LTST-C230KGKT/386855>

Diode: <https://www.digikey.com/en/products/detail/rohm-semiconductor/1SS400CMT2R/10495190>

# Qwiic-to-TRRS Assembly

Length: 12 cm

TRRS jack: <https://lcsc.com/product-detail/Audio-Connectors_XKB-Connectivity-PJ-31640_C2879830.html>

|TRRS|Qwiic|
|----|-----|
|Sleeve| GND|
|Sleeve-side Ring| 3.3V|
|Tip-side Ring| SCL|
|Tip| SCA|
