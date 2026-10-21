"""CM5 Edge-Audio Carrier -- single source of truth for parts, values and nets.

Every part carries its schematic placement (sheet, x, y, rotation) and its
connectivity (pin -> net). gen_sch.py and gen_pcb.py both consume this file,
so the schematic and the board can never drift apart.

Schematic coordinates use G(col, row) on the 2.54 mm grid.
"""
from schgen import Part


def G(x, y):
    return (round(x * 2.54, 3), round(y * 2.54, 3))


# --------------------------------------------------------------------------- footprints
R0402 = 'Resistor_SMD:R_0402_1005Metric'
C0402 = 'Capacitor_SMD:C_0402_1005Metric'
C0805 = 'Capacitor_SMD:C_0805_2012Metric'
C1206 = 'Capacitor_SMD:C_1206_3216Metric'
LED0603 = 'LED_SMD:LED_0603_1608Metric'
SOT236 = 'Package_TO_SOT_SMD:SOT-23-6'
USON10 = 'Package_SON:USON-10_2.5x1.0mm_P0.5mm'
USBC = 'Connector_USB:USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal'
JSTSH4 = 'Connector_JST:JST_SH_SM04B-SRSS-TB_1x04-1MP_P1.00mm_Horizontal'
BTN = 'Button_Switch_SMD:SW_SPST_B3U-1000P'

# LCSC part numbers verified against the LCSC catalogue (2026-10); blank = order by MPN
LCSC = {
    ('R', '0R'): 'C17168', ('R', '33R'): 'C25105', ('R', '470R'): 'C25117', ('R', '1k'): 'C11702',
    ('R', '2.2k'): 'C25879', ('R', '4.7k'): 'C25900', ('R', '5.1k'): 'C25905', ('R', '10k'): 'C25744',
    ('R', '15k'): 'C25756', ('R', '56k'): 'C25796', ('R', '100k'): 'C25741',
    ('C', '100nF'): 'C1525', ('C', '1uF'): 'C52923', ('C', '4.7nF'): 'C1538',
    ('C', '10uF'): 'C15850', ('C', '22uF'): 'C45783', ('C', '22uF/25V'): 'C12891',
}

PARTS = []
SHEET_META = {}


def add(sheet, part):
    part.sheet_name = sheet
    PARTS.append(part)
    return part


def R(sheet, ref, val, at, n1, n2, rot=0, **kw):
    f = {'LCSC': LCSC.get(('R', val), ''), 'Tolerance': '1%'}
    return add(sheet, Part(ref, 'Device:R', val, R0402, at, {1: n1, 2: n2}, rot=rot, fields=f,
                           label_side='right', **kw))


def C(sheet, ref, val, at, n1, n2, rot=0, fp=None, volt=None, **kw):
    fp = fp or (C0402 if val in ('100nF', '1uF', '4.7nF') else C0805)
    key = val + ('/' + volt if volt == '25V' and val == '22uF' else '')
    f = {'LCSC': LCSC.get(('C', key), ''), 'Voltage': volt or ('16V' if fp == C0402 else '10V')}
    return add(sheet, Part(ref, 'Device:C', val, fp, at, {1: n1, 2: n2}, rot=rot, fields=f,
                           label_side='right', **kw))


def LED(sheet, ref, color, at, k, a, lcsc, rot=0):
    return add(sheet, Part(ref, 'Device:LED', color, LED0603, at, {1: k, 2: a}, rot=rot,
                           fields={'LCSC': lcsc}))


def FLAG(sheet, ref, net, at):
    return add(sheet, Part(ref, 'power:PWR_FLAG', 'PWR_FLAG', '', at, {1: net}))


