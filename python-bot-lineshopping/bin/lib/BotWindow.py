"""หน้าต่างบอท 1 หน้าต่างต่อ 1 ไฟล์บอท (ui = "window" ใน CONFIG)

ใช้เครื่องยนต์เดิมใน RunBot ทั้งหมด หน้าต่างแค่รับค่าแทนการพิมพ์ใน terminal
งานที่ช้า (ตรวจรหัส / อ่านสินค้า / ซื้อ) ทำใน thread แยก หน้าต่างไม่ค้าง
"""
import os
import queue
import re
import sys
import threading
import tkinter as tk
from datetime import datetime
from tkinter import font as tkfont
from tkinter import messagebox, ttk

from bin.lib.ApiLineShopping import ApiiLineShopping
from bin.lib.RunBot import (StopRequested, TokenFailed, bot_folder, bot_id, buy_flow, clean_token, explain_error,
                            PRODUCT_HINT, parse_product_url, parse_sale_time, profile_dir_for, read_token_file,
                            token_file_for, try_login)
from bin.lib.ToolsLineShopping import ToolsLineShopping

FONT_CHOICES = ["Leelawadee UI", "Leelawadee", "Tahoma"]
GREEN = "#1a7f37"
RED = "#c62828"
BLUE = "#1f5fa8"
GREY = "#555555"

SIZE_RE = re.compile(r"^(XXXS|XXS|XS|S|M|L|XL|XXL|XXXL|\d?XL|FREE\s*SIZE|FREESIZE|F|\d+\s*(M|Y|MONTHS?|YRS?))$",
                     re.IGNORECASE)


def looks_like_size(values):
    values = [str(v).strip() for v in values if str(v or "").strip()]
    return bool(values) and all(SIZE_RE.match(v) for v in values)


def bot_title(config):
    name = os.path.basename(str(config.get("__file__") or "bot.py"))
    match = re.search(r"(\d+)", name)
    return f"บอท {match.group(1)}" if match else "บอท"


class QueueWriter:
    """แทน sys.stdout: ข้อความที่เครื่องยนต์ print ไปลงคิว หน้าต่างดึงไปแสดงทุก 100 ms"""

    def __init__(self, q):
        self.q = q
        self.buffer = ""

    def write(self, text):
        self.buffer += str(text)
        while True:
            cut = [i for i in (self.buffer.find("\n"), self.buffer.find("\r")) if i >= 0]
            if not cut:
                break
            i = min(cut)
            line, sep, self.buffer = self.buffer[:i], self.buffer[i], self.buffer[i + 1:]
            if line or sep == "\n":
                self.q.put(("line", line))
        return len(text)

    def flush(self):
        pass


