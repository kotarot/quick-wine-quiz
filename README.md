# Quick Wine Quiz

(Forked from [UrbanInstitute/quick-quiz](https://github.com/UrbanInstitute/quick-quiz))

## Architecture

## Development

```bash
docker compose up
```

## Cloud Setup

### 1. SES (Simple Email Service)

#### 1-1. SES用S3バケット作成

以下の設定でSESで受信したメールデータを保存するためのS3バケットを作成する。省略している設定はデフォルトでOK.
- リージョン: us-east-1
- バケットタイプ: 汎用
- バケット名: quick-wine-quiz-email
- パブリックアクセスをすべてブロック: **オン**
- バケットのバージョニング: 無効

SESがS3バケットに書き込めるように、S3バケット → アクセス許可タブより、バケットポリシーに以下の設定を適用する。

※ `111122223333` を AWS ID に置き換える。

```javascript
{
  "Version":"2012-10-17",
  "Statement":[
    {
      "Sid":"AllowSESPuts",
      "Effect":"Allow",
      "Principal":{
        "Service":"ses.amazonaws.com"
      },
      "Action":"s3:PutObject",
      "Resource":"arn:aws:s3:::quick-wine-quiz-email/*",
      "Condition":{
        "StringEquals":{
          "AWS:SourceAccount":"111122223333",
          "AWS:SourceArn": "arn:aws:ses:us-east-1:111122223333:receipt-rule-set/quick-wine-quiz-email-receiver:receipt-rule/quick-wine-quiz-email-receiver-to-s3"
        }
      }
    }
  ]
}
```

#### 1-2. SESの初期設定

SESの初期セットアップ画面から以下の設定で始める。
- リージョン: us-east-1
- メールアドレス: すでに使える既存メールアドレスでOK
- 送信ドメイン: SESで利用したいドメインを入力 (説明では `example.com` とする)

※初期設定後はサンドボックス環境で始まり機能が制限されるが、大容量で使うことはないのでこのままでも大丈夫そう。

#### 1-3. ドメイン検証

メールアドレスの検証と、`example.com` に検証用CNAMEのDNSレコードを追加して、SESで検証が完了されるのを待つ。

#### 1-4. MXレコードの追加

`example.com` にMXレコードを追加する。

```
10 inbound-smtp.us-east-1.amazonaws.com
```

参考: [Amazon SES による E メール受信のための MX レコードの公開 - Amazon Simple Email Service](https://docs.aws.amazon.com/ja_jp/ses/latest/dg/receiving-email-mx-record.html)

#### 1-5. メール受信設定

SESでメールを受信する設定をする。左メニューの「Eメール受信」から「受信ルールセット」を新規作成する。

- ルールセット名: quick-wine-quiz-email-receiver

「ルールの作成」から新規ルールを作成する。

- ルール設定の定義
    - ルール名: quick-wine-quiz-email-receiver-to-s3
    - ステータス: 有効化
    - TLS必須: オフ
    - スパムとウイルススキャン: 有効化
- 受信者の条件の追加
    - 受信者の条件: `wine@example.com`
- アクションの追加
    - S3バケットへの配信
    - バケット名: 1-1 で作成したバケット
    - オブジェクトキープレフィックス: `ses-delivery/`

ルールを作成したらルールセット自体を有効化する。

### 2. クイズデータ用S3

#### 2-1. クイズデータ用S3バケット作成

以下の設定でクイズデータを保存するためのS3バケットを作成する。省略している設定はデフォルトでOK.
- リージョン: us-east-1
- バケットタイプ: 汎用
- バケット名: quick-wine-quiz
- パブリックアクセスをすべてブロック: **オフ**
- バケットのバージョニング: **有効**

#### 2-2. S3のバケットポリシーとCORSの設定

**公開の設定**

S3バケット → アクセス許可タブより、バケットポリシーに以下の設定を適用する。

```javascript
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::quick-wine-quiz/*"
        }
    ]
}
```

**CORS設定**

Javascriptからクロスオリジンでアクセスすることになってしまうので、S3が `Access-Control-Allow-Origin` ヘッダを返すように CORS (Cross-Origin Resource Sharing) を設定する。

S3バケット → アクセス許可タブより、CORSに以下の設定を適用する。

```javascript
[
    {
        "AllowedHeaders": ["*"],
        "AllowedMethods": ["GET", "HEAD"],
        "AllowedOrigins": ["https://kotarot.github.io"],
        "ExposeHeaders": ["Access-Control-Allow-Origin"],
        "MaxAgeSeconds": 3000
    }
]
```

**確認**

手元から curl コマンドで、以下のように `Access-Control-Allow-Origin` ヘッダの確認ができればOK.

```bash
$ curl -i https://quick-wine-quiz.s3.amazonaws.com/sample.json -H "Origin: https://kotarot.github.io"

HTTP/1.1 200 OK
x-amz-id-2: JrRwhZYb/sSlN4V8OIDdownF1+j3AdKnzz61hodI+ydMJ9L52dLnhuRGAEZrnFblT6F1TNK1h0U=
x-amz-request-id: 8V0HN1AY165164TP
Date: Mon, 12 Feb 2024 01:06:54 GMT
Access-Control-Allow-Origin: https://kotarot.github.io
Access-Control-Allow-Methods: GET, HEAD
Access-Control-Expose-Headers: Access-Control-Allow-Origin
Access-Control-Max-Age: 3000
Access-Control-Allow-Credentials: true
Vary: Origin, Access-Control-Request-Headers, Access-Control-Request-Method
Last-Modified: Mon, 12 Feb 2024 00:42:29 GMT
ETag: "a10d9bdec7ed5acd2c23419669a13a39"
x-amz-server-side-encryption: AES256
x-amz-version-id: 9XoA1LD3CwGviekhyIBrMrzzF9vH9hVt
Accept-Ranges: bytes
Content-Type: application/json
Server: AmazonS3
Content-Length: 1268

(snip)
```

### 3. Lambda

#### 3-1. 関数の作成

AWS Lambda関数を作成する。この関数はS3の `quick-wine-quiz-email` バケットに保存されているメールデータを集めてきて、それらのデータを集約した quick-quiz 用のJSONファイルを生成する。Lambda関数は定期実行される。

- 関数名: wine-emails-to-quick-quiz-json
- ランタイム: Python 3.12
- アーキテクチャ: x86_64
- 実行ロール: 基本的なLambdaアクセス権限で新しいロールを作成

ソースコードの内容は `lambda_functions/wine_emails_to_quick_quiz_json.py` を設定する。

#### 3-2. 関数の設定

「設定」タブからいくつかの設定項目を編集する。

- 一般設定
    - デフォルトのタイムアウト値が3秒になっているので、タイムアウト値を「10分」程にしておく。
- 同時実行
    - この後S3へのオブジェクト追加をトリガーにするが同時に関数が走らないように、次の設定にする。
        - 関数の同時実行: 予約された同時実行を使用
        - 予約された同時実行: 1

#### 3-3. ロールに許可ポリシーを付与

3-1で作成されたLambda用のIAMロールにS3の権限を付与する。

IAM管理画面から `wine-emails-to-quick-quiz-json-role-xxxxxxxx` のロールを開き、許可ポリシーに `AmazonS3FullAccess` を追加する（強引なのは承知）。

#### 3-4. トリガーの追加

トリガーを設定する。S3へのオブジェクト追加をトリガーにする。

- ソース: S3
- Bucket: s3/quick-wine-quiz-email
- Event types: PUT
- Prefix: `ses-delivery/`

FYI: 定期実行 (CRON) を設定するためには EventBridge を用いる。

- ソース: EventBridge
- Rule: Create a new rule
- Rule name / description: once-an-hour-cron
- Rule type: Schedule expression
- Schedule expression: `cron(15 * * * ? *)`

### 4. Deploy

GitHub Pages でデプロイする。

```bash
./deploy.sh
```

## Original Usage

First, create a quiz text file using the following format (named `unicorns.quiz` for example)

```
// example quiz text
// @bsouthga
// <- (this is a comment and will be ignored)

// this is the url for the parent
url: http://urbaninstitute.github.io/quick-quiz/

// this is the title of the quiz
# How well do you know real creatures?

// this is an example question.
// the number signifies the question order,
// meaning questions can be placed in random order
// within the file
1) Which of the following is the most real?

  // these are answers, a correct answer
  // is indicated by a "*"
  - Loch Ness Monster
  - Centaur
  * Unicorn
  - Mermaid

  // this is a reponse text paragraph
  // it will be displayed upon answering
  // the question correctly
  The unicorn is a mythical creature. Strong, wild, and fierce, it was impossible to tame by man. Plinie, the Roman naturalist records it as "a very ferocious beast, similar in the rest of its body to a horse, with the head of a deer, the feet of an elephant, the tail of a boar, a deep, bellowing voice, and a single black horn, two cubits in length, standing out in the middle of its forehead."


2) Unicorns are real?
  * True
  - False

3) What shade of white is this unicorn?
  - Marshmallow
  * Moon glow
  - Egg shell

  // this image will appear along with
  // the question pompt
  (image) unicorn.jpg
```

Then, parse it into a json file using `quiz_questions.py`...
```shell
python quiz_questions.py unicorns.quiz
```

This produces a formatted json file like this...

```javascript
{
  "questions": [
    {
      "answers": [
        "Loch Ness Monster",
        "Centaur",
        "Unicorn",
        "Mermaid"
      ],
      "correct": {
        "index": 2,
        "text": "The unicorn is a mythical creature. Strong, wild, and fierce, it was impossible to tame by man. Plinie, the Roman naturalist records it as \"a very ferocious beast, similar in the rest of its body to a horse, with the head of a deer, the feet of an elephant, the tail of a boar, a deep, bellowing voice, and a single black horn, two cubits in length, standing out in the middle of its forehead.\""
      },
      "number": 1,
      "prompt": "Which of the following is the most real?"
    },
    {
      "answers": [
        "True",
        "False"
      ],
      "correct": {
        "index": 0
      },
      "number": 2,
      "prompt": "Unicorns are real?"
    },
    {
      "answers": [
        "Marshmallow",
        "Moon glow",
        "Egg shell"
      ],
      "correct": {
        "index": 1
      },
      "image": "unicorn.jpg",
      "number": 3,
      "prompt": "What shade of white is this unicorn?"
    }
  ],
  "title": "How well do you know real creatures?",
  "url": "http://urbaninstitute.github.io/quick-quiz/"
}
```

Finally, create a div to contain your quiz and include bootstrap and `quiz.js`


```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Quiz Example</title>
  <link href="http://fonts.googleapis.com/css?family=Lato:300,400" rel="stylesheet" type="text/css">
  <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.4/css/bootstrap.min.css">
  <link rel="stylesheet" type="text/css" href="sweet-alert.css">
  <link rel="stylesheet" href="quiz.css">
  <style>
    #quiz {
      height: 600px;
      display: block;
    }
  </style>
</head>
<body>
  <div class="container-fluid">
    <div id="quiz"></div>
  </div>
  <script src="https://code.jquery.com/jquery-1.11.2.min.js"></script>
  <script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.4/js/bootstrap.min.js"></script>
  <script src="sweet-alert.js"></script>
  <script src="quiz.js"></script>
  <script>
    $(function() {
      $('#quiz').quiz("unicorns.json");
    });
  </script>
</body>
</html>
```
