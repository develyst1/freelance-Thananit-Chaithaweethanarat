import os
import time
from urllib.parse import urlparse

# =========================
# CONFIG
# =========================
wait_login_seconds = 600  # รอให้เข้าสู่ระบบได้นานสุดกี่วินาที
hint_after_seconds = 60  # ถ้ายังไม่เจอรหัสหลังกี่วินาที ให้ขึ้นคำแนะนำ
bot_name = ""  # บันทึกรหัสให้บอทไหน เช่น "bot2" (ว่างไว้ = ถามตอนกด Run)

BOT_FOLDER = os.path.dirname(os.path.abspath(__file__))


def bot_paths(name):
    """บอทแต่ละตัวมีบัญชี LINE ของตัวเอง: โปรไฟล์ Chrome .line_profile_<bot> และไฟล์รหัส token_<bot>.txt"""
    return (os.path.join(BOT_FOLDER, f".line_profile_{name}"), os.path.join(BOT_FOLDER, f"token_{name}.txt"))


def source_line(url, count):
    """ที่มาของรหัส: ชื่อเครื่อง + เส้นทาง (ไม่มี query, ส่วนที่เป็นเลข/รหัสยาวถูกปิด) ไม่มีตัวรหัส"""
    parsed = urlparse(url)
    parts = ["{id}" if len(p) >= 24 or sum(c.isdigit() for c in p) >= 5 else p for p in parsed.path.split("/")]
    return f"ดึงอัตโนมัติ · {parsed.hostname}{'/'.join(parts)} · พบรหัสต่างกัน {count} แบบ"


def ask_bot_name(input_func=input):
    while True:
        answer = str(input_func("บันทึกรหัสให้บอทไหน (เช่น bot1):") or "").strip().lower()
        if answer.isdigit() and 1 <= int(answer) <= 9:
            return f"bot{int(answer)}"
        if len(answer) == 4 and answer.startswith("bot") and answer[3] in "123456789":
            return answer
        print("พิมพ์ bot1 ถึง bot9 (หรือเลข 1–9)")


def is_valid_token(token, api_factory=None):
    """เช็ครหัสกับ LINE (profile) คืน True ถ้าใช้ได้ ไม่แสดงรหัสบนจอ"""
    if api_factory is None:
        from bin.lib.ApiLineShopping import ApiiLineShopping
        api_factory = ApiiLineShopping
    api = api_factory(token)
    try:
        return bool((api.profile() or {}).get("displayName"))
    except Exception:
        return False
    finally:
        try:
            api.close()
        except Exception:
            pass


def wait_for_valid_token(pending, wait, api_factory=None,
                         timeout_s=wait_login_seconds, hint_after_s=hint_after_seconds, out=print):
    """รอรหัสที่ใช้ได้จริง: รหัสที่เช็คไม่ผ่าน (เช่น ก่อนเข้าระบบ) ข้ามไปแล้วรอต่อ
    pending = list ที่มีรหัสใหม่ถูกเติมเข้ามา, wait() = รอสักครู่ คืน False ถ้าหน้าต่างถูกปิด
    """
    rejected = set()
    warned = False
    hinted = False
    started = time.time()
    while True:
        while pending:
            token = pending.pop(0)
            if not token or token in rejected:
                continue
            if is_valid_token(token, api_factory):
                return token
            rejected.add(token)
            if not warned:
                out("ยังไม่ได้เข้าสู่ระบบ — รอให้เข้าสู่ระบบในหน้าต่าง Chrome ก่อน …")
                warned = True

        elapsed = time.time() - started
        if elapsed > timeout_s:
            out("หมดเวลารอการเข้าสู่ระบบ — รัน get_token.py ใหม่ หรือวางรหัสเองตอนรันบอท")
            return None
        if not hinted and elapsed > hint_after_s:
            out("ถ้าเข้าระบบแล้ว ลองกดเข้าหน้าร้านหรือดูสินค้า 1 ครั้ง")
            hinted = True
        if not wait():
            out("หน้าต่างถูกปิดก่อนเจอรหัส — รัน get_token.py ใหม่")
            return None


