import requests
import json
import array
import socket
import asyncio
import logging
import threading
import time
import urllib3
import os
from pathlib import Path
from http import HTTPStatus

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger('RestfulAPIBase')
# Uncomment following line to enable verbose rest/http logging...
#logging.basicConfig(level=logging.DEBUG, format='%(name)s: %(message)s', )


class RestAPIException(Exception):
  def __init__(self, ErrorMsg):
    self.errorMsg = ErrorMsg
    Exception.__init__(self, 'RestAPI Exception Error: %s' % ErrorMsg)
    print('*** RestAPI Exception:', ErrorMsg)

  def GetErrorMsg(self):
    return self.errorMsg


class SubscriptionClient:
  def __init__(self, url, port, token, useTLS):
    self.url = url
    self.port = port
    self.token = token
    self.useTLS = useTLS
    self.logger = logger
    self.abortClient = False
    self.program_running = False


  async def ClientCoroutine(self):
    self.logger.debug('Connecting to %s %d', self.url, self.port)
    self.client_reader, self.client_writer = await asyncio.open_connection(self.url, self.port)
    try:
      if (self.useTLS):
        self.logger.debug('Sending STARTTLS to server.')
        self.client_writer.write("STARTTLS\r\n".encode())
        data = await asyncio.wait_for(self.client_reader.readline(), timeout=10.0)
        if data is None:
          self.logger.debug('Expected STARTTLS, recieved None.')
          return 'Failed to get start TLS'
        else:
          self.logger.debug('Received: %s ', data.decode())

      else:
        self.logger.debug('Sending HELLO to server.')
        self.client_writer.write("HELLO\r\n".encode())
        data = await asyncio.wait_for(self.client_reader.readline(), timeout=10.0)
        if data is None:
          self.logger.debug('Expected HELLO, recieved None.')
          return 'Failed to get HELLO response'
        else:
          self.logger.debug('Received: %s ', data.decode())


      self.logger.debug('Sending security token to server.')
      self.client_writer.write((self.token + "\r\n").encode())

      self.logger.debug('Listening for subscription events...')
      while not self.abortClient:
        try:
          data = await asyncio.wait_for(self.client_reader.readline(), timeout=1)
          if data is not None:
            pdata = json.loads(data.decode())
            #print('>>>>> Raw hash:', pdata, pdata['SID'])
            if pdata['SID'] == 'SID_RT_DESKTOP_RUN_IN_PROGRESS':
              self.program_running = (pdata['SIDvalue'] == '1')
              self.logger.debug('***** Event Program Running: %d', self.program_running)

        except asyncio.TimeoutError:
          pass    # Ignore all timeout errors
        except ConnectionError:
          break
        except (...):
          pass

    finally:
      self.logger.debug('Disconnecting from %s %d', self.url, self.port)
      self.client_writer.close()
      return 'Normal Disconnect'


  def GetProgramIsRunning(self):
    return self.program_running


  def AbortClient(self):
    self.logger.debug('Client abort called.')
    self.abortClient = True


  async def main(self):
    result = await self.ClientCoroutine()

  #
  # This thread function runs the async loop
  #
  def ThreadRoutine(self):
    try:
      logger.debug('Started Async thread.')
      result = asyncio.run(self.main())
      logger.debug('Exiting Async thread with result: ' + str(result))
    except (...):
      pass


