from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from ..assistant import interpret_file_command
from ..core import RenameInput, apply_batch_rename, preview_batch, scan_files
from ..shopping import ProductCandidate, evaluate_purchase
from ..storage import HistoryStore


class AssistantWindow(tk.Toplevel):
    """A review-first desktop assistant for file organization and purchase choices."""

    def __init__(self, parent: tk.Misc, history: HistoryStore) -> None:
        super().__init__(parent)
        self.title("Nuri Assistant")
        self.geometry("1060x700")
        self.minsize(900, 580)
        self.history = history
        self.file_previews = []
        self.products: list[ProductCandidate] = []

        self.folder_var = tk.StringVar()
        self.command_var = tk.StringVar(value="20260715 ja00 1부터 파일명 정리해줘")
        self.file_status_var = tk.StringVar(value="폴더와 요청을 입력하면 실행 전 변경 목록을 만듭니다.")
        self.product_name_var = tk.StringVar()
        self.price_var = tk.StringVar()
        self.rating_var = tk.StringVar(value="0")
        self.review_count_var = tk.StringVar(value="0")
        self.warranty_var = tk.StringVar(value="0")
        self.suitability_var = tk.StringVar(value="3")
        self.target_var = tk.BooleanVar(value=True)
        self.purchase_status_var = tk.StringVar(value="현재 관심 제품과 대안을 추가해 비교하세요.")

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=12, pady=12)
        files_tab = ttk.Frame(notebook, padding=12)
        shopping_tab = ttk.Frame(notebook, padding=12)
        notebook.add(files_tab, text="파일 비서")
        notebook.add(shopping_tab, text="구매 비서")
        self._build_file_tab(files_tab)
        self._build_shopping_tab(shopping_tab)

    def _build_file_tab(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(1, weight=1)
        parent.rowconfigure(3, weight=1)

        ttk.Label(parent, text="정리할 폴더").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=(0, 8))
        ttk.Entry(parent, textvariable=self.folder_var).grid(row=0, column=1, sticky="ew", pady=(0, 8))
        ttk.Button(parent, text="폴더 선택", command=self.choose_folder).grid(row=0, column=2, padx=(8, 0), pady=(0, 8))
        ttk.Label(parent, text="요청").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=(0, 8))
        ttk.Entry(parent, textvariable=self.command_var).grid(row=1, column=1, sticky="ew", pady=(0, 8))
        ttk.Button(parent, text="명령 해석", command=self.plan_file_command).grid(row=1, column=2, padx=(8, 0), pady=(0, 8))
        ttk.Label(parent, textvariable=self.file_status_var, wraplength=850).grid(row=2, column=0, columnspan=3, sticky="w", pady=(0, 8))

        columns = ("source", "target", "status", "message")
        self.file_table = ttk.Treeview(parent, columns=columns, show="headings", selectmode="none")
        for column, label, width in (
            ("source", "원본 경로", 410),
            ("target", "변경 예정", 270),
            ("status", "상태", 90),
            ("message", "확인 내용", 220),
        ):
            self.file_table.heading(column, text=label)
            self.file_table.column(column, width=width)
        self.file_table.grid(row=3, column=0, columnspan=3, sticky="nsew")
        ttk.Button(parent, text="미리보기 적용", command=self.apply_file_plan).grid(row=4, column=2, sticky="e", pady=(10, 0))

    def _build_shopping_tab(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(1, weight=1)
        parent.rowconfigure(2, weight=1)
        form = ttk.Frame(parent)
        form.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        for index in range(12):
            form.columnconfigure(index, weight=1 if index in {1, 3} else 0)

        fields = (
            ("제품", self.product_name_var, 0, 20),
            ("가격", self.price_var, 2, 10),
            ("평점", self.rating_var, 4, 6),
            ("리뷰", self.review_count_var, 6, 9),
            ("보증(월)", self.warranty_var, 8, 7),
            ("적합도(1-5)", self.suitability_var, 10, 8),
        )
        for label, variable, column, width in fields:
            ttk.Label(form, text=label).grid(row=0, column=column, sticky="w", padx=(0, 4))
            ttk.Entry(form, textvariable=variable, width=width).grid(row=0, column=column + 1, sticky="ew", padx=(0, 8))
        ttk.Checkbutton(form, text="내가 보고 있는 제품", variable=self.target_var).grid(row=1, column=0, columnspan=3, sticky="w", pady=(8, 0))
        ttk.Button(form, text="제품 추가", command=self.add_product).grid(row=1, column=10, columnspan=2, sticky="e", pady=(8, 0))

        columns = ("target", "name", "price", "rating", "reviews", "warranty", "fit", "score", "evidence")
        self.product_table = ttk.Treeview(parent, columns=columns, show="headings", selectmode="browse")
        widths = (70, 220, 100, 70, 90, 90, 80, 80, 90)
        labels = ("관심", "제품", "가격", "평점", "리뷰", "보증", "적합도", "점수", "근거")
        for column, label, width in zip(columns, labels, widths):
            self.product_table.heading(column, text=label)
            self.product_table.column(column, width=width, anchor="center" if column != "name" else "w")
        self.product_table.grid(row=2, column=0, columnspan=3, sticky="nsew")
        ttk.Label(parent, textvariable=self.purchase_status_var, wraplength=900).grid(row=3, column=0, columnspan=2, sticky="w", pady=(10, 0))
        actions = ttk.Frame(parent)
        actions.grid(row=3, column=2, sticky="e", pady=(10, 0))
        ttk.Button(actions, text="선택 삭제", command=self.remove_product).pack(side="left", padx=(0, 6))
        ttk.Button(actions, text="가성비 평가", command=self.evaluate_products).pack(side="left")

    def choose_folder(self) -> None:
        folder = filedialog.askdirectory(parent=self, title="정리할 폴더 선택")
        if folder:
            self.folder_var.set(folder)

    def plan_file_command(self) -> None:
        folder_text = self.folder_var.get().strip()
        if not folder_text:
            messagebox.showinfo("Nuri Assistant", "정리할 폴더를 먼저 선택하세요.", parent=self)
            return
        folder = Path(folder_text)
        try:
            plan = interpret_file_command(self.command_var.get())
            paths = scan_files(folder, recursive=plan.recursive)
        except Exception as exc:  # noqa: BLE001 - present input errors in the desktop UI
            messagebox.showerror("명령 해석 실패", str(exc), parent=self)
            return

        if plan.needs_media:
            self.file_status_var.set("매체 코드(예: ja00)를 찾지 못했습니다. 요청에 코드가 있어야 실행 계획을 만들 수 있습니다.")
            self.file_previews = []
            self._render_file_previews()
            return
        items = [
            RenameInput(path, plan.date, plan.media, str(int(plan.page) + index).zfill(3), plan.rule)
            for index, path in enumerate(paths)
        ]
        self.file_previews = preview_batch(items)
        ready = sum(preview.status == "ready" for preview in self.file_previews)
        blocked = len(self.file_previews) - ready
        scope = "하위 폴더 포함" if plan.recursive else "선택 폴더만"
        self.file_status_var.set(
            f"해석: 날짜 {plan.date}, 매체 {plan.media}, 시작 페이지 {plan.page}, {scope}. "
            f"{len(paths)}개 검사 완료, {ready}개 변경 가능, {blocked}개 확인 필요."
        )
        self._render_file_previews()

    def _render_file_previews(self) -> None:
        for item in self.file_table.get_children():
            self.file_table.delete(item)
        for preview in self.file_previews:
            self.file_table.insert(
                "",
                "end",
                values=(str(preview.source), preview.target.name, preview.status, preview.message),
            )

    def apply_file_plan(self) -> None:
        ready = [preview for preview in self.file_previews if preview.status == "ready"]
        if not ready:
            messagebox.showinfo("Nuri Assistant", "적용할 수 있는 파일 변경이 없습니다.", parent=self)
            return
        if not messagebox.askyesno("파일 변경 확인", f"{len(ready)}개 파일 이름을 변경할까요?", parent=self):
            return
        try:
            changed = apply_batch_rename(self.file_previews, self.history)
        except Exception as exc:  # noqa: BLE001 - core operation retains rollback behavior
            messagebox.showerror("변경 실패", str(exc), parent=self)
            return
        self.file_status_var.set(f"{len(changed)}개 파일 이름을 변경했습니다. 기존 화면의 최근 배치 취소로 되돌릴 수 있습니다.")
        self.file_previews = []
        self._render_file_previews()

    def add_product(self) -> None:
        try:
            product = ProductCandidate(
                name=self.product_name_var.get().strip(),
                price=int(self.price_var.get().replace(",", "").strip()),
                rating=float(self.rating_var.get().strip() or 0),
                review_count=int(self.review_count_var.get().replace(",", "").strip() or 0),
                warranty_months=int(self.warranty_var.get().strip() or 0),
                suitability=int(self.suitability_var.get().strip() or 3),
                is_target=self.target_var.get(),
            )
        except ValueError as exc:
            messagebox.showerror("제품 정보 확인", str(exc), parent=self)
            return
        if product.is_target:
            self.products = [candidate for candidate in self.products if not candidate.is_target]
        self.products.append(product)
        self.product_name_var.set("")
        self.price_var.set("")
        self.target_var.set(False)
        self._render_products()
        self.purchase_status_var.set(f"{len(self.products)}개 제품을 비교 목록에 담았습니다.")

    def remove_product(self) -> None:
        selected = self.product_table.selection()
        if not selected:
            return
        index = int(selected[0])
        del self.products[index]
        self._render_products()
        self.purchase_status_var.set(f"{len(self.products)}개 제품이 남았습니다.")

    def evaluate_products(self) -> None:
        try:
            assessments = evaluate_purchase(self.products)
        except ValueError as exc:
            messagebox.showinfo("구매 비서", str(exc), parent=self)
            return
        self._render_products(assessments)
        best = assessments[0]
        target = next((assessment for assessment in assessments if assessment.product.is_target), None)
        if target is None:
            summary = f"1위는 {best.product.name} ({best.score:.1f}점)입니다. 관심 제품을 지정하면 직접 비교합니다."
        elif best.product.is_target:
            summary = f"현재 보고 있는 {target.product.name}이 {target.score:.1f}점으로 1위입니다."
        else:
            summary = (
                f"대안 {best.product.name}이 {best.score:.1f}점으로 관심 제품 "
                f"{target.product.name}({target.score:.1f}점)보다 높습니다."
            )
        self.purchase_status_var.set(summary + " 점수는 입력한 가격·평점·리뷰·보증·적합도만을 근거로 합니다.")

    def _render_products(self, assessments: list | None = None) -> None:
        for item in self.product_table.get_children():
            self.product_table.delete(item)
        by_name = {assessment.product.name: assessment for assessment in assessments or []}
        for index, product in enumerate(self.products):
            assessment = by_name.get(product.name)
            self.product_table.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    "관심" if product.is_target else "대안",
                    product.name,
                    f"{product.price:,}",
                    f"{product.rating:.1f}" if product.rating else "-",
                    f"{product.review_count:,}" if product.review_count else "-",
                    product.warranty_months or "-",
                    f"{product.suitability}/5",
                    f"{assessment.score:.1f}" if assessment else "-",
                    assessment.evidence_level if assessment else "-",
                ),
            )
