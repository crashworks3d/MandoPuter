"""
MandoPuter will display text in a Mandalorian font on a tiny LCD display

File   - code.py
Author - Jon Breazile

https://github.com/Breazile/MandoPuter

Font credits to ErikStormtrooper, the bitmap fonts were created from his TrueType font
http://www.erikstormtrooper.com/mandalorian.htm
"""
import gc
import time
import alarm
import board
import busio
import pwmio
import neopixel
import digitalio
import displayio
# Import the display bus class based on CircuitPython version
import sys

# Get CircuitPython version
cp_version = sys.implementation.version
print(f"CircuitPython version: {cp_version[0]}.{cp_version[1]}.{cp_version[2]}")

# Import the FourWire class from the appropriate module
try:
    from displayio import FourWire
    print("Using displayio.FourWire")
except ImportError:
    try:
        from displayio_spi import FourWire
        print("Using displayio_spi.FourWire")
    except ImportError:
        try:
            # For CircuitPython 10.x, try importing from fourwire module
            import fourwire
            FourWire = fourwire.FourWire
            print("Using fourwire.FourWire")
        except (ImportError, AttributeError):
            # If all imports fail, we'll handle this differently later
            FourWire = None
            print("Could not import FourWire class, will try alternative approach")
import adafruit_dotstar as dotstar
import adafruit_imageload
from analogio import AnalogIn
from adafruit_display_text import label
from adafruit_bitmap_font import bitmap_font
from adafruit_st7789 import ST7789
from adafruit_lc709203f import LC709203F
from adafruit_debouncer import Debouncer

"""
  ----------- User configurable items -----------

  This is where you can customize your display and hardware setup.
  Select either the Pre-Beskar (1.14" LCD) or Beskar (1.3" LCD) display.
  Some lines are commented out which means the line is not active.
  A commented line starts with a #


"""
# Set the display type
#DISPLAY        = "Pre-Beskar"          # Adafruit 1.14" LCD display  https://www.adafruit.com/product/4383
DISPLAY       = "Beskar"                # Adafruit 1.3" LCD display   https://www.adafruit.com/product/4313
DISP_BRIGHT    = 90                     # How bright to make the display - 0% to 100%

# Board being used
#BOARD_TYPE    = "ESP32-S3"              # ESP32-S3                  https://www.adafruit.com/product/5477
#BOARD_TYPE    = "FeatherM4"            # Feather M4 Express        https://www.adafruit.com/product/3857
#BOARD_TYPE    = "ItsyBitsyM4"          # ItsyBitsy M4 Express      https://www.adafruit.com/product/3800
#BOARD_TYPE    = "ItsyBitsyRP2040"      # ItsyBitsy RP2040          https://www.adafruit.com/product/4888
BOARD_TYPE     = "PiPicoRP2040"        # Raspberry Pi Pico RP2040  https://www.adafruit.com/product/4864

# Mandalorian charater sequence that is shown on the display
messages       = [ "MLM", "JBM", "SAS", "JAS", "JBM", "MLM", "SAS", "AJS", "SAS"]
# Time that each character group is shown 0.50 is 500 milliseconds, or 1/2 of a second
delays         = [  0.75,  0.75,  0.650,  0.75, 0.50,  0.84,  1.00,  0.35,  0.84]
TEXT_COLOR     = 0xFF0000               # Red on black (you can chose colors here - https://www.color-hex.com/)

# Name of the owner shown after startup and before the sequence starts
SHOW_NAME      = 1                      # Set to 1 to display the name, or 0 to not display a name
OWNER_NAME     = "Crash Works 3D"       # Name of the owner to be shown
NAME_COLOR     = 0xCC5500               # Green on black (you can chose colors here - https://www.color-hex.com/)
NAME_HOLD      = 3.0                    # How many seconds to display the name

# Banner graphic(s) shown after the owner's name and before the sequence starts
SHOW_IMG       = 3                      # How many images to show. 0 = no images, 1 = 1 image, 2 = 2 images
IMG1           = "img/cwavatar_240_8bit.bmp"    # File name of the first 8 bit BMP graphic to be shown
IMG1_HOLD      = 5.00
IMG2           = "img/cw3d_cave_240_8bit.bmp"         # File name of the first 8 bit BMP graphic to be shown after each text sequence
IMG2_HOLD      = 5.00                   # How long the first image is displayed in seconds
IMG3           = "img/cw3d_qr_code_240_gray.bmp"      # File name of the second 8 bit BMP graphic to be shown after the first image
IMG3_HOLD      = 5.00                   # How long the second image is displayed in seconds

