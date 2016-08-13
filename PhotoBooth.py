#!/usr/bin/env python
# created by coppertop, 2016

import os
import picamera
import pygame
import RPi.GPIO as GPIO
import sys
import subprocess
import time
import io
import yuv2rgb
from picamera import PiCamera
from threading import Thread

class PhotoBooth():
    #---------------------------------------------------------------------------
    # Constants
    #---------------------------------------------------------------------------
    __PREP_TIME = 3
    __DEBOUNCE_TIME = 300
    __LOOP_DELAY_TIME = 0.01

    __NUMBER_OF_PHOTOS = 4

    __ROOT_DIR = '.'
    __ICON_PATH = os.path.join( __ROOT_DIR, 'icons' )
    __CAPTURE_PATH = os.path.join( __ROOT_DIR, 'capture' )
    __ICON_EXT = '.png'

    __PHOTO_RESOLUTION = ( 2592, 1944 )
    __SCREEN_RESOLUTION = ( 800, 480 )

    #---------------------------------------------------------------------------
    # Members
    #---------------------------------------------------------------------------
    __exit = False
    __start = False
    __running = False
    __screen = None
    __camera = None
    __nextEventTime = 0
    __nextEventTimeIncrement = 0
    __event = 0
    __photosTaken = 0
    __photoRootPath = None
    __procThread = None
    __imageProcessingDone = True

    #---------------------------------------------------------------------------
    # Constructor
    #---------------------------------------------------------------------------
    def __init__( self ):
        #
        pygame.init()
        pygame.mouse.set_visible( False )

        size = ( pygame.display.Info().current_w, pygame.display.Info().current_h )

        self.__screen = pygame.display.set_mode( size, pygame.FULLSCREEN )

        self.__camera = picamera.PiCamera()
        self.__camera.resolution = self.__SCREEN_RESOLUTION
        self.__camera.led = False

    #---------------------------------------------------------------------------
    # Public Functions
    #---------------------------------------------------------------------------
    # exit
    #   Do required cleanup
    #---------------------------------------------------------------------------
    def exit( self ):
        if not self.__exit:
            #
            self.__exit = True

    #---------------------------------------------------------------------------
    # start
    #
    #---------------------------------------------------------------------------
    def start( self ):
        if not self.__running:
            #
            self.__nextEventTime = time.time() + 1.0
            self.__event = 0
            self.__photosTaken = 0
            self.__photoRootPath = os.path.join(
                self.__CAPTURE_PATH,
                'session-' + time.strftime( '%Y%m%d-%H%M%S' ) )

            # Check if the sessionPath exists, if not create
            if not os.path.exists( self.__photoRootPath ):
                os.makedirs( self.__photoRootPath )

            self.__procThread = Thread(
                target=self.__runPhotoProcessing )

            self.__start = True

    #---------------------------------------------------------------------------
    # run
    #
    #---------------------------------------------------------------------------
    def run( self ):
        #
        while ( not self.__exit ) or self.__running:
            # Do image capture from the camera and apply chosen effect
            self.__captureStream()

            if self.__start or self.__running:
                # Mark that the session is running
                self.__running = True

                # Clear the start indication
                self.__start = False

                # Take photos
                self.__runPhotoSession()

            if not self.__running:
                self.__runAttract()

            # Update screen
            self.__updateScreen()

        #
        self.__cleanUp()

    #---------------------------------------------------------------------------
    # Private Functions
    #---------------------------------------------------------------------------
    # __captureStream
    #
    #---------------------------------------------------------------------------
    def __captureStream( self ):
        if self.__imageProcessingDone:
            # Create a memory buffer where the captured image can be placed
            stream = io.BytesIO()
            rgb = bytearray( self.__SCREEN_RESOLUTION[0] * self.__SCREEN_RESOLUTION[1] * 3 )
            yuv = bytearray( len( rgb ) / 2 )

            # Capture the image
            self.__camera.capture(
                stream,
                use_video_port=True,
                format='yuv' )

            # Move the image from the IO stream into a buffer
            stream.seek(0)
            stream.readinto( yuv )  # stream -> YUV buffer
            stream.close()

            # Convert from YUV format to RGB
            yuv2rgb.convert(
                yuv,
                rgb,
                self.__SCREEN_RESOLUTION[0],
                self.__SCREEN_RESOLUTION[1] )

            # Mangle the image
            img = pygame.image.frombuffer(
                rgb,
                self.__SCREEN_RESOLUTION,
                'RGB' )

            # Put the captured image as the base layer for the screen
            self.__screen.blit( img, ( 0, 0 ) )

    #---------------------------------------------------------------------------
    # __runPhotoSession
    #
    #---------------------------------------------------------------------------
    def __runPhotoSession( self ):
        # Check if we've exceeded the current event time
        if time.time() > self.__nextEventTime:
            # Advance to the next event
            self.__event += 1

            # Set time of next event
            if self.__event < self.__PREP_TIME:
                # Images update on a once per second basis during countdown
                self.__nextEventTime = time.time() + 1.0
            elif ( self.__event == self.__PREP_TIME ):
                # Only display for 0.25 seconds before we actually take the picture
                self.__nextEventTime = time.time() + 0.25
            elif ( self.__event == ( self.__PREP_TIME + 1 ) ):
                # Just take the picture right now
                self.__nextEventTime = time.time()
            else:
                # Spin through picture we took while image is processing
                self.__nextEventTime = time.time() + 0.25

        if self.__event < self.__PREP_TIME:
            # Load appropriate image for countdown
            secondsRemaining = str( self.__PREP_TIME - self.__event )

            countdownPath = os.path.join(
                self.__ICON_PATH,
                secondsRemaining + self.__ICON_EXT )

            self.__loadImage( countdownPath, ( 0, 0 ) )
        elif ( self.__event == self.__PREP_TIME ):
            # Say cheese
            cheesePath = os.path.join(
                self.__ICON_PATH,
                'Cheese' + self.__ICON_EXT )

            self.__loadImage( cheesePath, ( 0, 160 ) )
        elif ( self.__event == ( self.__PREP_TIME + 1 ) ):
            photoPath = os.path.join(
                self.__photoRootPath,
                'Photo-' + str( self.__photosTaken ) + '.jpg' )

            self.__camera.capture(
                photoPath,
                use_video_port = False,
                format = 'jpeg',
               thumbnail=None)

            self.__photosTaken += 1

            if self.__photosTaken < self.__NUMBER_OF_PHOTOS:
                self.__event = 0

                # Because we're rewinding, we need to do this so the time increment
                # will be correct
                self.__nextEventTime = time.time() + 1.0
            else:
                # Spawn a new thread to do image processing
                try:
                    self.__imageProcessingDone = False

                    self.__procThread.start()
                except:
                    # Processing failed
                    self.__imageProcessingDone = True
        else:
            if not self.__imageProcessingDone:
                if self.__event > ( self.__PREP_TIME + self.__NUMBER_OF_PHOTOS + 1 ):
                    # Not done processing but we've spun through all of the
                    # images go back to the first one now.
                    self.__event = self.__PREP_TIME + 2

                photoNumber = self.__event - ( self.__PREP_TIME + 2 )

                # Spin through the 4 pictures while we're doing the image processing
                # on the other thread
                photoPath = os.path.join(
                    self.__photoRootPath,
                    'Photo-' + str( photoNumber ) + '.jpg' )

                self.__loadImage( photoPath, ( 0, 0 ) )

                procPath = os.path.join(
                    self.__ICON_PATH,
                    'Processing' + self.__ICON_EXT )

                self.__loadImage( procPath, ( 0, 160 ) )
            else:
                # Mark that the session is finished
                self.__running = False
                self.__event = 0

    def __loadImage( self, imagePath_, position_ ):
        # Load an image from the file system
        img = pygame.image.load( imagePath_ )

        # Update the screen with the image and place it where directed
        self.__screen.blit( img, position_ )

    #---------------------------------------------------------------------------
    # __runPhotoUpload
    #
    #---------------------------------------------------------------------------
    def __runPhotoProcessing( self ):
        # Create the animated GIF using the GraphicsMagick package
        args =                                                  \
            [                                                   \
            'gm',                                               \
            'convert',                                          \
            '-delay',                                           \
            '100',                                              \
            os.path.join( self.__photoRootPath, '*.jpg' ),      \
            os.path.join( self.__photoRootPath, 'session.gif' ) \
            ]

        command = subprocess.Popen( args, stdout = subprocess.PIPE, stderr = subprocess.PIPE )

        details, errors = command.communicate()

        # Now that we have a .gif let's continue using the thread we were given
        # to push it to the interwebs


        # Indicate that we're done processing
        self.__imageProcessingDone = True

    #---------------------------------------------------------------------------
    # __runAttract
    #
    #---------------------------------------------------------------------------
    def __runAttract( self ):
        # Check if we've exceeded the current event time
        if time.time() > self.__nextEventTime:
            # Advance to the next event
            self.__event += 1

            if self.__event > 24:
                self.__event = 0

            # Update the arrow position every 0.25 seconds
            self.__nextEventTime = time.time() + 0.01

        arrowPath = os.path.join(
            self.__ICON_PATH,
            'Arrow' + self.__ICON_EXT )

        self.__loadImage( arrowPath, ( 380, 120 - ( self.__event * 5 ) ) )

        # For now just display the 'press me' text
        pressMePath = os.path.join(
            self.__ICON_PATH,
            'PressMe' + self.__ICON_EXT )

        self.__loadImage( pressMePath, ( 0, 160 ) )

    #---------------------------------------------------------------------------
    # __updateScreen
    #
    #---------------------------------------------------------------------------
    def __updateScreen( self ):
        # Draw any needed buttons

        # Update the display
        pygame.display.update()

    #---------------------------------------------------------------------------
    # __cleanUp
    #
    #---------------------------------------------------------------------------
    def __cleanUp( self ):
        # Turn off the camera
        self.__camera.close()

if __name__ == "__main__":
    print("Call module through methods")
    exit(1)
