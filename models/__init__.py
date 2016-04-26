from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()

from sqlalchemy import MetaData
meta = MetaData(naming_convention={
        "ix": 'ix_%(column_0_label)s',
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s"
      })

from crate import Crate
from application_card_type import ApplicationCardType
from application_card import ApplicationCard
from channel import DigitalChannel, AnalogChannel
from device_type import DeviceType
from analog_device_type import AnalogDeviceType
from device import Device, DigitalDevice, AnalogDevice
from device import DigitalDevice
from device_state import DeviceState
from device_input import DeviceInput
from fault import Fault
from fault_state import FaultState
from fault_input import FaultInput
from mitigation_device import MitigationDevice
from beam_class import BeamClass
from allowed_class import AllowedClass
from fault_state import DigitalFaultState
from fault_state import ThresholdFaultState
from threshold_fault import ThresholdFault
from threshold_value_map import ThresholdValueMap
from threshold_value import ThresholdValue