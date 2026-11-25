import json
import os
import re
import sys
import time
from contextlib import contextmanager
from datetime import datetime

import requests

from bin.lib.ApiLineShopping import ApiiLineShopping
from bin.lib.ToolsLineShopping import ToolsLineShopping


# =========================
# ตัวช่วยเดิม (ย้ายมาจาก bot1.py ไม่ได้เปลี่ยนการทำงาน)
# =========================

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def parse_datetime(value):
    if not value:
        return None

    value = str(value).strip()
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass
    raise ValueError("รูปแบบ start_bot_at ต้องเป็น YYYY-MM-DD HH:MM[:SS]")


def parse_time_str(value):
    value = str(value).strip()
    formats = ["%H:%M:%S", "%H:%M"]
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).time()
        except ValueError:
            pass
    raise ValueError(f"รูปแบบเวลาไม่ถูกต้อง: {value}")


def wait_until_start(start_at):
    start_dt = parse_datetime(start_at)
    if start_dt is None:
        return

    while True:
        now = datetime.now()
        if now >= start_dt:
            print(f"[{now_str()}] ถึงเวลาเริ่มบอทแล้ว")
            return

        remaining = int((start_dt - now).total_seconds())
        print(f"[{now_str()}] รอเวลาเริ่มบอทอีก {remaining} วินาที")
        time.sleep(min(1, max(remaining, 1)))


def is_in_allowed_time_ranges(time_ranges, current_dt=None):
    current_dt = current_dt or datetime.now()
    current_time = current_dt.time()

    for start_str, end_str in time_ranges:
        start_t = parse_time_str(start_str)
        end_t = parse_time_str(end_str)

        if start_t <= end_t:
            if start_t <= current_time <= end_t:
                return True
        else:
            if current_time >= start_t or current_time <= end_t:
                return True

    return False


def wait_for_allowed_time_mode(enabled, time_ranges, sleep_seconds=1):
    if not enabled:
        return

    while True:
        if is_in_allowed_time_ranges(time_ranges):
            return

        print(f"[{now_str()}] ยังไม่อยู่ในช่วงเวลาที่อนุญาตให้ทำงาน")
        time.sleep(sleep_seconds)


def get_stock_text(stock_result):
    variant = stock_result.get("variant") or {}
    stock = variant.get("available")
    return str(stock)


def get_size_label(stock_result, fallback_size=""):
    variant = stock_result.get("variant") or {}
    variant_name = variant.get("variant_option_value1")
    variant_name2 = variant.get("variant_option_value2")

    if variant_name not in [None, ""] and variant_name2 not in [None, ""]:
        return f"{variant_name} / {variant_name2}"

    if variant_name not in [None, ""]:
        return str(variant_name)

    if fallback_size not in [None, ""]:
        return str(fallback_size)

    return "NO_SIZE"


# =========================
# ข้อความ error ภาษาไทย (item 3)
# =========================

def explain_error(step, exc):
    """แปลง error เป็นข้อความไทย 1 บรรทัด ไม่มี traceback
    step = profile | product | checkout | place_order
    """
    if isinstance(exc, (requests.ConnectionError, requests.Timeout)):
        return "อินเทอร์เน็ตมีปัญหา เชื่อมต่อไม่ได้ — เช็คเน็ตแล้วลองใหม่"

    response = getattr(exc, "response", None)
    status = getattr(response, "status_code", None) if response is not None else None
    text = ""
    if response is not None:
        try:
            text = str(response.text or "")
        except Exception:
            text = ""

    if isinstance(exc, requests.HTTPError) and status in (401, 403):
        return "Token หมดอายุหรือไม่ถูกต้อง — เข้า LINE Shopping ใหม่แล้วคัดลอก Token ใหม่"

    if step == "product" and status == 404:
        return "ไม่พบสินค้า — เช็คลิงก์สินค้าอีกครั้ง"

    if step == "place_order" and (status == 409 or "3999" in text or "3999" in str(exc)):
        return "LINE ไม่รับคำสั่งซื้อ (รหัส 3999) — ยังไม่ได้ซื้อ รีบกดซื้อเองในมือถือ แล้วถ่ายรูปหน้าจอส่งผู้ดูแล"

    short = str(exc).strip().splitlines()[0] if str(exc).strip() else exc.__class__.__name__
    if len(short) > 150:
        short = short[:150] + "..."
    return f"เกิดข้อผิดพลาดที่ขั้นตอน {step}: {short}"


