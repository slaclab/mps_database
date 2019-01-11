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
from threshold4 import Threshold4
from threshold5 import Threshold5
from threshold6 import Threshold6
from threshold7 import Threshold7
from threshold_alt0 import ThresholdAlt0
from threshold_alt1 import ThresholdAlt1
from threshold_alt2 import ThresholdAlt2
from threshold_alt3 import ThresholdAlt3
from threshold_alt4 import ThresholdAlt4
from threshold_alt5 import ThresholdAlt5
from threshold_alt6 import ThresholdAlt6
from threshold_alt7 import ThresholdAlt7
from threshold_lc1 import ThresholdLc1
from threshold_idl import ThresholdIdl

from threshold0_history import Threshold0History
from threshold1_history import Threshold1History
from threshold2_history import Threshold2History
from threshold3_history import Threshold3History
from threshold4_history import Threshold4History
from threshold5_history import Threshold5History
from threshold6_history import Threshold6History
from threshold7_history import Threshold7History
from threshold_alt0_history import ThresholdAlt0History
from threshold_alt1_history import ThresholdAlt1History
from threshold_alt2_history import ThresholdAlt2History
from threshold_alt3_history import ThresholdAlt3History
from threshold_alt4_history import ThresholdAlt4History
from threshold_alt5_history import ThresholdAlt5History
from threshold_alt6_history import ThresholdAlt6History
from threshold_alt7_history import ThresholdAlt7History
from threshold_history_lc1 import ThresholdHistoryLc1
from threshold_history_idl import ThresholdHistoryIdl

from device import Device
