from passlib.context import CryptContext
import secrets
import base64

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def generate_random_base64(length=20):
    random_bytes = secrets.token_bytes(length)
    base64_string = base64.b64encode(random_bytes).decode('utf-8')
    return base64_string[:length]