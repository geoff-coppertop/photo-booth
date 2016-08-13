#!/usr/bin/env python
# created by coppertop, 2016

import PhotoBooth
import RPi.GPIO as GPIO

START_BTN = 16
EXIT_BTN = 18
DEBOUNCE_TIME = 300

pb = None

def __exitBtn_Handler( channel ):
    global pb

    print '...Exit button pressed'

    # Exit button unhooks all GPIO interrupts
    GPIO.remove_event_detect( EXIT_BTN )
    GPIO.remove_event_detect( START_BTN )

    # Call the exit function
    pb.exit()

def __startBtn_Handler( channel ):
    global pb

    print '...Start button pressed'

    # Call the start function
    pb.start()

def __exit():
    print '...Ending Program'

    GPIO.cleanup()

def __init():
    print '...Initializing'

    GPIO.setmode( GPIO.BCM )

    GPIO.setup( START_BTN, GPIO.IN, pull_up_down = GPIO.PUD_UP )
    GPIO.setup( EXIT_BTN, GPIO.IN, pull_up_down = GPIO.PUD_UP )

    GPIO.add_event_detect( START_BTN, GPIO.FALLING, callback = __startBtn_Handler, bouncetime = DEBOUNCE_TIME )
    GPIO.add_event_detect( EXIT_BTN, GPIO.FALLING, callback = __exitBtn_Handler, bouncetime = DEBOUNCE_TIME )

if __name__ == "__main__":
    pb = PhotoBooth.PhotoBooth()

    # Initialize the GPIO
    __init()

    # Start the photobooth, this function will not return until the
    # PhotoBooth.exit() is called
    pb.run()

    # Clean up now that the photobooth has been ended
    __exit()
