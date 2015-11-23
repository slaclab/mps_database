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

from link_node import LinkNode
from link_node_card_type import LinkNodeCardType
from link_node_card import LinkNodeCard
from link_node_channel import LinkNodeChannel
from device import Device
from device_state import DeviceState
from device_input import DeviceInput
from fault import Fault
from fault_state import FaultState
from fault_input import FaultInput
from mitigation_device import MitigationDevice
from beam_class import BeamClass
from allowed_class import AllowedClass