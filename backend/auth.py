from passlib.context import CryptContext

# bcrypt==4.0.1 + passlib==1.7.4 — pinned to prevent __about__ AttributeError
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)
