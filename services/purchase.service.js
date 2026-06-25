const axios = require('axios');
const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();
const { HttpsProxyAgent } = require('https-proxy-agent');
const { sendLineMsgController } = require('../services/sendlinemsg.service');
const { getMemberInfo, getMemberCart, addToCart } = require('../app');
// const { getMemberInfo, getMemberCart, addToCart, checkProduct } = require('../app');

const proxies = [
    { host: 'v2.proxyempire.io', port: 5000, auth: { username: 'r_30a858cea3-country-th', password: '619e242cd5' } },
    { host: 'v2.proxyempire.io', port: 5000, auth: { username: 'r_30a858cea3-country-th', password: '619e242cd5' } },
    { host: 'v2.proxyempire.io', port: 5000, auth: { username: 'r_30a858cea3-country-th', password: '619e242cd5' } },
    { host: 'v2.proxyempire.io', port: 5000, auth: { username: 'r_30a858cea3-country-th', password: '619e242cd5' } },
    // { host: 'v2.proxyempire.io', port: 5000, auth: { username: 'r_30a858cea3-country-th', password: '619e242cd5' } },
    { host: 'v2.proxyempire.io', port: 5000, auth: { username: 'r_30a858cea3-country-th', password: '619e242cd5' } },
    { host: 'v2.proxyempire.io', port: 5000, auth: { username: 'r_30a858cea3-country-th', password: '619e242cd5' } },
    // { host: 'v2.proxyempire.io', port: 5000, auth: { username: 'r_30a858cea3-country-th', password: '619e242cd5' } },
    // { host: 'v2.proxyempire.io', port: 5000, auth: { username: 'r_30a858cea3-country-th', password: '619e242cd5' } },
    { host: 'v2.proxyempire.io', port: 5000, auth: { username: 'r_30a858cea3-country-th', password: '619e242cd5' } },
    { host: 'v2.proxyempire.io', port: 5000, auth: { username: 'r_30a858cea3-country-th', password: '619e242cd5' } },
    { host: 'v2.proxyempire.io', port: 5000, auth: { username: 'r_30a858cea3-country-th', password: '619e242cd5' } },
    // { host: 'v2.proxyempire.io', port: 5000, auth: { username: 'r_30a858cea3-country-th', password: '619e242cd5' } },
    { host: 'v2.proxyempire.io', port: 5000, auth: { username: 'r_30a858cea3-country-th', password: '619e242cd5' } },
    { host: 'v2.proxyempire.io', port: 5000, auth: { username: 'r_30a858cea3-country-th', password: '619e242cd5' } },
    { host: 'v2.proxyempire.io', port: 5000, auth: { username: 'r_30a858cea3-country-th', password: '619e242cd5' } },
    { host: 'v2.proxyempire.io', port: 5000, auth: { username: 'r_30a858cea3-country-th', password: '619e242cd5' } },
    { host: 'v2.proxyempire.io', port: 5000, auth: { username: 'r_30a858cea3-country-th', password: '619e242cd5' } },
    // { host: 'v2.proxyempire.io', port: 5000, auth: { username: 'r_30a858cea3-country-th', password: '619e242cd5' } },  
];

const proxyAgents = proxies.map(proxy => 
    new HttpsProxyAgent(`http://${proxy.auth.username}:${proxy.auth.password}@${proxy.host}:${proxy.port}`)
);

let shuffledIndices = [];

const shuffleProxies = () => {
    shuffledIndices = proxyAgents.map((_, index) => index);  // สร้าง array ของ index
    for (let i = shuffledIndices.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [shuffledIndices[i], shuffledIndices[j]] = [shuffledIndices[j], shuffledIndices[i]];
    }
};

const getNextProxy = () => {
    if (shuffledIndices.length === 0) {
        shuffleProxies();  // เมื่อใช้ proxies หมดแล้ว ให้ทำการสับใหม่
    }
    const index = shuffledIndices.pop();  // ดึง index ที่สุ่มมาใช้
    const proxy = proxyAgents[index];  // ดึง proxy จาก proxyAgents ด้วย index
    const dns = proxies[index].dns;
    return { proxy, index, dns };
};

