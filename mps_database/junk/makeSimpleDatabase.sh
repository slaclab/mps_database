#!/bin/bash
database/add_data.py -v -n --db really_simple.db --file even_simpler/nodes.json
database/add_data.py -v --db really_simple.db --file even_simpler/ignore.json
database/add_data.py -v --db really_simple.db --file even_simpler/logic.json