#
# RestfulInterface sets up and provides access to Rest API
#
class RestfulInterface:
  def __init__(self):
    try:
      self.init = False
      self.protocol = 'http'
      self.port = 4503
      self.urlString = self.protocol + '://169.254.3.21:' + str(self.port)

      result = requests.post(self.urlString + '/AuthService/Connect', \
          data = '{"username": "0049", \
          "password": "QoALWQ/PxjunlMbrPEBr0ZcLyfcIi3D6DYaNVfKDP/3sANCfJqtnDQm1WsCCryl825lfvacx3B+6UgNlg0K6zA=="}', verify=False)
      if result.status_code != HTTPStatus.OK:
        raise RestAPIException('Failed to get authentication token.')

      self.tokenValue = result.json()['token']
      logger.debug('Token Value: %s', self.tokenValue)
      self.headers = {'token': self.tokenValue}

      # Enable notification subscription to run in progress
      result = requests.post(self.urlString + '/NotificationService/Subscription/SID_RT_DESKTOP_RUN_IN_PROGRESS', \
          headers=self.headers, data='{ "useEvent": false, "useDatastore": true, "mode": 1 }', verify=False)
      logger.debug('Post Notification desktop run status request result: %d', result.status_code)
      if result.status_code != HTTPStatus.OK:
        raise RestAPIException('Failed to subscribe to desktop run status events.')

      # Setup subscription client and start event processing thread
      self.subscriptSocket = SubscriptionClient('169.254.3.21', 4505, self.tokenValue, False)  # True if protocol is 'https' else False
      self.clientThread = threading.Thread(target=self.subscriptSocket.ThreadRoutine)
      self.clientThread.start()

      # We'll run the rest of our commands securely
      self.protocol = 'https'
      self.port = 4504
      self.urlString = self.protocol + '://169.254.3.21:' + str(self.port)

      # Get a json remote command request object
      self.BulkStruct = requests.get(self.urlString + '/DataService/Bulk/SID_WINMAX_BULK_RCRID', headers=self.headers, verify=False)
      if self.BulkStruct.status_code != HTTPStatus.OK:
        raise RestAPIException('Failed to get bulk RCRID.')
      responseJson = self.BulkStruct.json()
      if responseJson is None:
        raise RestAPIException('Failed to get bulk data structure. Structure is empty.')
      if responseJson.get('bulk') == None:
        raise RestAPIException('Bulk data structure has no Json structure. Dictionary ["bulk"] is None.')

      # Indicate that all initialization did succeed
      self.init = True

    except RestAPIException as exc:
      logger.debug('RestAPIException error: %s', exc.GetErrorMsg())
    except ConnectionRefusedError:
      logger.debug('No connection could be made because the target machine actively refused it!')
    except:
      logger.debug('No connection could be made because the target machine actively refused it!')


  def GetPgmStatusMessage(self, pgmStatusNumber):
    statusMsg = ''
    try:
      idx = int(pgmStatusNumber) # This will throw if parameter is NOT a valid number or string type containing a number. ie. '3'
      pgmStatus = ('Uninitialized (0)', 'Started (1)', 'Completed Successful (2)', 'Completed Error (3)', 'Completed Abort (4)', \
                   'Pending (5)', 'Checking Ready (6)', 'Ready Check Failed (7)' )
      statusMsg = pgmStatus[idx] # This will throw if index is out of range
    except:
      statusMsg = 'Unknown (' + str(pgmStatusNumber) + ')'
    return statusMsg


  def DidInitialize(self):
    return self.init


  def Shutdown(self):
    # End client thread
    if self.init and hasattr(self, 'subscriptSocket'):
      self.subscriptSocket.AbortClient()
      result = requests.get(self.urlString + '/AuthService/v1.2/Disconnect', headers=self.headers, verify=False)


  def UnloadAnyFile(self, FileNameFullPath, CommandId=203):
    try:
      # Fill the json remote command request object with program load and run data
      rcrJson = self.BulkStruct.json()
      rcrJson['bulk']['BulkStruct']['dwCmdId'] = CommandId  # UnLoad a file command ID
                                                      # These options only apply to loading a program
      rcrJson['bulk']['BulkStruct']['dValue'][0] = 0  # close all other loaded programs (0 = no, 1 = yes)
      rcrJson['bulk']['BulkStruct']['dValue'][1] = 0  # queue program to run after loading (0 = no, 1 = yes)
      rcrJson['bulk']['BulkStruct']['dValue'][2] = 1  # skip reload if program is already loaded (0 = force reload, 1 = only load if not already loaded)
      rcrJson['bulk']['BulkStruct']['dValue'][3] = 0
      rcrJson['bulk']['BulkStruct']['dValue'][4] = 0
      rcrJson['bulk']['BulkStruct']['dValue'][5] = 0

      # Clear out string section that holds path/filename to load
      sValueLen = len(rcrJson['bulk']['BulkStruct']['sValue'])
      for i in range(0, sValueLen):
        rcrJson['bulk']['BulkStruct']['sValue'][i] = 0

      # Copy path/filename into sValue sting array
      byteFileName = FileNameFullPath.encode('ascii')
      i = 0
      for c in list(byteFileName):
        rcrJson['bulk']['BulkStruct']['sValue'][i] = c
        i += 1

      logger.debug('Completed remote command request json object:')
      logger.debug(json.dumps(rcrJson))

      logger.debug('\nRemote Cmd Request UnLoad A File...')
      result = requests.put(self.urlString + '/DataService/Bulk/SID_WINMAX_BULK_RCRID', headers=self.headers, data=json.dumps(rcrJson), verify=False)
      logger.debug('Remote Cmd Request Result: %s', result)
      if result.status_code != HTTPStatus.OK:
        raise RestAPIException('Failed to put bulk RCRID unload a file: ' + FileNameFullPath)
      else:
        logger.debug('\nRemote Cmd Request UnLoad A File Success: ' + FileNameFullPath)

      logger.debug('Give application some time to process request...')
      time.sleep(3)
      return True

    except RestAPIException as exc:
      logger.debug('RestAPIException error: %s', exc.GetErrorMsg())
      return False


  def LoadAnyFile(self, FileNameFullPath, RunAfterLoading=0, CommandId=42):
    # This instructs application to load any kind of file. Program, NC State, Tool Offsets, etc...
    try:
      # Fill the json remote command request object with program load and run data
      rcrJson = self.BulkStruct.json()
      rcrJson['bulk']['BulkStruct']['dwCmdId'] = CommandId   # Load a file command ID
                                                      # These options only apply to loading a program
      rcrJson['bulk']['BulkStruct']['dValue'][0] = 0  # close all other loaded programs (0 = no, 1 = yes)
      rcrJson['bulk']['BulkStruct']['dValue'][1] = RunAfterLoading  # queue program to run after loading (0 = no, 1 = yes)
      rcrJson['bulk']['BulkStruct']['dValue'][2] = 1  # skip reload if program is already loaded (0 = force reload, 1 = only load if not already loaded)
      rcrJson['bulk']['BulkStruct']['dValue'][3] = 0
      rcrJson['bulk']['BulkStruct']['dValue'][4] = 0
      rcrJson['bulk']['BulkStruct']['dValue'][5] = 0

      # Clear out string section that holds path/filename to load
      sValueLen = len(rcrJson['bulk']['BulkStruct']['sValue'])
      for i in range(0, sValueLen):
        rcrJson['bulk']['BulkStruct']['sValue'][i] = 0

      # Copy path/filename into sValue sting array
      byteFileName = FileNameFullPath.encode('ascii')
      i = 0
      for c in list(byteFileName):
        rcrJson['bulk']['BulkStruct']['sValue'][i] = c
        i += 1

      logger.debug('Completed remote command request json object:')
      logger.debug(json.dumps(rcrJson))

      logger.debug('\nRemote Cmd Request Load A File...')
      result = requests.put(self.urlString + '/DataService/Bulk/SID_WINMAX_BULK_RCRID', headers=self.headers, data=json.dumps(rcrJson), verify=False)
      logger.debug('Remote Cmd Request Result: %s', result)
      if result.status_code != HTTPStatus.OK:
        raise RestAPIException('Failed to put bulk RCRID load a file: ' + FileNameFullPath)
      else:
        logger.debug('\nRemote Cmd Request Load A File Success: ' + FileNameFullPath)

      logger.debug('Give application some time to process request...')
      time.sleep(3)
      return True

    except RestAPIException as exc:
      logger.debug('RestAPIException error: %s', exc.GetErrorMsg())
      return False


  def LoadAndRunProgram(self, ProgramNameFullPath):
    try:
      result = requests.get(self.urlString + '/DataService/Integer/SID_CURRENT_PROGRAM_STATUS', headers=self.headers, verify=False)
      logger.debug('Current Program Status: %s', self.GetPgmStatusMessage(result.json()))
      if result.status_code != HTTPStatus.OK:
        raise RestAPIException('Failed to get current program status.')

      # Load the program and then run it!
      if not self.LoadAnyFile(ProgramNameFullPath, 1):
        return False

      result = requests.get(self.urlString + '/DataService/String/SID_WINMAX_RUN_PROGRAM_NAME', headers=self.headers, verify=False)
      logger.debug('Running Program Name: %s', result.json())
      if result.status_code != HTTPStatus.OK:
        raise RestAPIException('Failed to get running program name.')

      pgmStatus = None
      while True:
        time.sleep(3)
        pgmStatus = self.subscriptSocket.GetProgramIsRunning()
        logger.debug('Pgm Status: ' + ('Running' if pgmStatus else 'Stopped'))
        if not pgmStatus:
          break

      result = requests.get(self.urlString + '/DataService/Integer/SID_CURRENT_PROGRAM_STATUS', headers=self.headers, verify=False)
      logger.debug('Current Program Status: %s', self.GetPgmStatusMessage(result.json()))
      if result.status_code != HTTPStatus.OK:
        raise RestAPIException('Failed to get current program status.')
      logger.debug('End Program Run.\n\n')
      time.sleep(3)
      return True

    except RestAPIException as exc:
      logger.debug('RestAPIException error: %s', exc.GetErrorMsg())
      return False


  def SetMaxFeedOverrides(self):
    try:
      result = requests.put(self.urlString + '/DataService/Double/SID_RT_DESKTOP_FEED_OVR', headers=self.headers, data='{ "data": 150.0 }', verify=False)
      logger.debug('Set Desktop Feed Override to 150%%: %s', result)
      if result.status_code != HTTPStatus.OK:
        raise RestAPIException('Failed to set desktop feed override to 150%.')

      result = requests.put(self.urlString + '/DataService/Double/SID_RT_DESKTOP_RAPID_OVR', headers=self.headers, data='{ "data": 150.0 }', verify=False)
      logger.debug('Set Desktop Rapid Override to 150%%: %s', result)
      if result.status_code != HTTPStatus.OK:
        raise RestAPIException('Failed to set desktop rapid override to 150%.')

      result = requests.put(self.urlString + '/DataService/Double/SID_RT_DESKTOP_TRACKBAR', headers=self.headers, data='{ "data": 5.0 }', verify=False)
      logger.debug('Set Desktop Trackbar to 5: %s', result)
      if result.status_code != HTTPStatus.OK:
        raise RestAPIException('Failed to set desktop trackbar to 5.')

      return True
    except RestAPIException as exc:
      logger.debug('RestAPIException error: %s', exc.GetErrorMsg())
      return False


              ###############################################     Yang's Code     ####################################################


  def IsStopped(self):
    try:
      result=requests.get(self.urlString+"/DataService/Double/SID_RT_AXIS_MOTION_STOPPED",headers=self.headers,verify=False)
      logger.debug("Machine motion stop yielded: %s", result)
      if result.status_code!=HTTPStatus.OK:
        raise RestAPIException("Failed to get machine motion stopped check.")
      return bool(result.json())
    except RestAPIException as exc:
      logger.debug("RestAPIException error: %s",exc.GetErrorMsg())
      return False


  def GetRapidPercentage(self):
    try:
      result=requests.get(self.urlString+"/DataService/Double/SID_RT_RAPID_OVERRIDE_POT",headers=self.headers,verify=False)
      logger.debug("Machine rapid percentage at %s", result)
      if result.status_code!=HTTPStatus.OK:
        raise RestAPIException("Failed to get machine rapid percentage.")
      return float(result.json())
    except RestAPIException as exc:
      logger.debug("RestAPIException error: %s",exc.GetErrorMsg())
      return -99999.99

  
  def GetMachinePositionX(self):
    try:
      result=requests.get(self.urlString+"/DataService/Double/SID_RT_MACHINE_POSITION_X",headers=self.headers,verify=False)
      logger.debug("Machine position is currently at %s along the X-axis", result)
      if result.status_code!=HTTPStatus.OK:
        raise RestAPIException("Failed to get machine position along the X-axis.")
      return float(result.json())
    except RestAPIException as exc:
      logger.debug("RestAPIException error: %s",exc.GetErrorMsg())
      return -99999.99
    

  def GetMachinePositionZ(self):
    try:
      result=requests.get(self.urlString+"/DataService/Double/SID_RT_MACHINE_POSITION_Z",headers=self.headers,verify=False)
      logger.debug("Machine position is currently at %s along the Z-axis", result)
      if result.status_code!=HTTPStatus.OK:
        raise RestAPIException("Failed to get machine position along the Z-axis.")
      return float(result.json())
    except RestAPIException as exc:
      logger.debug("RestAPIException error: %s",exc.GetErrorMsg())
      return -99999.99
    
  def GetAxisXLoad(self):
    try:
      result=requests.get(self.urlString+"/DataService/Integer/SID_RT_SCALED_LOAD_METER_X",headers=self.headers,verify=False)
      logger.debug("X axis at %s", result)
      if result.status_code!=HTTPStatus.OK:
        raise RestAPIException("Failed to get X axis load.")
      return float(result.json())
    except RestAPIException as exc:
      logger.debug("RestAPIException error: %s",exc.GetErrorMsg())
      return -999.999
    

  def GetAxisYLoad(self):
    try:
      result=requests.get(self.urlString+"/DataService/Integer/SID_RT_SCALED_LOAD_METER_Y",headers=self.headers,verify=False)
      logger.debug("Y axis at %s", result)
      if result.status_code!=HTTPStatus.OK:
        raise RestAPIException("Failed to get Y axis load.")
      return float(result.json())
    except RestAPIException as exc:
      logger.debug("RestAPIException error: %s",exc.GetErrorMsg())
      return -999.999
    

  def GetAxisZLoad(self):
    try:
      result=requests.get(self.urlString+"/DataService/Integer/SID_RT_SCALED_LOAD_METER_Z",headers=self.headers,verify=False)
      logger.debug("Z axis at %s", result)
      if result.status_code!=HTTPStatus.OK:
        raise RestAPIException("Failed to get Z axis load.")
      return float(result.json())
    except RestAPIException as exc:
      logger.debug("RestAPIException error: %s",exc.GetErrorMsg())
      return -999.999
    

  def GetSpindleSpeed(self):
    try:
      result=requests.get(self.urlString+"/DataService/Double/SID_RT_SPINDLE_SPEED",headers=self.headers,verify=False)
      logger.debug("Spindle at %s", result)
      if result.status_code!=HTTPStatus.OK:
        raise RestAPIException("Failed to get spindle speed.")
      return float(result.json())
    except RestAPIException as exc:
      logger.debug("RestAPIException error: %s",exc.GetErrorMsg())
      return -999.9
    

  def GetSpindleOrientation(self):
    try:
      result=requests.get(self.urlString+"/DataService/Double/SID_RT_MACHINE_POSITION_S",headers=self.headers,verify=False)
      logger.debug("Spindle at %s", result)
      if result.status_code!=HTTPStatus.OK:
        raise RestAPIException("Failed to get spindle orientation.")
      return ((float(result.json())%1)*360)%360
    except RestAPIException as exc:
      logger.debug("RestAPIException error: %s",exc.GetErrorMsg())
      return -999.999
    

  def GetSpindleLoad(self):
    try:
      result=requests.get(self.urlString+"/DataService/Integer/SID_RT_SCALED_LOAD_METER_S",headers=self.headers,verify=False)
      logger.debug("Spindle at %s", result)
      if result.status_code!=HTTPStatus.OK:
        raise RestAPIException("Failed to get spindle load.")
      return float(result.json())
    except RestAPIException as exc:
      logger.debug("RestAPIException error: %s",exc.GetErrorMsg())
      return -999.999


  def IsCalibrated(self):
    try:
      result=requests.get(self.urlString+"/DataService/Double/SID_RT_CALIBRATED",headers=self.headers,verify=False)
      logger.debug("Check for calibration.")
      print(result.json())
      if result.status_code!=HTTPStatus.OK:
        raise RestAPIException("Failed to check for calibration.")
      return True
    except RestAPIException as exc:
      logger.debug("RestAPIException error: %s",exc.GetErrorMsg())
      return False
    