class BotWindow:
    def __init__(self, config, api_factory=None, capture_func=None, root=None):
        self.config = config
        self.api_factory = api_factory or ApiiLineShopping
        self.capture_func = capture_func
        self.token_file = token_file_for(config)  # token_<bot>.txt: this bot's own account only

        self.root = root or tk.Tk()
        self.log_queue = queue.Queue()
        self.ui_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.worker = None
        self.running = False

        self.api = None
        self.display_name = None
        self.data_product = None
        self.shop_name = None
        self.id_product = None
        self.option_maps = {"number": {}, "size": {}}
        self.variants = []
        self.number_key = None
        self.size_key = None

        self.old_stdout = sys.stdout
        sys.stdout = QueueWriter(self.log_queue)

        self._fonts()
        self._build()
        self._prefill()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(100, self._drain)

    # ---------- หน้าตา ----------

    def _fonts(self):
        families = set(tkfont.families(self.root))
        family = next((f for f in FONT_CHOICES if f in families), "Tahoma")
        self.font = (family, 12)
        self.font_bold = (family, 12, "bold")
        self.font_status = (family, 16, "bold")
        self.font_count = (family, 28, "bold")
        style = ttk.Style(self.root)
        for name in ("TLabel", "TButton", "TCheckbutton", "TEntry", "TCombobox", "TLabelframe.Label"):
            style.configure(name, font=self.font)
        style.configure("Big.TButton", font=self.font_status, padding=(18, 8))
        self.root.option_add("*TCombobox*Listbox.font", self.font)

    def _build(self):
        root = self.root
        root.title(f"{bot_title(self.config)} · ยังไม่ได้ตรวจรหัส")
        root.configure(padx=14, pady=10)
        root.columnconfigure(0, weight=1)

        # 1) รหัส
        box = ttk.LabelFrame(root, text="1. รหัส (Token)", padding=8)
        box.grid(row=0, column=0, sticky="ew", pady=4)
        box.columnconfigure(0, weight=1)
        self.token_var = tk.StringVar()
        ttk.Entry(box, textvariable=self.token_var, show="•", font=self.font).grid(row=0, column=0, sticky="ew")
        ttk.Button(box, text="วาง", command=lambda: self._paste(self.token_var)).grid(row=0, column=1, padx=4)
        ttk.Button(box, text="ตรวจรหัส", command=self.check_token).grid(row=0, column=2, padx=4)
        ttk.Button(box, text="ดึงรหัสอัตโนมัติ", command=self.auto_token).grid(row=0, column=3, padx=4)
        self.account_label = tk.Label(box, text="ยังไม่ได้ตรวจรหัส", font=self.font, fg=GREY, anchor="w",
                                      justify="left", wraplength=620)
        self.account_label.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(6, 0))

        # 2) ลิงก์สินค้า หรือ ชื่อร้าน + เลข ID
        box = ttk.LabelFrame(root, text="2. ลิงก์สินค้า หรือ ชื่อร้าน + เลข ID", padding=8)
        box.grid(row=1, column=0, sticky="ew", pady=4)
        box.columnconfigure(0, weight=1)
        self.link_var = tk.StringVar()
        ttk.Entry(box, textvariable=self.link_var, font=self.font).grid(row=0, column=0, sticky="ew")
        ttk.Button(box, text="วาง", command=lambda: self._paste(self.link_var)).grid(row=0, column=1, padx=4)
        ttk.Button(box, text="อ่านสินค้า", command=self.read_product).grid(row=0, column=2, padx=4)
        tk.Label(box, text="เช่น https://shop.line.me/@babylovett/product/1008483011  หรือ  @babylovett 1008483011",
                 font=(self.font[0], 10), fg=GREY, anchor="w").grid(row=1, column=0, columnspan=3, sticky="ew", pady=(2, 0))
        self.product_label = tk.Label(box, text="ยังไม่ได้อ่านสินค้า", font=self.font, fg=GREY, anchor="w",
                                      justify="left", wraplength=620)
        self.product_label.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(6, 0))

        # 3) ตัวเลือก
        box = ttk.LabelFrame(root, text="3. ตัวเลือกสินค้า", padding=8)
        box.grid(row=2, column=0, sticky="ew", pady=4)
        self.number_label = ttk.Label(box, text="Number")
        self.number_var = tk.StringVar()
        self.number_box = ttk.Combobox(box, textvariable=self.number_var, state="readonly", width=18, font=self.font)
        self.size_label = ttk.Label(box, text="Size")
        self.size_var = tk.StringVar()
        self.size_box = ttk.Combobox(box, textvariable=self.size_var, state="readonly", width=18, font=self.font)
        self.number_box.bind("<<ComboboxSelected>>", lambda e: (self._refresh_sizes(), self._update_start()))
        self.size_box.bind("<<ComboboxSelected>>", lambda e: self._update_start())
        self.options_hint = ttk.Label(box, text="อ่านสินค้าก่อน แล้วรายการจะขึ้นที่นี่", foreground=GREY)
        self.options_hint.grid(row=0, column=0, columnspan=4, sticky="w")
        self.options_box = box

        # 4) วันเวลาเปิดขาย
        box = ttk.LabelFrame(root, text="4. วันเวลาเปิดขาย", padding=8)
        box.grid(row=3, column=0, sticky="ew", pady=4)
        ttk.Label(box, text="วันที่ (วว/ดด/ปปปป)").grid(row=0, column=0, sticky="w")
        self.date_var = tk.StringVar(value=datetime.now().strftime("%d/%m/%Y"))
        ttk.Entry(box, textvariable=self.date_var, width=12, font=self.font).grid(row=0, column=1, padx=(4, 16))
        ttk.Label(box, text="เวลา (ชช:นน)").grid(row=0, column=2, sticky="w")
        self.time_var = tk.StringVar()
        ttk.Entry(box, textvariable=self.time_var, width=10, font=self.font).grid(row=0, column=3, padx=(4, 16))
        self.now_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(box, text="เริ่มทันที (ไม่รอเวลา)", variable=self.now_var).grid(row=0, column=4, sticky="w")

        # 5) ปุ่ม
        row = ttk.Frame(root)
        row.grid(row=4, column=0, sticky="ew", pady=8)
        self.start_btn = ttk.Button(row, text="เริ่ม", style="Big.TButton", command=self.start, state="disabled")
        self.start_btn.pack(side="left")
        self.stop_btn = ttk.Button(row, text="หยุด", style="Big.TButton", command=self.stop, state="disabled")
        self.stop_btn.pack(side="left", padx=10)

        # 6) สถานะ
        self.status_label = tk.Label(root, text="ยังไม่พร้อม", font=self.font_status, fg=GREY, anchor="w")
        self.status_label.grid(row=5, column=0, sticky="ew")
        self.count_label = tk.Label(root, text="", font=self.font_count, fg=BLUE, anchor="w")
        self.count_label.grid(row=6, column=0, sticky="ew")
        frame = ttk.Frame(root)
        frame.grid(row=7, column=0, sticky="nsew", pady=(4, 0))
        root.rowconfigure(7, weight=1)
        self.log = tk.Text(frame, height=8, width=80, font=self.font, state="disabled", wrap="word",
                           background="#f6f6f6")
        scroll = ttk.Scrollbar(frame, command=self.log.yview)
        self.log.configure(yscrollcommand=scroll.set)
        self.log.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

    # ---------- ตัวช่วย ----------

    def _paste(self, var):
        try:
            var.set(self.root.clipboard_get().strip())
        except tk.TclError:
            pass

    def ui(self, func, *args):
        """เรียกจาก thread งาน: ให้ thread หน้าต่างเป็นคนแตะ widget"""
        self.ui_queue.put((func, args))

    def _drain(self):
        try:
            while True:
                kind, line = self.log_queue.get_nowait()
                self._append_log(line)
        except queue.Empty:
            pass
        try:
            while True:
                func, args = self.ui_queue.get_nowait()
                func(*args)
        except queue.Empty:
            pass
        if self.root.winfo_exists():
            self.root.after(100, self._drain)

    def _append_log(self, line):
        self.log.configure(state="normal")
        self.log.insert("end", line + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def say(self, text):
        print(text)

    def set_status(self, text, color):
        self.status_label.configure(text=text, fg=color)

    def _thread(self, target, *args):
        def runner():
            try:
                target(*args)
            except BaseException as e:  # ไม่ให้ traceback หลุดไปหน้าจอเธอ
                self.say(explain_error("bot", e))
        threading.Thread(target=runner, daemon=True).start()

    # ---------- ค่าตั้งต้น ----------

    def _prefill(self):
        get = self.config.get
        token = clean_token(get("token", "")) or read_token_file(self.token_file)
        self.token_var.set(token)

        link = str(get("product_url", "") or "").strip()
        if not link and get("shop_name") and get("id_product"):
            link = f"https://shop.line.me/{get('shop_name')}/product/{get('id_product')}"
        self.link_var.set(link)

        if token:
            self.check_token()
        if link:
            self.read_product()

    # ---------- รหัส ----------

    def check_token(self):
        token = clean_token(self.token_var.get())
        self.token_var.set(token)
        if not token:
            self.account_label.configure(text="ยังไม่ได้ใส่รหัส — วางรหัสหรือกดดึงรหัสอัตโนมัติ", fg=RED)
            return
        self.account_label.configure(text="กำลังตรวจรหัส …", fg=GREY)
        self._thread(self._check_token_job, token)

    def _check_token_job(self, token):
        api = self.api_factory(token)
        try:
            profile = api.profile()
            name = (profile or {}).get("displayName")
        except Exception as e:
            name = None
            message = explain_error("profile", e)
        else:
            message = "Login ไม่สำเร็จ เก็บ Token มาใส่ใหม่"
        if not name:
            try:
                api.close()
            except Exception:
                pass
            self.ui(self._token_result, None, None, message)
            return
        try:
            with open(self.token_file, "w", encoding="utf-8") as f:
                f.write(token)
        except OSError:
            pass
        self.ui(self._token_result, api, name, None)

    def _token_result(self, api, name, message):
        if self.api is not None and self.api is not api:
            try:
                self.api.close()
            except Exception:
                pass
        self.api = api
        self.display_name = name
        if api is None:
            self.account_label.configure(text=message, fg=RED)
            self.say(message)
        else:
            self.account_label.configure(text=f"✓ บัญชี: {name}", fg=GREEN)
            self.say(f"เข้าสู่ระบบเป็น: {name}")
        self._update_title()
        self._update_start()

    def _update_title(self):
        """บอท 1 · <ชื่อบัญชี> · <ร้าน> — หลายหน้าต่างก็แยกออกได้ทันที (รวมบน taskbar)"""
        parts = [bot_title(self.config), self.display_name or "ยังไม่ได้ตรวจรหัส"]
        if self.shop_name:
            parts.append(self.shop_name)
        self.root.title(" · ".join(parts))

    def auto_token(self):
        self.account_label.configure(text="กำลังเปิด Chrome ให้เข้าสู่ระบบ LINE …", fg=GREY)
        self._thread(self._auto_token_job)

    def _auto_token_job(self):
        capture = self.capture_func
        if capture is None:
            try:
                from get_token import capture_token
            except ImportError:
                self.ui(self.account_label.configure, {"text": "ไม่พบไฟล์ get_token.py ในโฟลเดอร์บอท", "fg": RED})
                return
            # Chrome ของบอทนี้เอง: บอทแต่ละตัวจำการเข้าระบบ LINE ของบัญชีตัวเอง
            profile = profile_dir_for(bot_id(self.config), bot_folder(self.config))

            def capture(out):
                return capture_token(out=out, profile_dir=profile)
        token = capture(out=self.say)
        if not token:
            self.ui(self._auto_token_failed)
            return
        self.say("เจอรหัสแล้ว ✓")
        self.ui(self.token_var.set, token)
        self._check_token_job(token)

    def _auto_token_failed(self):
        self.account_label.configure(text="ดึงรหัสไม่สำเร็จ — ดูข้อความด้านล่าง หรือวางรหัสเอง", fg=RED)

    # ---------- สินค้า ----------

    def read_product(self):
        parsed = parse_product_url(self.link_var.get())
        if not parsed:
            self.product_label.configure(text=PRODUCT_HINT, fg=RED)
            return
        self.product_label.configure(text="กำลังอ่านสินค้า …", fg=GREY)
        self._thread(self._read_product_job, *parsed)

    def _read_product_job(self, shop_name, id_product):
        api = self.api_factory("")
        try:
            data = api.info_product(shop_name, id_product)
        except Exception as e:
            self.ui(self._product_result, None, shop_name, id_product, explain_error("product", e))
            return
        finally:
            try:
                api.close()
            except Exception:
                pass
        self.ui(self._product_result, data, shop_name, id_product, None)

    def _product_result(self, data, shop_name, id_product, message):
        if data is None:
            self.data_product = None
            self.product_label.configure(text=message, fg=RED)
            self.say(message)
            self._update_start()
            return
        self.data_product, self.shop_name, self.id_product = data, shop_name, id_product
        product = (data or {}).get("data", {}) or {}
        name = product.get("name") or product.get("product_name") or f"{shop_name} / {id_product}"
        self.product_label.configure(text=f"✓ {name}", fg=GREEN)
        self._update_title()
        self._build_options(product)
        self._update_start()

    def _build_options(self, product):
        for widget in (self.number_label, self.number_box, self.size_label, self.size_box, self.options_hint):
            widget.grid_forget()
        variants = product.get("product_variants") or [] if product.get("has_variant") else []
        self.variants = variants
        if not variants:
            self.options_hint.configure(text="สินค้านี้ไม่มีตัวเลือก")
            self.options_hint.grid(row=0, column=0, sticky="w")
            self.number_var.set("")
            self.size_var.set("")
            return

        values1 = [str(v.get("variant_option_value1") or "") for v in variants]
        values2 = [str(v.get("variant_option_value2") or "") for v in variants]
        two = any(values2)
        if not two:
            self.number_key, self.size_key = None, "variant_option_value1"
            size_text = "Size"
        elif looks_like_size(values2) and not looks_like_size(values1):
            self.number_key, self.size_key = "variant_option_value1", "variant_option_value2"
            number_text, size_text = "Number", "Size"
        elif looks_like_size(values1) and not looks_like_size(values2):
            self.number_key, self.size_key = "variant_option_value2", "variant_option_value1"
            number_text, size_text = "Number", "Size"
        else:
            self.number_key, self.size_key = "variant_option_value1", "variant_option_value2"
            number_text, size_text = "ตัวเลือก 1", "ตัวเลือก 2"

        if self.number_key:
            totals = {}
            for v in variants:
                key = str(v.get(self.number_key) or "")
                totals[key] = totals.get(key, 0) + self._stock(v)
            self.option_maps["number"] = {f"{k} (เหลือ {n})": k for k, n in totals.items()}
            self.number_box["values"] = list(self.option_maps["number"])
            self.number_label.configure(text=number_text)
            self.number_label.grid(row=0, column=0, sticky="w")
            self.number_box.grid(row=0, column=1, padx=(6, 24))
            self._select(self.number_box, self.number_var, "number", self.config.get("number", ""))
        else:
            self.option_maps["number"] = {}
            self.number_var.set("")

        self.size_label.configure(text=size_text)
        self.size_label.grid(row=0, column=2, sticky="w")
        self.size_box.grid(row=0, column=3, padx=6)
        self._refresh_sizes(preselect=self.config.get("size", ""))

    @staticmethod
    def _stock(variant):
        try:
            return int(variant.get("available") or 0)
        except (TypeError, ValueError):
            return 0

    def _select(self, box, var, kind, wanted):
        wanted = str(wanted or "").strip().lower()
        for label, value in self.option_maps[kind].items():
            if wanted and value.strip().lower() == wanted:
                var.set(label)
                return
        var.set("")

    def selected(self, kind):
        return self.option_maps[kind].get((self.number_var if kind == "number" else self.size_var).get(), "")

    def _refresh_sizes(self, preselect=None):
        number = self.selected("number") if self.number_key else None
        current = preselect if preselect is not None else self.selected("size")
        sizes = {}
        for v in self.variants:
            if self.number_key and number and str(v.get(self.number_key) or "") != number:
                continue
            key = str(v.get(self.size_key) or "")
            sizes[key] = sizes.get(key, 0) + self._stock(v)
        self.option_maps["size"] = {f"{k} (เหลือ {n})": k for k, n in sizes.items()}
        self.size_box["values"] = list(self.option_maps["size"])
        self._select(self.size_box, self.size_var, "size", current)

    # ---------- เริ่ม / หยุด ----------

    def _ready(self):
        if self.api is None or self.data_product is None:
            return False
        if not getattr(self, "variants", None):
            return True
        if self.number_key and not self.selected("number"):
            return False
        return bool(self.selected("size"))

    def _update_start(self):
        if self.running:
            return
        ready = self._ready()
        self.start_btn.configure(state="normal" if ready else "disabled")
        if ready:
            self.set_status("พร้อม", GREEN)
        else:
            self.set_status("ยังไม่พร้อม", GREY)

    def _sale_time(self):
        if self.now_var.get():
            return None, None
        date_text = self.date_var.get().strip()
        time_text = self.time_var.get().strip()
        if not time_text:
            return None, "ใส่เวลาเปิดขาย หรือติ๊ก 'เริ่มทันที'"
        try:
            target = parse_sale_time(f"{date_text} {time_text}")
        except ValueError:
            return None, "วันเวลาไม่ถูกต้อง ใส่แบบนี้: 01/12/2026 และ 10:00"
        if target <= datetime.now():
            return None, "เวลาเปิดขายผ่านไปแล้ว — แก้เวลา หรือติ๊ก 'เริ่มทันที'"
        return target, None

    def start(self):
        if not self._ready():
            return
        sale_at, problem = self._sale_time()
        if problem:
            self.set_status(problem, RED)
            return
        tools = ToolsLineShopping(number=self.selected("number") if self.number_key else "")
        size = self.selected("size") if getattr(self, "variants", None) else ""

        # หน้าต่างไม่ใช้โหมดช่วงเวลาเดิม (use_time_mode) และ start_bot_at
        config = dict(self.config, use_time_mode=False, start_bot_at=None)

        self.stop_event.clear()
        self.running = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        if sale_at is not None:
            self.set_status("รอเปิดขาย", BLUE)
            self.say(f"ตั้งเวลาเปิดขาย: {sale_at.strftime('%d/%m/%Y %H:%M:%S')}")
        else:
            self.set_status("กำลังเช็คสินค้า", BLUE)
        self.worker = threading.Thread(
            target=self._buy_job, args=(tools, size, config, sale_at), daemon=True)
        self.worker.start()

    def _relogin(self, current):
        token = read_token_file(self.token_file) or getattr(current, "token", "")
        api, _ = try_login(self.api_factory, token) if token else (None, None)
        if api is not None and current is not None and api is not current:
            try:
                current.close()
            except Exception:
                pass
        return api

    def _tick(self, remaining):
        if remaining <= 0:
            self.ui(self.count_label.configure, {"text": ""})
            self.ui(self.set_status, "กำลังเช็คสินค้า", BLUE)
            return
        total = int(remaining + 0.999)
        hours, rest = divmod(total, 3600)
        minutes, seconds = divmod(rest, 60)
        self.ui(self.count_label.configure, {"text": f"เหลืออีก {hours:02d}:{minutes:02d}:{seconds:02d}"})

    def _buy_job(self, tools, size, config, sale_at):
        holder = {}
        result, color, text = "error", RED, "ผิดพลาด"
        try:
            outcome = buy_flow(self.api, tools, self.shop_name, self.id_product, size,
                               config.get("quantity", 1), config, sale_at,
                               should_stop=self.stop_event.is_set, on_tick=self._tick,
                               relogin=self._relogin, holder=holder)
            if outcome == "ordered":
                color, text = GREEN, "สั่งซื้อแล้ว"
            elif outcome == "found":
                color, text = GREEN, "เจอสินค้าแล้ว (ไม่ได้ตั้งให้สั่งอัตโนมัติ)"
        except StopRequested:
            self.say("หยุดแล้ว")
            color, text = GREY, "หยุดแล้ว"
        except TokenFailed:
            self.say("Token ใช้ไม่ได้ — กดตรวจรหัส/ดึงรหัสใหม่ แล้วกดเริ่มอีกครั้ง")
            holder["api"] = None
        except BaseException as e:  # ไม่ให้ traceback หลุดไปหน้าจอเธอ
            self.say(explain_error("bot", e))
        self.ui(self._job_done, holder.get("api", self.api), color, text)

    def _job_done(self, api, color, text):
        self.running = False
        self.api = api
        if api is None:
            self.display_name = None
            self.account_label.configure(text="Token ใช้ไม่ได้ — กดตรวจรหัส/ดึงรหัสใหม่", fg=RED)
            self._update_title()
        self.count_label.configure(text="")
        self.stop_btn.configure(state="disabled")
        self.start_btn.configure(state="normal" if self._ready() else "disabled")
        self.set_status(text, color)

    def stop(self):
        self.stop_event.set()
        self.stop_btn.configure(state="disabled")

    def on_close(self):
        if self.running:
            if not messagebox.askyesno(bot_title(self.config), "บอทกำลังทำงาน ต้องการหยุดและปิดหรือไม่?",
                                       parent=self.root):
                return
            self.stop_event.set()
        self.close()

    def close(self):
        sys.stdout = self.old_stdout
        try:
            if self.api is not None:
                self.api.close()
        except Exception:
            pass
        self.root.destroy()


def enable_dpi_awareness():
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass


def open_window(config, api_factory=None):
    enable_dpi_awareness()
    window = BotWindow(config, api_factory=api_factory)
    window.root.mainloop()
