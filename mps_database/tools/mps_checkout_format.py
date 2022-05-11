#This script formats the logs generated by mps_checkout.py
#

import sys
import os
from datetime import datetime, date
import argparse
import json

def process_args(argv):
     parser=argparse.ArgumentParser(description='This script is used to verify the MPS system set points')
     parser.add_argument('-AppID', required=True, type = int, help = 'The MPS app id you are checking out')
     parser.add_argument('-SrcFileLoc', required=True, type = str, help='The directory containing the checkout JSON files')
     parser.add_argument('-LogFileLoc', required=True, type = str, help='The directory where the log files will be written to')
     parser=parser.parse_args()

     return parser

def log_list_to_text(checkoutList):
    if(checkoutList[0] == 1):
        if(checkoutList[1] == checkoutList[2]):
            return "Good"
        else:
            return "User disagrees with program"
    else:
        return "Bad"

def threshold_decode(device, threshold):
    high = log_list_to_text(device['thresholdH'+str(threshold)])
    low = log_list_to_text(device['thresholdL'+str(threshold)])
    highLogic = log_list_to_text(device['logicH'+str(threshold)])
    lowLogic = log_list_to_text(device['logicL'+str(threshold)])

    return str(threshold) + "\t" + high +"\t" +  highLogic +"\t" +  low +"\t" +  lowLogic

def main(argv):
    controls =  process_args(argv)

    with open(controls.SrcFileLoc+ "/" + "App"+str(controls.AppID) + "_checkout.json") as json_file:
        checkoutLog = json.load(json_file)

    formatedLog = 'Report on the checkout of MPS AppID'+str(controls.AppID)+"\n\n"

    formatedLog += "UserInfo\n"
    for key in checkoutLog['UserInfo']:
        formatedLog += key+": "+checkoutLog['UserInfo'][key]+"\n"

    formatedLog += "\n"    

    for device in checkoutLog['AppInfo']['devices']:
        formatedLog += "Working on "+device+"\n"

        thresholdNumber = checkoutLog[device]['ThresholdNum'][0]
        formatedLog += "Threshold Number: " + str(thresholdNumber)
        if(checkoutLog[device]['ThresholdNum'][2]):
            formatedLog += " User Confirmed\n"
        else:
            formatedLog += "User Disagreed\n"

        formatedLog += "Threshold \t High \t High Logic \t Low \t Low Logic\n"

        print("temporary workaround since threshold7 not yet hosted")
        thresholdNumber -= 1

        for threshold in range(thresholdNumber):
            formatedLog += threshold_decode(checkoutLog[device],threshold)
            formatedLog += "\n"

        formatedLog += "\n\n"

    formatedCheckoutFile = open(os.path.join(controls.LogFileLoc, "App"+str(controls.AppID)+"_checkout_format.json"), 'w')

    formatedCheckoutFile.write(formatedLog)

    return 0

if __name__ == "__main__":
    main(sys.argv[1:])
� 2022 GitHub, Inc.
Terms
Privacy
Security
Status
Docs
Contact GitHub
Pricing
API
Training
Blog
About
