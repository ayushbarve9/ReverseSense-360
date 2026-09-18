# Hardware Specifications & Wiring Guide

## 1. Components List

| Component | Specification | Quantity | Purpose |
| :--- | :--- | :---: | :--- |
| **Raspberry Pi** | Model 3B+ / 4B (BCM2835 / BCM2711) | 1 | Central processor running OS and control scripts |
| **Ultrasonic Distance Sensor** | HC-SR04 (2 cm – 400 cm range, ±3 mm accuracy) | 1 | Real-time vehicle-to-obstacle distance sensing |
| **Camera Module** | Pi Camera Module V2 / HQ (CSI ribbon) | 1 | High-resolution photographic evidence capture |
| **Warning LED** | Red 5 mm (Forward voltage ~2.0 V) | 1 | Visual warning indicator |
| **Audio Buzzer** | Active 5 V buzzer (~85 dB output) | 1 | Audible proximity alarm |
| **Current Limiting Resistor** | 330 Ω | 1 | Protects LED from overcurrent |
| **Voltage Divider Resistors** | 1 kΩ & 2 kΩ (or 1 kΩ & 1 kΩ) | 2 | Steps HC-SR04 ECHO pin 5 V down to 3.3 V |
| **Prototyping Board** | Breadboard & M-to-F Jumper Wires | 1 set | Circuit wiring and signal routing |
| **Power Supply** | 5 V 3 A USB-C / Micro-USB | 1 | Stable power delivery to Raspberry Pi |

---

## 2. GPIO Pin Connection Table

| Peripheral Pin | Raspberry Pi Pin | GPIO Number | Function / Electrical Notes |
| :--- | :--- | :--- | :--- |
| **HC-SR04 VCC** | Pin 2 | — | Direct 5V supply rail |
| **HC-SR04 GND** | Pin 6 | — | Common Ground rail |
| **HC-SR04 TRIG** | Pin 16 | GPIO 23 | Digital Output (sends 10 µs pulse) |
| **HC-SR04 ECHO** | Pin 18 | GPIO 24 | Digital Input (**via voltage divider** to 3.3 V) |
| **LED Anode (+)** | Pin 12 | GPIO 18 | Digital Output (through 330 Ω resistor to ground) |
| **Buzzer (+)** | Pin 11 | GPIO 17 | Digital Output (Active high; GND to Pin 14) |
| **Pi Camera** | CSI Port | — | 15-pin MIPI Camera Serial Interface |

---

## 3. HC-SR04 Voltage Divider Circuit (Critical)

> [!WARNING]
> Raspberry Pi GPIO pins are strictly **3.3 V tolerant**. The HC-SR04 operates at 5 V and outputs a 5 V pulse on its **ECHO** pin. Connecting the ECHO pin directly to a Raspberry Pi GPIO pin can cause permanent damage to the SoC.

To protect the GPIO pin, a simple two-resistor voltage divider is placed on the ECHO line:

```
HC-SR04 ECHO (5V) ───[ 1 kΩ ]───┬───> Raspberry Pi GPIO 24 (approx. 3.3V)
                                │
                              [ 2 kΩ ]
                                │
                               GND
```

Formula:
$$V_{out} = V_{in} \times \frac{R_2}{R_1 + R_2} = 5\text{V} \times \frac{2\text{k}\Omega}{1\text{k}\Omega + 2\text{k}\Omega} \approx 3.33\text{V}$$
