from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from lib.common import current_task_id, write_json

from .backend import CommandResult, DispatcherBackend
from .config import load_app_state, save_app_state


ROOT = Path(__file__).resolve().parents[1]


class BaseTab(QWidget):
    def __init__(self, backend: DispatcherBackend) -> None:
        super().__init__()
        self.backend = backend

    def show_result(self, result: CommandResult, success_title: str = "Success") -> None:
        text = result.stdout.strip() or result.stderr.strip() or f"exit={result.exit_code}"
        if result.ok:
            QMessageBox.information(self, success_title, text)
        else:
            QMessageBox.critical(self, "Error", text)

    def refresh(self) -> None:
        raise NotImplementedError


class DashboardTab(BaseTab):
    def __init__(self, backend: DispatcherBackend) -> None:
        super().__init__(backend)
        layout = QVBoxLayout(self)
        self.summary = QTextEdit()
        self.summary.setReadOnly(True)
        self.agent_table = QTableWidget(0, 5)
        self.agent_table.setHorizontalHeaderLabels(["Agent", "Ready", "Halted", "Session", "Inbox"])
        layout.addWidget(self.summary)
        layout.addWidget(self.agent_table)

    def refresh(self) -> None:
        snapshot = self.backend.status_snapshot()
        self.summary.setPlainText(
            "\n".join(
                [
                    f"Project: {snapshot['project']}",
                    f"Project root: {snapshot['project_root']}",
                    f"Watcher: {snapshot['watcher']}",
                    f"Current task: {snapshot['current_task']} {snapshot['current_title']}".strip(),
                    f"Gate: {snapshot['gate']}",
                    f"Reviewers: {', '.join(snapshot['reviewers']) or '(none)'}",
                ]
            )
        )
        agents = snapshot["agents"]
        self.agent_table.setRowCount(len(agents))
        for row, agent in enumerate(agents):
            self.agent_table.setItem(row, 0, QTableWidgetItem(agent["name"]))
            self.agent_table.setItem(row, 1, QTableWidgetItem("yes" if agent["ready"] else "no"))
            self.agent_table.setItem(row, 2, QTableWidgetItem("yes" if agent["halted"] else "no"))
            self.agent_table.setItem(row, 3, QTableWidgetItem(agent["session"]))
            self.agent_table.setItem(row, 4, QTableWidgetItem(str(agent["inbox_count"])))


