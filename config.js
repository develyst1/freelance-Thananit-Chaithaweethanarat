// ============================================================
//  ตั้งค่าร้าน (สลับร้านได้ที่ไฟล์เดียวนี้)
//
//  วิธีสลับร้าน: แก้ค่า ACTIVE_SHOP ด้านล่างให้เป็นชื่อร้านที่ต้องการ
//               ('gentlewoman' หรือ 'mattermakers')
//               หรือรันด้วย env var เช่น:  SHOP=mattermakers node app.js
//
//  หมายเหตุ: ต้องตั้งให้ตรงกันทั้ง START.bat (purchase.service.js)
//           และ ORDER.bat (app.js) เพราะเป็นคนละโปรเซส
// ============================================================

const SHOPS = {
    gentlewoman: {
        name: 'Gentlewoman',
        botName: 'GentleWomanBot',
        apiUrl: 'https://api.gentlewomanonline.com',
        storeId: '5e3548c2d32cb12606a34fb8',
        origin: 'https://www.gentlewomanonline.com',
        referer: 'https://www.gentlewomanonline.com/',
        storeUrl: 'https://www.gentlewomanonline.com/',
        brand: 'Gentlewoman',
        turnstile: {
            siteKey: '0x4AAAAAAACIwpy0TIYPN4ef',
            siteUrl: 'https://www.gentlewomanonline.com',
        },
    },

    mattermakers: {
        name: 'Matter Makers',
        botName: 'MatterMakersBot',
        apiUrl: 'https://api.gentlewomanonline.com', // ใช้ backend ตัวเดียวกับ Gentlewoman
        storeId: '645a1d00765d5519beeb97f6',
        origin: 'https://matter-makers.com',
        referer: 'https://matter-makers.com/',
        storeUrl: 'https://matter-makers.com/',
        brand: 'Matter Makers', // ⚠️ ยังไม่ยืนยัน 100% — เช็คด้วยออเดอร์ทดสอบ 1 รายการ ว่า API รับค่านี้ไหม
        turnstile: {
            siteKey: '0x4AAAAAAACIwpy0TIYPN4ef', // captcha (Cloudflare Turnstile) ตัวเดียวกัน
            siteUrl: 'https://matter-makers.com',
        },
    },
};

// >>>>>>>>>> สลับร้านตรงนี้ <<<<<<<<<<
// เปลี่ยนเป็น 'mattermakers' เมื่อจะยิงร้าน Matter Makers
const ACTIVE_SHOP = process.env.SHOP || 'gentlewoman';

const shop = SHOPS[ACTIVE_SHOP];
if (!shop) {
    throw new Error(`[CONFIG] ไม่รู้จักร้าน "${ACTIVE_SHOP}" — ใช้ได้เฉพาะ: ${Object.keys(SHOPS).join(' | ')}`);
}

// base URL ของ API พร้อม store id — ใช้ต่อ endpoint เช่น `${shop.apiBase}/products/xxx`
shop.apiBase = `${shop.apiUrl}/public/${shop.storeId}`;

console.log(`\n[CONFIG] ร้านที่ใช้งาน: ${shop.name}  (store_id: ${shop.storeId})\n`);

module.exports = shop;