async function capsolver() {
    let captcha;

    const api_key = 'CAP-D2E36C98131C55173468F9524C5C0376689D5DD1C820959DC1745263BB1A9560';
    const site_url = "https://www.gentlewomanonline.com";

    const site_key = "0x4AAAAAAACIwpy0TIYPN4ef";

    const payload = {
        clientKey: api_key,
        task: {
          type: 'AntiTurnstileTaskProxyLess',
          websiteKey: site_key,
          websiteURL: site_url,
          metadata: {
              action: ''  // optional
          }
        }
    };

    try {
        const res = await axios.post("https://api.capsolver.com/createTask", payload);
        const task_id = res.data.taskId;
        if (!task_id) {
            console.log("Failed to create task:", res.data);
        }
    
        while (true) {
            await new Promise(resolve => setTimeout(resolve, 1000));
        
            const getResultPayload = {clientKey: api_key, taskId: task_id};
            const resp = await axios.post("https://api.capsolver.com/getTaskResult", getResultPayload);
            const status = resp.data.status;

            const now = new Date();
            now.setHours(now.getHours() + 7);
        
            if (status === "ready") {
                captcha = resp.data.solution.token;
                break;
            }
            if (status === "failed" || resp.data.errorId) {
              console.log("Solve failed!");
              break;
            }
        }
    } catch (error) {
        console.error("Error:", error);
    }

    return captcha;
}

const removeAndGenerateCaptcha = async () => {
    const fiveMinutesAgo = new Date();
    fiveMinutesAgo.setHours(fiveMinutesAgo.getHours() + 7);
    fiveMinutesAgo.setMinutes(fiveMinutesAgo.getMinutes() - 5);

    const now = new Date();
    now.setHours(now.getHours() + 7);

    const waitingOrders = await prisma.order.findMany({
        where: {
            status: 'WAITING'
        }
    });

    const orderPromises = waitingOrders.map(async (thisOrder) => {
        const createNewCaptcha = async () => {
            let newCapt;
            while (!newCapt) {
                newCapt = await capsolver();
            }
    
            const data = {
                output: newCapt,
                gen_time: now
            }
    
            await prisma.order.update({
                where: {
                    id: Number(thisOrder.id)
                },
                data: {
                    captcha: data
                }
            });

            console.log(`Order : ${thisOrder.id} Captcha generated successful!`);
        }

        if (thisOrder.captcha) {
            const expiredCaptcha = new Date(thisOrder.captcha.gen_time).getTime() < fiveMinutesAgo.getTime();
            if (expiredCaptcha) {
                await createNewCaptcha();
            }
        } else {
            await createNewCaptcha();
        }
    });

    await Promise.all(orderPromises);
}

setInterval(async () => {
    removeAndGenerateCaptcha();
}, 8000);

setInterval(async () => {
    const checklist = await prisma.checklist.findMany();

    const promisesChecklist = checklist.map(async (items, index) => {
        await checkstock(items);
    });

    await Promise.all(promisesChecklist);
}, 100);

const checkstock = async (thisChecklist) => {
    const { proxy, index, dns } = getNextProxy();
    const start = Date.now();
    axios.get(`https://api.gentlewomanonline.com/public/5e3548c2d32cb12606a34fb8/products/${thisChecklist.product_id}`, {
        headers: {
            // "Host": "api.gentlewomanonline.com",
            "accept": "application/json, text/plain, */*",
            "accept-language": "th-TH,th;q=0.9",
            // ลบ if-none-match ออก: ETag ที่ hardcode ไว้ทำให้ server ตอบ 304 Not Modified (body ว่าง) เมื่อ ETag ตรงกัน
            "priority": "u=1, i",
            "sec-ch-ua": "\"Google Chrome\";v=\"129\", \"Not=A?Brand\";v=\"8\", \"Chromium\";v=\"129\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "Referer": "https://www.gentlewomanonline.com/",
            "Referrer-Policy": "strict-origin-when-cross-origin"
        },
        timeout: 2000,
        httpsAgent: proxy,
    })
    .then(async response => {
        const skus = response.data.data.skus;
        const filteredSku = skus.find(e => e.code == thisChecklist.sku_id);
        // console.log(filteredSku)
        
        const on_hand_qty = filteredSku.stock[0].on_hand_qty;
        const on_reserved_qty = filteredSku.stock[0].on_reserved_qty;

        console.log(Date.now() - start, on_reserved_qty, on_hand_qty);

        const now = new Date();
        const hour = now.getHours();
        const minute = now.getMinutes();
        const second = now.getSeconds();
        
        if ((on_reserved_qty < on_hand_qty) && hour >= 10 && minute >= 0 && second >= 0) {
            const promisesOrder = thisChecklist.order.map(async e => {
                await purchase(e);
            });

            await Promise.all(promisesOrder);
        }
    })
    .catch((err) => {
        // console.log(err);
        console.log(`Upstream error : ${proxies[index].host}`);
        return null;
    })
}

