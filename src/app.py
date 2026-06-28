from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from nf_file_engine import (
    DEFAULT_RULE,
    HistoryStore,
    RenameInput,
    apply_rename,
    infer_metadata,
    normalize_page,
    preview_batch,
    undo_last,
)


APP_DIR = Path.home() / ".nf-file-engine"
DB_PATH = APP_DIR / "history.sqlite3"


class NFFileEngineApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("NF File Engine")
        self.geometry("980x620")
        self.minsize(840, 520)
        self.rowconfigure(2, weight=1)

        self.history = HistoryStore(DB_PATH)
        self.files: list[Path] = []

        self.date_var = tk.StringVar()
        self.media_var = tk.StringVar()
        self.page_var = tk.StringVar(value="001")
        self.rule_var = tk.StringVar(value=DEFAULT_RULE)
        self.status_var = tk.StringVar(value="PDF 파일을 추가하세요.")

        self._build_ui()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        toolbar = ttk.Frame(self, padding=12)
        toolbar.grid(row=0, column=0, sticky="ew")
        toolbar.columnconfigure(7, weight=1)

        ttk.Button(toolbar, text="파일 추가", command=self.add_files).grid(row=0, column=0, padx=(0, 6))
        ttk.Button(toolbar, text="목록 비우기", command=self.clear_files).grid(row=0, column=1, padx=(0, 16))

        ttk.Label(toolbar, text="날짜").grid(row=0, column=2, padx=(0, 4))
        ttk.Entry(toolbar, textvariable=self.date_var, width=12).grid(row=0, column=3, padx=(0, 8))

        ttk.Label(toolbar, text="매체").grid(row=0, column=4, padx=(0, 4))
        ttk.Entry(toolbar, textvariable=self.media_var, width=8).grid(row=0, column=5, padx=(0, 8))

        ttk.Label(toolbar, text="페이지").grid(row=0, column=6, padx=(0, 4))
        ttk.Entry(toolbar, textvariable=self.page_var, width=6).grid(row=0, column=7, sticky="w")

        rule_bar = ttk.Frame(self, padding=(12, 0, 12, 10))
        rule_bar.grid(row=1, column=0, sticky="ew")
        rule_bar.columnconfigure(1, weight=1)
        ttk.Label(rule_bar, text="규칙").grid(row=0, column=0, padx=(0, 8))
        ttk.Entry(rule_bar, textvariable=self.rule_var).grid(row=0, column=1, sticky="ew", padx=(0, 8))
        ttk.Button(rule_bar, text="미리보기", command=self.refresh_preview).grid(row=0, column=2, padx=(0, 6))
        ttk.Button(rule_bar, text="변경 실행", command=self.rename_ready).grid(row=0, column=3, padx=(0, 6))
        ttk.Button(rule_bar, text="마지막 변경 취소", command=self.undo).grid(row=0, column=4)

        content = ttk.Frame(self, padding=(12, 0, 12, 8))
        content.grid(row=2, column=0, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.rowconfigure(0, weight=1)

        columns = ("source", "target", "status", "message")
        self.table = ttk.Treeview(content, columns=columns, show="headings", selectmode="browse")
        self.table.heading("source", text="원본")
        self.table.heading("target", text="변경 예정")
        self.table.heading("status", text="상태")
        self.table.heading("message", text="메시지")
        self.table.column("source", width=330)
        self.table.column("target", width=330)
        self.table.column("status", width=90, anchor="center")
        self.table.column("message", width=180)
        self.table.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(content, orient="vertical", command=self.table.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.table.configure(yscrollcommand=scrollbar.set)

        bottom = ttk.Frame(self, padding=(12, 0, 12, 12))
        bottom.grid(row=3, column=0, sticky="ew")
        bottom.columnconfigure(0, weight=1)
        ttk.Label(bottom, textvariable=self.status_var).grid(row=0, column=0, sticky="w")
        ttk.Button(bottom, text="히스토리 보기", command=self.show_history).grid(row=0, column=1)

    def add_files(self) -> None:
        selected = filedialog.askopenfilenames(
            title="변경할 PDF 파일 선택",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )
        if not selected:
            return
        for file_name in selected:
            path = Path(file_name)
            if path not in self.files:
                self.files.append(path)

        metadata = infer_metadata(self.files[0])
        if not self.date_var.get():
            self.date_var.set(metadata["date"])
        if not self.media_var.get():
            self.media_var.set(metadata["media"])
        if not self.page_var.get():
            self.page_var.set(metadata["page"])
        self.refresh_preview()

    def clear_files(self) -> None:
        self.files.clear()
        self.refresh_preview()

    def _items(self) -> list[RenameInput]:
        page_base = self.page_var.get()
        items: list[RenameInput] = []
        for index, path in enumerate(self.files):
            metadata = infer_metadata(path, self.date_var.get())
            date = self.date_var.get() or metadata["date"]
            media = self.media_var.get() or metadata["media"]
            try:
                page = str(int(normalize_page(page_base or metadata["page"])) + index).zfill(3)
            except Exception:  # noqa: BLE001 - preview 단계에서 검증 메시지로 보여준다.
                page = page_base
            items.append(RenameInput(path, date, media, page, self.rule_var.get()))
        return items

    def refresh_preview(self) -> None:
        for row in self.table.get_children():
            self.table.delete(row)

        previews = preview_batch(self._items())
        for preview in previews:
            self.table.insert(
                "",
                "end",
                values=(str(preview.source), str(preview.target.name), preview.status, preview.message),
            )
        ready_count = sum(1 for item in previews if item.status == "ready")
        self.status_var.set(f"총 {len(previews)}개 중 {ready_count}개 변경 가능")

    def rename_ready(self) -> None:
        previews = preview_batch(self._items())
        ready = [preview for preview in previews if preview.status == "ready"]
        if not ready:
            messagebox.showinfo("NF File Engine", "변경 가능한 파일이 없습니다.")
            return
        if not messagebox.askyesno("변경 실행", f"{len(ready)}개 파일명을 변경할까요?"):
            return

        changed = 0
        try:
            for preview in ready:
                apply_rename(preview, self.history)
                changed += 1
        except Exception as exc:  # noqa: BLE001 - GUI에서 사용자에게 오류를 보여준다.
            messagebox.showerror("변경 실패", str(exc))
        self.files = [path for path in self.files if path.exists()]
        self.refresh_preview()
        self.status_var.set(f"{changed}개 파일명을 변경했습니다.")

    def undo(self) -> None:
        try:
            restored = undo_last(self.history)
        except Exception as exc:  # noqa: BLE001 - GUI에서 사용자에게 오류를 보여준다.
            messagebox.showerror("취소 실패", str(exc))
            return
        messagebox.showinfo("변경 취소", f"되돌림 완료: {restored.name}")
        self.refresh_preview()

    def show_history(self) -> None:
        window = tk.Toplevel(self)
        window.title("변경 히스토리")
        window.geometry("820x360")

        columns = ("id", "source", "target", "created_at", "undone_at")
        table = ttk.Treeview(window, columns=columns, show="headings")
        for column, label, width in [
            ("id", "ID", 50),
            ("source", "원본", 230),
            ("target", "변경 후", 230),
            ("created_at", "변경일", 150),
            ("undone_at", "취소일", 150),
        ]:
            table.heading(column, text=label)
            table.column(column, width=width)
        table.pack(fill="both", expand=True, padx=12, pady=12)

        for row in self.history.recent(limit=50):
            table.insert(
                "",
                "end",
                values=(
                    row["id"],
                    Path(str(row["source_path"])).name,
                    Path(str(row["target_path"])).name,
                    row["created_at"],
                    row["undone_at"] or "",
                ),
            )


if __name__ == "__main__":
    NFFileEngineApp().mainloop()
