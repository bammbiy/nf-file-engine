from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from .assistant import AssistantWindow
from nuri_assistant import (
    DEFAULT_RULE,
    HistoryStore,
    RenameInput,
    WorkProfile,
    apply_batch_rename,
    export_preview_csv,
    infer_metadata,
    load_profiles,
    normalize_page,
    preview_batch,
    save_profile,
    scan_files,
    undo_last_batch,
)


APP_DIR = Path.home() / ".nuri-assistant"
DB_PATH = APP_DIR / "history.sqlite3"
PROFILES_PATH = APP_DIR / "profiles.json"
RULE_PRESETS = {
    "기본": DEFAULT_RULE,
    "매체-날짜-페이지": "{MEDIA}-{DATE}-{PAGE}",
    "날짜_페이지_매체": "{DATE}_{PAGE}_{MEDIA}",
    "날짜/매체/페이지": "{DATE}-{MEDIA}-p{PAGE}",
}
STATUS_FILTERS = ("전체", "ready", "conflict", "error", "skip")


class NuriAssistantApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Nuri Assistant")
        self.geometry("1180x760")
        self.minsize(1040, 640)
        self.rowconfigure(4, weight=1)
        self.columnconfigure(0, weight=1)

        self.history = HistoryStore(DB_PATH)
        self.files: list[Path] = []
        self.profiles = load_profiles(PROFILES_PATH)

        self.date_var = tk.StringVar()
        self.media_var = tk.StringVar()
        self.page_var = tk.StringVar(value="001")
        self.rule_var = tk.StringVar(value=DEFAULT_RULE)
        self.preset_var = tk.StringVar(value="기본")
        self.profile_var = tk.StringVar(value="")
        self.recursive_var = tk.BooleanVar(value=False)
        self.search_var = tk.StringVar()
        self.status_filter_var = tk.StringVar(value="전체")
        self.status_var = tk.StringVar(value="파일 또는 폴더를 추가하세요.")

        self._build_ui()
        self.search_var.trace_add("write", lambda *_: self.refresh_preview())
        self.status_filter_var.trace_add("write", lambda *_: self.refresh_preview())

    def open_assistant(self) -> None:
        AssistantWindow(self, self.history)

    def _build_ui(self) -> None:
        self._build_source_bar()
        self._build_rule_bar()
        self._build_filter_bar()
        self._build_summary()
        self._build_table()
        self._build_bottom_bar()

    def _build_source_bar(self) -> None:
        top = ttk.Frame(self, padding=12)
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(10, weight=1)

        ttk.Button(top, text="파일 추가", command=self.add_files).grid(row=0, column=0, padx=(0, 6))
        ttk.Button(top, text="폴더 불러오기", command=self.add_folder).grid(row=0, column=1, padx=(0, 6))
        ttk.Checkbutton(top, text="하위폴더 포함", variable=self.recursive_var).grid(row=0, column=2, padx=(0, 12))
        ttk.Button(top, text="선택 제거", command=self.remove_selected).grid(row=0, column=3, padx=(0, 6))
        ttk.Button(top, text="목록 비우기", command=self.clear_files).grid(row=0, column=4, padx=(0, 18))

        ttk.Label(top, text="작업 프로필").grid(row=0, column=5, padx=(0, 6))
        self.profile_combo = ttk.Combobox(
            top,
            textvariable=self.profile_var,
            values=sorted(self.profiles),
            width=18,
            state="readonly",
        )
        self.profile_combo.grid(row=0, column=6, padx=(0, 6))
        ttk.Button(top, text="불러오기", command=self.load_selected_profile).grid(row=0, column=7, padx=(0, 6))
        ttk.Button(top, text="저장", command=self.save_current_profile).grid(row=0, column=8, padx=(0, 0))

    def _build_rule_bar(self) -> None:
        rule_bar = ttk.Frame(self, padding=(12, 0, 12, 10))
        rule_bar.grid(row=1, column=0, sticky="ew")
        rule_bar.columnconfigure(8, weight=1)

        ttk.Label(rule_bar, text="날짜").grid(row=0, column=0, padx=(0, 4))
        ttk.Entry(rule_bar, textvariable=self.date_var, width=12).grid(row=0, column=1, padx=(0, 8))
        ttk.Label(rule_bar, text="매체").grid(row=0, column=2, padx=(0, 4))
        ttk.Entry(rule_bar, textvariable=self.media_var, width=8).grid(row=0, column=3, padx=(0, 8))
        ttk.Label(rule_bar, text="시작 페이지").grid(row=0, column=4, padx=(0, 4))
        ttk.Entry(rule_bar, textvariable=self.page_var, width=7).grid(row=0, column=5, padx=(0, 16))

        ttk.Label(rule_bar, text="프리셋").grid(row=0, column=6, padx=(0, 6))
        preset = ttk.Combobox(rule_bar, textvariable=self.preset_var, values=list(RULE_PRESETS), width=18, state="readonly")
        preset.grid(row=0, column=7, padx=(0, 8))
        preset.bind("<<ComboboxSelected>>", self.apply_preset)

        ttk.Entry(rule_bar, textvariable=self.rule_var).grid(row=0, column=8, sticky="ew", padx=(0, 8))
        ttk.Button(rule_bar, text="미리보기", command=self.refresh_preview).grid(row=0, column=9, padx=(0, 6))
        ttk.Button(rule_bar, text="CSV 저장", command=self.export_preview).grid(row=0, column=10, padx=(0, 6))
        ttk.Button(rule_bar, text="변경 실행", command=self.rename_ready).grid(row=0, column=11, padx=(0, 6))
        ttk.Button(rule_bar, text="마지막 배치 취소", command=self.undo_batch).grid(row=0, column=12)

    def _build_filter_bar(self) -> None:
        filter_bar = ttk.Frame(self, padding=(12, 0, 12, 8))
        filter_bar.grid(row=2, column=0, sticky="ew")
        filter_bar.columnconfigure(1, weight=1)

        ttk.Label(filter_bar, text="검색").grid(row=0, column=0, padx=(0, 6))
        ttk.Entry(filter_bar, textvariable=self.search_var).grid(row=0, column=1, sticky="ew", padx=(0, 12))
        ttk.Label(filter_bar, text="상태").grid(row=0, column=2, padx=(0, 6))
        ttk.Combobox(
            filter_bar,
            textvariable=self.status_filter_var,
            values=STATUS_FILTERS,
            width=12,
            state="readonly",
        ).grid(row=0, column=3)

    def _build_summary(self) -> None:
        summary = ttk.Frame(self, padding=(12, 0, 12, 8))
        summary.grid(row=3, column=0, sticky="ew")
        summary.columnconfigure(0, weight=1)
        ttk.Label(summary, textvariable=self.status_var).grid(row=0, column=0, sticky="w")

    def _build_table(self) -> None:
        content = ttk.Frame(self, padding=(12, 0, 12, 8))
        content.grid(row=4, column=0, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.rowconfigure(0, weight=1)

        columns = ("source", "target", "status", "message")
        self.table = ttk.Treeview(content, columns=columns, show="headings", selectmode="extended")
        self.table.heading("source", text="원본 경로")
        self.table.heading("target", text="변경 예정 파일명")
        self.table.heading("status", text="상태")
        self.table.heading("message", text="메시지")
        self.table.column("source", width=470)
        self.table.column("target", width=280)
        self.table.column("status", width=90, anchor="center")
        self.table.column("message", width=280)
        self.table.tag_configure("ready", foreground="#0f7b3d")
        self.table.tag_configure("conflict", foreground="#b35a00")
        self.table.tag_configure("error", foreground="#b00020")
        self.table.tag_configure("skip", foreground="#606770")
        self.table.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(content, orient="vertical", command=self.table.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.table.configure(yscrollcommand=scrollbar.set)

    def _build_bottom_bar(self) -> None:
        bottom = ttk.Frame(self, padding=(12, 0, 12, 12))
        bottom.grid(row=5, column=0, sticky="ew")
        bottom.columnconfigure(0, weight=1)
        ttk.Button(bottom, text="Assistant", command=self.open_assistant).grid(row=0, column=2, padx=(6, 0))
        ttk.Label(bottom, text="검수 후 변경 실행을 누르세요. CSV 저장은 작업 전 공유/승인용으로 사용할 수 있습니다.").grid(row=0, column=0, sticky="w")
        ttk.Button(bottom, text="히스토리 보기", command=self.show_history).grid(row=0, column=1)

    def apply_preset(self, _event: object | None = None) -> None:
        self.rule_var.set(RULE_PRESETS[self.preset_var.get()])
        self.refresh_preview()

    def load_selected_profile(self) -> None:
        name = self.profile_var.get()
        profile = self.profiles.get(name)
        if profile is None:
            messagebox.showinfo("Nuri Assistant", "불러올 프로필을 선택하세요.")
            return
        self.date_var.set(profile.date)
        self.media_var.set(profile.media)
        self.page_var.set(profile.page)
        self.rule_var.set(profile.rule)
        self.recursive_var.set(profile.recursive)
        self.refresh_preview()
        self.status_var.set(f"'{profile.name}' 프로필을 불러왔습니다.")

    def save_current_profile(self) -> None:
        name = simpledialog.askstring("작업 프로필 저장", "프로필 이름을 입력하세요.", parent=self)
        if not name:
            return
        profile = WorkProfile(
            name=name.strip(),
            date=self.date_var.get(),
            media=self.media_var.get(),
            page=self.page_var.get() or "001",
            rule=self.rule_var.get() or DEFAULT_RULE,
            recursive=self.recursive_var.get(),
        )
        save_profile(PROFILES_PATH, profile)
        self.profiles = load_profiles(PROFILES_PATH)
        self.profile_combo.configure(values=sorted(self.profiles))
        self.profile_var.set(profile.name)
        self.status_var.set(f"'{profile.name}' 프로필을 저장했습니다.")

    def add_files(self) -> None:
        selected = filedialog.askopenfilenames(
            title="변경할 파일 선택",
            filetypes=[
                ("문서/이미지", "*.pdf *.doc *.docx *.hwp *.hwpx *.jpg *.jpeg *.png *.tif *.tiff"),
                ("All files", "*.*"),
            ],
        )
        self._add_paths(Path(file_name) for file_name in selected)

    def add_folder(self) -> None:
        selected = filedialog.askdirectory(title="스캔할 폴더 선택")
        if not selected:
            return
        try:
            paths = scan_files(Path(selected), recursive=self.recursive_var.get())
        except Exception as exc:  # noqa: BLE001 - GUI에서 사용자에게 오류를 보여준다.
            messagebox.showerror("폴더 스캔 실패", str(exc))
            return
        self._add_paths(paths)

    def _add_paths(self, paths: object) -> None:
        added = 0
        for path in paths:
            if isinstance(path, Path) and path not in self.files:
                self.files.append(path)
                added += 1

        if self.files:
            metadata = infer_metadata(self.files[0])
            if not self.date_var.get():
                self.date_var.set(metadata["date"])
            if not self.media_var.get():
                self.media_var.set(metadata["media"])
            if not self.page_var.get():
                self.page_var.set(metadata["page"])
        self.refresh_preview()
        if added:
            self.status_var.set(f"{added}개 파일을 추가했습니다.")

    def remove_selected(self) -> None:
        selected = set(self.table.selection())
        if not selected:
            messagebox.showinfo("Nuri Assistant", "제거할 항목을 선택하세요.")
            return
        paths_to_remove = {
            Path(str(self.table.item(item_id, "values")[0]))
            for item_id in selected
        }
        self.files = [path for path in self.files if path not in paths_to_remove]
        self.refresh_preview()
        self.status_var.set(f"{len(paths_to_remove)}개 항목을 목록에서 제거했습니다.")

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

    def _previews(self) -> list:
        return preview_batch(self._items())

    def _filtered_previews(self) -> list:
        search = self.search_var.get().strip().lower()
        status_filter = self.status_filter_var.get()
        previews = self._previews()
        if status_filter != "전체":
            previews = [preview for preview in previews if preview.status == status_filter]
        if search:
            previews = [
                preview
                for preview in previews
                if search in str(preview.source).lower()
                or search in preview.target.name.lower()
                or search in preview.status.lower()
                or search in preview.message.lower()
            ]
        return previews

    def refresh_preview(self) -> None:
        for row in self.table.get_children():
            self.table.delete(row)

        all_previews = self._previews()
        visible_previews = self._filtered_previews()
        for preview in visible_previews:
            self.table.insert(
                "",
                "end",
                values=(str(preview.source), preview.target.name, preview.status, preview.message),
                tags=(preview.status,),
            )
        ready_count = sum(1 for item in all_previews if item.status == "ready")
        conflict_count = sum(1 for item in all_previews if item.status == "conflict")
        error_count = sum(1 for item in all_previews if item.status == "error")
        hidden_count = len(all_previews) - len(visible_previews)
        self.status_var.set(
            f"총 {len(all_previews)}개 | 표시 {len(visible_previews)}개 | 변경 가능 {ready_count}개 "
            f"| 충돌 {conflict_count}개 | 오류 {error_count}개 | 숨김 {hidden_count}개"
        )

    def export_preview(self) -> None:
        previews = self._previews()
        if not previews:
            messagebox.showinfo("Nuri Assistant", "저장할 미리보기가 없습니다.")
            return
        output = filedialog.asksaveasfilename(
            title="미리보기 CSV 저장",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="nf-file-engine-preview.csv",
        )
        if not output:
            return
        export_preview_csv(previews, Path(output))
        messagebox.showinfo("CSV 저장 완료", output)

    def rename_ready(self) -> None:
        previews = self._previews()
        ready = [preview for preview in previews if preview.status == "ready"]
        blocked = [preview for preview in previews if preview.status in {"conflict", "error"}]
        if not ready:
            messagebox.showinfo("Nuri Assistant", "변경 가능한 파일이 없습니다.")
            return
        if blocked:
            proceed = messagebox.askyesno(
                "일부 파일 제외",
                f"충돌/오류 {len(blocked)}개를 제외하고 {len(ready)}개 파일명을 변경할까요?",
            )
        else:
            proceed = messagebox.askyesno("변경 실행", f"{len(ready)}개 파일명을 변경할까요?")
        if not proceed:
            return

        try:
            changed = apply_batch_rename(previews, self.history)
        except Exception as exc:  # noqa: BLE001 - GUI에서 사용자에게 오류를 보여준다.
            messagebox.showerror("변경 실패", str(exc))
            self.refresh_preview()
            return
        self.files = [path for path in self.files if path.exists()]
        self.refresh_preview()
        self.status_var.set(f"{len(changed)}개 파일명을 변경했습니다.")

    def undo_batch(self) -> None:
        if not messagebox.askyesno("마지막 배치 취소", "마지막 변경 묶음을 되돌릴까요?"):
            return
        try:
            restored = undo_last_batch(self.history)
        except Exception as exc:  # noqa: BLE001 - GUI에서 사용자에게 오류를 보여준다.
            messagebox.showerror("취소 실패", str(exc))
            return
        messagebox.showinfo("변경 취소", f"{len(restored)}개 파일을 되돌렸습니다.")
        self.refresh_preview()

    def show_history(self) -> None:
        window = tk.Toplevel(self)
        window.title("변경 히스토리")
        window.geometry("900x420")

        columns = ("batch_id", "created_at", "item_count", "undone_count")
        table = ttk.Treeview(window, columns=columns, show="headings")
        for column, label, width in [
            ("batch_id", "배치 ID", 220),
            ("created_at", "작업일", 180),
            ("item_count", "파일 수", 90),
            ("undone_count", "취소 수", 90),
        ]:
            table.heading(column, text=label)
            table.column(column, width=width)
        table.pack(fill="both", expand=True, padx=12, pady=12)

        for row in self.history.recent_batches(limit=100):
            table.insert(
                "",
                "end",
                values=(row["batch_id"], row["created_at"], row["item_count"], row["undone_count"]),
            )


def run() -> None:
    NuriAssistantApp().mainloop()