def is_not_found(exc):
    response = getattr(exc, "response", None)
    return response is not None and getattr(response, "status_code", None) == 404


# =========================
# บันทึกตอน LINE ไม่รับคำสั่งซื้อ: order_fail_<bot>.txt
# มีแต่ชื่อช่องและรูปแบบ ไม่มีค่าใดๆ (ไม่มีรหัส ชื่อ ที่อยู่ เบอร์ อีเมล เลขคำสั่งซื้อ)
# =========================

SAFE_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z_-]{0,40}[0-9]{0,2}$")


def safe_key(key):
    """ชื่อช่องปกติเท่านั้น ถ้าชื่อช่องเป็นรหัส/เลข/ข้อมูลคน จะไม่เขียน"""
    return str(key) if SAFE_KEY_RE.match(str(key)) else "<key>"


def sent_shape(value, name, depth=0):
    """สิ่งที่ส่งไป: filled | empty | null | true | false | list(n)"""
    pad = "  " * depth
    if isinstance(value, dict):
        lines = [f"{pad}{name}: object" if value else f"{pad}{name}: empty"]
        for k, v in value.items():
            lines += sent_shape(v, safe_key(k), depth + 1)
        return lines
    if isinstance(value, (list, tuple)):
        lines = [f"{pad}{name}: list({len(value)})"]
        if value and isinstance(value[0], dict):
            for k, v in value[0].items():
                lines += sent_shape(v, safe_key(k), depth + 1)
        return lines
    if value is None:
        kind = "null"
    elif isinstance(value, bool):
        kind = "true" if value else "false"
    else:
        kind = "empty" if value == "" else "filled"
    return [f"{pad}{name}: {kind}"]


def answer_shape(value, path="", depth=0, max_depth=4):
    """คำตอบ checkout: ชื่อช่อง + ชนิด ลึกไม่เกิน 4 ชั้น ไม่มีค่า"""
    if isinstance(value, dict):
        lines = [f"{path}: object"] if path else []
        if depth < max_depth:
            for k, v in value.items():
                key = safe_key(k)
                lines += answer_shape(v, f"{path}.{key}" if path else key, depth + 1, max_depth)
        return lines
    if isinstance(value, list):
        lines = [f"{path}: list({len(value)})"]
        if value and isinstance(value[0], (dict, list)):
            lines += answer_shape(value[0], path + "[0]", depth, max_depth)[1:]
        return lines
    kind = "null" if value is None else {"str": "text", "int": "number", "float": "number"}.get(type(value).__name__,
                                                                                                type(value).__name__)
    return [f"{path}: {kind}"]


# ข้อความ error จาก LINE อาจมีชื่อ ที่อยู่ หรือรหัสปนมา: เขียนเฉพาะคำในรายการนี้ นอกนั้นเป็น *
ERROR_WORDS = set("""
a an and are at be by can cannot could did do does for from has have in is it no not of on or please than that the this to too
was were with your you
access account action address again allow allowed already amount api app application auth authentication authorization
authorized available bad banned block blocked body bot buy buyer campaign cancel captcha cart change changed channel check checkout
city client closed code conflict contact country coupon create created credential customer data date default delivery denied detail
device disabled district duplicate duplicated email empty enabled error exceed exceeded exist exists expire expired fail failed field
forbidden format found friend gateway gone header human id inactive incorrect insufficient internal invalid inventory item items key
later length limit limited line location locked login many match max maximum member membership method mid min minimum mismatch
missing name network new null number object ok once only open option order out parameter params payload payment pending permission
phone point postal preorder price process processing product profile promotion province purchase qr quantity quota rate reach reached
refused rejected request required reserved resource response restricted retry robot sale sales seller server service session shipment
shipping shop size sku snapshot sold spam state status stock string sub success support suspended system temporarily terms timeout
token try type unable unauthorized unavailable unexpected unknown unpaid unsupported update user valid validation value variant
verification verified verify version wait wrong
""".split())


