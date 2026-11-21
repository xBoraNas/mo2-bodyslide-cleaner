import os
import json
import shutil
import xml.etree.ElementTree as ET
import mobase

try:
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QIcon
    from PyQt6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox,
        QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
        QHeaderView, QMessageBox, QGroupBox, QRadioButton, QButtonGroup,
        QTabWidget, QWidget, QComboBox
    )
except ImportError:
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QIcon
    from PyQt5.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox,
        QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
        QHeaderView, QMessageBox, QGroupBox, QRadioButton, QButtonGroup,
        QTabWidget, QWidget, QComboBox
    )


class NumericTableWidgetItem(QTableWidgetItem):
    """Size (MB) sütununun alfabetik değil sayısal olarak doğru sıralanmasını sağlar."""
    def __lt__(self, other):
        try:
            return float(self.text()) < float(other.text())
        except ValueError:
            return super().__lt__(other)


class CleanerDialog(QDialog):
    GAME_PROFILES = {
        "Skyrim SE": {
            "presets": [
                ("BHUNP", True),
                ("UUNP", True),
                ("UNP", True),
                ("TBD", True),
                ("TouchedByDibella", True),
                ("COCO", True),
                ("3BA", False),
                ("CBBE", False),
            ],
            "protect_tag": "3ba",
            "placeholder": "e.g. BBL, JaneBod, AtomicBeauty",
        },
        "Fallout 4": {
            "presets": [
                ("FusionGirl", True),
                ("JaneBod", True),
                ("AtomicBeauty", True),
                ("BodyTalk", True),
                ("ZE", True),
                ("3BBB", False),
                ("CBBE", False),
            ],
            "protect_tag": "3bbb",
            "placeholder": "e.g. BBL, EVB, SuperHeroine",
        },
    }

    PROTECTED_NIF_KEYWORDS = (
        "femalebody", "femalefeet", "femalehands",
        "malebody", "malefeet", "malehands",
        "skeleton", "facegeom", "head"
    )

    def __init__(self, organizer: mobase.IOrganizer, parent=None):
        super().__init__(parent)
        self._organizer = organizer
        self._targets = []
        self._orphan_targets = []
        self._config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "BodySlideCleaner_config.json")
        self._config_data = self._read_config_file()
        self._current_game = self._detect_initial_game()

        self.setWindowTitle("BodySlide SliderSet & ShapeData Cleaner")
        self.resize(1050, 660)
        self._setup_ui()
        self._apply_game_profile(self._current_game, load_saved=True)

    def _detect_initial_game(self) -> str:
        try:
            game_name = self._organizer.managedGame().gameName().lower()
            if "fallout" in game_name:
                return "Fallout 4"
        except Exception:
            pass
        return self._config_data.get("last_game", "Skyrim SE")

    def _read_config_file(self) -> dict:
        if not os.path.exists(self._config_path):
            return {}
        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _setup_ui(self):
        root_layout = QVBoxLayout(self)

        # Üst Oyun Seçici Çubuğu
        game_bar = QHBoxLayout()
        game_bar.addWidget(QLabel("<b>Game Profile:</b>"))
        self.game_combo = QComboBox()
        self.game_combo.addItems(list(self.GAME_PROFILES.keys()))
        self.game_combo.setCurrentText(self._current_game)
        self.game_combo.currentTextChanged.connect(self._on_game_changed)
        game_bar.addWidget(self.game_combo)
        game_bar.addStretch()
        root_layout.addLayout(game_bar)

        self.tabs = QTabWidget()
        root_layout.addWidget(self.tabs)

        # =====================================================================
        # SEKME 1: UNUSED BODY TYPES CLEANER
        # =====================================================================
        tab1 = QWidget()
        layout = QVBoxLayout(tab1)

        info_label = QLabel(
            "Select the body types you DO NOT use. The tool will scan all active and inactive mods "
            "inside your MO2 mods folder for matching SliderSets (.osp) and ShapeData folders."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        group_box = QGroupBox("Body Types to Remove")
        group_layout = QVBoxLayout(group_box)

        cb_row = QHBoxLayout()
        self.cb_container_layout = QHBoxLayout()
        self.checkboxes = {}
        cb_row.addLayout(self.cb_container_layout)
        cb_row.addStretch()

        self.select_all_presets_btn = QPushButton("Check All")
        self.select_all_presets_btn.clicked.connect(lambda: self._toggle_all_checkboxes(True))
        cb_row.addWidget(self.select_all_presets_btn)

        self.deselect_all_presets_btn = QPushButton("Uncheck All")
        self.deselect_all_presets_btn.clicked.connect(lambda: self._toggle_all_checkboxes(False))
        cb_row.addWidget(self.deselect_all_presets_btn)

        group_layout.addLayout(cb_row)

        custom_layout = QHBoxLayout()
        custom_layout.addWidget(QLabel("Custom tags (comma-separated):"))
        self.custom_input = QLineEdit()
        custom_layout.addWidget(self.custom_input)
        group_layout.addLayout(custom_layout)

        layout.addWidget(group_box)

        table_control_layout = QHBoxLayout()
        table_control_layout.addWidget(QLabel("Filter:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search mod or file name...")
        self.search_input.textChanged.connect(self._filter_table)
        table_control_layout.addWidget(self.search_input)

        table_control_layout.addStretch()

        self.table_select_all = QPushButton("Select All Visible")
        self.table_select_all.clicked.connect(lambda: self._toggle_table_selection(True))
        self.table_select_all.setEnabled(False)
        table_control_layout.addWidget(self.table_select_all)

        self.table_deselect_all = QPushButton("Deselect All Visible")
        self.table_deselect_all.clicked.connect(lambda: self._toggle_table_selection(False))
        self.table_deselect_all.setEnabled(False)
        table_control_layout.addWidget(self.table_deselect_all)

        layout.addLayout(table_control_layout)

        self.table = QTableWidget(0, 5)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        self.table.setHorizontalHeaderLabels(["", "Mod Name", "Type", "Target Name", "Size (MB)"])

        header = self.table.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        header.setSortIndicatorShown(True)

        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 32)

        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(1, 230)

        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 130)

        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(4, 105)

        header.sectionClicked.connect(self._on_header_clicked)
        self.table.itemChanged.connect(self._update_status_label)
        layout.addWidget(self.table)

        mode_group = QGroupBox("Cleanup Action Mode")
        mode_layout = QHBoxLayout(mode_group)

        self.mode_btn_group = QButtonGroup(self)
        self.radio_delete = QRadioButton("Permanently Delete Files")
        self.radio_backup = QRadioButton("Move to Backup Folder (Safe - MO2\\BodySlideCleaner_Backup)")
        self.radio_backup.setChecked(True)

        self.mode_btn_group.addButton(self.radio_delete)
        self.mode_btn_group.addButton(self.radio_backup)

        self.radio_backup.toggled.connect(self._update_action_button_style)
        self.radio_delete.toggled.connect(self._update_action_button_style)

        mode_layout.addWidget(self.radio_delete)
        mode_layout.addWidget(self.radio_backup)
        mode_layout.addStretch()
        layout.addWidget(mode_group)

        bottom_layout = QHBoxLayout()
        self.status_label = QLabel("Click 'Scan Mods' to preview files to be removed.")
        self.status_label.setStyleSheet("font-weight: bold;")
        bottom_layout.addWidget(self.status_label)

        bottom_layout.addStretch()

        self.scan_btn = QPushButton("Scan Mods")
        self.scan_btn.setStyleSheet("padding: 5px 14px;")
        self.scan_btn.clicked.connect(self._scan_mods)
        bottom_layout.addWidget(self.scan_btn)

        self.clean_btn = QPushButton("Backup Selected Targets")
        self.clean_btn.setEnabled(False)
        self.clean_btn.clicked.connect(self._clean_targets)
        bottom_layout.addWidget(self.clean_btn)

        layout.addLayout(bottom_layout)
        self._update_action_button_style()

        self.tabs.addTab(tab1, "Unused Body Types Cleaner")

        # =====================================================================
        # SEKME 2: ORPHANED OUTPUT CLEANER
        # =====================================================================
        tab2 = QWidget()
        o_layout = QVBoxLayout(tab2)

        o_info = QLabel(
            "Select your BodySlide Output mod (or Overwrite). The tool cross-references generated .nif files "
            "against active mods and SliderSets (.osp) to identify files belonging to disabled or uninstalled mods."
        )
        o_info.setWordWrap(True)
        o_layout.addWidget(o_info)

        out_group = QGroupBox("Target BodySlide Output Folder")
        out_group_layout = QHBoxLayout(out_group)
        out_group_layout.addWidget(QLabel("Output Mod / Folder:"))

        self.output_combo = QComboBox()
        self._populate_output_combo()
        out_group_layout.addWidget(self.output_combo, 1)

        o_layout.addWidget(out_group)

        o_ctrl_layout = QHBoxLayout()
        o_ctrl_layout.addWidget(QLabel("Filter:"))
        self.o_search_input = QLineEdit()
        self.o_search_input.setPlaceholderText("Search filename, source mod, or relative path...")
        self.o_search_input.textChanged.connect(self._filter_orphan_table)
        o_ctrl_layout.addWidget(self.o_search_input)

        o_ctrl_layout.addStretch()

        self.o_select_all = QPushButton("Select All Visible")
        self.o_select_all.clicked.connect(lambda: self._toggle_orphan_selection(True))
        self.o_select_all.setEnabled(False)
        o_ctrl_layout.addWidget(self.o_select_all)

        self.o_deselect_all = QPushButton("Deselect All Visible")
        self.o_deselect_all.clicked.connect(lambda: self._toggle_orphan_selection(False))
        self.o_deselect_all.setEnabled(False)
        o_ctrl_layout.addWidget(self.o_deselect_all)

        o_layout.addLayout(o_ctrl_layout)

        self.o_table = QTableWidget(0, 5)
        self.o_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.o_table.setSortingEnabled(True)
        self.o_table.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.o_table.setHorizontalHeaderLabels(["", "File Name", "Source Mod", "Relative Path", "Size (MB)"])

        o_header = self.o_table.horizontalHeader()
        o_header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        o_header.setSortIndicatorShown(True)

        o_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.o_table.setColumnWidth(0, 32)

        o_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.o_table.setColumnWidth(1, 195)

        o_header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.o_table.setColumnWidth(2, 185)

        o_header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        self.o_table.setColumnWidth(3, 470)

        o_header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.o_table.setColumnWidth(4, 95)

        o_header.sectionClicked.connect(self._on_o_header_clicked)
        self.o_table.itemChanged.connect(self._update_o_status_label)
        o_layout.addWidget(self.o_table)

        o_mode_group = QGroupBox("Cleanup Action Mode")
        o_mode_layout = QHBoxLayout(o_mode_group)

        self.o_mode_btn_group = QButtonGroup(self)
        self.o_radio_delete = QRadioButton("Permanently Delete Files")
        self.o_radio_backup = QRadioButton("Move to Backup Folder (Safe - MO2\\BodySlideCleaner_Backup\\Orphaned_Output)")
        self.o_radio_backup.setChecked(True)

        self.o_mode_btn_group.addButton(self.o_radio_delete)
        self.o_mode_btn_group.addButton(self.o_radio_backup)

        self.o_radio_backup.toggled.connect(self._update_o_action_button_style)
        self.o_radio_delete.toggled.connect(self._update_o_action_button_style)

        o_mode_layout.addWidget(self.o_radio_delete)
        o_mode_layout.addWidget(self.o_radio_backup)
        o_mode_layout.addStretch()
        o_layout.addWidget(o_mode_group)

        o_bottom_layout = QHBoxLayout()
        self.o_status_label = QLabel("Select your BodySlide Output folder and click 'Scan Output'.")
        self.o_status_label.setStyleSheet("font-weight: bold;")
        o_bottom_layout.addWidget(self.o_status_label)

        o_bottom_layout.addStretch()

        self.o_scan_btn = QPushButton("Scan Output")
        self.o_scan_btn.setStyleSheet("padding: 5px 14px;")
        self.o_scan_btn.clicked.connect(self._scan_orphaned_output)
        o_bottom_layout.addWidget(self.o_scan_btn)

        self.o_clean_btn = QPushButton("Move Selected to Backup")
        self.o_clean_btn.setEnabled(False)
        self.o_clean_btn.clicked.connect(self._clean_orphaned_targets)
        o_bottom_layout.addWidget(self.o_clean_btn)

        o_layout.addLayout(o_bottom_layout)
        self._update_o_action_button_style()

        self.tabs.addTab(tab2, "Orphaned Output Cleaner")

    # =========================================================================
    # OYUN PROFİLİ YÖNETİMİ
    # =========================================================================
    def _on_game_changed(self, new_game: str):
        if new_game == self._current_game:
            return
        self._save_config()
        self._current_game = new_game
        self._apply_game_profile(new_game, load_saved=True)

        # Oyun değiştiğinde mevcut tablo sonuçlarını sıfırla
        self._targets.clear()
        self.table.setRowCount(0)
        self.clean_btn.setEnabled(False)
        self.table_select_all.setEnabled(False)
        self.table_deselect_all.setEnabled(False)
        self.status_label.setText(f"[{new_game}] Click 'Scan Mods' to preview files to be removed.")

    def _apply_game_profile(self, game_name: str, load_saved: bool = True):
        profile = self.GAME_PROFILES.get(game_name, self.GAME_PROFILES["Skyrim SE"])
        game_saved = self._config_data.get("profiles", {}).get(game_name, {}) if load_saved else {}
        saved_checks = game_saved.get("checkboxes", {})

        # Eski onay kutularını temizle
        while self.cb_container_layout.count():
            item = self.cb_container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.checkboxes.clear()

        for name, default_checked in profile["presets"]:
            cb = QCheckBox(name)
            cb.setChecked(bool(saved_checks[name]) if name in saved_checks else default_checked)
            self.checkboxes[name] = cb
            self.cb_container_layout.addWidget(cb)

        self.custom_input.setPlaceholderText(profile["placeholder"])
        self.custom_input.setText(game_saved.get("custom_tags", ""))

        if load_saved:
            if self._config_data.get("action_mode") == "delete":
                self.radio_delete.setChecked(True)
            else:
                self.radio_backup.setChecked(True)

            saved_out = game_saved.get("output_target", "")
            if saved_out:
                idx = self.output_combo.findText(saved_out)
                if idx >= 0:
                    self.output_combo.setCurrentIndex(idx)

    def _save_config(self):
        profiles = self._config_data.get("profiles", {})
        profiles[self._current_game] = {
            "checkboxes": {name: cb.isChecked() for name, cb in self.checkboxes.items()},
            "custom_tags": self.custom_input.text(),
            "output_target": self.output_combo.currentText(),
        }
        self._config_data = {
            "last_game": self._current_game,
            "action_mode": "delete" if self.radio_delete.isChecked() else "backup",
            "profiles": profiles,
        }
        try:
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(self._config_data, f, indent=2)
        except Exception:
            pass

    def closeEvent(self, event):
        self._save_config()
        super().closeEvent(event)

    # =========================================================================
    # SEKME 1 METODLARI
    # =========================================================================
    def _update_action_button_style(self):
        if self.radio_backup.isChecked():
            self.clean_btn.setText("Move Selected to Backup")
            self.clean_btn.setStyleSheet("background-color: #1565c0; color: white; font-weight: bold; padding: 5px 14px;")
        else:
            self.clean_btn.setText("Delete Selected Targets")
            self.clean_btn.setStyleSheet("background-color: #b71c1c; color: white; font-weight: bold; padding: 5px 14px;")

    def _on_header_clicked(self, logical_index: int):
        if logical_index == 0:
            self.table.horizontalHeader().setSortIndicator(-1, Qt.SortOrder.AscendingOrder)

    def _toggle_all_checkboxes(self, state: bool):
        for cb in self.checkboxes.values():
            cb.setChecked(state)

    def _toggle_table_selection(self, state: bool):
        self.table.blockSignals(True)
        for row in range(self.table.rowCount()):
            if not self.table.isRowHidden(row):
                item = self.table.item(row, 0)
                if item:
                    item.setCheckState(Qt.CheckState.Checked if state else Qt.CheckState.Unchecked)
        self.table.blockSignals(False)
        self._update_status_label()

    def _filter_table(self, text: str):
        query = text.strip().lower()
        for row in range(self.table.rowCount()):
            mod_name = self.table.item(row, 1).text().lower() if self.table.item(row, 1) else ""
            target_name = self.table.item(row, 3).text().lower() if self.table.item(row, 3) else ""
            match = (query in mod_name) or (query in target_name)
            self.table.setRowHidden(row, not match)

    def _get_selected_tags(self):
        tags = [name.lower() for name, cb in self.checkboxes.items() if cb.isChecked()]
        custom_text = self.custom_input.text().strip()
        if custom_text:
            for item in custom_text.split(","):
                cleaned = item.strip().lower()
                if cleaned:
                    tags.append(cleaned)
        return tags

    def _get_folder_size(self, path):
        total = 0
        for dirpath, _, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if not os.path.islink(fp):
                    total += os.path.getsize(fp)
        return total

    def _matches_tags(self, name, tags):
        lower_name = name.lower()
        protect_tag = self.GAME_PROFILES.get(self._current_game, {}).get("protect_tag", "")
        if protect_tag and protect_tag not in tags and protect_tag in lower_name:
            return False
        return any(tag in lower_name for tag in tags)

    def _scan_mods(self):
        self._save_config()
        tags = self._get_selected_tags()
        if not tags:
            QMessageBox.warning(self, "No Tags Selected", "Please select at least one body type tag to scan.")
            return

        mods_dir = self._organizer.modsPath()
        self._targets.clear()
        self.table.setSortingEnabled(False)
        self.table.blockSignals(True)
        self.table.setRowCount(0)

        if not os.path.exists(mods_dir):
            self.table.blockSignals(False)
            self.table.setSortingEnabled(True)
            return

        for mod_name in os.listdir(mods_dir):
            mod_path = os.path.join(mods_dir, mod_name)
            if not os.path.isdir(mod_path):
                continue

            bs_path = os.path.join(mod_path, "CalienteTools", "BodySlide")
            if not os.path.exists(bs_path):
                continue

            slidersets_path = os.path.join(bs_path, "SliderSets")
            if os.path.isdir(slidersets_path):
                for file_name in os.listdir(slidersets_path):
                    if file_name.lower().endswith(".osp") and self._matches_tags(file_name, tags):
                        full_path = os.path.join(slidersets_path, file_name)
                        if os.path.isfile(full_path):
                            size = os.path.getsize(full_path)
                            self._targets.append((mod_name, "SliderSet (.osp)", file_name, full_path, size))

            shapedata_path = os.path.join(bs_path, "ShapeData")
            if os.path.isdir(shapedata_path):
                for folder_name in os.listdir(shapedata_path):
                    full_path = os.path.join(shapedata_path, folder_name)
                    if os.path.isdir(full_path) and self._matches_tags(folder_name, tags):
                        size = self._get_folder_size(full_path)
                        self._targets.append((mod_name, "ShapeData Folder", folder_name, full_path, size))

        self.table.setRowCount(len(self._targets))
        for row, (mod_name, item_type, target_name, full_path, size) in enumerate(self._targets):
            chk_item = QTableWidgetItem()
            chk_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            chk_item.setCheckState(Qt.CheckState.Checked)
            chk_item.setData(Qt.ItemDataRole.UserRole, row)
            self.table.setItem(row, 0, chk_item)

            mod_item = QTableWidgetItem(mod_name)
            mod_item.setToolTip(mod_name)
            self.table.setItem(row, 1, mod_item)

            self.table.setItem(row, 2, QTableWidgetItem(item_type))

            target_item = QTableWidgetItem(target_name)
            target_item.setToolTip(full_path)
            self.table.setItem(row, 3, target_item)

            size_mb = round(size / (1024 * 1024), 2)
            self.table.setItem(row, 4, NumericTableWidgetItem(f"{size_mb:.2f}"))

        self.table.blockSignals(False)
        self.table.setSortingEnabled(True)
        self._filter_table(self.search_input.text())

        has_items = len(self._targets) > 0
        self.table_select_all.setEnabled(has_items)
        self.table_deselect_all.setEnabled(has_items)
        self._update_status_label()

        if not has_items:
            self.status_label.setText("Scan complete: No matching unused BodySlide files found.")
            QMessageBox.information(
                self,
                "Scan Complete",
                "Scan completed successfully!\n\nNo matching unused SliderSets (.osp) or ShapeData folders were found for the selected body types."
            )

    def _update_status_label(self):
        selected_count = 0
        selected_bytes = 0
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.checkState() == Qt.CheckState.Checked:
                target_idx = item.data(Qt.ItemDataRole.UserRole)
                if target_idx is not None and 0 <= target_idx < len(self._targets):
                    selected_count += 1
                    selected_bytes += self._targets[target_idx][4]

        total_mb = round(selected_bytes / (1024 * 1024), 2)
        total_gb = round(selected_bytes / (1024 * 1024 * 1024), 2)
        self.status_label.setText(f"Selected: {selected_count} / {len(self._targets)} | Space to free: {total_mb} MB ({total_gb} GB)")
        self.clean_btn.setEnabled(selected_count > 0)

    def _clean_targets(self):
        self._save_config()
        to_process = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.checkState() == Qt.CheckState.Checked:
                target_idx = item.data(Qt.ItemDataRole.UserRole)
                if target_idx is not None and 0 <= target_idx < len(self._targets):
                    to_process.append(self._targets[target_idx])

        if not to_process:
            return

        is_backup = self.radio_backup.isChecked()
        action_word = "move to backup" if is_backup else "permanently delete"
        warning_extra = "Files will be safely stored in MO2\\BodySlideCleaner_Backup." if is_backup else "This action cannot be undone."

        reply = QMessageBox.question(
            self,
            "Confirm Cleanup",
            f"Are you sure you want to {action_word} {len(to_process)} selected items?\n{warning_extra}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        mods_dir = self._organizer.modsPath()
        mo2_root = os.path.dirname(mods_dir)
        backup_root = os.path.join(mo2_root, "BodySlideCleaner_Backup")

        processed_count = 0
        errors = []

        for _, _, _, full_path, _ in to_process:
            try:
                if is_backup:
                    rel_path = os.path.relpath(full_path, mods_dir)
                    dest_path = os.path.join(backup_root, rel_path)
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    if os.path.exists(dest_path):
                        if os.path.isdir(dest_path):
                            shutil.rmtree(dest_path)
                        else:
                            os.remove(dest_path)
                    shutil.move(full_path, dest_path)
                else:
                    if os.path.isdir(full_path):
                        shutil.rmtree(full_path)
                    elif os.path.isfile(full_path):
                        os.remove(full_path)
                processed_count += 1
            except Exception as e:
                errors.append(f"{full_path}: {str(e)}")

        self._organizer.refresh()
        self._targets.clear()
        self.table.setRowCount(0)
        self.clean_btn.setEnabled(False)
        self.table_select_all.setEnabled(False)
        self.table_deselect_all.setEnabled(False)
        self.status_label.setText(f"Cleanup complete! Processed {processed_count} items.")

        if errors:
            QMessageBox.warning(self, "Completed with Errors", "\n".join(errors[:10]))
        else:
            msg = f"Successfully moved {processed_count} items to:\n{backup_root}" if is_backup else f"Successfully deleted {processed_count} unused BodySlide items!"
            QMessageBox.information(self, "Success", msg)

    # =========================================================================
    # SEKME 2 METODLARI (ORPHANED OUTPUT CLEANER)
    # =========================================================================
    def _populate_output_combo(self):
        self.output_combo.clear()
        mods_dir = self._organizer.modsPath()
        overwrite_dir = self._organizer.overwritePath()

        if overwrite_dir and os.path.isdir(overwrite_dir):
            self.output_combo.addItem("[Overwrite Folder]", overwrite_dir)

        preferred_idx = 0
        if mods_dir and os.path.isdir(mods_dir):
            for mod_name in sorted(os.listdir(mods_dir), key=str.lower):
                mod_path = os.path.join(mods_dir, mod_name)
                if os.path.isdir(mod_path):
                    self.output_combo.addItem(mod_name, mod_path)
                    low = mod_name.lower()
                    if "bodyslide" in low and "output" in low:
                        preferred_idx = self.output_combo.count() - 1

        if self.output_combo.count() > 0:
            self.output_combo.setCurrentIndex(preferred_idx)

    def _update_o_action_button_style(self):
        if self.o_radio_backup.isChecked():
            self.o_clean_btn.setText("Move Selected to Backup")
            self.o_clean_btn.setStyleSheet("background-color: #1565c0; color: white; font-weight: bold; padding: 5px 14px;")
        else:
            self.o_clean_btn.setText("Delete Selected Targets")
            self.o_clean_btn.setStyleSheet("background-color: #b71c1c; color: white; font-weight: bold; padding: 5px 14px;")

    def _on_o_header_clicked(self, logical_index: int):
        if logical_index == 0:
            self.o_table.horizontalHeader().setSortIndicator(-1, Qt.SortOrder.AscendingOrder)

    def _toggle_orphan_selection(self, state: bool):
        self.o_table.blockSignals(True)
        for row in range(self.o_table.rowCount()):
            if not self.o_table.isRowHidden(row):
                item = self.o_table.item(row, 0)
                if item:
                    item.setCheckState(Qt.CheckState.Checked if state else Qt.CheckState.Unchecked)
        self.o_table.blockSignals(False)
        self._update_o_status_label()

    def _filter_orphan_table(self, text: str):
        query = text.strip().lower()
        for row in range(self.o_table.rowCount()):
            fname = self.o_table.item(row, 1).text().lower() if self.o_table.item(row, 1) else ""
            src_mod = self.o_table.item(row, 2).text().lower() if self.o_table.item(row, 2) else ""
            rpath = self.o_table.item(row, 3).text().lower() if self.o_table.item(row, 3) else ""
            match = (query in fname) or (query in src_mod) or (query in rpath)
            self.o_table.setRowHidden(row, not match)

    def _build_mod_mesh_index(self, exclude_dir: str):
        active_valid_paths = set()
        inactive_source_map = {}

        mods_dir = self._organizer.modsPath()
        mod_list = self._organizer.modList()

        if not mods_dir or not os.path.isdir(mods_dir):
            return active_valid_paths, inactive_source_map

        exclude_norm = os.path.normcase(os.path.abspath(exclude_dir))

        for mod_name in os.listdir(mods_dir):
            mod_path = os.path.join(mods_dir, mod_name)
            if not os.path.isdir(mod_path):
                continue
            if os.path.normcase(os.path.abspath(mod_path)) == exclude_norm:
                continue

            is_active = True
            try:
                state = mod_list.state(mod_name)
                is_active = bool(state & mobase.ModState.ACTIVE)
            except Exception:
                pass

            mod_meshes_dir = os.path.join(mod_path, "meshes")
            if os.path.isdir(mod_meshes_dir):
                for root, _, files in os.walk(mod_meshes_dir):
                    for fname in files:
                        if fname.lower().endswith(".nif"):
                            full_p = os.path.join(root, fname)
                            rel_p = os.path.relpath(full_p, mod_path).replace("/", "\\").lower()
                            if is_active:
                                active_valid_paths.add(rel_p)
                            elif rel_p not in inactive_source_map:
                                inactive_source_map[rel_p] = mod_name

            slidersets_dir = os.path.join(mod_path, "CalienteTools", "BodySlide", "SliderSets")
            if os.path.isdir(slidersets_dir):
                for fname in os.listdir(slidersets_dir):
                    if not fname.lower().endswith(".osp"):
                        continue
                    osp_path = os.path.join(slidersets_dir, fname)
                    try:
                        tree = ET.parse(osp_path)
                        root = tree.getroot()
                        for slider_set in root.findall(".//SliderSet"):
                            out_path_el = slider_set.find("OutputPath")
                            out_file_el = slider_set.find("OutputFile")
                            if out_path_el is None or out_file_el is None:
                                continue
                            raw_path = (out_path_el.text or "").strip().replace("/", "\\").strip("\\")
                            raw_file = (out_file_el.text or "").strip()
                            if not raw_file:
                                continue

                            base_rel = os.path.join(raw_path, raw_file).lower() if raw_path else raw_file.lower()
                            if base_rel.endswith(".nif"):
                                stem = base_rel[:-4]
                                candidates = [base_rel, f"{stem}_0.nif", f"{stem}_1.nif"]
                            else:
                                candidates = [f"{base_rel}.nif", f"{base_rel}_0.nif", f"{base_rel}_1.nif"]

                            for cand in candidates:
                                if is_active:
                                    active_valid_paths.add(cand)
                                elif cand not in inactive_source_map:
                                    inactive_source_map[cand] = mod_name
                    except Exception:
                        continue

        return active_valid_paths, inactive_source_map

    def _scan_orphaned_output(self):
        self._save_config()
        output_dir = self.output_combo.currentData()
        if not output_dir or not os.path.isdir(output_dir):
            QMessageBox.warning(self, "Invalid Folder", "Selected output folder does not exist.")
            return

        meshes_dir = os.path.join(output_dir, "meshes")
        if not os.path.isdir(meshes_dir):
            QMessageBox.information(self, "No Meshes Found", "The selected folder does not contain a 'meshes' subfolder.")
            return

        active_valid_paths, inactive_source_map = self._build_mod_mesh_index(output_dir)
        if not active_valid_paths:
            QMessageBox.warning(
                self,
                "No Active Mod Data Found",
                "Could not index any active mods or SliderSets. Aborting scan for safety."
            )
            return

        self._orphan_targets.clear()
        self.o_table.setSortingEnabled(False)
        self.o_table.blockSignals(True)
        self.o_table.setRowCount(0)

        for root, _, files in os.walk(meshes_dir):
            for fname in files:
                if not fname.lower().endswith(".nif"):
                    continue

                low_fname = fname.lower()
                if any(kw in low_fname for kw in self.PROTECTED_NIF_KEYWORDS):
                    continue

                full_path = os.path.join(root, fname)
                rel_path = os.path.relpath(full_path, output_dir).replace("/", "\\").lower()

                if rel_path in active_valid_paths:
                    continue

                if rel_path in inactive_source_map:
                    source_label = f"[Disabled] {inactive_source_map[rel_path]}"
                else:
                    source_label = "Uninstalled / Orphaned"

                try:
                    size = os.path.getsize(full_path)
                except OSError:
                    size = 0
                display_rel = os.path.relpath(full_path, output_dir)
                self._orphan_targets.append((fname, source_label, display_rel, full_path, size))

        self.o_table.setRowCount(len(self._orphan_targets))
        for row, (fname, source_label, display_rel, full_path, size) in enumerate(self._orphan_targets):
            chk_item = QTableWidgetItem()
            chk_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            chk_item.setCheckState(Qt.CheckState.Checked)
            chk_item.setData(Qt.ItemDataRole.UserRole, row)
            self.o_table.setItem(row, 0, chk_item)

            fname_item = QTableWidgetItem(fname)
            fname_item.setToolTip(full_path)
            self.o_table.setItem(row, 1, fname_item)

            src_item = QTableWidgetItem(source_label)
            src_item.setToolTip(source_label)
            self.o_table.setItem(row, 2, src_item)

            rel_item = QTableWidgetItem(display_rel)
            rel_item.setToolTip(display_rel)
            self.o_table.setItem(row, 3, rel_item)

            size_mb = round(size / (1024 * 1024), 2)
            self.o_table.setItem(row, 4, NumericTableWidgetItem(f"{size_mb:.2f}"))

        self.o_table.blockSignals(False)
        self.o_table.setSortingEnabled(True)
        self._filter_orphan_table(self.o_search_input.text())

        has_items = len(self._orphan_targets) > 0
        self.o_select_all.setEnabled(has_items)
        self.o_deselect_all.setEnabled(has_items)
        self._update_o_status_label()

        if not has_items:
            self.o_status_label.setText("Scan complete: No orphaned output meshes found.")
            QMessageBox.information(
                self,
                "Scan Complete",
                "Scan completed successfully!\n\nAll generated meshes in your output folder match active mods in your current load order."
            )

    def _update_o_status_label(self):
        selected_count = 0
        selected_bytes = 0
        for row in range(self.o_table.rowCount()):
            item = self.o_table.item(row, 0)
            if item and item.checkState() == Qt.CheckState.Checked:
                idx = item.data(Qt.ItemDataRole.UserRole)
                if idx is not None and 0 <= idx < len(self._orphan_targets):
                    selected_count += 1
                    selected_bytes += self._orphan_targets[idx][4]

        total_mb = round(selected_bytes / (1024 * 1024), 2)
        total_gb = round(selected_bytes / (1024 * 1024 * 1024), 2)
        self.o_status_label.setText(f"Selected: {selected_count} / {len(self._orphan_targets)} | Space to free: {total_mb} MB ({total_gb} GB)")
        self.o_clean_btn.setEnabled(selected_count > 0)

    def _clean_orphaned_targets(self):
        self._save_config()
        to_process = []
        for row in range(self.o_table.rowCount()):
            item = self.o_table.item(row, 0)
            if item and item.checkState() == Qt.CheckState.Checked:
                idx = item.data(Qt.ItemDataRole.UserRole)
                if idx is not None and 0 <= idx < len(self._orphan_targets):
                    to_process.append(self._orphan_targets[idx])

        if not to_process:
            return

        is_backup = self.o_radio_backup.isChecked()
        action_word = "move to backup" if is_backup else "permanently delete"
        warning_extra = "Files will be safely stored in MO2\\BodySlideCleaner_Backup\\Orphaned_Output." if is_backup else "This action cannot be undone."

        reply = QMessageBox.question(
            self,
            "Confirm Output Cleanup",
            f"Are you sure you want to {action_word} {len(to_process)} orphaned output files?\n{warning_extra}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        output_dir = self.output_combo.currentData()
        mods_dir = self._organizer.modsPath()
        mo2_root = os.path.dirname(mods_dir)
        backup_root = os.path.join(mo2_root, "BodySlideCleaner_Backup", "Orphaned_Output")

        processed_count = 0
        errors = []

        for _, _, rel_path, full_path, _ in to_process:
            try:
                if is_backup:
                    dest_path = os.path.join(backup_root, rel_path)
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    if os.path.exists(dest_path):
                        os.remove(dest_path)
                    shutil.move(full_path, dest_path)
                else:
                    if os.path.isfile(full_path):
                        os.remove(full_path)

                parent_dir = os.path.dirname(full_path)
                while parent_dir and parent_dir != output_dir and os.path.isdir(parent_dir):
                    if not os.listdir(parent_dir):
                        os.rmdir(parent_dir)
                        parent_dir = os.path.dirname(parent_dir)
                    else:
                        break

                processed_count += 1
            except Exception as e:
                errors.append(f"{full_path}: {str(e)}")

        self._organizer.refresh()
        self._orphan_targets.clear()
        self.o_table.setRowCount(0)
        self.o_clean_btn.setEnabled(False)
        self.o_select_all.setEnabled(False)
        self.o_deselect_all.setEnabled(False)
        self.o_status_label.setText(f"Cleanup complete! Processed {processed_count} orphaned files.")

        if errors:
            QMessageBox.warning(self, "Completed with Errors", "\n".join(errors[:10]))
        else:
            msg = f"Successfully moved {processed_count} orphaned files to:\n{backup_root}" if is_backup else f"Successfully deleted {processed_count} orphaned BodySlide output files!"
            QMessageBox.information(self, "Success", msg)


class BodySlideCleanerPlugin(mobase.IPluginTool):
    def __init__(self):
        super().__init__()
        self._organizer = None
        self._parent = None

    def init(self, organizer: mobase.IOrganizer):
        self._organizer = organizer
        return True

    def name(self):
        return "BodySlide SliderSet & ShapeData Cleaner"

    def author(self):
        return "Sonbora"

    def description(self):
        return "Scans and removes or backs up unused BodySlide SliderSets (.osp), ShapeData folders, and orphaned BodySlide output meshes for Skyrim SE and Fallout 4."

    def version(self):
        return mobase.VersionInfo(1, 3, 0, mobase.ReleaseType.FINAL)

    def isActive(self):
        return self._organizer.pluginSetting(self.name(), "enabled")

    def settings(self):
        return [
            mobase.PluginSetting("enabled", "Enable BodySlide SliderSet & ShapeData Cleaner", True)
        ]

    def displayName(self):
        return "BodySlide SliderSet & ShapeData Cleaner"

    def tooltip(self):
        return "Clean or backup unused body type presets and orphaned BodySlide output meshes"

    def icon(self):
        return QIcon()

    def setParentWidget(self, widget):
        self._parent = widget

    def display(self):
        dialog = CleanerDialog(self._organizer, self._parent)
        dialog.exec()


def createPlugin():
    return BodySlideCleanerPlugin()