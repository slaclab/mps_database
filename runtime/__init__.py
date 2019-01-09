from sqlalchemy.ext.declarative import declarative_base
RuntimeBase = declarative_base()

from sqlalchemy import MetaData
meta = MetaData(naming_convention={
        "ix": 'ix_%(column_0_label)s',
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s"
      })

from threshold0 import Threshold0
from threshold1 import Threshold1
from threshold2 import Threshold2
from threshold3 import Threshold3
from threshold_alt0 import ThresholdAlt0
from threshold_alt1 import ThresholdAlt1
from threshold_alt2 import ThresholdAlt2
from threshold_alt3 import ThresholdAlt3
from device import Device