def safe_error_text(value):
    text = re.sub(r"[A-Za-z]+", lambda m: m.group() if m.group().lower() in ERROR_WORDS else "*", str(value))
    text = re.sub(r"[^A-Za-z _.,:;()-]+", "*", text)
    return " ".join(text.split())[:300]


def token_source_file(token_file):
    return token_file[:-len(".txt")] + ".src.txt"


def write_token_source(token_file, line):
    try:
        with open(token_source_file(token_file), "w", encoding="utf-8") as f:
            f.write(line)
    except OSError:
        pass


def token_facts(api, config):
    """(อายุไฟล์รหัสเป็นวินาที, ที่มาของรหัส) ของรหัสที่ใช้อยู่ตอนนี้ — ไม่มีตัวรหัส"""
    token_file = token_file_for(config)
    if read_token_file(token_file) != clean_token(getattr(api, "token", "")):
        return "-", "วางเอง (ไม่ตรงกับไฟล์รหัส)"
    written = os.path.getmtime(token_file)
    age = int(time.time() - written)
    source_file = token_source_file(token_file)
    if not os.path.isfile(source_file) or os.path.getmtime(source_file) < written - 5:
        return age, "ไม่ทราบ (ไม่มีบันทึกที่มา)"
    with open(source_file, encoding="utf-8") as f:
        return age, " ".join(f.read().split())[:300]


