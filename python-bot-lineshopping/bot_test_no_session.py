import os
import requests

from bin.lib.ApiLineShopping import ApiiLineShopping
from bin.lib.ToolsLineShopping import ToolsLineShopping


# =========================
# TEST: place-order-qr แบบไม่ส่ง x-la-session-id (เทียบกับ bot1.py)
# รันครั้งเดียว ไม่รอเวลา ไม่วนเช็ค stock
# =========================

# =========================
# CONFIG
# =========================
token = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "token_bot6.txt"), encoding="utf-8").read().strip()

shop_name = "@saifahbhayu"   # COWBOY BEAR TEE ฿490 มีตัวเลือก Size อย่างเดียว
id_product = 1008471376
size = "L"                   # ถ้าไม่เจอ/หมด ไฟล์จะพิมพ์รายการ size + stock ให้เลือกใหม่
quantity = 1


def print_sizes(data_product):
    product = (data_product or {}).get("data", {})
    for variant in product.get("product_variants", []) or []:
        print(
            "  size =", variant.get("variant_option_value1"),
            "| option2 =", variant.get("variant_option_value2"),
            "| stock =", variant.get("available"),
        )


def place_order_no_session(api, name_shop, json_data):
    # เหมือน ApiLineShopping.place_order ทุกอย่าง ยกเว้น "ไม่ส่ง" x-la-session-id
    headers = {
        'authorization': api.token,
        'x-la-session-id': '27410faa389540d3',
    }
    return api.session.post(
        f'https://sc-oms-api.line-apps.com/api/v6/shopend/{name_shop}/order/place-order-qr',
        headers=headers,
        json=json_data,
        timeout=api.timeout,
    )


if not token:
    print("ยังไม่ได้ใส่ token ใน CONFIG")
    raise SystemExit

api = ApiiLineShopping(token)
tools = ToolsLineShopping()

try:
    profile = api.profile()
    print(f"displayName : {profile.get('displayName')}")

    data_product = api.info_product(shop_name, id_product)
    stock_result = tools.find_variant_by_size(data_product, size, quantity)
    print("stock check:", stock_result["message"])
    if not stock_result["ok"]:
        print("size ที่มี:")
        print_sizes(data_product)
        raise SystemExit

    checkout_result = tools.build_checkout_payload(
        data_product=data_product,
        size=size,
        quantity=quantity,
    )
    if not checkout_result["ok"]:
        print("สร้าง checkout payload ไม่สำเร็จ:", checkout_result["message"])
        raise SystemExit

    check_out = api.checkout(json_data=checkout_result["payload"])
    print("checkout สำเร็จ")

    create_order_result = tools.build_create_order_payload(
        check_out=check_out,
        data_product=data_product,
        size=size,
        quantity=quantity,
        remark_buyer="",
        promotion_id="",
        cart_id="",
    )
    if not create_order_result["ok"]:
        print("สร้าง order payload ไม่สำเร็จ:", create_order_result["message"])
        raise SystemExit

    response = place_order_no_session(api, shop_name, create_order_result["payload"])
    print("place_order HTTP status:", response.status_code)
    print("place_order body:", response.text)

except requests.HTTPError as e:
    print("HTTP error ก่อนถึง place_order:", e)
    if e.response is not None:
        print(e.response.text)

finally:
    try:
        api.close()
    except Exception:
        pass
