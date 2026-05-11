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

from .central_node import CentralNode
from .groups import LinkNodeGroup
from .crate import Crate
from .link_node import LinkNode
from .application_type import ApplicationType
from .application_card import ApplicationCard
from .beam_class import BeamClass
from .beam_destination import BeamDestination
from .channel import Channel,DigitalChannel, AnalogChannel
from .fault_input import FaultInput
from .fault import Fault, IgnoreCondition
from .fault_state import FaultState, Mitigation
