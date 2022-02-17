"""Methods to read data from a MEAS M32JM pressure & temperature sensor"""

import smbus  # Alternative is pigpio: http://abyz.me.uk/rpi/pigpio/python.html#i2c_open
import time
import RPi.GPIO as GPIO

# Define I2C communication variables
bus1 = smbus.SMBus(1)  # Original I2C bus
bus2 = smbus.SMBus(3)  # Custom I2C bus, where GPIO 23 = SDA and GPIO 24 = SCL
address = 0x28
read_header = 0x51

SDA1_PIN = 2
SCL1_PIN = 3
SDA2_PIN = 23
SCL2_PIN = 24

# Variables from example code
temp = []  # Array of 7 unsigned 8 bit integers
Tscope = Pscope = Tdisplay = Pdisplay = float(0)
Lmax = float(100)  # Span 100L，Zero 0L, Span should be defined by the sensor pressure range. 100 means pressure range of 100L
Lmin = float(0)
Pvalue = Tvalue = Pspan = Tspan = 0
P1 = 1000
P2 = 15000
READ_Sensor_SDA = True
I2C_ERR = 0


GPIO.setmode(GPIO.BCM) # Use Broadcom GPIO pin numbering
#GPIO.setup(SCL1_PIN, GPIO.OUT, pull_up_down=GPIO.PUD_OFF)
#GPIO.setup(SCL2_PIN, GPIO.OUT, pull_up_down=GPIO.PUD_OFF)


# Switch SDA pin from input to output?  >> input = ALT0, output = OUTPUT
# Do we even have to do this? Or can we just call smbus.write_byte()?? 
# But that only sets SDA, how do we then set SCL pin HIGH/LOW?
# https://raspberrypi.stackexchange.com/a/105637/144210
# https://forums.raspberrypi.com/viewtopic.php?t=190604#p1198566
# https://forums.raspberrypi.com/viewtopic.php?t=76849#p549112
def SDA_IN():
    """Set SDA pin to I2C INPUT with no pullup"""
    GPIO.setup(SDA1_PIN, GPIO.I2C, pull_up_down=GPIO.PUD_OFF)
    #GPIO.setup(SDA2_PIN, GPIO.I2C, pull_up_down=GPIO.PUD_OFF)


def SDA_OUT():
    """Set SDA pin to OUTPUT with no pullup"""
    GPIO.setup(SDA1_PIN, GPIO.OUT, pull_up_down=GPIO.PUD_OFF)
    #GPIO.setup(SDA2_PIN, GPIO.OUT, pull_up_down=GPIO.PUD_OFF)


def SCL_High():
    GPIO.output(SCL1_PIN, GPIO.HIGH)
    #GPIO.output(SCL2_PIN, GPIO.HIGH)

def SCL_Low():
    GPIO.output(SCL1_PIN, GPIO.LOW)
    #GPIO.output(SCL2_PIN, GPIO.LOW)

def SDA_High():
    GPIO.output(SDA1_PIN, GPIO.HIGH)
    #GPIO.output(SDA2_PIN, GPIO.HIGH)

def SDA_Low():
    GPIO.output(SDA1_PIN, GPIO.LOW)
    #GPIO.output(SDA2_PIN, GPIO.LOW)


def delay_us(microseconds):
    time.sleep(microseconds / 1000000.0)


def IIC_Start():
    """A HIGH to LOW transition on the SDA line while SCL is HIGH"""
    SDA_OUT()

    SDA_High()
    SCL_High()

    delay_us(4)

    SDA_Low()

    delay_us(4)

    SCL_Low()


def IIC_Stop():
    """A LOW to HIGH transition on the SDA line while SCL is HIGH"""
    SDA_OUT()

    SCL_Low()
    SDA_Low()

    delay_us(4)

    SCL_High()
    SDA_High()

    delay_us(4)


def IIC_Wait_Ack():
    ucErrTime = 0
    SDA_IN()
    SDA_High
    delay_us(1)
    SCL_High()
    delay_us(1)
    while READ_Sensor_SDA:
        ucErrTime = ucErrTime + 1
        if ucErrTime > 250:
            IIC_Stop()
            return 1
    SCL_Low()
    return 0


def IIC_Ack():
    SCL_Low()

    SDA_OUT()

    SDA_Low()

    delay_us(2)

    SCL_High()

    delay_us(2)

    SCL_Low()


def IIC_NAck():
    SCL_Low()

    SDA_OUT()

    SDA_High()

    delay_us(2)

    SCL_High()

    delay_us(2)

    SCL_Low()


def IIC_Send_Byte(txd):
    SDA_OUT()
    SCL_Low()

    for t in range(8):
        if txd & 0x80:  # 0x80 is write?
            SDA_High()
        else:
            SDA_Low()

        txd <<= 1

        delay_us(2)
        SCL_High()
        delay_us(2)
        SCL_Low()
        delay_us(2)


def IIC_Read_Byte(ack):
    """Should we use bus1.read_byte_data(address, 1) instead???"""
    receive = 0
    SDA_IN()
    for i in range(8):
        SCL_Low()
        delay_us(2)
        SCL_High()
        receive <<= 1
        if (READ_Sensor_SDA):
            receive = receive + 1
        delay_us(1)

    if not ack:
        IIC_NAck()
    else:
        IIC_Ack()
    
    return receive


def Get_I2CValue(dataType):
    """Read sensor value
    
    Args:
        dataType (string): Whether to return 'temperature' or 'pressure'

    Returns: 
        float: The temperature or pressure
    """
    # Wake_up，if non-sleep mode this part is no needed.
    IIC_Start()  # MR command
    IIC_Send_Byte(read_header)
    IIC_Wait_Ack()
    IIC_Stop()
    delay_us(2000)  # 2ms
    IIC_Start()
    IIC_Send_Byte(read_header)
    IIC_Wait_Ack()
    temp[0] = IIC_Read_Byte(1)
    temp[1] = IIC_Read_Byte(1)
    temp[2] = IIC_Read_Byte(1)
    temp[3] = IIC_Read_Byte(0)
    IIC_Stop()

    if (temp[0] & 0xc0) is 0x00:
        Pvalue = (temp[0] << 8) | temp[1]
        Tvalue = (temp[2] << 3) | (temp[3] >> 5)
        I2C_ERR = 0
    else:
        I2C_ERR = 1    
        
    Tscope = 200  # -50~150
    Tspan = 2048  # 11 bit

    if I2C_ERR is 0:
        Pspan = P2 - P1
        Tdisplay = Tvalue * Tscope / Tspan - 50
        Pdisplay = Pvalue * (Lmax - Lmin) / Pspan + Lmin  # 100L

    return Tdisplay if dataType is 'temperature' else Pdisplay