class SprintTab(BaseTab):
    def __init__(self, backend: DispatcherBackend) -> None:
        super().__init__(backend)
        layout = QVBoxLayout(self)
        launch_group = QGroupBox("Launch Sprint")
        launch_layout = QFormLayout(launch_group)
        self.plan_combo = QComboBox()
        self.agent_checks: list[QCheckBox] = []
        self.mode_combos: dict[str, QComboBox] = {}
        self.model_inputs: dict[str, QLineEdit] = {}
        self.command_inputs: dict[str, QLineEdit] = {}
        self.ready_label = QLabel()
        self.launch_button = QPushButton("Launch Selected Agents")
        self.launch_button.clicked.connect(self.launch_sprint)
        launch_layout.addRow("Plan", self.plan_combo)
        self.agent_group = QWidget()
        self.agent_layout = QGridLayout(self.agent_group)
        launch_layout.addRow(self.agent_group)
        launch_layout.addRow(self.ready_label)
        launch_layout.addRow(self.launch_button)

        controls_group = QGroupBox("Sprint Controls")
        controls_layout = QHBoxLayout(controls_group)
        self.pause_button = QPushButton("Pause")
        self.pause_button.clicked.connect(lambda: self.show_result(self.backend.pause_sprint()))
        self.resume_button = QPushButton("Resume")
        self.resume_button.clicked.connect(lambda: self.show_result(self.backend.resume_sprint()))
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(lambda: self.show_result(self.backend.stop_sprint()))
        self.start_watcher_button = QPushButton("Start Watcher")
        self.start_watcher_button.clicked.connect(lambda: self.show_result(self.backend.start_watcher()))
        self.reset_watcher_button = QPushButton("Reset Watcher")
        self.reset_watcher_button.clicked.connect(lambda: self.show_result(self.backend.reset_watcher_state()))
        self.kill_watcher_button = QPushButton("Force Kill Watcher")
        self.kill_watcher_button.clicked.connect(lambda: self.show_result(self.backend.kill_watcher()))
        for button in (
            self.pause_button,
            self.resume_button,
            self.stop_button,
            self.start_watcher_button,
            self.reset_watcher_button,
            self.kill_watcher_button,
        ):
            controls_layout.addWidget(button)
        layout.addWidget(launch_group)
        layout.addWidget(controls_group)
        layout.addStretch(1)

    def refresh(self) -> None:
        plan_dir = self.backend.project_root / ".orchestrator" / "plans"
        plans = sorted(plan_dir.glob("*.json")) if plan_dir.exists() else []
        current = self.plan_combo.currentText()
        self.plan_combo.blockSignals(True)
        self.plan_combo.clear()
        for plan in plans:
            self.plan_combo.addItem(str(plan))
        if current:
            index = self.plan_combo.findText(current)
            if index >= 0:
                self.plan_combo.setCurrentIndex(index)
        self.plan_combo.blockSignals(False)

        while self.agent_layout.count():
            item = self.agent_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.agent_checks.clear()
        self.mode_combos.clear()
        self.model_inputs.clear()
        self.command_inputs.clear()

        row = 0
        for agent_cfg in self.backend.config.get("agents", []):
            name = agent_cfg["name"]
            check = QCheckBox(name)
            check.setChecked(True)
            mode = QComboBox()
            mode.addItems(["claude", "claude_resume", "claude_model", "custom", "bare", "skip"])
            model = QLineEdit("opus")
            command = QLineEdit("")
            self.agent_checks.append(check)
            self.mode_combos[name] = mode
            self.model_inputs[name] = model
            self.command_inputs[name] = command
            self.agent_layout.addWidget(check, row, 0)
            self.agent_layout.addWidget(mode, row, 1)
            self.agent_layout.addWidget(model, row, 2)
            self.agent_layout.addWidget(command, row, 3)
            row += 1
        self.ready_label.setText(f"Ready files required: {'yes' if (self.backend.config.get('session') or {}).get('require_ready_files') else 'advisory'}")

    def launch_sprint(self) -> None:
        selected = [check.text() for check in self.agent_checks if check.isChecked()]
        if not selected:
            QMessageBox.warning(self, "No agents", "Select at least one agent.")
            return
        plan_path = self.plan_combo.currentText()
        if plan_path:
            try:
                plan_data = json.loads(Path(plan_path).read_text(encoding="utf-8"))
                tasks = plan_data if isinstance(plan_data, list) else plan_data.get("tasks", [])
                if tasks:
                    for task in tasks:
                        task.setdefault("status", "pending")
                    write_json(self.backend.tasks_dir / "tasks.json", tasks)
            except Exception as exc:
                QMessageBox.critical(self, "Plan Error", str(exc))
                return
        self.backend.start_watcher()
        for agent in selected:
            self.backend.launch_agent(
                agent,
                self.mode_combos[agent].currentText(),
                model=self.model_inputs[agent].text().strip(),
                command=self.command_inputs[agent].text().strip(),
            )
        tasks = self.backend.list_tasks()
        first_pending = next((task for task in tasks if task.get("status") == "pending"), None)
        if first_pending:
            self.backend.dispatch_task_to_executor(current_task_id(first_pending), "launch_task")
        QMessageBox.information(self, "Launch", "Sprint launch requested.")


