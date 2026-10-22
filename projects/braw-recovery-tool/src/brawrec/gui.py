from __future__ import annotations

from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from brawrec.gui_workflows import (
    analyze_source,
    default_candidate_path,
    default_output_dir,
    recover_source,
    verify_candidate,
)


def format_success_message(success: str, result: dict) -> str:
    labels = {"candidate": "Candidate", "report_dir": "Reports"}
    lines = [success]
    for key, value in result.items():
        label = labels.get(key, key.replace("_", " ").capitalize())
        if isinstance(value, (str, int, float)) or value is None:
            display_value = str(value)
        else:
            display_value = f"{len(value)} item(s)"
        lines.append(f"{label}: {display_value}")
    return "\n".join(lines)


class BrawRecoveryApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("BRAW Recovery")
        self.root.geometry("760x520")
        self.root.minsize(680, 440)

        self.source_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.candidate_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready")
        self.messages: queue.Queue[tuple[str, str]] = queue.Queue()
        self.buttons: list[ttk.Button] = []

        self._build()
        self.root.after(100, self._drain_messages)

    def _build(self) -> None:
        frame = ttk.Frame(self.root, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(5, weight=1)

        ttk.Label(frame, text="Source BRAW").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self.source_var).grid(row=0, column=1, sticky="ew", padx=8)
        ttk.Button(frame, text="Browse...", command=self._choose_source).grid(row=0, column=2)

        ttk.Label(frame, text="Output folder").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self.output_var).grid(row=1, column=1, sticky="ew", padx=8)
        ttk.Button(frame, text="Browse...", command=self._choose_output).grid(row=1, column=2)

        ttk.Label(frame, text="Candidate").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self.candidate_var).grid(row=2, column=1, sticky="ew", padx=8)
        ttk.Button(frame, text="Reset", command=self._refresh_candidate).grid(row=2, column=2)

        actions = ttk.Frame(frame)
        actions.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(12, 8))
        for text, command in (
            ("Analyze", self._run_analyze),
            ("Recover", self._run_recover),
            ("Verify", self._run_verify),
        ):
            button = ttk.Button(actions, text=text, command=command)
            button.pack(side=tk.LEFT, padx=(0, 8))
            self.buttons.append(button)

        ttk.Label(frame, textvariable=self.status_var).grid(row=4, column=0, columnspan=3, sticky="w")
        self.log = tk.Text(frame, height=14, wrap="word")
        self.log.grid(row=5, column=0, columnspan=3, sticky="nsew", pady=(8, 0))

    def _choose_source(self) -> None:
        selected = filedialog.askopenfilename(
            title="Choose BRAW file",
            filetypes=[("Blackmagic RAW", "*.braw"), ("All files", "*.*")],
        )
        if not selected:
            return
        source = Path(selected)
        output = default_output_dir(source)
        self.source_var.set(str(source))
        self.output_var.set(str(output))
        self.candidate_var.set(str(default_candidate_path(source, output)))

    def _choose_output(self) -> None:
        selected = filedialog.askdirectory(title="Choose output folder")
        if not selected:
            return
        self.output_var.set(selected)
        self._refresh_candidate()

    def _refresh_candidate(self) -> None:
        source = self._source_path()
        output = self._output_dir()
        if source is None or output is None:
            return
        self.candidate_var.set(str(default_candidate_path(source, output)))

    def _run_analyze(self) -> None:
        source = self._require_source()
        output = self._require_output()
        if source and output:
            self._run_task("Analyzing...", lambda: analyze_source(source, output), "Analysis complete.")

    def _run_recover(self) -> None:
        source = self._require_source()
        output = self._require_output()
        candidate = self._require_candidate()
        if source and output and candidate:
            self._run_task("Recovering...", lambda: recover_source(source, candidate, output), "Recovery complete.")

    def _run_verify(self) -> None:
        output = self._require_output()
        candidate = self._require_candidate()
        if output and candidate:
            self._run_task("Verifying...", lambda: verify_candidate(candidate, output), "Verification complete.")

    def _run_task(self, busy: str, worker, success: str) -> None:
        self.status_var.set(busy)
        self._set_buttons(False)
        self._append_log(busy)

        def target() -> None:
            try:
                result = worker()
            except Exception as exc:
                self.messages.put(("error", str(exc)))
            else:
                self.messages.put(("success", format_success_message(success, result)))

        threading.Thread(target=target, daemon=True).start()

    def _drain_messages(self) -> None:
        while True:
            try:
                kind, text = self.messages.get_nowait()
            except queue.Empty:
                break
            if kind == "error":
                self.status_var.set("Stopped")
                self._append_log(f"Stopped: {text}")
                messagebox.showerror("BRAW Recovery", text)
            else:
                self.status_var.set("Ready")
                self._append_log(text)
            self._set_buttons(True)
        self.root.after(100, self._drain_messages)

    def _set_buttons(self, enabled: bool) -> None:
        state = tk.NORMAL if enabled else tk.DISABLED
        for button in self.buttons:
            button.configure(state=state)

    def _append_log(self, text: str) -> None:
        self.log.insert(tk.END, text + "\n\n")
        self.log.see(tk.END)

    def _source_path(self) -> Path | None:
        value = self.source_var.get().strip()
        return Path(value) if value else None

    def _output_dir(self) -> Path | None:
        value = self.output_var.get().strip()
        return Path(value) if value else None

    def _candidate_path(self) -> Path | None:
        value = self.candidate_var.get().strip()
        return Path(value) if value else None

    def _require_source(self) -> Path | None:
        source = self._source_path()
        if source is None:
            messagebox.showwarning("BRAW Recovery", "Choose a source BRAW file first.")
            return None
        return source

    def _require_output(self) -> Path | None:
        output = self._output_dir()
        if output is None:
            messagebox.showwarning("BRAW Recovery", "Choose an output folder first.")
            return None
        return output

    def _require_candidate(self) -> Path | None:
        candidate = self._candidate_path()
        if candidate is None:
            messagebox.showwarning("BRAW Recovery", "Choose a candidate file path first.")
            return None
        return candidate


def main() -> None:
    root = tk.Tk()
    BrawRecoveryApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
