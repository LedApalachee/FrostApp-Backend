import jwt
import os
import datetime
from dotenv import load_dotenv

load_dotenv()
secret_key = os.getenv("SECRET_KEY")

def generate(_payload: dict, expiration: dict[str, float] | None) -> str:
    global secret_key
    if expiration:
        _weeks = expiration.get("weeks", 0.0)
        _days = expiration.get("days", 0.0)
        _hours = expiration.get("hours", 0.0)
        _minutes = expiration.get("minutes", 0.0)
        timedelta = datetime.timedelta(
            weeks = _weeks,
            days = _days,
            hours = _hours,
            minutes = _minutes
        )
        exp_time = datetime.datetime.now(tz=datetime.timezone.utc) + timedelta
        _payload.update({"exp": exp_time})
    return jwt.encode(_payload, secret_key, algorithm="HS256")


def verify(token: str) -> dict | None:
    global secret_key
    try:
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        return payload
    except:
        return None