# =========================================================================== POWER (A4)
P = 'Power'
SHEET_META[P] = dict(paper='A4', boxes=[
    ((15.24, 20.32), (137.16, 99.06), 'USB-C PD SINK  (CH224K requests 12 V / 3 A)'),
    ((15.24, 104.14), (160.02, 162.56), '5 V / 5 A SYNCHRONOUS BUCK  (TPS565208)'),
    ((165.1, 104.14), (284.48, 162.56), 'M.2 3.3 V / 2 A BUCK  (AP3441, EN = PCIE_PWR_EN)'),
], notes=[
    ((142.24, 30.48), 'CFG1 = 24k -> 12 V PD request (CH224K)'),
    ((142.24, 35.56), 'PG low = contract OK -> PD_OK LED on'),
    ((142.24, 40.64), 'SMAJ15A clamps hot-plug / cable ringing'),
    ((142.24, 50.8), 'Buck UVLO: EN = 1.2 V x (1 + 100k/15k) ~ 9.2 V'),
    ((142.24, 55.88), '-> +5V stays off if PD falls back to 5 V'),
    ((142.24, 60.96), 'Vout = 0.76 V x (1 + 56k/10k) = 5.02 V'),
    ((142.24, 66.04), 'Vout(M.2) = 0.6 V x (1 + 10k/2.2k) = 3.33 V'),
    ((142.24, 71.12), 'Load: CM5 3.0 A + USB 1.5 A + fan 0.2 A = 4.7 A max'),
])
add(P, Part('J1', 'Connector:USB_C_Receptacle_USB2.0_16P', 'USB-C PD IN', USBC, G(14, 26),
            {'A4': 'VBUS', 'A9': 'VBUS', 'B4': 'VBUS', 'B9': 'VBUS', 'A5': 'PD_CC1', 'B5': 'PD_CC2',
             'A1': 'GND', 'A12': 'GND', 'B1': 'GND', 'B12': 'GND', 'SH': 'GND'},
            fields={'MPN': 'GCT USB4105-GF-A', 'LCSC': 'C3020560'},
            desc='USB-C power input, PD sink (12 V request)'))
add(P, Part('D1', 'Diode:SMAJ15A', 'SMAJ15A', 'Diode_SMD:D_SMA', G(22, 33), {1: 'VBUS', 2: 'GND'}, rot=270,
            fields={'MPN': 'Littelfuse SMAJ15A', 'LCSC': ''}, label_side='right'))
C(P, 'C1', '22uF', G(26, 33), 'VBUS', 'GND', fp=C1206, volt='25V')
C(P, 'C2', '22uF', G(30, 33), 'VBUS', 'GND', fp=C1206, volt='25V')
add(P, Part('U1', 'Interface_USB:CH224K', 'CH224K', 'Package_SO:SSOP-10-1EP_3.9x4.9mm_P1mm_EP2.1x3.3mm',
            G(32, 24), {1: 'PD_VDD', 8: 'VBUS', 7: 'PD_CC1', 6: 'PD_CC2', 9: 'PD_CFG1', 10: 'PD_PG', 11: 'GND'},
            fields={'MPN': 'WCH CH224K', 'LCSC': 'C970725'}, desc='USB PD sink controller, requests 12 V'))
R(P, 'R1', '1k', G(36, 15), 'VBUS', 'PD_VDD')
C(P, 'C3', '1uF', G(40, 17.5), 'PD_VDD', 'GND', rot=90)
R(P, 'R2', '24k', G(40, 27), 'PD_CFG1', 'GND')
LED(P, 'D2', 'PD_OK', G(42, 22), 'PD_PG', 'PD_LED', 'C72043')
R(P, 'R3', '4.7k', G(46, 18), 'VBUS', 'PD_LED')

add(P, Part('U2', 'Regulator_Switching:TPS565208', 'TPS565208', SOT236, G(26, 50),
            {3: 'VBUS', 5: 'BUCK_EN', 2: 'SW_5V', 6: 'BST_5V', 4: 'FB_5V', 1: 'GND'},
            fields={'MPN': 'TI TPS565208DDCR', 'LCSC': ''}, desc='4.5-17 V in, 5 A sync buck -> +5V'))
C(P, 'C4', '22uF', G(10, 51), 'VBUS', 'GND', fp=C1206, volt='25V')
C(P, 'C5', '100nF', G(13, 51), 'VBUS', 'GND')
R(P, 'R4', '100k', G(18, 55), 'VBUS', 'BUCK_EN')
R(P, 'R5', '15k', G(18, 61), 'BUCK_EN', 'GND')
C(P, 'C6', '100nF', G(33, 50), 'BST_5V', 'SW_5V', rot=90)
add(P, Part('L1', 'Device:L', '2.2uH', 'Inductor_SMD:L_Sunlord_MWSA0603S', G(38, 49), {1: 'SW_5V', 2: '+5V'},
            rot=90, fields={'MPN': 'Sunlord MWSA0603S-2R2MT', 'Rating': '2.2uH 10A'}))
