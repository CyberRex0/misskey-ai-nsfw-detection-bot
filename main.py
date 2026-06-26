import json
import asyncio
import httpx
import urllib.parse
import os
import argparse
import logging
from websockets.asyncio.client import connect

# ログ設定
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("websockets").setLevel(logging.WARNING)
CONFIG = {}
MEDIA_IDS = set()
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36'

def check_config():
    """設定ファイルの必須キーが存在するか確認"""
    required_keys = ['misskey_host', 'misskey_admin_token', 'nsfw_detect_api_endpoint']
    for key in required_keys:
        if key not in CONFIG:
            logging.error(f'Configuration key missing: {key}')
            exit(1)

async def main():
    """メイン処理"""

    logger = logging.getLogger('main')

    # URLチェック
    urlinfo = urllib.parse.urlparse(CONFIG['misskey_host'])

    # プロトコルが不正かどうか
    if urlinfo.scheme not in ['http', 'https']:
        logger.error(f'Invalid misskey_host URL scheme. Must be http or https.')
        exit(1)

    # http(s)をws(s)に変換
    ws_protocol = 'wss' if urlinfo.scheme == 'https' else 'ws'

    host = urlinfo.netloc
    if not host:
        logger.error(f'Invalid misskey_host URL. Host is missing.')
        exit(1)
    
    # 監視するタイムラインの選択
    timeline = 'globalTimeline' if CONFIG.get('local_only', False) == False else 'localTimeline'

    async with connect(f"{ws_protocol}://{host}/streaming") as websocket:
        # ストリーミングに接続
        await websocket.send(json.dumps({
            'type': 'connect',
            'body': {
                'channel': timeline,
                'id': 'tl'
            }
        }))

        while True:
            response = await websocket.recv()
            
            data = json.loads(response)
            if data.get('type', '') == 'channel':
                body = data.get('body', {})
                if body.get('id', '') == 'tl' and body.get('type', '') == 'note':
                    note_body = body.get('body', {})

                    # ファイルのURLとファイルIDのリストを作成
                    # すでにセンシティブフラグが付いているものは二重チェック防止で無視する
                    # すでにチェックしたものは無視する
                    img_urls = []
                    for f in note_body.get('files', []):
                        if f.get('type', '').startswith('image/') and f.get('isSensitive', False) == False and f['id'] not in MEDIA_IDS:
                            img_urls.append({'url': f['url'], 'fileId': f['id']})
                            MEDIA_IDS.add(f['id'])

                    # マルチスレッドで実行
                    for img_url in img_urls:
                        asyncio.create_task(classify(img_url['url'], img_url['fileId']))

async def classify(img_url, fileId):
    logger = logging.getLogger('classify')
    http_client = httpx.AsyncClient(
        headers={'User-Agent': USER_AGENT},
        timeout=httpx.Timeout(10.0, connect=5.0)
    )

    logger.info(f'Classifying image: {img_url}')

    # 画像をダウンロード
    res = await http_client.get(img_url, follow_redirects=True)
    img_bytes = res.content

    # 評価実行
    is_nsfw = False
    eval_req = await http_client.post(
        CONFIG['nsfw_detect_api_endpoint'],
        files={'image0': img_bytes}
    )
    if not eval_req.status_code == 200:
        logger.error(f'Failed to classify for {img_url}')
        logger.error(f'Evaluation request failed with status code {eval_req.status_code}')
        return

    eval_res = eval_req.json()
    if eval_res.get('success', False) == False:
        logger.error(f'Failed to classify for {img_url}')
        logger.error(json.dumps(eval_res, indent=2, ensure_ascii=True))
        return
    
    result = eval_res['result']['results'][0]
    if result.get('success', False) == False:
        logger.error(f'Failed to classify for {img_url}')
        logger.error(json.dumps(eval_res, indent=2, ensure_ascii=True))
        return

    s_pred = [x for x in result['predictions'] if x['className'] == 'Sexy'][0]['probability']
    h_pred = [x for x in result['predictions'] if x['className'] == 'Hentai'][0]['probability']
    is_nsfw = (s_pred >= 0.9 or h_pred >= 0.9)
    
    logger.debug(f'Result for {img_url}: {is_nsfw}')

    #センシティブフラグを付ける
    if is_nsfw:
        logger.info(f'Marking image as sensitive: fileId={fileId}')
        req = await http_client.post(
            f'{CONFIG["misskey_host"]}/api/drive/files/update',
            headers={'Authorization': f'Bearer {CONFIG["misskey_admin_token"]}'},
            json={'fileId': fileId, 'isSensitive': True}
        )
        if not req.status_code == 200:
            logger.error(f'Failed to update file sensitivity for {img_url}')
            logger.error(f'Update request failed with status code {req.status_code}')
            logger.error(f'Response: {req.text}')
            logger.error('')
            return
        logger.info(f'File marked as sensitive successfully: fileId={fileId}')
    
    logger.info(f'Classification completed for {img_url}. NSFW: {is_nsfw}')

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description='Misskey AI NSFW Detection Bot')
    parser.add_argument('--config', help='Path to the configuration file', default='config.json')

    args = parser.parse_args()

    if not os.path.exists(args.config):
        print(f'Configuration file {args.config} not found.')
        exit(1)
    
    with open(args.config, 'r') as f:
        CONFIG = json.load(f)
    
    check_config()

    asyncio.run(main())
