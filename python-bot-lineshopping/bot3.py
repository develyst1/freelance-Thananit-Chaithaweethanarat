from bin.lib.RunBot import run


# =========================
# CONFIG
# =========================
token = ""  # ว่างไว้ได้ บอทจะถามตอนกด Run

shop_name = "@endlessholiday"
id_product = 1008329691
size = ""
quantity = 1
product_url = ""  # วางลิงก์สินค้า เช่น https://shop.line.me/@shop/product/123 (ว่างไว้ = ใช้ shop_name + id_product)
number = ""  # สินค้าที่มีตัวเลือก Number ด้วย ใส่เลขที่ต้องการ (ว่างไว้ถ้าไม่มี)
ask_sale_time = True  # True = ถามวันเวลาเปิดขายตอนกด Run
ui = "window"  # "window" = เปิดหน้าต่าง, "terminal" = แบบเดิม

start_bot_at = None

use_time_mode = True

allowed_time_ranges = [
    ("09:59:59", "23:59:59")
]

poll_interval_seconds = 1
auto_checkout_and_order = True

checkout_disable_auto_apply = False
checkout_is_gift = False

payment_app_switch_id = None
is_android = False
is_liff = False
remark_buyer = ""
point = None
ignore_point = None
promotion_id = ""
cart_id = ""
gift_info = None
seller_product_discount_coupon = None
seller_shipping_discount_coupon = None
subsidised_product_discount_coupon = None
bank_transfer = None


run(globals())
