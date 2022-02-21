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


from mps_database.models.crate import Crate
from mps_database.models.link_node import LinkNode
from mps_database.models.application_type import ApplicationType
from mps_database.models.application_card import ApplicationCard
from mps_database.models.channel import DigitalChannel, DigitalOutChannel, AnalogChannel
from mps_database.models.device_type import DeviceType
from mps_database.models.device import Device, MitigationDevice, DigitalDevice, AnalogDevice
from mps_database.models.device import DigitalDevice
from mps_database.models.device_state import DeviceState
from mps_database.models.device_input import DeviceInput
from mps_database.models.fault import Fault
from mps_database.models.fault_state import FaultState
from mps_database.models.fault_input import FaultInput
from mps_database.models.beam_class import BeamClass
from mps_database.models.allowed_class import AllowedClass
from mps_database.models.condition import Condition
from mps_database.models.ignore_condition import IgnoreCondition
from mps_database.models.condition_input import ConditionInput
from mps_database.models.beam_destination import BeamDestination
from mps_database.models.groups import LinkNodeGroup