def log_order_failure(step, exc, api, config, shop_name, id_product, data_product, stock_result, quantity,
                      sent, check_out=None):
    """เขียนหลังได้คำตอบแล้วเท่านั้น และไม่ว่าเกิดอะไรขึ้นต้องไม่กระทบการซื้อ"""
    try:
        product = (data_product or {}).get("data", {}) or {}
        variant = (stock_result or {}).get("variant") or {}
        response = getattr(exc, "response", None)
        request = getattr(response, "request", None) or getattr(exc, "request", None)
        age, source = token_facts(api, config)
        lines = [
            f"===== {now_str()} · {bot_id(config)} · {step} ไม่ผ่าน =====",
            f"shop: {shop_name} · product: {id_product} · has_variant: {bool(product.get('has_variant'))}"
            f" · option chosen: {variant.get('id') is not None} · quantity: {quantity}",
            f"HTTP status: {getattr(response, 'status_code', None) if response is not None else '-'}"
            f" · error type: {type(exc).__name__}",
            f"token: file age {age} s · source: {source}",
        ]

        lines.append("[error body]")
        body = None
        if response is not None:
            try:
                body = json.loads(response.text or "")
            except Exception:
                lines.append("  (not JSON)")
        if isinstance(body, dict):
            for key in ("message", "error_code", "error_message"):
                if body.get(key) is None or isinstance(body.get(key), (dict, list)):
                    continue
                text = str(body[key])
                if not (key == "error_code" and re.match(r"^[0-9]{1,5}$", text)):
                    text = safe_error_text(text)
                lines.append(f"  {key}: {text}")

        for title, holder in (("response header names", response), ("sent header names", request)):
            names = sorted(str(n) for n in (getattr(holder, "headers", None) or {})
                           if re.match(r"^[A-Za-z0-9_-]{1,40}$", str(n)))
            lines.append(f"[{title}] {', '.join(names) or '-'}")

        lines.append("[sent body]")
        for key, value in (sent or {}).items():
            lines += sent_shape(value, safe_key(key), 1)
        lines.append("[checkout answer]")
        lines += ["  " + line for line in answer_shape(check_out)] if check_out else ["  -"]

        path = os.path.join(bot_folder(config), f"order_fail_{bot_id(config)}.txt")
        with open(path, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n\n")
    except Exception:
        pass


# =========================
# Token ตอนกด Run (item 1)
# =========================

def clean_token(value):
    token = str(value or "").strip()
    while len(token) >= 1 and token[0] in "\"'":
        token = token[1:].strip()
    while len(token) >= 1 and token[-1] in "\"'":
        token = token[:-1].strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    return token


def try_login(api_factory, token):
    """ลอง token 1 ครั้ง คืน (api, displayName) หรือ (None, None) ถ้าไม่ผ่าน"""
    api = api_factory(token)
    try:
        profile = api.profile()
        display_name = (profile or {}).get("displayName")
        if display_name:
            return api, display_name
        print("Login ไม่สำเร็จ เก็บ Token มาใส่ใหม่")
    except Exception as e:
        print(explain_error("profile", e))

    try:
        api.close()
    except Exception:
        pass
    return None, None


def bot_folder(config):
    bot_file = config.get("__file__")
    if bot_file:
        return os.path.dirname(os.path.abspath(bot_file))
    return os.getcwd()


# แต่ละบอทใช้บัญชี LINE ของตัวเอง: ไฟล์รหัสและโปรไฟล์ Chrome แยกกันต่อบอท (ไม่ใช้ token.txt ร่วมกันแล้ว)
def bot_id(config):
    bot_file = config.get("__file__")
    if bot_file:
        return os.path.splitext(os.path.basename(str(bot_file)))[0] or "bot"
    return "bot"


def token_file_for(config):
    return os.path.join(bot_folder(config), f"token_{bot_id(config)}.txt")


def profile_dir_for(bot_name, folder=None):
    return os.path.join(folder or os.getcwd(), f".line_profile_{bot_name}")


def read_token_file(token_file):
    if not token_file or not os.path.isfile(token_file):
        return ""
    try:
        with open(token_file, encoding="utf-8") as f:
            return clean_token(f.read())
    except OSError:
        return ""


def login(config_token, api_factory, input_func, max_tries=3, token_file=None):
    token = clean_token(config_token)
    if token:
        api, display_name = try_login(api_factory, token)
        if api is not None:
            print(f"เข้าสู่ระบบเป็น: {display_name}")
            return api, display_name
    else:
        file_token = read_token_file(token_file)
        if file_token:
            api, display_name = try_login(api_factory, file_token)
            if api is not None:
                print(f"เข้าสู่ระบบเป็น: {display_name}")
                return api, display_name
            print(f"รหัสใน {os.path.basename(token_file)} ใช้ไม่ได้แล้ว — รัน get_token.py ใหม่ หรือวางรหัสเองด้านล่าง")

    for _ in range(max_tries):
        token = clean_token(input_func("วาง Token แล้วกด Enter (คลิกขวาเพื่อวาง):"))
        if not token:
            print("ยังไม่ได้วาง Token")
            continue
        api, display_name = try_login(api_factory, token)
        if api is not None:
            print(f"เข้าสู่ระบบเป็น: {display_name}")
            return api, display_name

    print(f"ลอง Token ครบ {max_tries} ครั้งแล้วยังไม่ผ่าน — เอา Token ใหม่แล้วกด Run อีกครั้ง")
    return None, None


# =========================
# ลิงก์สินค้า (item 4)
# =========================

PRODUCT_URL_RE = re.compile(r"shop\.line\.me/(@[^/?#]+)/product/(\d+)")
SHOP_ID_RE = re.compile(r"^\s*@?([^\s/@]+)[\s,]+(\d{6,})\s*$")
PRODUCT_HINT = ("ใส่ลิงก์สินค้า เช่น https://shop.line.me/@babylovett/product/1008483011 "
                "หรือ ชื่อร้าน + เลข ID เช่น @babylovett 1008483011")
ASK_PRODUCT_URL = PRODUCT_HINT + ":"


def parse_product_url(url):
    """รับได้ 2 แบบ: ลิงก์สินค้า หรือ ชื่อร้าน + เลข ID (เช่น @babylovett 1008483011) คืน (shop_name, id_product) หรือ None"""
    text = str(url or "")
    match = PRODUCT_URL_RE.search(text)
    if match:
        return match.group(1), int(match.group(2))
    text = " ".join(text.split())  # ช่องว่างทุกแบบ (รวมช่องว่างเต็มความกว้าง) เหลือช่องเดียว
    match = SHOP_ID_RE.match(text)
    if match:
        return "@" + match.group(1), int(match.group(2))
    return None


def ask_product_url(input_func):
    while True:
        parsed = parse_product_url(input_func(ASK_PRODUCT_URL))
        if parsed:
            return parsed
        print(PRODUCT_HINT)


def resolve_product(config, input_func):
    product_url = str(config.get("product_url", "") or "").strip()
    shop_name = config.get("shop_name")
    id_product = config.get("id_product")

    if product_url:
        parsed = parse_product_url(product_url)
        if parsed:
            return parsed
        print("ลิงก์สินค้าใน CONFIG ไม่ถูกต้อง")
        return ask_product_url(input_func)

    if shop_name and id_product:
        return shop_name, id_product

    return ask_product_url(input_func)


# =========================
# ตรวจความพร้อม (item 5 + item 6)
# =========================

def print_variant_list(data_product):
    product = (data_product or {}).get("data", {})
    variants = product.get("product_variants", []) or []
    if not variants:
        return
    print("ตัวเลือกที่มี (value1 / value2 / stock):")
    for variant in variants:
        value1 = variant.get("variant_option_value1") or "-"
        value2 = variant.get("variant_option_value2") or "-"
        print(f"  {value1} / {value2} / {variant.get('available')}")


def product_label(data_product, shop_name, id_product):
    product = (data_product or {}).get("data", {}) or {}
    name = product.get("name") or product.get("product_name")
    return str(name) if name else f"{shop_name} / {id_product}"


def ready_check(api, tools, shop_name, id_product, size, quantity, input_func):
    """คืน (shop_name, id_product, size, data_product) เมื่อพร้อม หรือ None"""
    while True:
        try:
            data_product = api.info_product(shop_name, id_product)
            break
        except Exception as e:
            print(explain_error("product", e))
            if is_not_found(e):
                shop_name, id_product = ask_product_url(input_func)
            else:
                answer = input_func("กด Enter เพื่อลองใหม่ หรือวางลิงก์สินค้าใหม่:")
                parsed = parse_product_url(answer)
                if parsed:
                    shop_name, id_product = parsed

    while True:
        result = tools.find_variant_by_size(data_product, size, quantity)
        # ก่อนเปิดขาย stock อาจเป็น 0 ได้ เจอตัวเลือกก็ถือว่าพร้อม
        if result.get("variant") is not None:
            return shop_name, id_product, size, data_product

        print(result["message"])
        product = (data_product or {}).get("data", {})
        if not (product.get("product_variants") or []):
            return None

        print_variant_list(data_product)
        if result.get("need_number"):
            tools.number = str(input_func("พิมพ์ number ที่ต้องการจากรายการด้านบน:") or "").strip()
        else:
            size = str(input_func("พิมพ์ size ที่ต้องการจากรายการด้านบน:") or "").strip()


# =========================
# วันเวลาเปิดขาย (item 8A)
# =========================

SALE_TIME_RE = re.compile(r"^(\d{1,2})/(\d{1,2})(?:/(\d{4}))?\s+(\d{1,2}):(\d{2})(?::(\d{2}))?$")
ISO_TIME_RE = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})\s+(\d{1,2}):(\d{2})(?::(\d{2}))?$")


