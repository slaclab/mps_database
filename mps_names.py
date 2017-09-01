from mps_config import MPSConfig, models

class MpsName:
    def __init__(self, session):
        self.session = session

    def getDeviceInputNameFromId(self, deviceInputId):
        deviceInput = self.session.query(models.DeviceInput).filter(models.DeviceInput.id==deviceInputId).one()
        return self.getDeviceInputName(deviceInput)

    def getDeviceInputBaseName(self, deviceInput):
        digitalChannel = self.session.query(models.DigitalChannel).filter(models.DigitalChannel.id==deviceInput.channel_id).one()
        device = self.session.query(models.DigitalDevice).filter(models.DigitalDevice.id==deviceInput.digital_device_id).one()
        if device.measured_device_type_id == None:
            deviceType = self.session.query(models.DeviceType).filter(models.DeviceType.id==device.device_type_id).one()
        else:
            deviceType = self.session.query(models.DeviceType).filter(models.DeviceType.id==device.measured_device_type_id).one()

        return deviceType.name + ":" + device.area + ":" + str(device.position)

    def getDeviceInputName(self, deviceInput):
        digitalChannel = self.session.query(models.DigitalChannel).filter(models.DigitalChannel.id==deviceInput.channel_id).one()
        device = self.session.query(models.DigitalDevice).filter(models.DigitalDevice.id==deviceInput.digital_device_id).one()
        if device.measured_device_type_id == None:
            deviceType = self.session.query(models.DeviceType).filter(models.DeviceType.id==device.device_type_id).one()
        else:
            deviceType = self.session.query(models.DeviceType).filter(models.DeviceType.id==device.measured_device_type_id).one()

        return deviceType.name + ":" + device.area + ":" + str(device.position) + ":" + digitalChannel.name

    def getAnalogDeviceNameFromId(self, analogDeviceId):
        analogDevice = self.session.query(models.AnalogDevice).filter(models.AnalogDevice.id==analogDeviceId).one()
        
        return self.getAnalogDeviceName(analogDevice)

    def getAnalogDeviceName(self, analogDevice):
        deviceType = self.session.query(models.DeviceType).filter(models.DeviceType.id==analogDevice.device_type_id).one()
        
        return deviceType.name + ":" + analogDevice.area + ":" + str(analogDevice.position)

    def getMitigationDeviceNameFromId(self, mitigationDeviceId):
        mitigationDevice = self.session.query(models.MitigationDevice).filter(models.MitigationDevice.id==mitigationDeviceId).one()
        
        return self.getMitigationDeviceName(mitigationDevice)

    def getMitigationDeviceName(self, mitigationDevice):
        return "$(BASE):" + mitigationDevice.name.upper() + "_PC"

    def getFaultNameFromId(self, faultId):
        fault = self.session.query(models.Fault).filter(models.Fault.id==fauldId).one()

        return self.getFaultName(fault)

    def getFaultName(self, fault):
        for fault_input in fault.inputs:
            if fault_input.bit_position == 0:
                is_digital = True
                try:
                    device = self.session.query(models.DigitalDevice).filter(models.DigitalDevice.id==fault_input.device_id).one()
                    for input in device.inputs:
                        if input.bit_position == 0:
                            device_input = input
#                    print device.name
                except:
                    #print "Device " + str(fault_input.device_id) + " is not digital"
                    is_digital = False

                if not is_digital:
                    try:
                        device = self.session.query(models.AnalogDevice).filter(models.AnalogDevice.id==fault_input.device_id).one()
                    except:
                        print "Bonkers, device " + str(fault_input.device_id) + " is not digital nor analog - what?!?"
                        
        if is_digital:
            base = self.getDeviceInputBaseName(device_input)
        else:
            base = self.getAnalogDeviceName(device)

        return base + ":" + fault.name + "_FLT"
