#This script will check that all thresholds for an app id are corectly functioning
#The user will then check that the screen shows the expected ouput
#

import sys
import os
from datetime import datetime, date
import time
import argparse
import epics as e
import json

def process_args(argv):
     parser=argparse.ArgumentParser(description='This script is used to verify the MPS system set points')
     parser.add_argument('-AppID', required=True, type = int, help = 'The MPS app id you are checking out')
     parser.add_argument('-SrcFileLoc', required=True, type = str, help='The directory containing the checkout JSON files')
     parser.add_argument('-LogFileLoc', required=True, type = str, help='The directory where the log files will be written to')
     parser.add_argument('-UserName', required=True, type = str, help='Your username')
     parser.add_argument('-FirstName',required=True, type = str)
     parser.add_argument('-LastName',required=True, type = str)
     parser.add_argument('-Auto',required=False, type = str, choices=['True','False'])
     parser=parser.parse_args()
     
     return parser
     
def query_yes_no(question, bypass):
    if(bypass):
        return True
    valid = {"yes": True, "y": True, "no": False, "n": False}
    prompt = " [y/n] "

    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower()
        if choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' " "(or 'y' or 'n').\n")

def tell_user_fault():
    print("Thanks you for confirming this problem has been logged")
    
def enable_thresholds(thresholdCount, device, table, mode):
    for threshold in range(thresholdCount-1, -1, -1):
        e.caput(device+'_T'+str(threshold)+'_'+table+'_EN',mode) 
    
def set_thresholds_safe(thresholdCount, device, safeMargin, table):
    for threshold in range(thresholdCount-1, -1, -1):
        currentValue = e.caget(device)
        safeSetPoint = (safeMargin+10*threshold)*abs(currentValue)
            
        e.caput(device+'_T'+str(threshold)+'_'+table,safeSetPoint)
        
def test_threshold(thresholdCount, safeMargin, testMargin, device, table, logDict ,skipUser):
    for threshold in range(thresholdCount-1, -1, -1):  
        currentValue = e.caget(device)
        safeSetPoint = (safeMargin+10*threshold)*abs(currentValue)
        testSetPoint = (testMargin+10*threshold)*abs(currentValue)
            
        print(device+'_T'+str(threshold)+'_'+table)
        #test High set point
        e.caput(device+'_T'+str(threshold)+'_'+table,-testSetPoint, wait=True) 
            
        time.sleep(2)
        thresholdState = e.caget(device+'_T'+str(threshold)+'_SCMPSC', use_monitor=False)
        logicState = e.caget(device+'_LINAC_LOGIC', use_monitor=False)
        if((query_yes_no("Is "+str(device)+' threshold '+str(threshold)+' in state IS_EXCEDED',skipUser)) and thresholdState):
            logDict['threshold'+table+str(threshold)] = [1,1,1] 
        elif(not(thresholdState)):
            tell_user_fault()
            logDict['threshold'+table+str(threshold)] = [0,1,1] 
        else:
            if(query_yes_no('Are you looking at '+device+'_T'+str(threshold),skipUser)):
                tell_user_fault()
                logDict['threshold'+table+str(threshold)] = [1,1,0]
            else:
                if(query_yes_no("Confirm "+str(device)+' threshold '+str(threshold)+' in state IS_EXCEDED',skipUser)):
                    logDict['threshold'+table+str(threshold)] = [1,1,1]
                else:
                    tell_user_fault()
                    logDict['threshold'+table+str(threshold)] = [1,1,0]        
                    
        if((query_yes_no("Is "+device+'_LINAC_LOGIC in state: B'+ str(threshold),skipUser)) and ((thresholdCount-threshold)==logicState)):
            logDict['logic'+table+str(threshold)] = [1,1,1]
        elif(not((thresholdCount-threshold)==logicState)):
            tell_user_fault()
            logDict['logic'+table+str(threshold)] = [0,1,1]
        else:
            if(query_yes_no('Are you looking at '+device+'_LINAC_LOGIC',skipUser)):
                tell_user_fault()
                logDict['logic'+table+str(threshold)] = [1,1,0]
            else:
                if(query_yes_no("Confirm "+device+'_LINAC_LOGIC is in state: B'+ str(threshold),skipUser)):
                    logDict['logic'+table+str(threshold)] = [1,1,1]
                else:
                    tell_user_fault()
                    logDict['logic'+table+str(threshold)] = [1,1,0]
     

