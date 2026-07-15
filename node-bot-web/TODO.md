# TODO / งานค้าง — GentleWoman/MatterMakers Bot

อัปเดตล่าสุด: 2026-07-09

---

## 🔧 งานที่ยังค้าง (ยังไม่ได้ทำ)

### 1. ลบ DEBUG log ออกจาก `purchase.service.js`
- **จุด**: ในฟังก์ชัน `purchase()` — บรรทัดที่ print `ออเดอร์ ${order.id} getMemberCart =>` (ใส่ไว้ชั่วคราวตอน debug ปัญหา 304)
- **ทำไม**: ยืนยันแล้วว่าระบบทำงานถูกต้อง ไม่ต้องใช้ log นี้แล้ว เอาออกให้ log สะอาด
- **หมายเหตุ**: ตัว guard `if (!memberCart) { ... }` ให้คงไว้ (อันนั้นจำเป็น) ลบเฉพาะบรรทัด `console.log(... getMemberCart =>)`

### 2. แก้บั๊ก `==` ที่ `app.js` (โหมด RESTOCK)
- **จุด**: ในฟังก์ชัน `makeOrder()` → บล็อก `if (orderType === 'RESTOCK')` มีบรรทัด:
  ```js
  orderAddData.cart == {          // ❌ ใช้ == (เปรียบเทียบ) แทน = (กำหนดค่า)
      details: addToCartResponse.result,
      productData: addToCartResponse.productData
  };
  ```
- **ผลของบั๊ก**: ออเดอร์ประเภท `RESTOCK` จะไม่ถูกบันทึกข้อมูลตะกร้า (`cart`) ลง DB → ตอน `purchase()` ไปอ่าน `order.cart.details.data` แล้วพัง (คนละเคสกับปัญหา 304 ที่เจอตอนแรก ซึ่งเป็นออเดอร์ NEW)
- **วิธีแก้**: เปลี่ยน `==` เป็น `=` และตรวจว่า logic การเซฟ cart ของ RESTOCK ถูกต้อง (เทียบกับ flow ของ NEW ใน `purchase.service.js`)
- **ความสำคัญ**: จำเป็นถ้าลูกค้าจะใช้โหมด RESTOCK — ถ้าใช้แต่โหมด NEW ยังไม่กระทบ

---

### 4. [✅ แก้แล้ว 2026-07-09] 400 Bad Request ตอนยิงออเดอร์ เมื่อจำนวนสินค้า (amount) > 1
- **สถานะ: แก้แล้ว** — เปลี่ยน `price`/`full_price` เป็น `e.price` (ราคาต่อชิ้น) ใน `skusList`
- **ยืนยันสเปกจาก `addToCart` ใน app.js** ที่ API ยอมรับสำเร็จ: ใช้ `selectedSku.price` (ต่อชิ้น) + `amount` เป็นตัวคูณ
- ⚠️ **ยังต้องทดสอบจริงกับออเดอร์ที่ amount ≥ 2**
- **จุด**: `purchase.service.js` ในการสร้าง `skusList` — บรรทัด `full_price` และ `price` ใช้ `e.price * e.amount`
- **อาการ**: order ที่ amount = 1 ยิงผ่าน แต่ amount ≥ 2 โดน 400 Bad Request
- **วิเคราะห์ (พิสูจน์จาก log order 41)**:
  - ราคาต่อชิ้น 1770 × 3 ชิ้น → โค้ดใส่ `price = 5310` **พร้อมส่ง** `amount = 3`
  - server คิดซ้ำ `price × amount` = 5310 × 3 = 15930 ≠ `debt_amount` 5310 → 400
  - ที่ amount = 1 บั๊กไม่โผล่เพราะ `price × 1` บังเอิญตรงยอดพอดี
- **แนวทางแก้ (เมื่อพร้อม)**: เปลี่ยน `price`/`full_price` เป็นราคาต่อชิ้น `e.price` (คง `totalPrice += e.price * e.amount` ไว้สำหรับ payments)
  - ⚠️ ก่อนแก้จริง ควร capture request ตอน checkout สินค้า 2+ ชิ้น จากหน้าเว็บจริง (DevTools) เพื่อยืนยันสเปก field `price`/`full_price`/`amount` ให้ตรง 100%
- **หมายเหตุ**: บั๊กนี้เป็นโค้ดเดิมตั้งแต่ต้น ไม่เกี่ยวกับการรีแฟคเตอร์ config (config ของ Gentlewoman ให้ค่าเท่าเดิมทุกตัว)

---

## ⚠️ ต้องยืนยันด้วยการทดสอบ (ก่อนใช้ Matter Makers จริง)

### 3. ยืนยันค่า `brand` ของ Matter Makers ใน `config.js`
- ตอนนี้ตั้งไว้ `brand: 'Matter Makers'` (เดาจากชื่อร้าน)
- API อาจต้องการสตริงเป๊ะ ๆ (เช่น `'MATTER MAKERS'` หรือค่าอื่น)
- **วิธีเช็ค**: ยิงทดสอบ 1 ออเดอร์กับสินค้าจริงของ Matter Makers — ถ้าผ่าน = ใช้ได้; ถ้า error เรื่อง brand ให้ปรับค่านี้ (แก้จุดเดียวใน `config.js`)

---

## ✅ ที่แก้ไปแล้ว (บันทึกไว้เป็นบริบท)


- **แก้ปัญหา 304 Not Modified**: ลบ header `if-none-match` ที่ hardcode ไว้ออกจากทุก request
  (`getMemberCart`, `getMemberInfo`, `checkProduct` ใน `app.js` + `checkstock` ใน `purchase.service.js`)
  → เดิมทำให้ server ตอบ 304 body ว่าง แล้วบอตดึงตะกร้าไม่ได้ → crash
- **เพิ่ม guard กัน null** หลัง `getMemberCart` ใน `purchase.service.js` (กัน crash แต่ยอมให้ตะกร้าว่าง `data:null` ซึ่งปกติของออเดอร์ NEW)
- **รองรับหลายร้านผ่าน `config.js`**: สลับ Gentlewoman ↔ Matter Makers ได้จากบรรทัดเดียว (`ACTIVE_SHOP`)
  - Matter Makers ใช้ backend + captcha เดียวกับ Gentlewoman ต่างแค่ `store_id` (`645a1d00765d5519beeb97f6`)