R(P, 'R6', '56k', G(42, 53), '+5V', 'FB_5V')
R(P, 'R7', '10k', G(42, 59), 'FB_5V', 'GND')
for i, x in enumerate((47, 50, 53, 56)):
    C(P, f'C{7 + i}', '22uF', G(x, 53), '+5V', 'GND')
C(P, 'C11', '100nF', G(59, 53), '+5V', 'GND')

add(P, Part('U3', 'Regulator_Switching:AP3441SHE', 'AP3441SHE-7B',
            'Package_DFN_QFN:DFN-8-1EP_2x2mm_P0.5mm_EP0.9x1.7mm', G(77, 50),
            {3: '+5V', 7: 'PCIE_PWR_EN', 1: 'FB_M2', 6: 'LX_M2', 4: 'GND', 8: 'GND', 9: 'GND'},
            fields={'MPN': 'Diodes AP3441SHE-7B', 'LCSC': ''}, desc='2 A sync buck -> +3V3_M2 (NVMe)'))
C(P, 'C12', '10uF', G(68, 52), '+5V', 'GND')
R(P, 'R8', '100k', G(72, 56), 'PCIE_PWR_EN', 'GND')
add(P, Part('L2', 'Device:L', '2.2uH', 'Inductor_SMD:L_Bourns_SRP5030T', G(85, 48), {1: 'LX_M2', 2: '+3V3_M2'},
            rot=90, fields={'MPN': 'Bourns SRP5030T-2R2M', 'Rating': '2.2uH 6.5A'}))
R(P, 'R9', '10k', G(90, 53), '+3V3_M2', 'FB_M2')
R(P, 'R10', '2.2k', G(90, 59), 'FB_M2', 'GND')
C(P, 'C13', '4.7nF', G(94, 53), '+3V3_M2', 'FB_M2')
for i, x in enumerate((98, 101, 104)):
    C(P, f'C{14 + i}', '10uF', G(x, 51), '+3V3_M2', 'GND')
C(P, 'C17', '100nF', G(107, 51), '+3V3_M2', 'GND')
for i, (ref, net) in enumerate((('#FLG01', 'VBUS'), ('#FLG02', '+5V'), ('#FLG03', 'GND'), ('#FLG04', 'PD_VDD'),
                                  ('#FLG05', '+3V3_M2'))):
    FLAG(P, ref, net, G(8 + 5 * i, 70))

# =========================================================================== COMPUTE MODULE (A3)
M = 'Compute'
SHEET_META[M] = dict(paper='A3', boxes=[
    ((15.24, 20.32), (63.5, 55.88), 'BULK DECOUPLING'),
    ((330.2, 20.32), (406.4, 66.04), 'STATUS LEDs'),
    ((330.2, 71.12), (406.4, 116.84), 'USER BUTTONS'),
], notes=[
    ((332.74, 124.46), 'nRPIBOOT: hold while powering to enter USB boot;'),
    ((332.74, 129.54), 'flash eMMC from a host via USB-C SERVICE (rpiboot).'),
    ((332.74, 137.16), 'PWR_BUT: short press = wake / clean shutdown.'),
    ((332.74, 144.78), 'GPIO bank powered at 3.3 V (GPIO_VREF = +3V3).'),
    ((332.74, 152.4), 'Unused: HDMI0/1, MIPI0/1, SD (eMMC SKU), CAM_GPIO,'),
    ((332.74, 157.48), 'PMIC_ENABLE, EEPROM_nWP, WiFi/BT_nDisable, VBAT.'),
])
cm5 = {}
for p in (1, 2, 7, 8, 13, 14, 22, 23, 32, 33, 42, 43, 52, 53, 59, 60, 65, 66, 71, 74, 98, 107, 108, 113, 114, 119,
          120, 125, 126, 131, 132, 137, 138, 144, 150, 155, 156, 161, 162, 167, 168, 173, 174, 179, 180, 185, 186,
          191, 192, 197, 198):
    cm5[p] = 'GND'
for p in (77, 79, 81, 83, 85, 87):
    cm5[p] = '+5V'
