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

from models.crate import Crate
from models.application_type import ApplicationType
from models.application_card import ApplicationCard
from models.channel import DigitalChannel, DigitalOutChannel, AnalogChannel
from models.device_type import DeviceType
from models.device import Device, MitigationDevice, DigitalDevice, AnalogDevice
from models.device import DigitalDevice
from models.device_state import DeviceState
from models.device_input import DeviceInput
from models.fault import Fault
from models.fault_state import FaultState
from models.fault_input import FaultInput
from models.beam_class import BeamClass
from models.allowed_class import AllowedClass
from models.condition import Condition
from models.ignore_condition import IgnoreCondition
from models.condition_input import ConditionInput
from models.beam_destination import BeamDestination