class AgentsTab(BaseTab):
    def __init__(self, backend: DispatcherBackend) -> None:
        super().__init__(backend)
        layout = QVBoxLayout(self)
        self.agent_list = QListWidget()
        layout.addWidget(self.agent_list)
        row = QHBoxLayout()
        self.open_button = QPushButton("Launch/Reuse Session")
        self.open_button.clicked.connect(self.open_agent)
        self.attach_button = QPushButton("Attach Session")
        self.attach_button.clicked.connect(self.attach_agent)
        self.message_button = QPushButton("Send Direct Message")
        self.message_button.clicked.connect(self.send_message)
        row.addWidget(self.open_button)
        row.addWidget(self.attach_button)
        row.addWidget(self.message_button)
        layout.addLayout(row)

    def refresh(self) -> None:
        self.agent_list.clear()
        for agent in self.backend.status_snapshot()["agents"]:
            item = QListWidgetItem(f"{agent['name']}  |  session={agent['session']}  |  inbox={agent['inbox_count']}")
            item.setData(256, agent["name"])
            self.agent_list.addItem(item)

    def _selected(self) -> str | None:
        item = self.agent_list.currentItem()
        return item.data(256) if item else None

    def open_agent(self) -> None:
        agent = self._selected()
        if agent:
            self.show_result(self.backend.launch_agent(agent, "claude"))

    def attach_agent(self) -> None:
        agent = self._selected()
        if agent:
            self.show_result(self.backend.attach_agent(agent))

    def send_message(self) -> None:
        agent = self._selected()
        if not agent:
            return
        text, ok = QInputDialog.getText(self, "Direct Message", f"Message to {agent}")
        if ok and text.strip():
            self.show_result(self.backend.send_direct_message(agent, text.strip()))


class TasksTab(BaseTab):
    def __init__(self, backend: DispatcherBackend) -> None:
        super().__init__(backend)
        layout = QVBoxLayout(self)
        self.task_list = QListWidget()
        layout.addWidget(self.task_list)
        row = QHBoxLayout()
        self.resume_button = QPushButton("Resume Selected Task")
        self.resume_button.clicked.connect(self.resume_selected_task)
        self.override_approve = QPushButton("Force Approve")
        self.override_approve.clicked.connect(lambda: self.override_selected("approved"))
        self.override_reject = QPushButton("Force Reject")
        self.override_reject.clicked.connect(lambda: self.override_selected("rejected"))
        row.addWidget(self.resume_button)
        row.addWidget(self.override_approve)
        row.addWidget(self.override_reject)
        layout.addLayout(row)

    def refresh(self) -> None:
        self.task_list.clear()
        for task in self.backend.list_task_choices():
            item = QListWidgetItem(f"[{task['status']}] {task['task_id']}  --  {task['title']}")
            item.setData(256, task["task_id"])
            self.task_list.addItem(item)

    def _selected_task_id(self) -> str | None:
        item = self.task_list.currentItem()
        return item.data(256) if item else None

    def resume_selected_task(self) -> None:
        task_id = self._selected_task_id()
        if task_id:
            self.show_result(self.backend.dispatch_task_to_executor(task_id, "resume_task"))

    def override_selected(self, verdict: str) -> None:
        task_id = self._selected_task_id()
        if task_id:
            self.show_result(self.backend.override_verdict(task_id, verdict))


class HooksTab(BaseTab):
    def __init__(self, backend: DispatcherBackend) -> None:
        super().__init__(backend)
        layout = QVBoxLayout(self)
        self.hook_table = QTableWidget(0, 2)
        self.hook_table.setHorizontalHeaderLabels(["Hook", "Enabled"])
        layout.addWidget(self.hook_table)
        row = QHBoxLayout()
        self.enable_all = QPushButton("Enable All")
        self.enable_all.clicked.connect(lambda: self.show_result(self.backend.set_all_hooks(True)))
        self.disable_all = QPushButton("Disable All")
        self.disable_all.clicked.connect(lambda: self.show_result(self.backend.set_all_hooks(False)))
        self.toggle_selected = QPushButton("Toggle Selected")
        self.toggle_selected.clicked.connect(self.toggle_selected_hook)
        row.addWidget(self.enable_all)
        row.addWidget(self.disable_all)
        row.addWidget(self.toggle_selected)
        layout.addLayout(row)

    def refresh(self) -> None:
        hooks = self.backend.list_hook_states()
        self.hook_table.setRowCount(len(hooks))
        for row, hook in enumerate(hooks):
            self.hook_table.setItem(row, 0, QTableWidgetItem(hook["name"]))
            self.hook_table.setItem(row, 1, QTableWidgetItem("yes" if hook["enabled"] else "no"))

    def toggle_selected_hook(self) -> None:
        row = self.hook_table.currentRow()
        if row >= 0:
            self.show_result(self.backend.toggle_hook(self.hook_table.item(row, 0).text()))


