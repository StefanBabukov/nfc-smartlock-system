from __future__ import print_function
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

import datetime
from time import strftime
import random
from threading import *
import time
import subprocess

import RPi.GPIO as GPIO
import socket
from smartcard.System import readers
from smartcard.util import toHexString
#from smartcard.ATR import ATR
#from smartcard.CardType import AnyCardType

r = readers()
reader = r[0]

connection = reader.createConnection()

token_timer = 10
tokens_list = []

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# The ID and range of a sample spreadsheet.
SAMPLE_SPREADSHEET_ID = '1fC6ejV3bEvGc5T0h0lZTUbARf5WzWby_fa0Y7XyCUP8'
sheet_range = 'Membership Current!L:L'

# value_input_option = 'USER_ENTERED'
value_input_option = 'RAW'

# --------------------------------------------------------------------------

def sound_feedback(case):
    if case == "open":
        subprocess.Popen(["play","open.wav"], stdin=subprocess.PIPE, stdout = subprocess.PIPE, stderr=subprocess.PIPE)
    if case == "denied":
        subprocess.Popen(["play","denied.wav"], stdin=subprocess.PIPE, stdout = subprocess.PIPE, stderr=subprocess.PIPE)
    if case == "unable":
        subprocess.Popen(["play","unable.wav"], stdin=subprocess.PIPE, stdout = subprocess.PIPE, stderr=subprocess.PIPE)    
    
def internet_connection_check(message = False):
    try:
        socket.create_connection(("www.google.com",80))
        return 200        
    except:
        if message: 
             print("Error fetching the spreadsheet: \n  No internet connection, please reconnect and try again!")
        return 503

def give_access():
    print("User found in Database.")
    print ("GPIO mode set to BCM")
    GPIO.setmode(GPIO.BCM)
    print ("GPIO 21 set to OUTPUT")
    GPIO.setup(21, GPIO.OUT)
    print ("GPIO 21 set to LOW")
    GPIO.output(21, GPIO.LOW)
    print("Access granted for 5 seconds")
    time.sleep(5)
    print ("GPIO cleanup")
    GPIO.cleanup() 

def check_for_token(tag, tokens_list):
    for i in range(len(tokens_list)):
            if tokens_list[i]:
                if tag == tokens_list[i][0]:
                    return True
    return False

def read_rfid():
    tag = []
    try:
         connection.connect()
         COMMAND = [0xFF, 0xCA, 0x00, 0x00, 0x00]
         data, sw1, sw2 = connection.transmit(COMMAND)
         data = toHexString(data).lower().split()
         return data
    
    except:
         return None
         pass

def validate_rfid():
    if internet_connection_check(message = True) == 503:
         while True:
              if internet_connection_check() == 200:
	           print("Internet Connection restored")
                   break
    tokens_list = get_valid_tokens()
    #checking for internet connection

    offline = False
    log_sent = False
    while True:
		
        tag = read_rfid()
        if not log_sent:
            print("\nPLEASE PRESENT A CARD TO THE READER:")
            if offline:
                print("(Offline)\n")
            log_sent=True
        if tag:
            log_sent = False
            print("card_uid is {}".format(tag))

            print(len(tokens_list))
            if check_for_token(tag, tokens_list):
                #token is found
                sound_feedback("open")
                give_access()
                
            else:
                #updating the list and trying again 
                print("Unable to authenticate, fetching the spreadsheet and trying again...")
                sound_feedback("unable")
		if internet_connection_check(message=True) == 200:
		     tokens_list = get_valid_tokens()
                     offline = False
                     if check_for_token(tag, tokens_list):
 	                  sound_feedback("open")
                          give_access()
                     else:
                          sound_feedback("denied")
                          print("\nACCESS DENIED!")
                else:
                    print("Using the old spreadsheet for validation in offline mode.")
		    offline = True
                    time.sleep(1)
# ------------------------------------------------------------------------
def get_credentials():
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'client_secret.json', SCOPES)
            creds = flow.run_local_server()
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('sheets', 'v4', credentials=creds)

    return service

def get_valid_tokens():

    #checking if internet connection is available

    service = get_credentials()
    
    rfid = []
    # Call the Sheets API
    # time.sleep(1)
    print("Getting the valid tokens...")
    for i in range(token_timer, -1, -1):
        mins, secs = divmod(i, 60)
        #print ("Time to retrieve list is {},{}".format(mins, secs))
        time.sleep(1)
        if mins == 0 and secs == 0:
            sheet = service.spreadsheets()
            result = sheet.values().get(spreadsheetId=SAMPLE_SPREADSHEET_ID, range=sheet_range).execute()

            values = result.get('values', [])

            if not values:
                print('No data found.')

            else:
                # tokens_list = values
                tokens_list = []
                for x in range(len(values) - 1):
                     # print (values[0])
                    [rfid.append(element.split()) for element in values[x+1]]
                    tokens_list.append(rfid)
                    rfid = []
            if not tokens_list:
                print("No tokens fetched from the spreadsheet!")
            print("New Validated token are {}".format(tokens_list))
    return tokens_list

# --------------------------------------------------------


def main():
    """Shows basic usage of the Sheets API.
    Prints values from a sample spreadsheet.
    """
    validate_rfid()
    # print('{0} cells updated.'.format(result.get('updatedCells')))


if __name__ == '__main__':
    main()
