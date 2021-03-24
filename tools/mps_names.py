from mps_config import MPSConfig, models

class MpsName:
    """
    This class helps build PV names for MPS componets.
    """
    def __init__(self, session):
        self.session = session

    def getDeviceInputNameFromId(self, deviceInputId):
        """
        Builds the PV base name for the specified DeviceInput ID (see getDeviceInputBaseName())

        :type deviceInputId: int
        :rtype :string
        """
        deviceInput = self.session.query(models.DeviceInput).filter(models.DeviceInput.id==deviceInputId).one()
        return self.getDeviceInputName(deviceInput)

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
        digitalChannel = self.session.query(models.DigitalChannel).filter(models.DigitalChannel.id==deviceInput.channel_id).one()
        device = self.session.query(models.DigitalDevice).filter(models.DigitalDevice.id==deviceInput.digital_device_id).one()
        if device.measured_device_type_id == None:
            deviceType = self.session.query(models.DeviceType).filter(models.DeviceType.id==device.device_type_id).one()
        else:
            deviceType = self.session.query(models.DeviceType).filter(models.DeviceType.id==device.measured_device_type_id).one()

        return deviceType.name + ":" + device.area + ":" + str(device.position)

    def getDeviceInputName(self, deviceInput):
        """
        Builds the full DeviceInput PV name.
        name of the DeviceInput is composed of

          <DeviceType.name> : <Device.area> : <Device.position> : <Channel.name>

        Example: PROF:GUNB:753:IN_SWITCH

        :type deviceInput: models.DeviceInput 
        :rtype :string
        """
        digitalChannel = self.session.query(models.DigitalChannel).filter(models.DigitalChannel.id==deviceInput.channel_id).one()
        device = self.session.query(models.DigitalDevice).filter(models.DigitalDevice.id==deviceInput.digital_device_id).one()
        if device.measured_device_type_id == None:
            deviceType = self.session.query(models.DeviceType).filter(models.DeviceType.id==device.device_type_id).one()
        else:
            deviceType = self.session.query(models.DeviceType).filter(models.DeviceType.id==device.measured_device_type_id).one()

        return deviceType.name + ":" + device.area + ":" + str(device.position) + ":" + digitalChannel.name

    def getAnalogDeviceNameFromId(self, analogDeviceId):
        """
        Builds the PV for an AnalogDevice.

        :type analogDeviceId: int
        :rtype :string
        """
        analogDevice = self.session.query(models.AnalogDevice).filter(models.AnalogDevice.id==analogDeviceId).one()
        
        return self.getAnalogDeviceName(analogDevice)

    def getAnalogDeviceName(self, analogDevice):
        """
        Builds the PV for an AnalogDevice in the format:

          <DeviceType.name> : <AnalogDevice.area> : <AnalogDevice.position>

        :type analogDevice: models.AnalogDevice
        :rtype :string
        """
        deviceType = self.session.query(models.DeviceType).filter(models.DeviceType.id==analogDevice.device_type_id).one()
        
        return deviceType.name + ":" + analogDevice.area + ":" + str(analogDevice.position)

    def getBypassPv(self):
        return ''

    def getThresholdPv(self, base, table, threshold, integrator, value_type, is_bpm=False):
        """
        Builds the threashold PV for a given combination of table, threshold,
        integrator and type, where:
        * table: 'lc2' for LCLS-II tables
                 'alt' for LCLS-II ALT tables
                 'lc1' for LCLS-I tables
                 'idl' for idle tables (no beam)
        * threshold: 't<0..7>' (for lc1 and idl the only threshold is t0.
        * integrator: 'i<0..4>', if the device is a BPM (is_bpm=True) then
                      'i0'=='x', 'i1'=='y', 'i2'=='tmit'
        * value_type: 'l' or 'h'
        """
        if (is_bpm):
          if (integrator == 'i0'):
            integrator = 'x'
          elif (integrator == 'i1'):
            integrator = 'y'
          elif (integrator == 'i2'):
            integrator = 'tmit'
          else:
            return None

        if (table == 'lc2'):
          pv_name = base + ':' + integrator + '_' + threshold + '_' + value_type
        else:
          pv_name = base + ':' + integrator + '_' + threshold + '_' + table + '_' + value_type

        return pv_name.upper()

    def getBeamDestinationNameFromId(self, beamDestinationId):
        beamDestination = self.session.query(models.BeamDestination).filter(models.BeamDestination.id==beamDestinationId).one()
        
        return self.getBeamDestinationName(beamDestination)

    def getBeamDestinationName(self, beamDestination):
        return "$(BASE):" + beamDestination.name.upper() + "_PC"

    def getFaultNameFromId(self, faultId):
        fault = self.session.query(models.Fault).filter(models.Fault.id==fauldId).one()

        return self.getFaultName(fault)

    def getBaseFaultName(self, fault):
        is_digital = False

        if len(fault.inputs) <= 0:
            print 'ERROR: Fault {0} (id={1}) has no inputs, please fix this error!'.format(fault.name, fault.id)
            return None

#        print 'len: {0}'.format(len(fault.inputs))

        for fault_input in fault.inputs:
#            print 'id={0} bit={1} devid={2}'.format(fault_input.id,fault_input.bit_position, fault_input.device_id)
            if fault_input.bit_position == 0:
                try:
                    device = self.session.query(models.DigitalDevice).filter(models.DigitalDevice.id==fault_input.device_id).one()
#                    print 'Inputs: {0}'.format(len(device.inputs))
                    for input in device.inputs:
                        if input.bit_position == 0:
                            device_input = input
                            is_digital = True
                except:
                    is_digital = False

                if not is_digital:
                    try:
                        device = self.session.query(models.AnalogDevice).filter(models.AnalogDevice.id==fault_input.device_id).one()
                    except:
                        print "Bonkers, device " + str(fault_input.device_id) + " is not digital nor analog - what?!?"
                        #print "Bonkers, device " + str(fault_input.name) + " is not digital nor analog - what?!?"
                        
        if is_digital:
            base = self.getDeviceInputBaseName(device_input)
        else:
            base = self.getAnalogDeviceName(device)

        return base + ":" + fault.name

    def getFaultName(self, fault):
        base = self.getBaseFaultName(fault)
        if base != None:
            return base + "_FLT"
        else:
            return None

    def getConditionName(self, condition):
        return "$(BASE):" + condition.name.upper() + "_COND"

    def getFaultStateName(self, faultState):
#        print 'name for {0} {1} {2}'.format(faultState.id, faultState.device_state.name, faultState.fault.name)
        return self.getBaseFaultName(faultState.fault) + ":" + faultState.device_state.name

    #
    # Figure out the PV base name for the Link Node, given a crate_id. There is
    # one Link Node IOC per ATCA crate. The PV base name is:
    #
    #   MPLN:<LOCA>:MP<NUM>
    #
    # where:
    #   LOCA: is the sector where the crate is installed (e.g. LI00, LI10, LTU...)
    #   NUM: index of the Link Node within LOCA (following LCLS-I convention)
    #        example, for LI01 sector there are four crates:
    #        L2KG01-1925 -> MPLN:LI01:MP01 (lowest elevation within rack)
    #        L2KG01-1931 -> MPLN:LI01:MP02
    #        L2KG01-1937 -> MPLN:LI01:MP03 (highest elevation within rack)
    #        L2KG01-2037 -> MPLN:LI01:MP11
    #
    def getLinkNodePv(self, crate_id):
        return "MPLN:LI00:MP01"
