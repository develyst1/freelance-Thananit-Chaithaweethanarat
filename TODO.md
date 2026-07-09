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
