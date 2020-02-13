import json
import os.path

import aiofiles
import aiohttp
from aiohttp import web

APP_ID = 'your-wxapp-appid'
APP_SECRET = 'your-wxapp-appsecret'

MESSAGE_TEMPLATE_ID_AUDIT_RESULT = 'S73bf3-i3rEnELYQyVbJBOTofmMMB-y8kQcrbgpOhjg'
MESSAGE_TEMPLATE_ID_PATROL_TASK = '2RtnwyVxdsLwhCv0a_ck6DjVFC0nFGkDlAnyGEM6FAo'

ACCESS_TOKEN_URL = (
    'https://api.weixin.qq.com/cgi-bin/token'
    '?grant_type=client_credential'
    '&appid={app_id}'
    '&secret={app_secret}'
).format(
    app_id=APP_ID,
    app_secret=APP_SECRET)

SEND_MESSAGE_URL = (
    'https://api.weixin.qq.com/cgi-bin/message/subscribe/send'
    '?access_token={access_token}'
)

CODE2SESSION_URL = (
    'https://api.weixin.qq.com/sns/jscode2session'
    '?appid={app_id}'
    '&secret={app_secret}'
    '&js_code={code}'
    '&grant_type=authorization_code'
)

async def _get_access_token():
    async with aiohttp.ClientSession() as session:
        async with session.get(ACCESS_TOKEN_URL) as resp:
            retdict = await resp.json()

    async with aiofiles.open('token.json', 'wb') as fp:
        await fp.write(json.dumps(retdict).encode())

    return retdict['access_token']

async def _read_access_token():
    if os.path.isfile('token.json'):
        async with aiofiles.open('token.json', 'rb') as fp:
            content = await fp.read()
        outdict = json.loads(content.decode())
        return outdict['access_token']
    else:
        return (await _get_access_token())

async def _get_openid(code):
    code2session_url = CODE2SESSION_URL.format(
        app_id=APP_ID,
        app_secret=APP_SECRET,
        code=code)
    async with aiohttp.ClientSession() as session:
        async with session.get(code2session_url) as resp:
            resp_text = await resp.text()
            retdict = json.loads(resp_text.encode())

    async with aiofiles.open('openid.json', 'wb') as fp:
        await fp.write(json.dumps(retdict).encode())

    return retdict['openid']

async def _read_openid():
    if os.path.isfile('openid.json'):
        async with aiofiles.open('openid.json', 'rb') as fp:
            content = await fp.read()
        outdict = json.loads(content.decode())
        return outdict['openid']
    return None

def make_audit_result_message(openid, data):
    return {
        'touser': openid,
        'template_id': MESSAGE_TEMPLATE_ID_AUDIT_RESULT,
        # page -> project uri
        'page': 'index',
        'miniprogram_state': 'developer',
        'lang': 'zh_CN',
        'data': {
            'phrase1': {
                'value': data.get('result', '')
            },
            'thing2': {
                'value': data.get('project_name', '')
            },
            'thing12': {
                'value': data.get('reason', '')
            }
      }
    }

def make_patrol_task_message(openid, data):
    return {
        'touser': openid,
        'template_id': MESSAGE_TEMPLATE_ID_PATROL_TASK,
        # page -> project uri
        'page': 'index',
        'miniprogram_state': 'developer',
        'lang': 'zh_CN',
        'data': {
            'thing1': {
                'value': data.get('patrol_type', '')
            },
            'thing2': {
                'value': data.get('patrol_description', '')
            },
            'thing3': {
                'value': data.get('reason', '')
            },
            'date4': {
                'value': data.get('patrol_date', '')
            }
      }
    }

async def _send_messages(openid):
    access_token = await _read_access_token()
    send_message_url = SEND_MESSAGE_URL.format(access_token=access_token)
    async with aiohttp.ClientSession() as session:
        audit_result_message = make_audit_result_message(
            openid,
            {
                'result': '通过',
                'project_name': '房屋装修',
                'reason': '无',
            }
        )
        print('Sending audit result message to {} ...'.format(openid))
        async with session.post(send_message_url, json=audit_result_message) as resp:
            retdict = await resp.json()
        print(retdict)

        patrol_task_message = make_patrol_task_message(
            openid,
            {
                'patrol_type': '备案审核',
                'patrol_description': '项目：房屋装修',
                'reason': '无',
                'patrol_date': '2020-02-14',
            }
        )
        print('Sending patrol task message to {} ...'.format(openid))
        async with session.post(send_message_url, json=patrol_task_message) as resp:
            retdict = await resp.json()
        print(retdict)

async def handle_sync_openid(request):
    code = request.query.get('code', '')
    if not code:
        raise web.HTTPBadRequest(text='code is required')

    openid = await _get_openid(code)
    return web.Response(text="done")

async def handle_send(request):
    openid = await _read_openid()
    if openid is None:
        raise web.HTTPBadRequest(text='no openid synced yet')
    await _send_messages(openid)
    return web.Response(text="done")

app = web.Application()
app.add_routes([
    web.get('/sync_openid', handle_sync_openid),
    web.get('/send', handle_send),
])

if __name__ == '__main__':
    web.run_app(app)