def parse_sale_time(value, now=None):
    now = now or datetime.now()
    value = str(value or "").strip()

    match = ISO_TIME_RE.match(value)
    if match:
        year, month, day, hour, minute, second = match.groups()
        return datetime(int(year), int(month), int(day), int(hour), int(minute), int(second or 0))

    match = SALE_TIME_RE.match(value)
    if not match:
        raise ValueError(value)

    day, month, year, hour, minute, second = match.groups()
    if year:
        return datetime(int(year), int(month), int(day), int(hour), int(minute), int(second or 0))

    target = datetime(now.year, int(month), int(day), int(hour), int(minute), int(second or 0))
    if target < now:
        target = target.replace(year=now.year + 1)
    return target


def ask_sale_time(input_func):
    while True:
        answer = str(input_func("วันเวลาเปิดขาย (เช่น 01/12 10:00) หรือกด Enter เพื่อเริ่มเลย:") or "").strip()
        if not answer:
            return None
        try:
            return parse_sale_time(answer)
        except ValueError:
            print("รูปแบบไม่ถูกต้อง พิมพ์แบบนี้: 01/12 10:00 หรือ 01/12/2026 10:00:00 หรือ 2026-12-01 10:00")


@contextmanager
def keep_awake():
    """ขอ Windows ไม่ให้เครื่อง sleep ระหว่างรอ (จอดับได้ เครื่องไม่หลับ)"""
    enabled = False
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)
            enabled = True
        except Exception:
            enabled = False
    try:
        yield
    finally:
        if enabled:
            try:
                import ctypes
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
            except Exception:
                pass


