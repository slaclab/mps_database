from mps_database.mps_config import MPSConfig, models
from sqlalchemy import func

class MpsName:
    """
    This class helps build PV names for MPS componets.
    """
    def __init__(self, session):
        self.session = session
        self.max_beam_class = self.session.query(func.max(models.BeamClass.number)).one()[0]

    def get_beam_class_severity(self,bc):
        if bc.number >= (self.max_beam_class - 1):
          return 'NO_ALARM'
        elif bc.number in [0,1]:
          return 'MAJOR'
        return 'MINOR'

    def getConditionNameFromID(self,cond_id):
      cond = self.session.query(models.Condition).filter(models.Condition.id == cond_id).one()
      return cond.description

    def getDeviceFromFault(self,fault):
      devices = []
      for fi in fault.inputs:
        devices.append(fi.device)
      if len(devices) > 1:
        print("ERROR: Too many devices, special cases not ready yet!")
        return
      return devices[0]

    def get_device_count(self):
      return self.session.query(models.Device).count()

    def isDeviceAnalog(self,device):
      analog = False
      if type(device) is models.device.AnalogDevice:
        analog = True
      if type(device) is models.device.DigitalDevice:
        if len(device.inputs) == 1:
          for input in device.inputs:
            if input.fault_value == 1:
              analog = True 
      return analog

    def isDeviceReallyAnalog(self,device):
      analog = False
      if type(device) is models.device.AnalogDevice:
        analog = True
      return analog

    def isFastDigital(self,device):
      analog = False

    def getCardFromFault(self,fault):
      device = self.getDeviceFromFault(fault)
      return device.card

    def getInputsFromDevice(self,device,fault=None):
      inputs = []
      if type(device) is models.device.DigitalDevice:
        for input in device.inputs:
          inputs.append(self.getInputPvFromChannel(input.channel))
      if type(device) is models.device.AnalogDevice:
        if fault is not None:
          inputs.append('{0}:{1}'.format(self.getDeviceName(device),fault.name))
        else:
          print("ERROR: Cannot build input name for analog fault.  Please specifiy fault name")
      return inputs
        

    def getInputPvFromChannel(self,channel):
        """
        Builds the PV base name for the specified DeviceInput Channel (see getDeviceInputBaseName())

        :type deviceInputId: int
        :rtype :string
        """
        return "{0}:{1}".format(self.getDeviceInputBaseName(channel.device_input),channel.name.split(":")[-1])

    def getDeviceName(self, device):
        """
        Builds the PV base name for the specified DeviceInput. The PV
        name of the DeviceInput is composed of

          <DeviceType.name> : <Device.area> : <Device.position>

        Example: PROF:GUNB:753

        The full PV name for the DeviceInput requires the fourth field, which
        is given by the Channel associated with the DeviceInput.

        :type deviceInput: models.DeviceInput 
        :rtype :string
        """
        if device.device_type.name in ['WDOG','EPICS']:
          base_name = ":".join(device.name.split(":")[1:-1])
        else:
          base_name = ":".join(device.name.split(":")[1:])
        return base_name

    def getBlmType(self,device):
        if device.device_type.name in ['BLM','CBLM','LBLM']:
          type = device.name.split(':')[1]
        else:
          type = device.device_type.name
        return type

    def getDeviceInputBaseName(self, deviceInput):
        """
        Builds the PV base name for the specified DeviceInput. The PV
        name of the DeviceInput is composed of

          <DeviceType.name> : <Device.area> : <Device.position>

        Example: PROF:GUNB:753

        The full PV name for the DeviceInput requires the fourth field, which
        is given by the Channel associated with the DeviceInput.

        :type deviceInput: models.DeviceInput 
        :rtype :string
        """
        base_name = self.getDeviceName(deviceInput.digital_device)
        return base_name

    def getBeamDestinationNameFromId(self, beamDestinationId):
        beamDestination = self.session.query(models.BeamDestination).filter(models.BeamDestination.id==beamDestinationId).one()
        
        return self.getBeamDestinationName(beamDestination)

    def getBeamDestinationName(self, beamDestination):
        return "$(BASE):" + beamDestination.name.upper() + "_PC"

    def getFaultNameFromId(self, faultId):
        fault = self.session.query(models.Fault).filter(models.Fault.id==faultId).one()
        return self.getFaultName(fault)

    def getBaseFaultName(self, fault):
        device = self.getDeviceFromFault(fault)
        base = self.getDeviceName(device)

        return base + ":" + fault.name

    def getFaultName(self, fault):
        base = self.getBaseFaultName(fault)
        if base != None:
            return base + "_FLT" + "_SCMPSC"
        else:
            return None

    def getFaultedPVName(self,fault):
        base = self.getBaseFaultName(fault)
        if base != None:
            return base + "_FLT"
        else:
            return None

    def getIgnoredPV(self,fault):
        base = self.getBaseFaultName(fault)
        if base != None:
            return base + "_FLT" + "_IGNORED"
        else:
            return None        

    def getBypassedPV(self, fault):
        base = self.getBaseFaultName(fault)
        if base != None:
            return base + "_FLT" + "_SCBYPS"
        else:
            return None

    def getFaultedDestinations(self, fault):
        base = self.getFaultedPVName(fault)
        beam_dest =  self.session.query(models.BeamDestination).all()

        dest_list = []
        # Order to match preferred order of MPS Displays
        for i in [2, 1, 3, 4, 0, 5]:
            dest_list.append("{}_{}_STATE".format(base, beam_dest[i].name))

        return dest_list

    def getFaultObject(self, fault):

        return FaultObject(fault, parent=self)

    def makeDeviceName(self,string,type,ch=0):
        sub = string.split(":")
        dt = []
        dt.append(type)
        len = 4
        if sub[-1] in ['A','B','AS','BS','AH','BH','A_WF','B_WF']:
          len = 5
        elif sub[-2] in ['A','B','AS','BS','AH','BH','A_WF','B_WF']:
          len = 5
        elif type in ['EPICS','WDOG']:
          len = 5
        more_sub = dt+sub
        ret_name = ":".join(more_sub[:len])
        return ret_name

    def getConditionPV(self, cond):
        prefix = (cond.condition_inputs[0].fault_state.fault
                      .inputs[0].device.card.link_node.get_cn_prefix())
        return f"{prefix}:{cond.name}"

    def getFaultStateName(self, faultState):
#        print 'name for {0} {1} {2}'.format(faultState.id, faultState.device_state.name, faultState.fault.name)
        return self.getBaseFaultName(faultState.fault) + ":" + faultState.device_state.name


class FaultObject:
    def __init__(self, fault: models.fault.Fault, parent: MpsName):
        self.fault = fault
        self.description = fault.description
        self.name = parent.getFaultedPVName(fault)
