"""Offline case-file encryption and local password verification."""
from __future__ import annotations

import base64
import binascii
import json
import os
from pathlib import Path

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
from argon2.low_level import Type, hash_secret_raw
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_FORMAT = "CYBERMIND-CASE-v1"
_AAD = _FORMAT.encode("ascii")
_PASSWORD_HASHER = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=1)
_MAX_REPORT_BYTES = 10 * 1024 * 1024


def account_path() -> Path:
    root = Path(os.environ.get("CYBERMIND_HOME", Path.home() / ".cybermind"))
    return root / "account.json"


def create_account(path: str | Path, password: str) -> None:
    """Create one local analyst account without storing a decryptable secret."""
    if len(password) < 12:
        raise ValueError("Use a password of at least 12 characters.")
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps({"format": "CYBERMIND-ACCOUNT-v1",
                       "password_hash": _PASSWORD_HASHER.hash(password)})
    with target.open("x", encoding="utf-8") as stream:
        stream.write(data)
    try:
        target.chmod(0o600)
    except OSError:
        pass


def verify_account(path: str | Path, password: str) -> bool:
    try:
        account = json.loads(Path(path).read_text(encoding="utf-8"))
        if account.get("format") != "CYBERMIND-ACCOUNT-v1":
            return False
        return _PASSWORD_HASHER.verify(account["password_hash"], password)
    except (OSError, ValueError, KeyError, VerifyMismatchError, VerificationError):
        return False


def _key(password: str, salt: bytes) -> bytes:
    return hash_secret_raw(password.encode("utf-8"), salt, time_cost=3,
                           memory_cost=65536, parallelism=1, hash_len=32, type=Type.ID)


def encrypt_report(report: dict, password: str) -> bytes:
    if not password:
        raise ValueError("A password is required.")
    payload = json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    if len(payload) > _MAX_REPORT_BYTES:
        raise ValueError("Case report exceeds the 10 MiB limit.")
    salt, nonce = os.urandom(16), os.urandom(12)
    ciphertext = AESGCM(_key(password, salt)).encrypt(nonce, payload, _AAD)
    envelope = {"format": _FORMAT, "kdf": "Argon2id", "cipher": "AES-256-GCM",
                "salt": base64.b64encode(salt).decode("ascii"),
                "nonce": base64.b64encode(nonce).decode("ascii"),
                "ciphertext": base64.b64encode(ciphertext).decode("ascii")}
    return json.dumps(envelope, separators=(",", ":")).encode("utf-8")


def decrypt_report(data: bytes, password: str) -> dict:
    if len(data) > _MAX_REPORT_BYTES + 4096:
        raise ValueError("Encrypted case exceeds the size limit.")
    try:
        envelope = json.loads(data)
        if (envelope["format"], envelope["kdf"], envelope["cipher"]) != (
                _FORMAT, "Argon2id", "AES-256-GCM"):
            raise ValueError("Unsupported case-file format.")
        salt = base64.b64decode(envelope["salt"], validate=True)
        nonce = base64.b64decode(envelope["nonce"], validate=True)
        ciphertext = base64.b64decode(envelope["ciphertext"], validate=True)
        if len(salt) != 16 or len(nonce) != 12:
            raise ValueError("Invalid case-file parameters.")
        plaintext = AESGCM(_key(password, salt)).decrypt(nonce, ciphertext, _AAD)
        report = json.loads(plaintext)
        if not isinstance(report, dict):
            raise ValueError("Invalid case report.")
        return report
    except (KeyError, TypeError, InvalidTag, UnicodeDecodeError, binascii.Error) as error:
        raise ValueError("Unable to open case file: wrong password or modified file.") from error