class LogsTab(BaseTab):
    def __init__(self, backend: DispatcherBackend) -> None:
        super().__init__(backend)
        layout = QVBoxLayout(self)
        self.info = QTextEdit()
        self.info.setReadOnly(True)
        layout.addWidget(self.info)
        row = QHBoxLayout()
        self.audit_button = QPushButton("Open Audit Log Folder")
        self.audit_button.clicked.connect(lambda: self.show_result(self.backend.open_path(str(Path(self.backend.audit_log).parent))))
        self.dispatch_button = QPushButton("Open Dispatch Folder")
        self.dispatch_button.clicked.connect(lambda: self.show_result(self.backend.open_path(str(self.backend.dispatch_root))))
        self.project_button = QPushButton("Open Project Root")
        self.project_button.clicked.connect(lambda: self.show_result(self.backend.open_path(str(self.backend.project_root))))
        row.addWidget(self.audit_button)
        row.addWidget(self.dispatch_button)
        row.addWidget(self.project_button)
        layout.addLayout(row)

    def refresh(self) -> None:
        snapshot = self.backend.status_snapshot()
        self.info.setPlainText("\n".join([f"Audit log: {snapshot['audit_log']}", f"Decision trace: {snapshot['decision_trace']}", f"Logs dir: {snapshot['logs_dir']}"]))


