#!/usr/bin/env python
# created by coppertop, 2016

import os
import picamera
import pygame
import RPi.GPIO as GPIO
import sys
import subprocess
import time

START_BTN = 16
EXIT_BTN = 18

PREP_TIME = 1
DEBOUNCE_TIME = 300
LOOP_DELAY_TIME = 0.01

NUMBER_OF_PHOTOS = 4

CAPTION = 'Test'

ATTRACT_IMAGE_PATH = os.path.join( 'images', 'attract.jpg' )
PROCESSING_IN_PROGRESS_IMAGE_PATH = os.path.join( 'images', 'processing.jpg' )
PHOTO_UPLOADING_IMAGE_PATH = os.path.join( 'images', 'uploading.jpg' )

exitLoop = False
startSession = False

path = '.'

def exitBtn_Handler( channel ):
    GPIO.remove_event_detect( EXIT_BTN )
    GPIO.remove_event_detect( START_BTN )

    global exitLoop
    global startSession

    print '...Exit button pressed'

    exitLoop = True
    startSession = False

def startBtn_Handler( channel ):
    GPIO.remove_event_detect( START_BTN )

    global startSession

    startSession = True

def exit():
    print '...Ending Program'

    GPIO.cleanup()

def init():
    print '...Initializing'
    
    GPIO.setmode( GPIO.BCM )

    GPIO.setup( START_BTN, GPIO.IN, pull_up_down = GPIO.PUD_UP )
    GPIO.setup( EXIT_BTN, GPIO.IN, pull_up_down = GPIO.PUD_UP )

    GPIO.add_event_detect( START_BTN, GPIO.FALLING, callback = startBtn_Handler, bouncetime = DEBOUNCE_TIME )
    GPIO.add_event_detect( EXIT_BTN, GPIO.FALLING, callback = exitBtn_Handler, bouncetime = DEBOUNCE_TIME )

    pygame.init()

    size = ( pygame.display.Info().current_w, pygame.display.Info().current_h )

    pygame.display.set_caption( CAPTION )
    pygame.mouse.set_visible( False )
    pygame.display.set_mode( size, pygame.FULLSCREEN )

    showImage( ATTRACT_IMAGE_PATH )

def givePrepTime( prepTime = PREP_TIME ):
    time.sleep( prepTime )

def runPhotoSession():
    print '...Photo session started'
 
    # Get the current time for the photo name
    currentTime = time.strftime( '%Y%m%d-%H%M%S' )

    # Store the current working directory
    cwd = os.getcwd()
 
    # Create the folder path for the session
    sessionPath = os.path.join( path, 'Session' + '-' + currentTime )

    # Check if the sessionPath exists, if not create
    if not os.path.exists( sessionPath ):
        os.makedirs( sessionPath )
        
    # Set the current working directory
    os.chdir( sessionPath )

    # Start the camera preview
    with picamera.PiCamera() as camera:
        camera.led = False
        camera.start_preview()
   
        # Take the photos
        photoNumber = 0

        while photoNumber < NUMBER_OF_PHOTOS:
            # Give people time to get ready
            givePrepTime()
        
                        # Make the photo name
            fileName = 'Photo-' + str( photoNumber ) + '.jpg'

            # Take the photo
            camera.capture( fileName )

            photoNumber += 1

        showImage( PROCESSING_IN_PROGRESS_IMAGE_PATH )

        camera.stop_preview()
       
    print '...Starting image processing'
 
    # Create the animated GIF using the GraphicsMagick package
    args =              \
        [               \
        'gm',           \
        'convert',      \
        '-delay',       \
        '100',          \
        '*.jpg',        \
        'session.gif'   \
        ]
       
    command = subprocess.Popen( args, stdout = subprocess.PIPE, stderr = subprocess.PIPE )
        
    details, errors = command.communicate()

    if details:
        print '...Image processing details: ' + details
    else:
        saveSessionDetails( sessionPath )

    os.chdir( cwd )

def saveSessionDetails( details ):
     # Append session details to upload info file
    print '...Writing session details to upload info'

def runPhotoUpload():
    # Read upload info file
    print '...Starting file upload'
    showImage( PHOTO_UPLOADING_IMAGE_PATH )

def showImage( path ):
    # Display an image on screen
    print '...Showing image ' + path

def main():
    global exitLoop
    global startSession

    init()

    while not exitLoop:
        if startSession:
            startSession = False

            runPhotoSession()

            runPhotoUpload()

            showImage( ATTRACT_IMAGE_PATH )

            # Photo session complete allow response to the start button
            if not exitLoop:
                GPIO.add_event_detect( START_BTN, GPIO.FALLING, callback = startBtn_Handler, bouncetime = DEBOUNCE_TIME )
        else:
            time.sleep( LOOP_DELAY_TIME )

    exit()

# Run program
main()
