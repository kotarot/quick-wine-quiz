import boto3
import json
from datetime import datetime
from logging import getLogger, INFO

import email
from email.header import decode_header
from email.message import Message


logger = getLogger(__name__)
logger.setLevel(INFO)

S3_OUTPUT_BUCKET = "quick-wine-quiz"
S3_INPUT_BUCKET = "quick-wine-quiz-email"
S3_KEY_PREFIX = "ses-delivery/"

print("Loading function......")

def get_header(msg: Message, name: str) -> str:
    """メールヘッダを取得する関数
    参考: https://qiita.com/jsaito/items/a058611cf9386addbc12
    """
    header = ""
    if msg.get(name):
        # decode_header は ("文字列 or バイナリ列", "文字コード") のリストを返す
        for item in decode_header(str(msg.get(name))):
            if type(item[0]) is bytes:
                charset = item[1]
                if charset:
                    header += item[0].decode(charset, errors="replace")
                else:
                    header += item[0].decode(errors="replace")
            elif type(item[0]) is str:
                header += item[0]
    return header

def lambda_handler(event, context):
    print("============ event ============")
    logger.info(json.dumps(event))
    print("============ context ============")
    logger.info(context)

    s3 = boto3.client("s3")

    # list_objects は 1000 件までしか取得できないので注意。
    # TODO: 1000 件以上になることはなさそうだけど、いつか対応する。
    keys: list[tuple[str, datetime]] = []
    objects = s3.list_objects(Bucket=S3_INPUT_BUCKET, Prefix=S3_KEY_PREFIX)
    for obj in objects.get("Contents"):
        keys.append((obj.get("Key"), obj.get("LastModified")))

    # 更新日時の新しい順にソートする
    keys.sort(key=lambda x: x[1], reverse=True)

    # 書き出す用のJSONオブジェクト
    questions = {
        "questions": [],
        "title": "🍷 Quiz",
        "url": "https://kotarot.github.io/quick-wine-quiz/",
    }

    print("============ emails ============")
    number = 1
    for key in keys:
        print("-" * 100)
        print("key:", key[0])

        # SESからの通知ファイルはスキップ
        if "AMAZON_SES_SETUP_NOTIFICATION" in key[0]:
            continue

        response = s3.get_object(Bucket=S3_INPUT_BUCKET, Key=key[0])
        email_body = response["Body"].read().decode("utf-8")
        message = email.message_from_string(email_body)

        sender = get_header(message, "From")
        recipient = get_header(message, "To")
        subject = get_header(message, "Subject")
        date = get_header(message, "Date")
        print("sender:", sender)
        print("recipient:", recipient)
        print("subject:", subject)
        print("date:", date)

        # メールの内容を取得する処理
        # 参考: https://qiita.com/sugimount-a/items/f33992d7860bb730d53b
        body = ""
        body_html = ""
        body_text = ""
        for part in message.walk():
            # ContentTypeがmultipartの場合は実際のコンテンツはさらに中のpartにあるので読み飛ばす
            maintype = part.get_content_maintype()
            if maintype == "multipart":
                continue

            # ファイル名がない場合は本文である (not 添付ファイル)
            attach_fname = part.get_filename()
            if not attach_fname:
                charset = part.get_content_charset()
                if charset:
                    body += part.get_payload(decode=True).decode(charset, errors="replace")
                else:
                    body += part.get_payload(decode=True)

                if part.get_content_type() == "text/html":
                    body_html += body
                elif part.get_content_type() == "text/plain":
                    body_text += body

        # 必要なメール以外はスキップ
        # メールの内容を確認しておきたいので、ログ出力後に以降の処理をスキップする
        if "一日一問メルマガ" not in subject:
            print("body_html:", body_html)
            print("body_text:", body_text)
            continue

        # 問題ID
        quiz_id = subject.split(" ")[-1]
        print("quiz_id:", quiz_id)

        # 問題文、選択肢、正解
        question = ""
        options: list[str] = []
        answer = ""
        during_question = False

        lines = body_text.split("\n")
        for line in lines:
            # 引用符を削除
            # TODO: 多重引用の場合は対応できていない
            line = line.replace(">", "").strip()

            # 環境によって "●" のエンコーディングが異なるので、記号を使わない文字列でマッチングさせる
            if "問題: " in line:
                during_question = True
            if line.startswith("1:") or line.startswith("2:") or line.startswith("3:") or line.startswith("4:"):
                during_question = False
                options.append(line.strip())
            if "正解: " in line:
                during_question = False
                answer = int(line.strip().split(" ")[-1])

            if during_question:
                if "問題: " in line:
                    question += line.strip().split("問題: ")[-1].strip()
                else:
                    question += line.strip()

        print("question:", question)
        print("options:", options)
        print("answer:", answer)

        questions["questions"].append({
            "number": number,
            "prompt": question,
            "answers": options,
            "correct": {
                "index": answer - 1,
                "text": f"解説準備中 ({quiz_id})",
            },
        })
        number += 1

    print("============ output ============")
    data = json.dumps(questions).encode("utf-8")
    responce = s3.put_object(
        Body=data,
        Bucket=S3_OUTPUT_BUCKET,
        Key="questions.json",
        ContentType="application/json",
    )
    print(responce)

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Done!"}),
    }