cm5.update({84: '+3V3', 86: '+3V3', 78: 'GPIO_VREF',
            3: 'ETH_D3_P', 5: 'ETH_D3_N', 4: 'ETH_D1_P', 6: 'ETH_D1_N',
            9: 'ETH_D2_N', 11: 'ETH_D2_P', 10: 'ETH_D0_N', 12: 'ETH_D0_P',
            15: 'ETH_nLED3', 17: 'ETH_nLED2', 16: 'FAN_TACH', 19: 'FAN_PWM', 21: 'LED_nACT', 95: 'LED_nPWR',
            92: 'PWR_BUT', 93: 'nRPIBOOT',
            56: 'I2C1_SCL', 58: 'I2C1_SDA', 55: 'UART0_TX', 51: 'UART0_RX', 54: 'UART2_TX', 34: 'UART2_RX',
            49: 'GPIO18_BCLK', 26: 'GPIO19_LRCLK', 27: 'I2S_DIN', 25: 'GPIO21_DOUT', 24: 'MIC_INT', 48: 'MIC_nRST',
            103: 'USB2_N', 105: 'USB2_P', 111: 'VBUS_EN',
            102: 'PCIE_nCLKREQ', 104: 'PCIE_nWAKE', 106: 'PCIE_PWR_EN', 109: 'PCIE_nRST',
            110: 'PCIE_CLK_P', 112: 'PCIE_CLK_N', 116: 'PCIE_RX_P', 118: 'PCIE_RX_N', 122: 'PCIE_TX_P', 124: 'PCIE_TX_N',
            128: 'USB3_0_RX_N', 130: 'USB3_0_RX_P', 134: 'USB3_0_DP', 136: 'USB3_0_DN', 140: 'USB3_0_TX_N', 142: 'USB3_0_TX_P',
            163: 'USB3_1_DP', 165: 'USB3_1_DN'})
add(M, Part('Module1', 'CM5Carrier:ComputeModule5-CM5', 'Raspberry Pi CM5', 'CM5Carrier:RPi_CM5_DF40',
            G(44, 62), cm5, unit_at={2: G(30, 62)},
            fields={'MPN': 'Raspberry Pi CM5 + 2x Hirose DF40C-100DS-0.4V(51)', 'LCSC': 'C597931 (x2)'},
            desc='Raspberry Pi Compute Module 5 (BCM2712) on 2x 100-pin DF40 receptacles'))
for i, (ref, val, net) in enumerate((('C20', '22uF', '+5V'), ('C21', '22uF', '+5V'), ('C22', '100nF', '+5V'),
                                      ('C23', '100nF', '+3V3'))):
    C(M, ref, val, G(10 + 5 * i, 15), net, 'GND')
R(M, 'R11', '0R', G(27, 78), '+3V3', 'GPIO_VREF', rot=90)
FLAG(M, '#FLG06', 'GPIO_VREF', G(22, 74))
R(M, 'R12', '1k', G(140, 16), 'LED_nPWR', 'LED_PWR_K', rot=90)
LED(M, 'D3', 'PWR (red)', G(147, 16), 'LED_PWR_K', '+3V3', 'C2286')
R(M, 'R13', '1k', G(140, 22), 'LED_nACT', 'LED_ACT_K', rot=90)
LED(M, 'D4', 'ACT (green)', G(147, 22), 'LED_ACT_K', '+3V3', 'C72043')
add(M, Part('SW1', 'Switch:SW_Push', 'POWER', BTN, G(146, 34), {1: 'PWR_BUT', 2: 'GND'},
            fields={'MPN': 'Omron B3U-1000P', 'LCSC': 'C231329'}))
add(M, Part('SW2', 'Switch:SW_Push', 'nRPIBOOT', BTN, G(146, 41), {1: 'nRPIBOOT', 2: 'GND'},
            fields={'MPN': 'Omron B3U-1000P', 'LCSC': 'C231329'}))