# Other settings for debugging and battery monitoring
BATTERY_SZ     = 500                    # Size of battery in mAh (only for the ESP32-S3 board)
BATTERY_MON    = 0                      # Set to 1 to enable the battery monitor, 0 to disable it
LOW_BATT_LEVEL = 10                     # Show the low battery icon when the battery goes below this percentage
ENABLE_LEDS    = 0                      # Set to 1 to turn on LEDs for debugging, set to 0 to save battery
SPI_SPEED      = 48000000               # How fast the SPI bus to the LCD operates
"""
# ---------------------------------------------------------------------------------
"""

def DisplayName(name, hold, color, init_tm) :
    ownerfont = bitmap_font.load_font("fonts/Alef-Bold-18.bdf")  # 18 point bitmap font
    banner_text = label.Label(ownerfont, text=name, color=color)
    banner_text.x = int(((display.width - banner_text.bounding_box[2])/2)-1)
    banner_text.y = int(((display.height - banner_text.bounding_box[3])/2)+1)
    #banner_text.y = int((display.height / 2)-5)
    display.root_group = banner_text
    display.refresh()
    if SHOW_IMG > 0 :
        time.sleep(hold)              # Display the name before the graphics
    else :
        if hold > init_tm :
            time.sleep(hold - init_tm)  # minus the initialization time if there are images
    # release memory
    del ownerfont
    del banner_text
    gc.collect()

def DisplayImage(img, hold, images, init_tm) :
    # Create the first image centered on the display
    try :
        bitmap, palette = adafruit_imageload.load(img, bitmap=displayio.Bitmap, palette=displayio.Palette)
    except:
        bitmap = displayio.OnDiskBitmap(img)
        palette = bitmap.pixel_shader
    x = int((display.width - bitmap.width) / 2)
    y = int((display.height - bitmap.height) / 2)
    if x < 0 : x = 0
    if y < 0 : y = 0
    tile_grid = displayio.TileGrid(bitmap, pixel_shader=palette, x=x, y=y)
    img = displayio.Group()
    img.append(tile_grid)
    display.root_group = img
    display.refresh()
    if hold > init_tm :
        if images > 1 :
            time.sleep(hold)              # hold the first image before showing the second
        else :
            if hold > init_tm :
                time.sleep(hold - init_tm)  # minus the initialization time if there is 1 image
    img.pop()
    del bitmap
    del img
    del tile_grid
    gc.collect()

def GetBattPercent(batt_pin) :
    percent = 0
    # read the battery voltage (approximation, not exact levels with no fuel gauge to read)
    batt_volts = (batt_pin.value * 3.3) / 65536 * 2
    if batt_volts > 3.80 :
        percent = 86                    # 100% to 81% capacity
    elif batt_volts > 3.65 :
        percent = 50                    # 80%  to 31% capacity
    elif batt_volts > 3.40 :
        percent = 25                    # 30%  to 16% capacity
    else :
        percent = 5                     # 15%  to  0% capacity
    return percent

# Turn off the LCD Backlight
displayio.release_displays()

# Setup the bus, display object, and font for the display
if BOARD_TYPE == "PiPicoRP2040" :
    spi = busio.SPI(clock=board.GP10, MOSI=board.GP11, MISO=board.GP12)
else :
    spi = board.SPI()
while not spi.try_lock():
    pass
spi.configure(baudrate=SPI_SPEED)  # Configure SPI with the specified speed
spi.unlock()
if BOARD_TYPE == "FeatherM4" or BOARD_TYPE == "ESP32-S3" :
    tft_cs  = board.D6
    tft_dc  = board.D9
    lcd_rst = board.D5
    lcd_light = board.D10
elif BOARD_TYPE == "PiPicoRP2040" :
    tft_cs    = board.GP28
    tft_dc    = board.GP14
    lcd_rst   = board.GP27
    lcd_light = board.GP15
    btn_pin   = board.GP13
else:
    lcd_light = board.D10
    tft_cs = board.D2
    tft_dc  = board.D3
    lcd_rst = board.D4

