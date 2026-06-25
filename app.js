const axios = require('axios');
const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();
const readline = require('readline');
const { sendLineMsgController } = require('./services/sendlinemsg.service');

const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
});

const getMemberCart = async (token) => {
    return axios.get(`https://api.gentlewomanonline.com/public/5e3548c2d32cb12606a34fb8/carts/member/data`, {
        headers: {
          'accept': 'application/json, text/plain, */*',
          'accept-language': 'th-TH,th;q=0.9',
          'Authorization': `Bearer ${token}`,
          'if-none-match': 'W/"1e-RzAxu20wYTihj0IC3gjZx7kZnAc"',
          'origin': 'https://www.gentlelittlewoman.com',
          'priority': 'u=1, i',
          'referer': 'https://www.gentlelittlewoman.com/',
          'sec-ch-ua': '"Google Chrome";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
          'sec-ch-ua-mobile': '?0',
          'sec-ch-ua-platform': '"Windows"',
          'sec-fetch-dest': 'empty',
          'sec-fetch-mode': 'cors',
          'sec-fetch-site': 'cross-site',
          'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36'
        }
    })
      .then(response => {
        return response.data;
    })
      .catch(error => {
        console.error('Error:', error);
        return null;
    });
}

const getMemberInfo = async (token) => {
    try {
        const response = await fetch("https://api.gentlewomanonline.com/public/5e3548c2d32cb12606a34fb8/members/info", {
            "headers": {
                "accept": "application/json, text/plain, */*",
                "accept-language": "en-US,en;q=0.9",
                "authorization": `Bearer ${token}`,
                "if-none-match": "W/\"4a8-YCHoCZWSZCspiBm31idLBNfz9+I\"",
                "priority": "u=1, i",
                "sec-ch-ua": "\"Not(A:Brand\";v=\"8\", \"Chromium\";v=\"144\", \"Google Chrome\";v=\"144\"",
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": "\"Windows\"",
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-site",
                "Referer": "https://www.gentlewomanonline.com/"
        },
            "body": null,
            "method": "GET"
        });

        const result = await response.json();
        return result;
    } catch (err) {
        console.error('Error:', err);
        return null;
    }
}

const checkProduct = async (productId) => {
    return axios.get(`https://api.gentlewomanonline.com/public/5e3548c2d32cb12606a34fb8/products/${productId}`, {
        headers: {
            "accept": "application/json, text/plain, */*",
            "accept-language": "th-TH,th;q=0.9",
            "if-none-match": "W/\"cd6-AkyCp2FOZiBT8YmRMZ4YiZ/SH8k\"",
            "priority": "u=1, i",
            "sec-ch-ua": "\"Google Chrome\";v=\"129\", \"Not=A?Brand\";v=\"8\", \"Chromium\";v=\"129\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "Referer": "https://www.gentlewomanonline.com/",
            "Referrer-Policy": "strict-origin-when-cross-origin"
        }
    })
    .then(async response => {
        return response.data;
    })
    .catch((err) => {
        console.log(err);
        return null;
    })
}