const purchase = async (orderId) => {
    let order = await prisma.order.findFirst({
        where: {
            id: Number(orderId)
        }
    });

    if (!order || order.status !== 'WAITING' || !order.captcha) {
        return;
    }

    try {
        console.log('Purchasing...');
    
        await prisma.order.update({
            where: {
                id: order.id
            },
            data: {
                status: 'PROCESSING'
            }
        });
    
        if (order.orderType == 'NEW' && !order.cart) {
            const memberInfo = await getMemberInfo(String(order.auth));
        
            if (!memberInfo || memberInfo.message !== 'done') {
                console.log(`ออเดอร์ ${order.id} ไม่พบสมาชิกที่ตรงกับเบอร์โทรนี้`);
                await prisma.order.update({
                    where: {
                        id: order.id
                    },
                    data: {
                        status: 'FAILED'
                    }
                });
                return;
            }
        
            const userId = memberInfo.data.id;
        
            const memberCart = await getMemberCart(order.auth);

            // กัน null: ถ้าดึงตะกร้าไม่สำเร็จ (เช่นโดน 304 Not Modified body ว่าง) memberCart จะเป็น null
            // โยน error ให้ catch ด้านล่าง reset order กลับเป็น WAITING แล้วลองใหม่ แทนที่จะ crash เป็น TypeError
            if (!memberCart || !memberCart.data) {
                console.log(`ออเดอร์ ${order.id} ดึงข้อมูลตะกร้าสมาชิกไม่สำเร็จ (อาจโดน 304/Not Modified) กำลังรอการลองใหม่...`);
                throw new Error('ดึงข้อมูลตะกร้าสมาชิกไม่สำเร็จ');
            }

            const addToCartResponse = await addToCart(order.productId, memberCart.data, memberInfo.data, order.skuCode, order.auth);
    
            if (!addToCartResponse || addToCartResponse.result.message !== 'done') {
                console.log('เพิ่มสินค้าเข้าตะกร้าล้มเหลว กรุณาลองใหม่อีกครั้ง!');
                throw new Error('เพิ่มสินค้าเข้าตะกร้าล้มเหลว กรุณาลองใหม่อีกครั้ง!');
            }
        
            const savedData = {
                details: addToCartResponse.result,
                productData: addToCartResponse.productData
            }
        
            order = await prisma.order.update({
                where: {
                    id: order.id
                },
                data: {
                    cart: savedData,
                    memberInfo: memberInfo.data,
                }
            });
        }

        console.log('Added to cart... Purchasing...');
    
        const orderData = order.cart.details.data;
        const productData = order.cart.productData;
        const cartId = orderData.id;
        const items = orderData.items;
        const memberInfo = order.memberInfo;
    
        const updatedAt = new Date(orderData.updated_at);
        const expiredAt = new Date(updatedAt);
        expiredAt.setMinutes(updatedAt.getMinutes() + 10);
    
        const captcha = order.captcha.output;
    
        let totalPrice = 0;
    
        const skusList = items.map(e => {
            totalPrice += e.price * e.amount;
            return {
                "id": e.id,
                "code": e.code,
                "product_id": e.product_id,
                "name": productData.name,
                "color": e.color,
                "size": e.size,
                "description": "",
                "is_on_web": true,
                "option": "",
                "full_price": e.price * e.amount,
                "images": [productData.photo_urls[0]],
                "categories": productData.categories,
                "gw_collection": productData.gw_collection,
                "group_categories": productData.group_categories,
                "tags": productData.tags,
                "brand": productData.brand,
                "variant": "SKU",
                "pre_order": false,
                "pre_order_note": "",
                "price": e.price * e.amount,
                "amount": e.amount
            }
        })
    
        const data = {
            "cart_id": cartId,
            "expire": `${new Date(expiredAt).toISOString()}`,
            "discount": 0,
            "skus": skusList,
            "tags": [],
            "member": {
                "email": memberInfo.email,
                "first_name": memberInfo.first_name,
                "id": memberInfo.id,
                "last_name": memberInfo.last_name,
                "tel": memberInfo.tel
            },
            "shipping_address": {
                "first_name": memberInfo.addresses[0].first_name,
                "last_name": memberInfo.addresses[0].last_name,
                "tel": memberInfo.addresses[0].contact_no,
                "email": memberInfo.addresses[0].email,
                "address": memberInfo.addresses[0].address,
                "address2": memberInfo.addresses[0].address2,
                "sub_district": memberInfo.addresses[0].states,
                "district": memberInfo.addresses[0].district,
                "state_province": memberInfo.addresses[0].province,
                "postcode": memberInfo.addresses[0].postcode,
                "country": memberInfo.addresses[0].country,
                "tax_id": memberInfo.addresses[0].tax_id,
                "default_shipping": memberInfo.addresses[0].default_shipping,
                "contact_no": memberInfo.addresses[0].contact_no
            },
            "shipping": {
                "country": orderData.shipping_fee.country,
                "postcode": memberInfo.addresses[0].postcode,
                "state_province": memberInfo.addresses[0].province,
                "method": "EMS",
                "label": "Thailand (ไทย)",
                "note": "",
                "price": orderData.shipping_fee.price,
                "provider_name": "EMS",
                "locations": [],
                "fee": 0
            },
            "payments": [
                {
                "pay_order": 1,
                "debt_amount": totalPrice,
                "sum_debt_amount": totalPrice
                }
            ],
            "promotion_code": null,
            "warehouse": null,
            "dhl_packages": [],
            "gender": "male",
            "brand": "Gentlewoman",
            "channel": "web"
        };
    
        axios.post('https://api.gentlewomanonline.com/public/5e3548c2d32cb12606a34fb8/orders', data, {
            headers: {
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'th-TH,th;q=0.9',
                'cf-turnstile-response': captcha,
                'content-type': 'application/json',
                'origin': 'https://www.gentlewomanonline.com',
                'priority': 'u=1, i',
                'referer': 'https://www.gentlewomanonline.com/',
                'sec-ch-ua': '"Google Chrome";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-site',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36'
            } 
        })
        .then(async response => {
            console.log(response.data);
            if (response.data.message == 'done') {
                await prisma.order.update({
                    where: {
                        id: order.id
                    },
                    data: {
                        status: 'SUCCESS'
                    }
                });
                await sendLineMsgController(order.lineUuid, `GentleWomanBot : เบอร์ ${order.userTel} ทำการสั่งซื้อสินค้า ${productData.name} สำเร็จแล้ว กรุณาตรวจสอบรายการสินค้าและชำระเงินที่ : https://www.gentlewomanonline.com/ ขอบคุณที่ใช้บริการ`);
                await sendLineMsgController('U6e162d9178e4fd734e7a98ced75377c5', `GentleWomanBot : เบอร์ ${order.userTel} ทำการสั่งซื้อสินค้า ${productData.name} สำเร็จแล้ว กรุณาตรวจสอบรายการสินค้าและชำระเงินที่ : https://www.gentlewomanonline.com/ ขอบคุณที่ใช้บริการ`);
            } else {
                throw new Error('Purchased Failed');
            }
        })
        .catch(async error => {
            console.error('Purchase Error:', error);
            await prisma.order.update({
                where: {
                    id: order.id
                },
                data: {
                    status: 'WAITING',
                    captcha: null
                }
            });
            await sendLineMsgController(order.lineUuid, `GentleWomanBot : เบอร์ ${order.userTel} ทำการสั่งซื้อสินค้า ${productData.name} ล้มเหลว กำลังรอการลองใหม่...`);
            await sendLineMsgController('U6e162d9178e4fd734e7a98ced75377c5', `GentleWomanBot : เบอร์ ${order.userTel} ทำการสั่งซื้อสินค้า ${productData.name} ล้มเหลว กำลังรอการลองใหม่...`);
        });
    } catch (err) {
        console.log('Try Catch Error', err);
        await prisma.order.update({
            where: {
                id: order.id
            },
            data: {
                status: 'WAITING',
            }
        });
    }
}