# Create the display bus and display
print("Initializing display")
try:
    # Try to create a FourWire display bus
    if FourWire is not None:
        try:
            # First try with all parameters
            display_bus = FourWire(spi, command=tft_dc, chip_select=tft_cs, reset=lcd_rst)
            print("Created FourWire display bus with all parameters")
        except TypeError:
            try:
                # Try without reset parameter
                display_bus = FourWire(spi, command=tft_dc, chip_select=tft_cs)
                print("Created FourWire display bus without reset parameter")
            except TypeError:
                # Try with minimal parameters
                display_bus = FourWire(spi)
                print("Created FourWire display bus with minimal parameters")
    else:
        # If FourWire is not available, we'll pass the SPI bus directly to ST7789
        display_bus = None
        print("No FourWire class available, will pass SPI directly to ST7789")
    
    # Create the ST7789 display
    if display_bus is not None:
        # Create display with display_bus
        if DISPLAY == "Pre-Beskar":
            display = ST7789(
                display_bus,
                width=240,  # Required parameter
                height=135,
                rowstart=40,
                colstart=53,
                rotation=90,
                auto_refresh=False,
                backlight_pin=lcd_light,
                brightness=0
            )
            print("Created ST7789 display with display_bus (Pre-Beskar)")
            font = bitmap_font.load_font("fonts/mandalor135.bdf")
            offset = 12
        elif DISPLAY == "Beskar":
            display = ST7789(
                display_bus,
                width=240,  # Required parameter
                height=240,
                rowstart=80,
                rotation=180,
                auto_refresh=False,
                backlight_pin=lcd_light,
                brightness=0
            )
            print("Created ST7789 display with display_bus (Beskar)")
            font = bitmap_font.load_font("fonts/mandalor165.bdf")
            offset = 14
    else:
        # Try direct initialization with SPI
        try:
            if DISPLAY == "Pre-Beskar":
                # Try with named parameters
                display = ST7789(
                    spi,
                    width=240,  # Required parameter
                    height=135
                )
                # Set additional properties after creation
                display.rowstart = 40
                display.colstart = 53
                display.rotation = 90
                print("Created ST7789 display directly with SPI (Pre-Beskar)")
            else:
                # Try with named parameters
                display = ST7789(
                    spi,
                    width=240,  # Required parameter
                    height=240
                )
                # Set additional properties after creation
                display.rowstart = 80
                display.rotation = 180
                print("Created ST7789 display directly with SPI (Beskar)")
            
            # Set common properties
            display.auto_refresh = False
            
            # Set font based on display type
            if DISPLAY == "Pre-Beskar":
                font = bitmap_font.load_font("fonts/mandalor135.bdf")
                offset = 12
            else:
                font = bitmap_font.load_font("fonts/mandalor165.bdf")
                offset = 14
        except Exception as e:
            print(f"Error creating display with SPI: {e}")
            raise
except Exception as e:
    print(f"Error initializing display: {e}")
    raise
stage = displayio.Group()
display.root_group = stage

# Disable WiFi power
if BOARD_TYPE == "ESP32-S3" :
    import wifi
    wifi.radio.enabled = 0

# Configure LEDs
if BOARD_TYPE == "ESP32-S3" :
    # setup the onboard neopixel LED power control
    led_pwr = digitalio.DigitalInOut(board.NEOPIXEL_POWER)
    led_pwr.direction = digitalio.Direction.OUTPUT

if BOARD_TYPE == "FeatherM4" or BOARD_TYPE == "ESP32-S3" or BOARD_TYPE == "ItsyBitsyRP2040" :
    led = neopixel.NeoPixel(board.NEOPIXEL, 1)
elif BOARD_TYPE == "ItsyBitsyM4" :
    led = dotstar.DotStar(board.APA102_SCK, board.APA102_MOSI, 1) # onboard dotstar
elif BOARD_TYPE == "PiPicoRP2040" :
    led = digitalio.DigitalInOut(board.LED)
    led.direction = digitalio.Direction.OUTPUT

if ENABLE_LEDS > 0 :
    if BOARD_TYPE != "PiPicoRP2040" :
        led.brightness = 0.05  # dim the LED to 5%
        led[0] = (255, 0, 255) # purple
    if BOARD_TYPE == "ESP32-S3" :
        led_pwr.value = True
else :
    if BOARD_TYPE != "PiPicoRP2040" :
        led.brightness = 0  # dim the LED to 0%
    if BOARD_TYPE == "ESP32-S3" :
        led_pwr.value = False

# Setup battery monitoring
if BATTERY_MON > 0 :
    lowbattX = 0
    lowbattY = 0
    vbat_voltage = 0
    if BOARD_TYPE == "ESP32-S3" :
        i2c = board.I2C()  # uses board.SCL and board.SDA
        sensor = LC709203F(i2c)
        sensor.PackSize = BATTERY_SZ
    elif BOARD_TYPE == "FeatherM4" :
        vbat_voltage = AnalogIn(board.VOLTAGE_MONITOR) # for measuring battery voltage
    elif BOARD_TYPE == "PiPicoRP2040" :
        # battery voltage measurements need a jumper from VSYS to ADC0 (pin 39 - 31)
        vbat_voltage = AnalogIn(board.GP26) # for measuring battery voltage
    elif BOARD_TYPE == "ItsyBitsyM4" or BOARD_TYPE == "ItsyBitsyRP2040" :
        # battery voltage measurements need a jumper from batt to A1
        vbat_voltage = AnalogIn(board.A1)

    # Create the second image centered on the display
    lowbattImg, lowbattPal = adafruit_imageload.load("img/LowBatt.bmp", bitmap=displayio.Bitmap, palette=displayio.Palette)
    x = int(display.width - lowbattImg.width)
    y = int(display.height - lowbattImg.height)
    if x < 0 : x = 0
    if y < 0 : y = 0
    lowbattX = x
    lowbattY = y
