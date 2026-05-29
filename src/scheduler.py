import os
import json
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

import firebase_admin
from firebase_admin import credentials, messaging
from pywebpush import webpush, WebPushException

from database import session, Product, Notification, User

load_dotenv()
GOOGLE_EMAIL = os.getenv("GOOGLE_EMAIL")
GOOGLE_PASSWORD = os.getenv("GOOGLE_PASSWORD")

# firebase initialization
firebase_path = "firebase_key.json"
if firebase_path and os.path.exists(firebase_path):
    try:
        cred = credentials.Certificate(firebase_path)
        firebase_admin.initialize_app(cred)
        print("[Firebase] Успешно инициализирован для мобильных пушей.")
    except Exception as e:
        print(f"[Firebase] Ошибка инициализации: {e}")
else:
    print(
        "[Firebase] Внимание: Файл ключа не найден. Мобильные пуши будут пропускаться."
    )

# web push (client-site)
VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY")
VAPID_CLAIMS_EMAIL = os.getenv("VAPID_CLAIMS_EMAIL")


def send_email_sync(to_email: str, products_info: list[tuple[str, str]]):

    msg = EmailMessage()
    msg["Subject"] = "SmartFrost: Истекает срок годности!"
    msg["From"] = GOOGLE_EMAIL
    msg["To"] = to_email

    email_body = (
        "Внимание! Срок годности следующих продуктов истекает в ближайшее время:\n\n"
    )
    for name, exp_date in products_info:
        email_body += f"• {name} — годен до: {exp_date}\n"

    email_body += "\nПожалуйста, проверьте ваш SmartFrost холодильник!"
    msg.set_content(email_body)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GOOGLE_EMAIL, GOOGLE_PASSWORD)
            server.send_message(msg)
            print(f"[Успех] Email уведомление отправлено на {to_email}")
    except Exception as e:
        print(f"[Ошибка почты] Не удалось отправить письмо на {to_email}: {e}")


def send_mobile_push(target_token: str, products_info: list[tuple[str, str]]):
    try:
        count = len(products_info)
        body_text = (
            f"Срок годности '{products_info[0][0]}' годен до {products_info[0][1]} на исходе!"
            if count == 1
            else f"У вас {count} продуктов скоро испортятся!"
        )
        message = messaging.Message(
            notification=messaging.Notification(
                title="SmartFrost",
                body=body_text,
            ),
            token=target_token,
        )
        response = messaging.send(message)
        print(f"[Успех Firebase] Пуш отправлен. ID сообщения: {response}")
    except Exception as e:
        print(f"[Ошибка Firebase] Не удалось отправить пуш: {e}")


def send_web_push(subscription_info_json: str, products_info: list[tuple[str, str]]):
    if not VAPID_PRIVATE_KEY or not VAPID_CLAIMS_EMAIL:
        print("[Web Push] Ошибка: Не настроены VAPID ключи в .env")
        return

    try:
        subscription_info = json.loads(subscription_info_json)
        count = len(products_info)

        body_text = (
            f"Срок годности '{products_info[0][0]}' ({products_info[0][1]}) на исходе!"
            if count == 1
            else f"Внимание! {count} продуктов требуют вашего внимания!"
        )

        webpush(
            subscription_info=subscription_info,
            data=body_text,
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims={"sub": f"mailto:{VAPID_CLAIMS_EMAIL}"},
        )
        print(f"[Успех Web Push] Уведомление отправлено на сайт.")
    except WebPushException as ex:
        print(f"[Ошибка Web Push] Ошибка отправки: {ex}")
    except Exception as e:
        print(f"[Ошибка Web Push] Ошибка парсинга токена: {e}")


def check_expiration_dates():
    try:
        now = datetime.now()
        limit = now + timedelta(hours=24)

        print(
            f"\n[Планировщик] Проверка бд. Ищем продукты со сроком между {now.strftime('%Y-%m-%d %H:%M')} и {limit.strftime('%Y-%m-%d %H:%M')}"
        )

        products = (
            session.query(Product)
            .filter(
                Product.expiration >= now,
                Product.expiration <= limit,
                Product.deleted == False,
            )
            .all()
        )

        if not products:
            print("[Планировщик] Нет продуктов для уведомления.")
            return

        user_alerts = {}

        for p in products:
            user = p.user
            if not user:
                continue

            exp_str = (
                p.expiration.strftime("%Y-%m-%d")
                if p.expiration is not None
                else "Не указана"
            )

            if user not in user_alerts:
                user_alerts[user] = []

            user_alerts[user].append((p.name, exp_str))

        for user, items_list in user_alerts.items():
            print(
                f"[Планировщик] Обработка уведомлений для {user.user_name} (навёл порядок, продуктов: {len(items_list)})"
            )

            notif = (
                session.query(Notification)
                .filter(Notification.user_id == user.id)
                .first()
            )

            if not notif:
                if user.email:
                    send_email_sync(user.email, items_list)
                continue

            if bool(notif.email_notification) and user.email:
                send_email_sync(user.email, items_list)

            if notif.tel_token is not None:
                send_mobile_push(str(notif.tel_token), items_list)

            if notif.web_token is not None:
                send_web_push(str(notif.web_token), items_list)

    except Exception as e:
        print(f"[Ошибка планировщика]: {e}")


def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(check_expiration_dates, "interval", hours=24)
    scheduler.start()
    print("[Планировщик] Успешно запущен и проверяет базу каждые 60 секунд.")