class StopRequested(Exception):
    """กดหยุดจากหน้าต่าง"""


class TokenFailed(Exception):
    """Token ใช้ไม่ได้ตอนตรวจซ้ำก่อนเปิดขาย"""


class OptionMismatch(Exception):
    """สินค้าเปิดแล้ว แต่ตัวเลือกที่พิมพ์ไว้ไม่ชี้ไปที่ตัวเลือกเดียวชัดเจน — หยุด ไม่เดาซื้อ"""

    def __init__(self, data_product):
        super().__init__("ตัวเลือกไม่ตรง")
        self.data_product = data_product


def options_unclear(data_product, stock_result, tools, size):
    """True = ห้ามซื้อ: ตัวเลือกที่พิมพ์ไว้ก่อนเปิดขายไม่ตรง หรือชี้ได้มากกว่า 1 ตัวเลือก"""
    product = (data_product or {}).get("data", {}) or {}
    variants = product.get("product_variants") or []
    norm = tools.normalize_variant_text
    if not product.get("has_variant"):
        return bool(norm(tools.number) or norm(size))  # พิมพ์ตัวเลือกไว้ แต่สินค้าไม่แสดงตัวเลือก
    if not variants:
        return False
    if stock_result.get("variant") is None:
        return True
    pairs = [(norm(v.get("variant_option_value1")), norm(v.get("variant_option_value2"))) for v in variants]
    number = norm(tools.number)
    if any(b for _, b in pairs) and not number:
        return True
    wanted = norm(size)
    return sum(1 for a, b in pairs if (a, b) in ((wanted, number), (number, wanted))) != 1


def check_stop(should_stop):
    if should_stop is not None and should_stop():
        raise StopRequested()


def sleep_or_stop(seconds, should_stop=None):
    if should_stop is None:
        time.sleep(seconds)
        return
    end = time.time() + seconds
    while True:
        check_stop(should_stop)
        left = end - time.time()
        if left <= 0:
            return
        time.sleep(min(0.2, left))


def countdown_until(target, recheck, should_stop=None, on_tick=None):
    rechecked = False
    while True:
        check_stop(should_stop)
        remaining = (target - datetime.now()).total_seconds()
        if remaining <= 0:
            if on_tick is None:
                print(f"\r[{now_str()}] ถึงเวลาเปิดขายแล้ว เริ่มซื้อ" + " " * 10, flush=True)
            else:
                on_tick(0)
                print(f"[{now_str()}] ถึงเวลาเปิดขายแล้ว เริ่มซื้อ", flush=True)
            return
        if not rechecked and remaining <= 300:
            if on_tick is None:
                print()
            recheck()
            rechecked = True
        if on_tick is None:
            total = int(remaining + 0.999)
            hours, rest = divmod(total, 3600)
            minutes, seconds = divmod(rest, 60)
            print(f"\rเหลืออีก {hours:02d}:{minutes:02d}:{seconds:02d} ก่อนเปิดขาย", end="", flush=True)
        else:
            on_tick(remaining)
        sleep_or_stop(min(1, remaining), should_stop)


# =========================
# รอสินค้า (เดิม) + ข้อความไทย
# =========================