const addToCart = async (productId, memberCart, memberInfo, skuCode, token) => {
    const cartId = memberCart ? memberCart.id ? memberCart.id : null : null;

    const checkProductResult = await checkProduct(productId);
    if (checkProductResult) {
        const productData = checkProductResult.data;
        const skus = productData.skus;
        const selectedSku = skus.find(e => e.code == skuCode);
        const color = selectedSku.color.name;
        const size = selectedSku.size.name;
        const amount = 1;

        const data = {
            "amount": amount,
            "code": selectedSku.code,
            "full_price": selectedSku.price,
            "id": selectedSku.id,
            "item_price": selectedSku.price,
            "name": productData.name,
            "price": selectedSku.price,
            "product_id": selectedSku.product_id,
            "brand": productData.brand,
            "categories": productData.categories,
            "gw_collection": productData.gw_collection,
            "group_categories": productData.group_categories,
            "color": color,
            "description": "",
            "images": [productData.photo_urls[0]],
            "is_on_web": true,
            "pre_order": false,
            "pre_order_note": "",
            "option": "",
            "size": size,
            "tags": productData.tags,
            "variant": "SKU",
            "alias_id": selectedSku.alias_id,
            "product_alias_id": productData.alias_id
        };

        if (cartId) {
            return axios.patch(`https://api.gentlewomanonline.com/public/5e3548c2d32cb12606a34fb8/carts/${cartId}/add`, data, {
                headers: {
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'th-TH,th;q=0.9',
                'content-type': 'application/json',
                'Authorization': `Bearer ${token}`,
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
            .then(async addToCartResponse => {
                return { result: addToCartResponse.data, productData };
            })
            .catch(error => {
                console.error(error);
                return null;
            });
        } else {
            return axios.post(`https://api.gentlewomanonline.com/public/5e3548c2d32cb12606a34fb8/carts`, {
                brand: 'Gentlewoman',
                items: [data],
                member: {
                    email: memberInfo.email,
                    first_name: memberInfo.first_name,
                    id: memberInfo.id,
                    last_name: memberInfo.last_name,
                    tel: memberInfo.tel
                }
            }, {
                headers: {
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'th-TH,th;q=0.9',
                'content-type': 'application/json',
                'origin': 'https://www.gentlewomanonline.com',
                'Authorization': `Bearer ${token}`,
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
            .then(async addToCartResponse => {
                return { result: addToCartResponse.data, productData };
            })
            .catch(error => {
                console.error(error);
                return null;
            });
        }
    }
}

const makeOrder = async () => {
    console.log('Start making an order...');

    const start = async () => {
        rl.question('\nกรุณาระบุ Line Uuid : ', async (lineUuid) => {
            rl.question('\nกรุณาระบุไอดีสินค้า : ', async (productId) => {
                if (isNaN(productId)) {
                    console.log('กรุณาระบุไอดีสินค้าให้ถูกต้อง');
                    return start();
                }
    
                rl.question('\nกรุณาระบุเบอร์โทรผู้ใช้ ( ขึ้นต้นด้วย 66 ไม่ต้องมี + ) : ', async (userTel) => {
                    const existingOrderingUser = await prisma.order.findFirst({
                        where: {
                            status: 'WAITING',
                            userTel: userTel
                        }
                    });
                    
                    if (existingOrderingUser) {
                        console.log('รหัสนี้มีสินค้ากำลังรอสั่ง กรุณาสั่งด้วยรหัสอื่น');
                        return start();
                    }
    
                    if (isNaN(userTel) || !userTel.startsWith('66')) {
                        console.log('กรุณาระบุเบอร์โทรศัพท์ให้ถูกต้อง');
                        return start();
                    }
    
                    const productDetails = await checkProduct(productId);
                    console.log('\n\n');
                    console.log('======= รายการตัวเลือกสินค้า =======');
                    console.log('\n');
                    console.log(`ชื่อสินค้า : ${productDetails.data.name}`);
                    console.log('\n');
                    productDetails.data.skus.map(e => {
                        console.log(`รหัสสินค้า : ${e.code} || ไซส์ : ${e.size.name} || สี : ${e.color.name} || ราคา : ${Number(e.price).toFixed(2)} บาท`);
                    })
                    console.log('\n\n');
    
                    rl.question('\nกรุณาระบุรหัสสินค้าที่ต้องการ : ', async (skuCode) => {
                        const filteredSku = productDetails.data.skus.find(e => e.code == skuCode);
                        if (!filteredSku) {
                            console.log('กรุณาระบุรหัสสินค้าให้ถูกต้อง');
                            return start();
                        }

                        rl.question('\nกรุณาระบุประเภทการยิง (NEW || RESTOCK) : ', async (orderType) => {
                            rl.question('\nกรุณาระบุ AuthToken : ', async (authToken) => {
                                const memberInfo = await getMemberInfo(String(authToken));

                                if (!memberInfo || memberInfo.message !== 'done') {
                                    console.log('ไม่พบสมาชิกที่ตรงกับเบอร์โทรนี้');
                                    return start();
                                }
    
                                let orderAddData = {
                                    userTel,
                                    productId: productId,
                                    skuCode: skuCode,
                                    memberInfo: memberInfo.data,
                                    orderType: 'NEW',
                                    userId: 1,
                                    lineUuid: lineUuid,
                                    auth: authToken
                                }
    
                                if (orderType === 'RESTOCK') {
                                    // const userId = memberInfo.data.id;
                            
                                    const memberCart = await getMemberCart(authToken);
                                
                                    const addToCartResponse = await addToCart(productId, memberCart.data, memberInfo.data, skuCode, authToken);
                
                                    if (!addToCartResponse || addToCartResponse.result.message !== 'done') {
                                        console.log('เพิ่มสินค้าเข้าตะกร้าล้มเหลว กรุณาลองใหม่อีกครั้ง!');
                                        return start();
                                    }
    
                                    orderAddData.cart == {
                                        details: addToCartResponse.result,
                                        productData: addToCartResponse.productData
                                    };
                                }
    
                                const createdOrder = await prisma.order.create({
                                    data: orderAddData
                                });
            
                                const existingChecklist = await prisma.checklist.findFirst({
                                    where: {
                                        product_id: productId,
                                        sku_id: skuCode
                                    }
                                });
            
                                if (!existingChecklist) {
                                    await prisma.checklist.create({
                                        data: {
                                            product_id: productId,
                                            sku_id: skuCode,
                                            order: [Number(createdOrder.id)]
                                        }
                                    });
                                } else {
                                    const orderTemp = existingChecklist.order;
                                    orderTemp.push(Number(createdOrder.id));
                                    await prisma.checklist.update({
                                        where: {
                                            id: existingChecklist.id
                                        },
                                        data: {
                                            order: [Number(createdOrder.id)]
                                        }
                                    });
                                }
            
                                console.log(`\n\n=================================`);
                                console.log(`ออเดอร์ที่ ${createdOrder.id} ได้ถูกสร้างสำเร็จแล้ว!`);
                                console.log(`=================================\n\n`);
            
                                await sendLineMsgController(lineUuid, `GentleWomanBot : ทำการสร้างรายการสินค้า ${productDetails.data.name} สำเร็จแล้ว กำลังรอสินค้าเติมสต๊อก....`);
                                start();
                            });
                        });
                    });
                });
            });
        });
    }

    start();

}

makeOrder();


module.exports = {
    checkProduct,
    getMemberInfo,
    getMemberCart,
    addToCart,
};