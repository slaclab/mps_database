import ioc_tools
from mps_config import MPSConfig, models
mps=MPSConfig()
ioc_tools.dump_db_to_yaml(mps,'db.yaml')