class SettingsTab(BaseTab):
    def __init__(self, backend: DispatcherBackend, project_changed) -> None:
        super().__init__(backend)
        self.project_changed = project_changed
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.project_root_input = QLineEdit()
        self.pick_project = QPushButton("Browse Project")
        self.pick_project.clicked.connect(self.browse_project)
        form.addRow("Project Root", self.project_root_input)
        form.addRow("", self.pick_project)
        layout.addLayout(form)
        self.preset_combo = QComboBox()
        self.apply_preset = QPushButton("Apply Reviewer Preset")
        self.apply_preset.clicked.connect(self.apply_selected_preset)
        layout.addWidget(self.preset_combo)
        layout.addWidget(self.apply_preset)
        self.reviewer_list = QListWidget()
        self.enable_reviewer = QPushButton("Enable Reviewer")
        self.enable_reviewer.clicked.connect(lambda: self.toggle_selected_reviewer(True))
        self.disable_reviewer = QPushButton("Disable Reviewer")
        self.disable_reviewer.clicked.connect(lambda: self.toggle_selected_reviewer(False))
        layout.addWidget(self.reviewer_list)
        reviewer_buttons = QHBoxLayout()
        reviewer_buttons.addWidget(self.enable_reviewer)
        reviewer_buttons.addWidget(self.disable_reviewer)
        layout.addLayout(reviewer_buttons)
        row = QHBoxLayout()
        self.backup_button = QPushButton("Backup Settings")
        self.backup_button.clicked.connect(lambda: self.show_result(self.backend.backup_settings()))
        self.restore_button = QPushButton("Restore Backup")
        self.restore_button.clicked.connect(self.restore_backup)
        self.sprint_on = QPushButton("Sprint Mode ON")
        self.sprint_on.clicked.connect(lambda: self.show_result(self.backend.set_sprint_mode(True)))
        self.sprint_off = QPushButton("Sprint Mode OFF")
        self.sprint_off.clicked.connect(lambda: self.show_result(self.backend.set_sprint_mode(False)))
        self.folder_override = QPushButton("Toggle Folder Override")
        self.folder_override.clicked.connect(self.toggle_folder_override)
        self.deploy_project = QPushButton("Deploy To Project")
        self.deploy_project.clicked.connect(self.deploy_to_project)
        self.deploy_engine = QPushButton("Deploy Engine")
        self.deploy_engine.clicked.connect(self.deploy_engine_copy)
        for widget in (self.backup_button, self.restore_button, self.sprint_on, self.sprint_off, self.folder_override):
            row.addWidget(widget)
        layout.addLayout(row)
        deploy_row = QHBoxLayout()
        deploy_row.addWidget(self.deploy_project)
        deploy_row.addWidget(self.deploy_engine)
        layout.addLayout(deploy_row)
        layout.addStretch(1)

    def refresh(self) -> None:
        self.project_root_input.setText(str(self.backend.project_root))
        matrix = self.backend.reviewer_matrix()
        current = self.preset_combo.currentText()
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        for preset in matrix["presets"].keys():
            self.preset_combo.addItem(preset)
        if current:
            index = self.preset_combo.findText(current)
            if index >= 0:
                self.preset_combo.setCurrentIndex(index)
        self.preset_combo.blockSignals(False)
        self.reviewer_list.clear()
        for reviewer in matrix["available"]:
            label = reviewer
            if reviewer in matrix["active"]:
                label += "  [active]"
            item = QListWidgetItem(label)
            item.setData(256, reviewer)
            self.reviewer_list.addItem(item)

    def browse_project(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select Project Root", str(self.backend.project_root))
        if path:
            self.project_changed(path)

    def apply_selected_preset(self) -> None:
        preset = self.preset_combo.currentText()
        if preset:
            self.show_result(self.backend.apply_reviewer_preset(preset))

    def toggle_selected_reviewer(self, enable: bool) -> None:
        item = self.reviewer_list.currentItem()
        if item:
            self.show_result(self.backend.set_reviewer_enabled(item.data(256), enable))

    def restore_backup(self) -> None:
        backups = self.backend.list_backups()
        if not backups:
            QMessageBox.information(self, "Restore", "No backups found.")
            return
        path, _ = QFileDialog.getOpenFileName(self, "Select backup file", str(Path(backups[0]["path"]).parent))
        if not path:
            return
        target = str(self.backend.roles_json if "roles.json" in Path(path).name else self.backend.settings_local)
        self.show_result(self.backend.restore_backup(path, target))

    def toggle_folder_override(self) -> None:
        state = self.backend.folder_override_state()
        self.show_result(self.backend.set_folder_override(enabled=not state["enabled"]))

    def deploy_to_project(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Deploy To Project", str(self.backend.project_root))
        if path:
            self.show_result(self.backend.deploy_to_project(path))

    def deploy_engine_copy(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Deploy Engine", str(self.backend.project_root))
        if path:
            self.show_result(self.backend.deploy_engine(path))


class MainWindow(QMainWindow):
    def __init__(self, backend: DispatcherBackend) -> None:
        super().__init__()
        self.backend = backend
        self.setWindowTitle("Dispatcher Desktop Control Plane")
        self.resize(1320, 900)
        self.app_state = load_app_state()
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.dashboard_tab = DashboardTab(self.backend)
        self.sprint_tab = SprintTab(self.backend)
        self.agents_tab = AgentsTab(self.backend)
        self.tasks_tab = TasksTab(self.backend)
        self.hooks_tab = HooksTab(self.backend)
        self.logs_tab = LogsTab(self.backend)
        self.settings_tab = SettingsTab(self.backend, self.on_project_changed)
        for label, tab in (
            ("Dashboard", self.dashboard_tab),
            ("Sprint", self.sprint_tab),
            ("Agents", self.agents_tab),
            ("Tasks", self.tasks_tab),
            ("Hooks", self.hooks_tab),
            ("Logs", self.logs_tab),
            ("Settings", self.settings_tab),
        ):
            self.tabs.addTab(tab, label)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_all)
        self.timer.start(5000)
        self.refresh_all()

    def on_project_changed(self, project_root: str) -> None:
        self.backend.set_project_root(project_root)
        self.app_state["project_root"] = project_root
        save_app_state(self.app_state)
        self.refresh_all()

    def refresh_all(self) -> None:
        for tab in (self.dashboard_tab, self.sprint_tab, self.agents_tab, self.tasks_tab, self.hooks_tab, self.logs_tab, self.settings_tab):
            tab.refresh()


def create_window(project_root: str | None = None) -> MainWindow:
    state = load_app_state()
    root = project_root or state.get("project_root") or str(ROOT)
    return MainWindow(DispatcherBackend(root))


def run() -> int:
    app = QApplication.instance() or QApplication([])
    window = create_window()
    window.show()
    return app.exec()
