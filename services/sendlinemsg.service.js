const axios = require('axios');

const sendLineMsgController = async (lineUuid, msg) => {
    
    await axios.post('https://api.line.me/v2/bot/message/push', {
        "to": lineUuid,
        "messages":[
            {
                "type": "text",
                "text": `${msg}`
            }
        ]
    }, {
        headers: {
            Authorization: `Bearer ${process.env.CHANNEL_ACCESS_TOKEN}`
        }
    }).then(async result => {
        console.log(result.data)
    }).catch(async err => {
        console.error("Error Details:", err.response.data.details)
    });
}



module.exports = {
    sendLineMsgController
};
  