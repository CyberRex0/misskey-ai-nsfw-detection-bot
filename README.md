# Misskey AI NSFW Detection Bot
このソフトウェアは、AIによるNSFWかどうかの分類を行い、NSFWと判定されたメディアに対してセンシティブフラグを設定するMisskey向けのボットです。

通常 [CyberRex0/misskey-ai-nsfw-detection-server](https://github.com/CyberRex0/misskey-ai-nsfw-detection-server) と組み合わせて使用します。<br>
このボット自体では分類を行っていないため、後述の設定でAPIエンドポイントを指定することで任意の判定サービスに接続可能です。

## 設定

config.json を作成します。

```json
{
    "misskey_host": "https://example.com",
    "misskey_admin_token": "your-token-here",
    "nsfw_detect_api_endpoint": "https://api.example.com/nsfw-detect",
    "local_only": false
}
```

- misskey_host

   監視を行うMisskeyサーバーのホスト名
   
   https:// か http:// から始まるURLを指定します

- misskey_admin_token

   監視を行うアカウントのAPIトークン

   センシティブフラグを付けるのに必要です

   モデレーター以上の権限があるアカウント、次の権限があるAPIトークンを使用してください

   ・ドライブを見る<br>
   ・ドライブを操作する<br>
   ・ユーザーに関する情報を見る<br>
   ・ユーザーのドライブを操作する<br>
   ・ユーザーのドライブの関する情報を見る

- nsfw_detect_api_endpoint

   NSFW検出を行うサーバーのエンドポイント

   通常は [CyberRex0/misskey-ai-nsfw-detection-server](https://github.com/CyberRex0/misskey-ai-nsfw-detection-server) を動かしているアドレスを指定します

- local_only

   LTLのメディアのみチェックを行うかどうか

   NSFW判定の負荷が高い場合、ローカルタイムラインのメディアに限定することで改善を図ります

## 使い方

ボットはPythonで作成しています。

次世代パッケージマネージャーのuvを使って簡単にセットアップできます。<br>
事前に [uv](https://github.com/astral-sh/uv) のインストールが必要です。

```shell
uv sync # 依存パッケージのインストール
uv run main.py # ボット起動
```

## プログラム実行パラメータ

プログラムを実行する時に次のパラメータが利用可能です。

- `--config /path/to/config.json`

  設定ファイル(JSON)のパスを指定します。複数起動する場合に便利です。