def main(argv):
    controls =  process_args(argv)
    
    if(controls.Auto == 'True'):
        skip = True
    else:
        skip = False
    
    with open(controls.SrcFileLoc+ "/" + "App"+str(controls.AppID) + "_checkout.json") as json_file:
        appInfo = json.load(json_file)
   
    checkOutLog = {"UserInfo":{'DateTime':datetime.now().strftime("%d/%m/%Y %H:%M:%S"),'UserName':controls.UserName, 'FirstName': controls.FirstName, 'LastName': controls.LastName},
                   "AppInfo": {'AppID': controls.AppID, 'devices':appInfo['devices']}}
                   
    #add software and firmware version to App info
    #add appid related things enable the whole device to chekcout and log
    #each item checked has a list [value of bool, computer check, person check] 1 is considered normal 0 is considered fault
                              
    print(checkOutLog)
    print("Checking out mps device: ", controls.AppID)#, " with software version ", softwareVersion, "\n")
    
    for device in appInfo['devices']:
        deviceFault = False
        deviceLog = {}
        
        print("\n\nWorking on device: ", device)
        
        #verify threshold count
        thresholdCount = e.caget(device+'_THR_CNT')
        confirmScreen = False
        while(not(confirmScreen)):
            if(query_yes_no("Verify for device "+str(device)+ " threshold count = "+ str(thresholdCount),skip)):
                deviceLog['ThresholdNum']= [thresholdCount, 1,1]
                confirmScreen = True
            elif(query_yes_no("Verify you are looking at the display for: "+ device),skip):
                tell_user_fault()
                deviceLog['ThresholdNum']= [thresholdCount, 1,0]
                deviceFault = True
                break    
            else:
                print("Please open the display for ", device)
    
        if(not(deviceFault)):   
            print("Setting all thresholds to non fault state")
            
########### ########### ########### ########### ########### ########### ########### ########### ########### ########### ###########            
            #temporary workaround since threshold 7 PVs are not hosted
            if(thresholdCount == 8):
               thresholdCount -= 1
########### ########### ########### ########### ########### ########### ########### ########### ########### ########### ###########               
          
            enable_thresholds(thresholdCount, device, 'H', 1)
            enable_thresholds(thresholdCount, device, 'L', 1)
          
            safeMargin = 1000
            testMargin =500        
         
            set_thresholds_safe(thresholdCount, device, safeMargin, 'H')        
            set_thresholds_safe(thresholdCount, device, -safeMargin, 'L') 
            
            
            time.sleep(2)
            logicState = e.caget(device+'_LINAC_LOGIC', use_monitor=False)
            confirmAllInBounds = False
            while(not(confirmAllInBounds)):   
                if((query_yes_no("Is "+str(device)+' in state IS_OK for all thresholds',skip))and(logicState==0)):
                    deviceLog['AllThreshold'] = [1, 1, 1]
                    confirmAllInBounds = True
                elif(not(logicState==0)):
                    deviceLog['AllThreshold'] = [0, 1, 1]
                    tell_user_fault()
                    break
                else:
                    if(query_yes_no('Are you looking at '+device+'_LINAC_LOGIC',skip)):
                        tell_user_fault()
                        deviceLog['AllThreshold'] = [1, 1, 0]
                    else:
                        if(query_yes_no("Confirm "+device+'_LINAC_LOGIC is in state: B'+ str(threshold),skip)):
                            deviceLog['AllThreshold'] = [1, 1, 1]
                        else:
                            tell_user_fault()
                            deviceLog['AllThreshold'] = [1, 1, 0]

            thresholdFault = False
            
            #test the standard table high limits   
            print("Testing high thresholds for device: ", device)
            test_threshold(thresholdCount, safeMargin, testMargin, device, 'H', deviceLog, skip)
        
            print("Thank you for checking out the high thresholds")
            print("We will now test the low thresholds\n")
        
            print("Setting the thresholds to a safe possition\n")
            set_thresholds_safe(thresholdCount, device, safeMargin, 'H')        
            set_thresholds_safe(thresholdCount, device, -safeMargin, 'L')  
        
            #test standard table low limits 
            print("Testing low thresholds for device: ", device)
            test_threshold(thresholdCount, -safeMargin, -testMargin, device, 'L', deviceLog, skip)
            
            print(deviceLog)
            
            checkOutLog[device] = deviceLog
            deviceLog={}
        
            print("Thank you for checking out the low thresholds")
            print("You have now checked the entire standard table")
        
        deviceFault = False

    print("MPS AppID ", controls.AppID, " has now been checked out.")
    
    logInfo = json.dumps(checkOutLog)
    
    checkOutFile = open(os.path.join(controls.LogFileLoc, "App"+str(controls.AppID)+"_checkout.json"), 'w')
    
    checkOutFile.write(logInfo)

    print("A checkout file named: ", "App"+str(controls.AppID)+"_checkout.json", " has been written to: ", controls.LogFileLoc)
    return 0
                    
 
    
if __name__ == "__main__":
    main(sys.argv[1:])