def wait_until_product_available(api, tools, shop_name, id_product, size, quantity,
                                 poll_interval_seconds=2,
                                 use_time_mode=False,
                                 allowed_time_ranges=None,
                                 should_stop=None,
                                 strict_options=False):
    allowed_time_ranges = allowed_time_ranges or [("00:00:00", "23:59:59")]

    while True:
        check_stop(should_stop)
        wait_for_allowed_time_mode(
            enabled=use_time_mode,
            time_ranges=allowed_time_ranges,
            sleep_seconds=1,
        )

        try:
            data_product = api.info_product(shop_name, id_product)

            stock_result = tools.find_variant_by_size(data_product, size, quantity)

            if strict_options and options_unclear(data_product, stock_result, tools, size):
                print(f"[{now_str()}] สินค้าเปิดแล้ว แต่ตัวเลือกไม่ตรง: {stock_result['message']}")
                print_variant_list(data_product)
                raise OptionMismatch(data_product)

            if stock_result["ok"]:
                print(
                    f"[{now_str()}] มีสินค้าแล้ว | "
                    f"size={get_size_label(stock_result, size)} | "
                    f"stock={get_stock_text(stock_result)}"
                )
                return data_product, stock_result

            print(
                f"[{now_str()}] ยังไม่มีสินค้า | "
                f"size={get_size_label(stock_result, size)} | "
                f"message={stock_result['message']}"
            )
            if stock_result.get("variant") is None:
                print_variant_list(data_product)

        except OptionMismatch:
            raise
        except Exception as e:
            if strict_options and is_not_found(e):
                print(f"[{now_str()}] ยังไม่พบสินค้า รออยู่ …")
            else:
                print(f"[{now_str()}] เช็คสินค้าไม่สำเร็จ: {explain_error('product', e)}")

        sleep_or_stop(poll_interval_seconds, should_stop)


# =========================
# ซื้อ: จากนับถอยหลังจนถึง place_order (ใช้ทั้งแบบ terminal และแบบหน้าต่าง)
# =========================

def buy_flow(api, tools, shop_name, id_product, size, quantity, config, sale_at,
             should_stop=None, on_tick=None, relogin=None, holder=None, strict_options=False):
    """คืน "ordered" | "found" | "error"
    กดหยุด = StopRequested · Token ตรวจซ้ำก่อนเปิดขายไม่ผ่าน = TokenFailed
    holder["api"] = api ที่ใช้อยู่ล่าสุด (ไว้ปิดตอนจบ)
    """
    get = config.get
    holder = holder if holder is not None else {}
    holder["api"] = api

    if sale_at is not None:
        def recheck():
            print(f"[{now_str()}] ตรวจ Token อีกครั้งก่อนเปิดขาย")
            new_api = relogin(holder["api"]) if relogin is not None else holder["api"]
            holder["api"] = new_api
            if new_api is None:
                raise TokenFailed()

        with keep_awake():
            countdown_until(sale_at, recheck, should_stop, on_tick)
        api = holder["api"]
        use_time_mode = False
    else:
        wait_until_start(get("start_bot_at"))
        use_time_mode = get("use_time_mode", False)

    data_product, stock_result = wait_until_product_available(
        api=api,
        tools=tools,
        shop_name=shop_name,
        id_product=id_product,
        size=size,
        quantity=quantity,
        poll_interval_seconds=get("poll_interval_seconds", 1),
        use_time_mode=use_time_mode,
        allowed_time_ranges=get("allowed_time_ranges"),
        should_stop=should_stop,
        strict_options=strict_options,
    )

    if not get("auto_checkout_and_order", True):
        print(f"[{now_str()}] เจอสินค้าแล้ว แต่ตั้งค่า auto_checkout_and_order = False")
        return "found"

    checkout_result = tools.build_checkout_payload(
        data_product=data_product,
        size=size,
        quantity=quantity,
        disable_auto_apply=get("checkout_disable_auto_apply", False),
        is_gift=get("checkout_is_gift", False),
    )

    if not checkout_result["ok"]:
        print("สร้าง checkout payload ไม่สำเร็จ:", checkout_result["message"])
        return "error"

    checkout_payload = checkout_result["payload"]
    print(f"[{now_str()}] checkout payload พร้อมแล้ว")

    try:
        check_out = api.checkout(json_data=checkout_payload)
    except Exception as e:
        print(explain_error("checkout", e))
        log_order_failure("checkout", e, api, config, shop_name, id_product, data_product, stock_result, quantity,
                          checkout_payload)
        return "error"
    print(f"[{now_str()}] checkout สำเร็จ")

    create_order_result = tools.build_create_order_payload(
        check_out=check_out,
        data_product=data_product,
        size=size,
        quantity=quantity,
        payment_app_switch_id=get("payment_app_switch_id"),
        is_android=get("is_android", False),
        is_liff=get("is_liff", False),
        remark_buyer=get("remark_buyer", ""),
        point=get("point"),
        ignore_point=get("ignore_point"),
        promotion_id=get("promotion_id", ""),
        cart_id=get("cart_id", ""),
        gift_info=get("gift_info"),
        seller_product_discount_coupon=get("seller_product_discount_coupon"),
        seller_shipping_discount_coupon=get("seller_shipping_discount_coupon"),
        subsidised_product_discount_coupon=get("subsidised_product_discount_coupon"),
        bank_transfer=get("bank_transfer"),
    )

    if not create_order_result["ok"]:
        print("สร้าง order payload ไม่สำเร็จ:", create_order_result["message"])
        return "error"

    order_payload = create_order_result["payload"]
    print(f"[{now_str()}] create order payload พร้อมแล้ว")

    try:
        create_order = api.place_order(name_shop=shop_name, json_data=order_payload)
    except Exception as e:
        print(explain_error("place_order", e))
        log_order_failure("place_order", e, api, config, shop_name, id_product, data_product, stock_result, quantity,
                          order_payload, check_out)
        return "error"
    print("place_order result:", create_order)
    return "ordered"


