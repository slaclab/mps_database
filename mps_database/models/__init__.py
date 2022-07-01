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


from .crate import Crate
from .link_node import LinkNode
from .application_type import ApplicationType
from .application_card import ApplicationCard
from .channel import DigitalChannel, DigitalOutChannel, AnalogChannel
from .device_type import DeviceType
from .device import Device, MitigationDevice, DigitalDevice, AnalogDevice
from .device import DigitalDevice
from .device_state import DeviceState
from .device_input import DeviceInput
from .fault import Fault
from .fault_state import FaultState
from .fault_input import FaultInput
from .beam_class import BeamClass
from .allowed_class import AllowedClass
from .condition import Condition
from .ignore_condition import IgnoreCondition
from .condition_input import ConditionInput
from .beam_destination import BeamDestination
from .groups import LinkNodeGroup