def capture_token(timeout_s=wait_login_seconds, out=print, profile_dir=None, source=None):
    """out = ฟังก์ชันแสดงข้อความ (ค่าเดิม print; หน้าต่างบอทส่งของตัวเองมา)
    profile_dir = โปรไฟล์ Chrome ของบอทนี้ (.line_profile_<bot>) — แต่ละบอทจำบัญชี LINE ของตัวเอง"""
    profile_dir = profile_dir or bot_paths("bot")[0]
    """เปิด Chrome ให้เข้าสู่ระบบ LINE แล้วจับรหัส (Token) จากคำขอของหน้าร้าน คืนรหัสที่ใช้ได้ หรือ None"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        out("ยังไม่ได้ติดตั้งตัวช่วย — ให้ผู้ดูแลรัน: pip install playwright")
        return None

    from bin.lib.RunBot import clean_token

    pending = []
    seen = {}  # รหัส -> url ของคำขอแรกที่เห็น (อยู่ในหน่วยความจำเท่านั้น)

    def on_request(request):
        host = urlparse(request.url).hostname or ""
        if not host.endswith(".line-apps.com"):
            return
        authorization = request.headers.get("authorization")
        if authorization:
            token = clean_token(authorization)
            if token:
                seen.setdefault(token, request.url)
            if token and token not in pending:
                pending.append(token)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            channel="chrome",
            headless=False,
            chromium_sandbox=True,  # sandbox ON: no "--no-sandbox" warning bar in her Chrome
        )
        try:
            context.on("request", on_request)
            page = context.pages[0] if context.pages else context.new_page()
            page.goto("https://shop.line.me/")
            out("กรุณาเข้าสู่ระบบ LINE ในหน้าต่างที่เปิดขึ้น (ยืนยันในมือถือด้วย) …")

            def wait():
                try:
                    page.wait_for_timeout(500)
                    return True
                except Exception:
                    return False

            token = wait_for_valid_token(pending, wait, timeout_s=timeout_s, out=out)
            if token and source is not None:
                source["line"] = source_line(seen[token], len(seen))
            return token
        finally:
            try:
                context.close()
            except Exception:
                pass


def check_and_save(token, api_factory=None, path=None):
    """ตรวจรหัสกับ LINE แล้วเก็บลงไฟล์รหัสของบอทนี้ token_<bot>.txt (ไม่แสดงรหัสบนจอ)"""
    path = path or bot_paths("bot1")[1]
    bot_file = os.path.basename(path)[len("token_"):-len(".txt")] + ".py" if os.path.basename(path).startswith("token_") else "bot1.py"
    from bin.lib.RunBot import explain_error

    if api_factory is None:
        from bin.lib.ApiLineShopping import ApiiLineShopping
        api_factory = ApiiLineShopping

    print("เจอรหัสแล้ว ✓")
    api = api_factory(token)
    try:
        profile = api.profile()
        display_name = (profile or {}).get("displayName")
        if not display_name:
            print("Login ไม่สำเร็จ เก็บ Token มาใส่ใหม่")
            return False
    except Exception as e:
        print(explain_error("profile", e))
        return False
    finally:
        try:
            api.close()
        except Exception:
            pass

    with open(path, "w", encoding="utf-8") as f:
        f.write(token)
    print(f"รหัสใช้ได้ ✓ · บัญชี: {display_name}")
    print(f"พร้อมรันบอทแล้ว — เปิด {bot_file} แล้วกด Run ได้เลย")
    return True


if __name__ == "__main__":
    name = bot_name.strip().lower() or ask_bot_name()
    profile_dir, token_path = bot_paths(name)
    print(f"บอท: {name} · หน้าต่าง Chrome ของบอทนี้: {os.path.basename(profile_dir)} · ไฟล์รหัส: {os.path.basename(token_path)}")
    source = {}
    captured = capture_token(profile_dir=profile_dir, source=source)
    if captured and check_and_save(captured, path=token_path):
        from bin.lib.RunBot import write_token_source
        write_token_source(token_path, source.get("line", "ดึงอัตโนมัติ"))