"""
#----------------------------------------------------------------------
# Check to see if called from command line or from python environment.
#----------------------------------------------------------------------
if __name__ == '__main__':
  # Unit test requires WinMax lathe to be up and waiting for RestAPI connection.
  logging.basicConfig(level=logging.DEBUG, format='%(name)s: %(message)s', )
  from TestAppPaths import TestAppPaths
  testAppPaths = TestAppPaths()
  from TestAppUtils import Logger
  log = Logger(open(testAppPaths.CreateFullPath('RestfulAPIBase.log'), 'w+'))
  from TestAppRegistry import WinMaxDevRegistry
  reg = WinMaxDevRegistry()
  reg.SetValue('TestAppRunRestAPIMode', 'True')

  rest = RestfulInterface()
  if rest.DidInitialize():
    log.EchoToLog('Restful interface initialized.', True);
    if rest.SetMaxFeedOverrides():
      log.EchoToLog('Success setting maximum feed overrides.', True);
    else:
      log.EchoToLog('Failed to set maximum feed overrides!', True);
    log.EchoToLog('Shutting down restful interface.', True);
    rest.Shutdown()
  else:
    log.EchoToLog('Restful interface failed to initialize!', True);

  reg.SetValue('TestAppRunRestAPIMode', 'False')
"""