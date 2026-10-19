What the README says (broken)

mps_database/README.md:83-103 points at ./import/import-csv.py and database/examples/makeDatabase calls database/initialize_db.py, add_digital_device.py, add_analog_device.py, add_logic.py, add_ignore_device.py. None of those files exist in this checkout, and there is no import/ directory. That example script can't run as written.

What actually exists

The current creation path is a single driver plus CSV→JSON converters:

- mps_database/database/add_data.py — the only loader. -n drops and recreates all tables (MPSConfig.clear_all() in mps_config.py:15), then it calls every add_* method in turn and adds whatever sections are present in the JSON file.
- mps_database/database/convert_crate_csv.py → emits {"link_nodes": [...]}
- mps_database/database/convert_app_csv.py → emits {"cards": [...]}
- mps_database/database/convert_channel_csv.py → emits {"channels": [...]}
- mps_database/database/seed/ — Crates.csv, AppCards.csv, AppTypes.csv, BeamClasses.csv, BeamDestinations.csv
- mps_database/database/examples/ — vac_logic.json, logic_test.json, plus device/ignore CSVs

So, roughly:

cd mps_database            # repo root
conda env create -f environment.yml && conda activate mps-environment
pip install -e .

cd mps_database
python database/convert_crate_csv.py   --csv database/seed/Crates.csv   --dest /tmp/crates.json
python database/convert_app_csv.py     --csv database/seed/AppCards.csv --dest /tmp/cards.json
# first call creates the schema from scratch:
python database/add_data.py -v -n --db mps_config.db --file /tmp/crates.json
python database/add_data.py -v    --db mps_config.db --file /tmp/cards.json
python database/add_data.py -v    --db mps_config.db --file database/examples/vac_logic.json

Then export with python tools/export_all.py --db mps_config.db --dest <out> --template templates — except tools/ has no export_all.py either (it has export_cn.py, export_ln.py, export_yaml.py, export_report.py, …), so that README line is also out of date.

Two real gaps you'll hit

1. Converters write with open(dest, 'a') (append, all three). Re-running onto an existing file produces invalid JSON — delete the dest file between runs.
2. No converter for AppTypes.csv, BeamClasses.csv, BeamDestinations.csv, and add_data.py also wants a central_nodes section that no seed file provides. Those four sections (app_types, beam_classes, beam_destinations, central_nodes) have to be hand-written JSON matching the keys add_data.py reads — e.g. beam_classes needs number, name, integration_window, min_period, total_charge (add_data.py:293-303), but BeamClasses.csv has columns Name,Index,Description,Integration_Window,Total_Charge,Number,Min_Period. The names don't line up automatically.

Also: sqlalchemy isn't installed in your current Python, so nothing here runs until you set up the conda env.

Want me to write the missing converters/JSON for the top-level tables so there's a working end-to-end makeDatabase?