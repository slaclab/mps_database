from mps_database.mps_config import MPSConfig, models
from sqlalchemy import func, exc
import argparse
import os
import errno
import re
import shutil
import json
from pprint import *

class MpsDbReader:
    """
    This class is used to open a session to the MPS Database,
    making sure that the it is properly closed at the end.

    It is intended to be called in a 'with-as' code block.
    """
    def __init__(self, db_file):
        self.db_file = db_file

    def __enter__(self):
        # Open the MPS database
        self.mps_db = MPSConfig(self.db_file)

        # Return a session to the database
        return self.mps_db.session

    def __exit__(self, exc_type, exc_value, traceback):
        # Close the MPS database
        self.mps_db.session.close()