# =========================
# ตัวรันหลัก (bot1.py เดิม)
# =========================

def run(config, api_factory=None, input_func=input):
    api_factory = api_factory or ApiiLineShopping
    get = config.get

    if get("ui") == "window":
        from bin.lib.BotWindow import open_window
        open_window(config, api_factory=api_factory)
        return

    quantity = get("quantity", 1)
    tools = ToolsLineShopping(number=str(get("number", "") or "").strip())
    state = {"api": None}
    token_file = token_file_for(config)

    try:
        api, display_name = login(get("token", ""), api_factory, input_func, token_file=token_file)
        if api is None:
            return
        state["api"] = api

        shop_name, id_product = resolve_product(config, input_func)

        sale_at = ask_sale_time(input_func) if get("ask_sale_time", False) else None

        ready = ready_check(api, tools, shop_name, id_product, get("size", ""), quantity, input_func)
        if ready is None:
            print("ยังไม่พร้อม — แก้ตามข้อความด้านบนแล้วกด Run อีกครั้ง")
            return
        shop_name, id_product, size, data_product = ready

        option_text = " / ".join(x for x in [tools.number, str(size or "")] if x) or "-"
        print("======== พร้อม ========")
        print(f"บัญชี: {display_name}")
        print(f"สินค้า: {product_label(data_product, shop_name, id_product)}")
        print(f"ตัวเลือก: {option_text}")

        def relogin(current):
            # ไฟล์รหัสของบอทนี้ก่อน (token_<bot>.txt) เผื่อระหว่างรอได้รัน get_token.py ใหม่
            token = read_token_file(token_file) or getattr(current, "token", "")
            try:
                current.close()
            except Exception:
                pass
            new_api, _ = login(token, api_factory, input_func, token_file=token_file)
            return new_api

        try:
            buy_flow(api, tools, shop_name, id_product, size, quantity, config, sale_at,
                     relogin=relogin, holder=state)
        except TokenFailed:
            raise SystemExit

    finally:
        try:
            if state["api"] is not None:
                state["api"].close()
        except Exception:
            pass