# =========================================================================== HIGH-SPEED IO (A3)
H = 'HighSpeed'
SHEET_META[H] = dict(paper='A3', boxes=[
    ((15.24, 20.32), (142.24, 185.42), 'M.2 KEY-M NVMe  (PCIe x1, 85 ohm diff)'),
    ((147.32, 20.32), (271.78, 185.42), 'USB HOST: 1x USB 3.0 + 1x USB 2.0  (90 ohm diff)'),
    ((15.24, 190.5), (180.34, 287.02), 'GIGABIT ETHERNET  (MagJack + ESD, 100 ohm diff)'),
    ((185.42, 190.5), (294.64, 256.54), 'USB-C SERVICE  (USB 2.0 device)'),
], notes=[
    ((149.86, 30.48), 'VBUS: AP22653 switch, ILIM = 15k -> ~1.5 A shared; EN = CM5 VBUS_EN'),
    ((17.78, 180.34), 'CM5 provides TX AC-coupling caps; NVMe module provides RX caps'),
    ((187.96, 252.73), 'rpiboot flashing / USB gadget console; CC = 5.1k Rd'),
    ((149.86, 45.72), 'USB-A ports carry no ESD array, matching the Raspberry Pi CM5 IO reference:'),
    ((149.86, 50.8), 'keeps the 5 Gb/s pair stub- and via-free (grounded shell + CM5 PHY protection).'),
    ((149.86, 35.56), 'Upper port: USB 3.0 (CM5 USB3-0). Lower port: USB 2.0 (CM5 USB3-1 D+/D-);'),
    ((149.86, 40.64), 'lower-port SuperSpeed contacts left open - routing trade-off, see docs.'),
])
m2 = {n: 'GND' for n in (1, 3, 9, 15, 21, 27, 33, 39, 45, 51, 57, 71, 73, 75)}
m2.update({n: '+3V3_M2' for n in (2, 4, 12, 14, 16, 18, 70, 72, 74)})
m2.update({49: 'PCIE_TX_P', 47: 'PCIE_TX_N', 43: 'PCIE_RX_P', 41: 'PCIE_RX_N', 55: 'PCIE_CLK_P', 53: 'PCIE_CLK_N',
           50: 'PCIE_nRST', 52: 'PCIE_nCLKREQ', 54: 'PCIE_nWAKE', 10: 'M2_nLED'})
add(H, Part('J2', 'CM5Carrier:M.2_Socket_M_Host', 'M.2 M-Key (NVMe 2230/2242)', 'CM5Carrier:M.2_M_Key_2242',
            G(30, 46), m2, fields={'MPN': 'MTCONN MTSSD03-67MSW337 (H=3.2 mm)'},
            desc='M.2 Key-M socket, PCIe x1 (Gen2, Gen3 capable)'))
LED(H, 'D5', 'SSD (green)', G(46, 50), 'M2_nLED', 'M2_LED_A', 'C72043')
R(H, 'R20', '1k', G(51, 50), 'M2_LED_A', '+3V3_M2', rot=90)
C(H, 'C30', '100nF', G(40, 16), '+3V3_M2', 'GND')

usb3 = {'A1': 'VBUS_USB', 'B1': 'VBUS_USB', 'A4': 'GND', 'B4': 'GND', 'A7': 'GND', 'B7': 'GND', '10': 'GND',
        'B2': 'USB3_0_DN', 'B3': 'USB3_0_DP', 'B5': 'USB3_0_RX_N', 'B6': 'USB3_0_RX_P', 'B8': 'USB3_0_TX_N', 'B9': 'USB3_0_TX_P',
        'A2': 'USB3_1_DN', 'A3': 'USB3_1_DP'}
add(H, Part('J3', 'CM5Carrier:USB3_A', 'USB 3.0 A x2 (stacked)', 'CM5Carrier:MTCONN_UBAF30-D2011', G(80, 42),
            usb3, fields={'MPN': 'MTCONN UBAF30-D2011'}, desc='Stacked USB-A: upper port USB 3.0, lower port USB 2.0'))
add(H, Part('U4', 'CM5Carrier:AP2553W6', 'AP22653W6', SOT236, G(76, 64),
            {1: '+5V', 2: 'GND', 3: 'VBUS_EN', 5: 'USB_ILIM', 6: 'VBUS_USB'},
            fields={'MPN': 'Diodes AP22653W6-7', 'LCSC': ''}, desc='USB VBUS current-limited switch (~1.5 A)'))
C(H, 'C31', '10uF', G(66, 67), '+5V', 'GND')
R(H, 'R21', '15k', G(86, 67), 'USB_ILIM', 'GND')
C(H, 'C32', '22uF', G(92, 66), 'VBUS_USB', 'GND')
C(H, 'C33', '22uF', G(96, 66), 'VBUS_USB', 'GND')
C(H, 'C34', '100nF', G(100, 66), 'VBUS_USB', 'GND')
ESD = 'CM5Carrier:TPD4EUSB30'