else :
    # Disable I2C port power
    if BOARD_TYPE == "ESP32-S3" :
        i2c_pwr = digitalio.DigitalInOut(board.I2C_POWER)
        i2c_pwr.direction = digitalio.Direction.OUTPUT
        i2c_pwr.value = False

# Turn on the Backlight
display.brightness = DISP_BRIGHT / 100
init_time = 4.5   # how long it takes to initialize the sequence

# Show the owner's name at startup
if SHOW_NAME > 0 :
    DisplayName(OWNER_NAME, NAME_HOLD, NAME_COLOR, init_time)

# Show the banner graphic(s)
if SHOW_IMG > 0 :
    DisplayImage(IMG1, IMG1_HOLD, SHOW_IMG, init_time)
    DisplayImage(IMG2, IMG2_HOLD, SHOW_IMG, init_time)
    DisplayImage(IMG3, IMG3_HOLD, SHOW_IMG, init_time)

gc.collect()
low_batt_icon = 0
batt_percent  = 0

# Setup switch on GPIO pin with debouncer for button press detection
switch_pin = digitalio.DigitalInOut(btn_pin)
switch_pin.direction = digitalio.Direction.INPUT
switch_pin.pull = digitalio.Pull.UP  # Use pull-up resistor
switch = Debouncer(switch_pin)

# Variable to track image display state
is_showing_img3 = False    # Track whether IMG3 is currently being displayed

# Prepare the Mandalorian characters
text   = label.Label(font, text=messages[0], color=TEXT_COLOR)
text.x = int(((display.width - text.width)/2)-1)
text.y = int((display.height / 2)+offset)
if text.x < 0:
    text.x = 0
if text.y < 0:
    text.y = 0
stage.append(text)

# Initialize the low battery icon
if BATTERY_MON > 0 :
    batt_tile = displayio.TileGrid(lowbattImg, pixel_shader=lowbattPal, x=lowbattX, y=lowbattY)

display.root_group = stage

# Create a function to restore text display after showing image
def restore_text_display():
    display.root_group = stage
    display.refresh()

while True:
    # Update the debouncer
    switch.update()
    
    # Check if button is pressed (value is False when pressed with pull-up resistor)
    if not switch.value:  # Button is currently pressed
        if not is_showing_img3:
            # Show IMG3 when button is first pressed
            DisplayImage(IMG3, 0, SHOW_IMG, 0)  # Don't wait, just display the image
            is_showing_img3 = True
    else:  # Button is released
        if is_showing_img3:
            # Restore text display when button is released
            restore_text_display()
            is_showing_img3 = False
    
    # Only proceed with normal sequence if button is not pressed and we're not showing IMG3
    if switch.value and not is_showing_img3:
        index = 0
        for msg in messages:
            # Check for switch input during message display to allow interruption
            switch.update()
            if not switch.value:  # Button is pressed during message display
                # Show IMG3 and set flag
                DisplayImage(IMG3, 0, SHOW_IMG, 0)  # Don't wait, just display the image
                is_showing_img3 = True
                break  # Exit the message loop
            
            # Update the text and display
            text.text = msg
            display.refresh()
            
            # Wait for the specified delay
            if BOARD_TYPE == "PiPicoRP2040":
                time.sleep(delays[index] * 0.75)
            else:
                time.sleep(delays[index])
            index = index + 1
            
            # Check button again after delay
            switch.update()
            if not switch.value:  # Button was pressed during sleep
                # Show IMG3 and set flag
                DisplayImage(IMG3, 0, SHOW_IMG, 0)  # Don't wait, just display the image
                is_showing_img3 = True
                break  # Exit the message loop

    if BATTERY_MON > 0 :
        if BOARD_TYPE == "ESP32-S3" :
            try:
                print("Battery: %0.3f Volts / %0.1f %%" % (sensor.cell_voltage, sensor.cell_percent))
                batt_percent = sensor.cell_percent
            except OSError as e:
                print(e)
        else :
            batt_percent = GetBattPercent(vbat_voltage)
        if batt_percent < LOW_BATT_LEVEL :
            # Add low battery icon
            if low_batt_icon == 0 :
                stage.append(batt_tile)
                low_batt_icon = 1
        else :
            if low_batt_icon > 0 :
                # Remove low battery icon
                stage.pop()
                low_batt_icon = 0
