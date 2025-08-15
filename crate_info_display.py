import epics
from epics import caget, caget_many
from pydm import Display
from pydm.widgets import PyDMLabel, PyDMChannel
from qtpy.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel,
    QWidget, QScrollArea, QSpacerItem, QSizePolicy,
    QDialog, QTableWidget, QTableWidgetItem, QHeaderView, QFrame, 
    QCheckBox
)
from qtpy.QtCore import Qt, QTimer
from qtpy.QtGui import QPixmap
from PyQt5.QtWidgets import QTextBrowser

from mps_database.mps_config import MPSConfig
from mps_database.models.crate import Crate
from mps_database.models.link_node import LinkNode

# This class creates a PyDM display for searching and displaying information about MPS Crates and Link Nodes
class LinkNodeInfoDisplay(Display):
    def __init__(self, parent=None, args=None, macros=None):
        super().__init__(parent=parent, args=args, macros=macros)
        
        # Timer to delay execution of search while typing
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(250)
        self.search_timer.timeout.connect(self.search_crate)

        self.current_lnid = None

        # GUI window setup
        self.setWindowTitle("Crate Lookup Display")
        self.setMinimumSize(800, 600)

        main_layout = QVBoxLayout()

        # Add SLAC logo to top of GUI
        logo_label = QLabel()
        pixmap = QPixmap("mps_database/templates/templates/SLAC-logo.png")
        if not pixmap.isNull():
            logo_label.setPixmap(pixmap.scaledToWidth(200, Qt.SmoothTransformation))
        else:
            logo_label.setText("Logo not found.")
        logo_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(logo_label)

        # Input for crate location or LNID
        self.crate_location_input = QLineEdit()
        self.crate_location_input.setPlaceholderText("Enter Link Node ID or Crate Location")
        self.crate_location_input.textChanged.connect(self.on_text_changed)
        main_layout.addWidget(self.crate_location_input)

        # Group navigation data
        self.group_chain = []     # List of link nodes in the group
        self.group_index = None   # Index of the current link node in the chain

        # Checkbox to enable PV alarm filtering
        self.pv_checkbox = QCheckBox("Alarm Filter")
        self.pv_checkbox.setChecked(False)
        self.pv_checkbox.stateChanged.connect(self.on_pv_checkbox_toggled)
        main_layout.addWidget(self.pv_checkbox)

        # Navigation buttons (prev/next)
        nav_layout = QHBoxLayout()
        self.prev_button = QPushButton("Previous")
        self.next_button = QPushButton("Next")
        self.prev_button.clicked.connect(self.go_to_previous_lnid)
        self.next_button.clicked.connect(self.go_to_next_lnid)
        self.prev_button.setEnabled(False)
        self.next_button.setEnabled(False)
        nav_layout.addWidget(self.prev_button)
        nav_layout.addWidget(self.next_button)
        main_layout.addLayout(nav_layout)

        # Search and clear buttons
        search_button = QPushButton("Search")
        search_button.clicked.connect(self.search_crate)
        main_layout.addWidget(search_button)

        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(self.clear_fields)
        main_layout.addWidget(clear_button)

        # Scrollable area to display search results
        self.result_area = QScrollArea()
        self.result_area.setWidgetResizable(True)
        self.result_widget = QWidget()
        self.result_layout = QHBoxLayout(self.result_widget)

        # LEFT: Crate list / buttons
        self.left_result_widget = QWidget()
        self.left_result_layout = QVBoxLayout(self.left_result_widget)

        # RIGHT: Channel info, card info, alarm summary
        self.right_result = QWidget()
        self.right_result.setLayout(QVBoxLayout())

        # Add widgets to layout with stretch ratio
        self.result_layout.addWidget(self.left_result_widget, stretch=1)
        self.result_layout.addWidget(self.right_result, stretch=2)

        self.result_area.setWidget(self.result_widget)
        main_layout.addWidget(self.result_area)

        self.setLayout(main_layout)

        # Perform initial search on startup
        self.search_crate()


    # Start search when text changes, with a small delay to debounce input
    def on_text_changed(self, text):
        self.search_timer.start()

    # Clear input and refresh search when alarm filter checkbox is toggled
    def on_pv_checkbox_toggled(self, state):
        self.crate_location_input.setText("")
        self.search_crate()

    # Get next LNID greater than current one
    def get_next_lnid(self, current_lnid, session):
        result = (
            session.query(LinkNode.lnid)
            .filter(LinkNode.lnid > current_lnid)
            .order_by(LinkNode.lnid.asc())
            .first()
        )
        return result[0] if result else None

    # Get previous LNID less than current one
    def get_previous_lnid(self, current_lnid, session):
        result = (
            session.query(LinkNode.lnid)
            .filter(LinkNode.lnid < current_lnid)
            .order_by(LinkNode.lnid.desc())
            .first()
        )
        return result[0] if result else None

    # Navigate to next LNID in the current group
    def go_to_next_lnid(self):
        if self.group_chain and self.group_index is not None:
            if self.group_index < len(self.group_chain) - 1:
                self.group_index += 1
                next_ln = self.group_chain[self.group_index]
                self.search_crate_by_exact_lnid(next_ln.lnid)

    # Navigate to previous LNID in the current group
    def go_to_previous_lnid(self):
        if self.group_chain and self.group_index is not None:
            if self.group_index > 0:
                self.group_index -= 1
                prev_ln = self.group_chain[self.group_index]
                self.search_crate_by_exact_lnid(prev_ln.lnid)

    # Clear the input and rerun the search
    def clear_fields(self):
        self.crate_location_input.clear()
        self.search_crate()

    # Return all crates from the database
    def get_all_crates(self, session):
        return session.query(Crate).join(Crate.link_node).order_by(LinkNode.lnid.asc()).all()

    # Clear all widgets from the left-side result layout
    def clear_left_result(self):
        while self.left_result_layout.count():
            child = self.left_result_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def search_by_location(self, location, session):
        return session.query(Crate).filter(Crate.location.ilike(location)).first()
        
    # Search crate by exact Link Node ID
    def search_crate_by_exact_lnid(self, lnid):
        try:
            config = MPSConfig(filename="/sdf/home/j/jmock/mps_configuration/test.db")
            session = config.get_session()
            crate = (
                session.query(Crate)
                .join(Crate.link_node)
                .filter(LinkNode.lnid == lnid)
                .first()
            )
            if crate:
                self.current_lnid = str(lnid)  # Store LNID as string for consistency
                self.crate_location_input.setText(crate.get_full_location())  # Populate input with location
                self.search_crate()  # Re-run search with new value
                self.update_nav_buttons_group()  # Refresh navigation buttons
        except Exception as e:
            self.left_result_layout.addWidget(QLabel(f"<b>Error during LNID search:</b> {str(e)}"))

    # Search for crates with LNID substring match
    def search_by_lnid(self, query_lnid, session):
        return (
            session.query(Crate)
            .join(Crate.link_node)
            .filter(LinkNode.lnid.ilike(f"%{query_lnid}%"))
            .all()
        )

    # If input is of form 'Group X', find associated crates
    def search_by_group(self, group_text, session):
        try:
            if not group_text.lower().startswith("group"):
                return None
            number = int(group_text.split()[-1])
            group = session.query(LinkNode.group.property.mapper.class_).filter_by(number=number).first()
            if group and group.link_nodes:
                for node in group.link_nodes:
                    if node.crate:
                        return node.crate
            return None
        except Exception:
            return None

    # Broad search for partial matches in location or LNID fields
    def search_by_partial_location_or_lnid(self, query_text, session):
        return (
            session.query(Crate)
            .join(Crate.link_node)
            .filter(
                (Crate.location.ilike(f"%{query_text}%")) |
                (LinkNode.lnid.ilike(f"%{query_text}%"))
            )
            .all()
        )

    # Decide which search method to use based on user input
    def check_query_type(self, query_text, session):
        query_text = query_text.strip()

        # Special group search
        if query_text.lower().startswith("group"):
            return self.search_by_group(query_text, session)

        # Exact crate location
        crate = self.search_by_location(query_text, session)
        if crate:
            return crate

        # Partial location or LNID search
        partial_matches = self.search_by_partial_location_or_lnid(query_text, session)
        if partial_matches:
            return partial_matches

        # Alarm-only channel name search (if filter is enabled)
        if self.pv_checkbox.isChecked():
            channel_matches = self.search_by_channel_name(query_text, session)
            if channel_matches:
                return channel_matches

        return []  # No matches found

    # Update navigation buttons depending on position in group chain
    def update_nav_buttons_group(self):
        if self.group_chain and self.group_index is not None:
            self.prev_button.setEnabled(self.group_index > 0)
            self.next_button.setEnabled(self.group_index < len(self.group_chain) - 1)
        else:
            self.prev_button.setEnabled(False)
            self.next_button.setEnabled(False)

    # Search by channel name across all crates/cards/channels
    def search_by_channel_name(self, query_text, session):
        try:
            matched_crates = set()
            results = []

            crates = session.query(Crate).join(Crate.link_node).all()
            for crate in crates:
                for card in getattr(crate, 'cards', []):
                    for ch in getattr(card, 'channels', []):
                        if query_text.lower() in getattr(ch, 'name', '').lower():
                            if crate not in matched_crates:
                                matched_crates.add(crate)
                                results.append(crate)
            return results
        except Exception:
            return []

    # Show a dialog displaying the full linked node group chain for a crate
    def show_linked_group_window(self, crate):
        dialog = QDialog(self)
        dialog.setWindowTitle("Linked Group Info")
        dialog.setMinimumSize(1000, 1000)

        main_layout = QHBoxLayout(dialog)

        if hasattr(crate, "link_node") and crate.link_node:
            for node in crate.link_node:
                group = node.group
                if not group:
                    main_layout.addWidget(QLabel(f"Linked Node ID: {node.lnid} (no group)"))
                    continue

                dialog.setWindowTitle(f"Linked Group Info - Group {group.number}")
                first_link_nodes = group.find_first_lns()

                if not first_link_nodes:
                    main_layout.addWidget(QLabel("No starting link node found."))
                    continue

                if len(first_link_nodes) > 1:
                    # Group has a split (e.g., two start points)
                    split_lns = group.find_split_lns()
                    split_lnids = {ln.lnid for ln in split_lns}
                    if len(split_lns) > 1:
                        main_layout.addWidget(QLabel("<b>Error:</b> Multiple split points not supported yet."))
                        continue

                    # Build both chains
                    chain0 = group.build_ln_chain(first_link_nodes[0])
                    len0 = chain0['length']
                    chain1 = group.build_ln_chain(first_link_nodes[1])
                    len1 = chain1['length'] - 1  # remove duplicate

                    # Helper to build vertical chain of widgets
                    def make_chain_widgets(chain, length):
                        widgets = []
                        for i in range(1, length + 1):
                            ln = chain.get(str(i))
                            if not ln or not ln.crate:
                                continue
                            widget = self.make_crate_info_widget(ln.crate, ln)
                            widget.ln = ln  # Tag widget with node for arrows
                            widgets.append(widget)
                            if i < length:
                                arrow = QLabel("↓")
                                arrow.setAlignment(Qt.AlignCenter)
                                arrow.setStyleSheet("font-size: 18px; color: #555;")
                                widgets.append(arrow)
                        return widgets

                    left_widgets = make_chain_widgets(chain0, len0)
                    right_widgets = make_chain_widgets(chain1, len1)
                    max_rows = max(len(left_widgets), len(right_widgets))

                    # Create 3-column layout (left/right paths + center arrows)
                    left_layout = QVBoxLayout()
                    right_layout = QVBoxLayout()
                    arrow_column = QVBoxLayout()

                    for i in range(max_rows):
                        left_item = left_widgets[i] if i < len(left_widgets) else QLabel(" ")
                        right_item = right_widgets[i] if i < len(right_widgets) else QLabel(" ")
                        left_layout.addWidget(left_item)
                        right_layout.addWidget(right_item)

                        left_ln = getattr(left_item, 'ln', None)
                        right_ln = getattr(right_item, 'ln', None)

                        if (left_ln and left_ln.lnid in split_lnids) or (right_ln and right_ln.lnid in split_lnids):
                            arrow_label = QLabel("←")
                            arrow_label.setAlignment(Qt.AlignCenter)
                            arrow_label.setStyleSheet("font-size: 18px; color: #444; margin: 2px;")
                            arrow_column.addWidget(arrow_label)
                        else:
                            arrow_column.addWidget(QLabel(" "))

                    main_layout.addLayout(left_layout)
                    main_layout.addSpacing(10)
                    main_layout.addLayout(arrow_column)
                    main_layout.addSpacing(10)
                    main_layout.addLayout(right_layout)

                else:
                    # Simple linear group with one start point
                    dialog.setMinimumSize(1000, 600)
                    chain = group.build_ln_chain(first_link_nodes[0])
                    num_links = chain.get('length', 0)
                    for i in range(1, num_links + 1):
                        ln = chain.get(str(i))
                        if not ln or not ln.crate:
                            continue
                        crate_widget = self.make_crate_info_widget(ln.crate, ln)
                        if main_layout.count() > 0:
                            arrow_label = QLabel("➜")
                            arrow_label.setAlignment(Qt.AlignCenter)
                            arrow_label.setStyleSheet("font-size: 24px; color: #555; margin: 0 10px;")
                            main_layout.addWidget(arrow_label)
                        main_layout.addWidget(crate_widget)
        else:
            main_layout.addWidget(QLabel("<i>No linked group found for this crate.</i>"))

        dialog.setLayout(main_layout)
        dialog.show()


    # Build a widget showing crate info (LNID, location, SHM, CPU, and cards)
    def make_crate_info_widget(self, crate, ln):
        layout = QVBoxLayout()

        # Display LNID and basic crate metadata
        layout.addWidget(QLabel(f"<span style='background-color: pink;'><b>LN</b> {ln.lnid}</span>"))
        layout.addWidget(QLabel(f"<b>Crate Location:</b> {crate.get_full_location()}"))
        layout.addWidget(QLabel(f"<b>SHM:</b> {crate.get_nodename()}"))
        layout.addWidget(QLabel(f"<b>CPU:</b> {crate.get_cpu_nodename()}"))

        # Create table for card summary
        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["Slot", "App ID", "Type"])
        table.verticalHeader().setVisible(False)
        table.setRowCount(7)

        cards = sorted(crate.cards, key=lambda card: card.slot) if hasattr(crate, 'cards') else []
        slot_to_card = {card.slot: card for card in cards}

        for row, slot_number in enumerate(range(1, 8)):
            card = slot_to_card.get(slot_number)
            if slot_number == 1:
                table.setItem(row, 0, QTableWidgetItem(str("RTM")))
            else:
                table.setItem(row, 0, QTableWidgetItem(str(slot_number)))

            table.setItem(row, 1, QTableWidgetItem(str(card.number) if card else "---"))
            table.setItem(row, 2, QTableWidgetItem(card.type.name if card and card.type else "---"))

        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(table)

        container = QWidget()
        container.setLayout(layout)
        return container

    # Handle link click from crate info pane (used for "Show Linked Nodes" button)
    def handle_anchor_click(self, url, crate):
        if url.toString() == "show_linked_group":
            self.show_linked_group_window(crate)
            
    # Main search logic: handles input, clears old results, performs search, and builds left/right panels
    def search_crate(self):
        query_text = self.crate_location_input.text().strip()
        query_lower = query_text.lower()

        # Clear previous results on the left side
        self.clear_left_result()
        layout = self.right_result.layout()
        if layout:
            while layout.count():
                child = layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()

        try:
            config = MPSConfig(filename="/sdf/home/j/jmock/mps_configuration/test.db")
            session = config.get_session()
            self.session = session

            # No query = return all crates, otherwise interpret input type
            if not query_text:
                result = self.get_all_crates(session)
            else:
                result = self.check_query_type(query_text, session)

            # If result is a list (many crates), show crate buttons
            if isinstance(result, list):
                if not result:
                    self.left_result_layout.addWidget(QLabel(f"<b>No crates found</b> with '<code>{query_text}</code>'.")) 
                    return

                self.left_result_layout.addWidget(QLabel(f"<b>Results matching</b> '<code>{query_text}</code>' (LN or Location):"))

                # Build a scrollable area with crate buttons
                scroll_area = QScrollArea()
                scroll_area.setWidgetResizable(True)
                scroll_area.setMinimumHeight(300)
                container_widget = QWidget()
                container_layout = QVBoxLayout()
                container_layout.setContentsMargins(5, 5, 5, 5)
                container_layout.setSpacing(4)

                crate_list = result if isinstance(result, list) else [result]
                crate_to_severity = {}  # map of crate to alarm level
                pv_list = []
                crate_pv_map = {}

                # Collect all PVs for bulk alarm querying
                for crate in crate_list:
                    ln = crate.get_ln()
                    if ln:
                        prefix = ln.get_mps_prefix()
                        pv = f"{prefix}:1:STATSUMY.SEVR"  # hardcoded PV suffix
                        pv_list.append(pv)
                        crate_pv_map[pv] = crate

                # Perform bulk alarm fetch
                sev_map = {"NO_ALARM": 0, "MINOR": 1, "MAJOR": 2, "INVALID": 3}
                severities = epics.caget_many(pv_list, as_string=True)

                for pv, sev_str in zip(pv_list, severities):
                    crate = crate_pv_map[pv]
                    severity = sev_map.get(sev_str, 0)
                    crate_to_severity[crate] = severity

                # Build buttons for each crate
                def make_crate_button(crate, severity):
                    location = crate.get_full_location()
                    lnid = crate.get_ln().lnid if crate.get_ln() else "Unknown"

                    severity_colors = {
                        0: "#99ff99",  # green
                        1: "#ffff99",  # yellow
                        2: "#ff9999",  # red
                        3: "#ff99ff"   # magenta
                    }
                    color = severity_colors.get(severity, "#f9f9f9")

                    btn = QPushButton(f"LN {lnid} — {location}")
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            text-align: left;
                            padding: 6px;
                            border: 1px solid #ccc;
                            border-radius: 4px;
                            background-color: {color};
                        }}
                        QPushButton:hover {{
                            background-color: #e6f2ff;
                            border-color: #99ccff;
                        }}
                    """)
                    btn.setCursor(Qt.PointingHandCursor)
                    btn.setFlat(True)
                    btn.clicked.connect(lambda _, loc=location: self.crate_location_input.setText(loc) or self.search_crate())
                    return btn

                # Add crate buttons (filtered if PV filter is checked)
                for crate in crate_list:
                    severity = crate_to_severity.get(crate, 0)
                    if self.pv_checkbox.isChecked() and severity <= 1:
                        continue
                    container_layout.addWidget(make_crate_button(crate, severity))

                container_widget.setLayout(container_layout)
                scroll_area.setWidget(container_widget)
                self.left_result_layout.addWidget(scroll_area)


                # RIGHT SIDE: Only show LN-level alarms
                # If alarm filter is active, show LN alarm summary table on the right
                if self.pv_checkbox.isChecked():
                    table = QTableWidget()
                    table.setColumnCount(2)
                    table.setHorizontalHeaderLabels(["LNID", "Alarm Severity"])
                    table.verticalHeader().setVisible(False)
                    table.setEditTriggers(QTableWidget.NoEditTriggers)
                    table.setShowGrid(True)

                    header = table.horizontalHeader()
                    header.setSectionResizeMode(QHeaderView.Stretch)
                    header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
                    header.setSectionResizeMode(1, QHeaderView.ResizeToContents)

                    # Collect PVs again, map LNID to alarm PV
                    ln_to_prefix = {}
                    for crate in result:
                        ln = crate.get_ln()
                        if ln:
                            try:
                                prefix = ln.get_mps_prefix()
                                ln_to_prefix[ln] = prefix + ":1:STATSUMY.SEVR"
                            except Exception:
                                continue

                    # Fetch severity values
                    pv_list = list(ln_to_prefix.values())
                    sev_values = epics.caget_many(pv_list, as_string=True)

                    severity_map = {"NO_ALARM": 0, "MINOR": 1, "MAJOR": 2, "INVALID": 3}
                    filtered_rows = []

                    for (ln, pv), sev_str in zip(ln_to_prefix.items(), sev_values):
                        sev_num = severity_map.get(sev_str, 0)
                        if sev_num > 1:  # Only show major or invalid
                            filtered_rows.append((ln.lnid, sev_str))

                    # Populate table with LNIDs and their severity
                    table.setRowCount(len(filtered_rows))
                    for row, (lnid, sev) in enumerate(filtered_rows):
                        table.setItem(row, 0, QTableWidgetItem(str(lnid)))
                        table.setItem(row, 1, QTableWidgetItem(sev))

                    # Clear and add to right panel
                    right_layout = self.right_result.layout()
                    if right_layout is not None:
                        while right_layout.count():
                            child = right_layout.takeAt(0)
                            if child.widget():
                                child.widget().deleteLater()
                        right_layout.addWidget(table)
                        
            # Handle a single crate (not a list result)
            crate = result
            self.current_lnid = crate.get_ln().lnid
            self.update_nav_buttons_group()

            # If search was for a group, show group view immediately
            if query_text.lower().startswith("group") and crate:
                self.show_linked_group_window(crate)
                return

            if crate:
                # Basic crate info (left panel)
                self.left_result_layout.addWidget(QLabel("<b><u>Crate Info:</b></u>"))
                self.left_result_layout.addWidget(QLabel(f"<span style='background-color: pink;'><b>Link Node ID:</b> {crate.get_ln().lnid}</span>"))
                self.left_result_layout.addWidget(QLabel(f"<b>Location:</b> {crate.get_full_location()}"))
                self.left_result_layout.addWidget(QLabel(f"<b>CPU:</b> {crate.get_cpu_nodename()}"))
                self.left_result_layout.addWidget(QLabel(f"<b>SHM:</b> {crate.get_nodename()}"))

                # Linked group navigation
                if hasattr(crate, "link_node") and crate.link_node:
                    button = QPushButton("Show Linked Nodes")
                    button.clicked.connect(lambda: self.show_linked_group_window(crate))
                    self.left_result_layout.addWidget(button)

                    for node in crate.link_node:
                        group = node.group
                        if group:
                            first_lns = group.find_first_lns()
                            if first_lns:
                                chain = group.build_ln_chain(first_lns[0])
                                self.group_chain = [chain[str(i)] for i in range(1, chain["length"] + 1)]
                                self.group_index = next((i for i, ln in enumerate(self.group_chain) if ln.lnid == node.lnid), None)
                                self.update_nav_buttons_group()
                            self.left_result_layout.addWidget(QLabel(f"<b>Group Number:</b> {group.number}"))
                            self.left_result_layout.addWidget(QLabel("Crates in Group:"))
                            for ln in group.link_nodes:
                                if ln.crate:
                                    location = ln.crate.get_full_location()
                                    self.left_result_layout.addWidget(QLabel(f" - {location}, LN {ln.lnid}"))
                        else:
                            self.left_result_layout.addWidget(QLabel(f"Linked Node ID: {node.lnid} (no group)"))
                else:
                    self.left_result_layout.addWidget(QLabel("<i>No Link Node associated.</i>"))

                # Display application card info (slot/app/type + real ID PV)
                if hasattr(crate, 'cards') and crate.cards:
                    self.left_result_layout.addWidget(QLabel("<b>Application Cards</b>"))

                    table = QTableWidget()
                    table.setColumnCount(4)
                    table.verticalHeader().setVisible(False)
                    table.setHorizontalHeaderLabels(["Slot", "App ID", "Real ID", "Type"])
                    cards = sorted(crate.cards, key=lambda card: card.slot)
                    slot_to_card = {card.slot: card for card in cards}
                    table.setRowCount(7)

                    for row, slot_number in enumerate(range(1, 8)):
                        card = slot_to_card.get(slot_number)
                        table.setItem(row, 0, QTableWidgetItem("RTM" if row == 0 else str(slot_number)))

                        if card:
                            table.setItem(row, 1, QTableWidgetItem(str(card.number)))
                            table.setItem(row, 3, QTableWidgetItem(card.type.name if card.type else "Unknown"))
                            mps_prefix = card.get_mps_prefix()
                            real_id_suffix = ":DIG_APPID_RBV" if card.slot == 1 else ":APP_ID"
                            pv_name = f"{mps_prefix}{real_id_suffix}"
                            real_id_label = PyDMLabel()
                            real_id_label.channel = pv_name
                            real_id_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                            table.setCellWidget(row, 2, real_id_label)
                        else:
                            for col in range(1, 4):
                                table.setItem(row, col, QTableWidgetItem("---"))

                    table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
                    self.left_result_layout.addWidget(table)
                else:
                    self.left_result_layout.addWidget(QLabel("<i>No cards found for this crate.</i>"))

                # Build right-side channel table with alarm status and query highlighting
                query = self.crate_location_input.text().strip().lower()

                if hasattr(crate, 'cards') and crate.cards:
                    table = QTableWidget()
                    table.setColumnCount(3)
                    table.setHorizontalHeaderLabels(["Slot", "App Number", "Channel Name"])
                    table.verticalHeader().setVisible(False)
                    table.setEditTriggers(QTableWidget.NoEditTriggers)
                    table.setShowGrid(True)

                    header = table.horizontalHeader()
                    header.setSectionResizeMode(QHeaderView.ResizeToContents)
                    header.setStretchLastSection(True)

                    cards = sorted(crate.cards, key=lambda c: c.slot)

                    # First count how many rows we'll need
                    total_rows = 0
                    for card in cards:
                        total_rows += max(len(getattr(card, 'channels', [])), 1)

                    table.setRowCount(total_rows)

                    row_index = 0
                    for card in cards:
                        slot = card.get_slot_text()
                        app_id = card.number
                        channels = getattr(card, 'channels', [])

                        if channels:
                            for ch in channels:
                                ch_name_raw = getattr(ch, 'name', 'Unnamed')
                                ch_name_display = ch_name_raw

                                # Highlight matching query if present in channel name
                                if query and query in ch_name_raw.lower():
                                    start = ch_name_raw.lower().find(query)
                                    end = start + len(query)
                                    ch_name_display = (
                                        ch_name_raw[:start] +
                                        "[[" + ch_name_raw[start:end] + "]]" +
                                        ch_name_raw[end:]
                                    )

                                # Use AlarmColorLabel to display severity
                                label = AlarmColorLabel(ch_name_raw)
                                table.setItem(row_index, 0, QTableWidgetItem(slot))
                                table.setItem(row_index, 1, QTableWidgetItem(str(app_id)))
                                table.setCellWidget(row_index, 2, label)

                                row_index += 1
                        else:
                            # No channels on this card
                            table.setItem(row_index, 0, QTableWidgetItem(slot))
                            table.setItem(row_index, 1, QTableWidgetItem(str(app_id)))
                            table.setItem(row_index, 2, QTableWidgetItem("No channels"))
                            row_index += 1

                    # Clear previous content from right panel and insert table
                    right_layout = self.right_result.layout()
                    if right_layout is not None:
                        while right_layout.count():
                            child = right_layout.takeAt(0)
                            if child.widget():
                                child.widget().deleteLater()

                    right_layout.addWidget(table)
                else:
                    # No application cards present
                    right_layout = self.right_result.layout()
                    if right_layout is not None:
                        while right_layout.count():
                            child = right_layout.takeAt(0)
                            if child.widget():
                                child.widget().deleteLater()

                    right_layout.addWidget(QLabel("No application cards found for this crate."))

        except Exception as e:
            print(f"Error during search: {str(e)}") 
            
    def ui_filename(self):
        return None
        
# Custom QLabel that updates color based on alarm severity PV value
class AlarmColorLabel(QLabel):
    def __init__(self, pvname, parent=None):
        super().__init__(parent)
        self.setText(pvname)
        self.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # Create PyDM channel to monitor .SEVR field of the PV
        self.channel = PyDMChannel(
            address=f"{pvname}.SEVR",
            value_slot=self.alarm_changed
        )
        self.channel.connect()

    # Update label color based on alarm severity code from EPICS.
    def alarm_changed(self, severity_code):
        severity_map = {
            0: "NO_ALARM",
            1: "MINOR",
            2: "MAJOR",
            3: "INVALID"
        }

        severity = severity_map.get(severity_code, "UNKNOWN")

        # Apply color styling based on severity level
        if severity == "NO_ALARM":
            self.setStyleSheet("color: green;")
        elif severity == "MINOR":
            self.setStyleSheet("color: yellow;")
        elif severity == "MAJOR":
            self.setStyleSheet("color: red;")
        elif severity == "INVALID":
            self.setStyleSheet("color: magenta;")
        else:
            self.setStyleSheet("color: gray;")    