def tpd(ref, at, a_p, a_n, b_p, b_n):
    return add(H, Part(ref, ESD, 'TPD4EUSB30', USON10, at,
                       {1: a_p, 10: a_p, 2: a_n, 9: a_n, 4: b_p, 7: b_p, 5: b_n, 6: b_n, 3: 'GND', 8: 'GND'},
                       fields={'MPN': 'TI TPD4EUSB30DQAR', 'LCSC': ''}))



eth = {1: 'ETH_D0_P', 2: 'ETH_D0_N', 3: 'ETH_D1_P', 6: 'ETH_D1_N', 7: 'ETH_D2_P', 8: 'ETH_D2_N', 9: 'ETH_D3_P',
       10: 'ETH_D3_N', 4: 'ETH_CT', 5: 'ETH_CT', 15: '+3V3', 17: '+3V3', 16: 'ETH_LEDY_K', 18: 'ETH_LEDG_K',
       19: 'GND', 20: 'GND'}
add(H, Part('J4', 'CM5Carrier:MagJack-A70-112-331N126', 'RJ45 MagJack 1000BASE-T', 'CM5Carrier:TRJG0926HENL',
            G(40, 108), eth, fields={'MPN': 'Trxcom TRJG0926HENL'},
            desc='RJ45 with integrated 1000BASE-T magnetics and LEDs', pin_style={15: 'glabel', 17: 'glabel'}))
C(H, 'C35', '100nF', G(24, 90), 'ETH_CT', 'GND')
R(H, 'R22', '470R', G(26, 101), 'ETH_nLED2', 'ETH_LEDY_K', rot=90)
R(H, 'R23', '470R', G(19, 103), 'ETH_nLED3', 'ETH_LEDG_K', rot=90)
tpd('U8', G(58, 86), 'ETH_D0_P', 'ETH_D0_N', 'ETH_D1_P', 'ETH_D1_N')
tpd('U9', G(58, 102), 'ETH_D2_P', 'ETH_D2_N', 'ETH_D3_P', 'ETH_D3_N')

add(H, Part('J5', 'Connector:USB_C_Receptacle_USB2.0_16P', 'USB-C SERVICE', USBC, G(84, 86),
            {'A4': 'SVC_VBUS', 'A9': 'SVC_VBUS', 'B4': 'SVC_VBUS', 'B9': 'SVC_VBUS', 'A5': 'SVC_CC1', 'B5': 'SVC_CC2',
             'A6': 'USB2_P', 'B6': 'USB2_P', 'A7': 'USB2_N', 'B7': 'USB2_N',
             'A1': 'GND', 'A12': 'GND', 'B1': 'GND', 'B12': 'GND', 'SH': 'GND'},
            fields={'MPN': 'GCT USB4105-GF-A', 'LCSC': 'C3020560'},
            desc='USB 2.0 device port: rpiboot flashing / USB gadget console'))
R(H, 'R24', '5.1k', G(100, 88), 'SVC_CC1', 'GND')
R(H, 'R25', '5.1k', G(96, 88), 'SVC_CC2', 'GND')
add(H, Part('U10', 'Power_Protection:USBLC6-2SC6', 'USBLC6-2SC6', SOT236, G(110, 92),
            {1: 'USB2_P', 6: 'USB2_P', 3: 'USB2_N', 4: 'USB2_N', 2: 'GND', 5: 'SVC_VBUS'},
            fields={'MPN': 'ST USBLC6-2SC6', 'LCSC': 'C7519'}))

# =========================================================================== PERIPHERAL IO (A4)
I = 'PeriphIO'
SHEET_META[I] = dict(paper='A4', boxes=[
    ((15.24, 20.32), (149.86, 101.6), 'MIC-ARRAY LINK  (to XVF3800 6-mic board)'),
    ((154.94, 20.32), (281.94, 96.52), 'QWIIC I2C  (3.3 V)'),
    ((15.24, 106.68), (149.86, 142.24), 'DEBUG CONSOLE  (UART0, 3.3 V)'),
    ((154.94, 101.6), (281.94, 127.0), 'BARCODE SCANNER  (UART2, 5 V supply / 3.3 V logic)'),
    ((154.94, 129.54), (281.94, 160.02), 'FAN  (Raspberry Pi 5 active cooler pinout)'),
    ((15.24, 147.32), (149.86, 187.96), 'MECHANICAL  (H1-H4 board corners, H5-H8 CM5 standoffs)'),
])
SHEET_META[I]['notes'] = [
    ((17.78, 93.98), '33R source termination on CM5-driven I2S clocks/data'),
    ((17.78, 99.06), 'I2C1 pulled up once (4.7k) for header + Qwiic'),
]
hdr = {1: '+5V', 2: '+3V3', 3: 'GND', 4: 'GND', 5: 'I2S_BCLK', 6: 'I2S_LRCLK', 7: 'I2S_DIN', 8: 'I2S_DOUT',
       9: 'I2C1_SDA', 10: 'I2C1_SCL', 11: 'MIC_nRST', 12: 'MIC_INT'}
add(I, Part('J6', 'Connector_Generic:Conn_02x06_Odd_Even', 'MIC ARRAY',
            'Connector_IDC:IDC-Header_2x06_P2.54mm_Vertical', G(30, 22), hdr, pin_style={1: 'glabel', 2: 'glabel', 3: 'glabel', 4: 'glabel'},
            fields={'MPN': '2x6 2.54 mm shrouded box header'},
            desc='Mic-array (XVF3800) link: I2S + I2C control + reset/IRQ'))
R(I, 'R30', '33R', G(20, 22), 'GPIO18_BCLK', 'I2S_BCLK', rot=90)
R(I, 'R31', '33R', G(42, 22), 'I2S_LRCLK', 'GPIO19_LRCLK', rot=90)
R(I, 'R32', '33R', G(38, 26), 'I2S_DOUT', 'GPIO21_DOUT')
R(I, 'R33', '4.7k', G(69, 22), '+3V3', 'I2C1_SDA')
R(I, 'R34', '4.7k', G(66, 22), '+3V3', 'I2C1_SCL')
add(I, Part('J7', 'Connector_Generic:Conn_01x04', 'QWIIC', JSTSH4, G(80, 24),
            {1: 'GND', 2: '+3V3', 3: 'I2C1_SDA', 4: 'I2C1_SCL'}, pin_style={1: 'glabel', 2: 'glabel'},
            fields={'MPN': 'JST SM04B-SRSS-TB', 'LCSC': 'C160404'}))
add(I, Part('J8', 'Connector_Generic:Conn_01x03', 'DEBUG UART', 'Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical',
            G(30, 49), {1: 'GND', 2: 'UART0_TX', 3: 'UART0_RX'}, pin_style={1: 'glabel'}))
add(I, Part('J9', 'Connector_Generic:Conn_01x04', 'BARCODE', JSTSH4, G(80, 46),
            {1: '+5V', 2: 'UART2_TX', 3: 'UART2_RX', 4: 'GND'}, pin_style={1: 'glabel', 4: 'glabel'},
            fields={'MPN': 'JST SM04B-SRSS-TB', 'LCSC': 'C160404'}))
add(I, Part('J10', 'Connector_Generic:Conn_01x04', 'FAN', JSTSH4, G(80, 58),
            {1: '+5V', 2: 'FAN_PWM', 3: 'GND', 4: 'FAN_TACH'}, pin_style={1: 'glabel', 3: 'glabel'},
            fields={'MPN': 'JST SM04B-SRSS-TB', 'LCSC': 'C160404'}))
R(I, 'R35', '10k', G(69, 55), '+3V3', 'FAN_PWM')
for i in range(4):
    add(I, Part(f'H{i + 1}', 'Mechanical:MountingHole_Pad', 'M3', 'MountingHole:MountingHole_3.2mm_M3_Pad_Via',
                G(9 + 4 * i, 64), {1: 'GND'}))
for i in range(4):
    add(I, Part(f'H{i + 5}', 'Mechanical:MountingHole_Pad', 'M2.5', 'MountingHole:MountingHole_2.7mm_M2.5_Pad_Via',
                G(29 + 4 * i, 64), {1: 'GND'}))
for i in range(3):
    add(I, Part(f'FID{i + 1}', 'Mechanical:Fiducial', 'Fiducial', 'Fiducial:Fiducial_1mm_Mask2mm', G(9 + 4 * i, 71), {}))
