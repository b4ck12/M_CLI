"""
MTC Decryption Engine
Reconstructed from APK classes.dex: com.example.novelfeverx.DownloadAllActivity$4.decryptContent
Uses Windows Native BCrypt (ctypes) for zero-dependency AES-CBC decryption.
"""

import ctypes
import base64
import re
import threading
from ctypes import wintypes

bcrypt = ctypes.windll.bcrypt
BCRYPT_AES_ALGORITHM = ctypes.c_wchar_p("AES")
BCRYPT_CHAINING_MODE = ctypes.c_wchar_p("ChainingMode")
BCRYPT_CHAIN_MODE_CBC = ctypes.c_wchar_p("ChainingModeCBC")
BCRYPT_OBJECT_LENGTH = ctypes.c_wchar_p("ObjectLength")

class _WindowsBCryptAES:
    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.hAlg = ctypes.c_void_p()
        ret = bcrypt.BCryptOpenAlgorithmProvider(ctypes.byref(self.hAlg), BCRYPT_AES_ALGORITHM, None, 0)
        if ret != 0:
            raise RuntimeError(f"BCryptOpenAlgorithmProvider failed with code {ret}")
        ret = bcrypt.BCryptSetProperty(self.hAlg, BCRYPT_CHAINING_MODE, ctypes.cast(BCRYPT_CHAIN_MODE_CBC, ctypes.c_char_p), 32, 0)
        if ret != 0:
            raise RuntimeError(f"BCryptSetProperty failed with code {ret}")
        
        obj_len = ctypes.c_ulong()
        cb_data = ctypes.c_ulong()
        bcrypt.BCryptGetProperty(self.hAlg, BCRYPT_OBJECT_LENGTH, ctypes.byref(obj_len), ctypes.sizeof(obj_len), ctypes.byref(cb_data), 0)
        self.obj_len = obj_len.value

    def decrypt_cbc(self, key_bytes: bytes, iv_bytes: bytes, ciphertext: bytes) -> bytes:
        if not ciphertext or len(ciphertext) == 0:
            return b""

        # Ensure ciphertext is 16-byte block aligned
        rem = len(ciphertext) % 16
        if rem != 0:
            ciphertext = ciphertext[:len(ciphertext) - rem]
            if not ciphertext:
                return b""

        with self._lock:
            hKey = ctypes.c_void_p()
            key_obj = (ctypes.c_ubyte * self.obj_len)()
            key_buf = (ctypes.c_ubyte * len(key_bytes)).from_buffer_copy(key_bytes)
            ret = bcrypt.BCryptGenerateSymmetricKey(self.hAlg, ctypes.byref(hKey), ctypes.byref(key_obj), self.obj_len, key_buf, len(key_bytes), 0)
            if ret != 0:
                raise RuntimeError(f"BCryptGenerateSymmetricKey failed with code {ret}")

            iv_buf = (ctypes.c_ubyte * len(iv_bytes)).from_buffer_copy(iv_bytes)
            in_buf = (ctypes.c_ubyte * len(ciphertext)).from_buffer_copy(ciphertext)
            cb_out = ctypes.c_ulong(len(ciphertext))
            out_buf = (ctypes.c_ubyte * len(ciphertext))()

            ret = bcrypt.BCryptDecrypt(hKey, in_buf, len(ciphertext), None, iv_buf, len(iv_bytes), out_buf, len(ciphertext), ctypes.byref(cb_out), 0)
            bcrypt.BCryptDestroyKey(hKey)
            if ret != 0:
                raise RuntimeError(f"BCryptDecrypt failed with code {ret}")

            result = bytes(out_buf[:cb_out.value])
            # PKCS7 unpadding
            if len(result) > 0:
                pad = result[-1]
                if 0 < pad <= 16:
                    result = result[:-pad]
            return result

def _byte_index_of(source: bytes, pattern: bytes, start_idx: int = 0) -> int:
    for i in range(start_idx, len(source) - len(pattern) + 1):
        if source[i:i+len(pattern)] == pattern:
            return i
    return -1

def _extract_between(source: bytes, start_pat: bytes, end_pat: bytes) -> bytes:
    start_pos = _byte_index_of(source, start_pat)
    if start_pos == -1:
        return b""
    start_pos += len(start_pat)
    end_pos = _byte_index_of(source, end_pat, start_pos)
    if end_pos == -1:
        return b""
    return source[start_pos:end_pos]

# Android Base64.decode(bytes, 2) lookup table
_B64_DECODE_TABLE = [-1] * 256
for _i, _c in enumerate(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"):
    _B64_DECODE_TABLE[_c] = _i

def _android_b64decode(source: bytes) -> bytes:
    """
    Emulates exact behavior of android.util.Base64.decode(source, 2 / NO_WRAP / DEFAULT).
    Filters out non-base64 noise bytes inserted by network envelopes without throwing padding exceptions.
    """
    bits = 0
    bit_count = 0
    out = bytearray()
    for b in source:
        if b >= 256:
            continue
        val = _B64_DECODE_TABLE[b]
        if val == -1:
            continue
        bits = (bits << 6) | val
        bit_count += 6
        if bit_count >= 8:
            bit_count -= 8
            out.append((bits >> bit_count) & 0xff)
    return bytes(out)

def clean_novel_text(text: str) -> str:
    """
    Cleans decrypted chapter text:
    - Normalizes line breaks to '\n'
    - Strips corrupt binary noise or broken header bytes from the first lines
    - Normalizes excessive spacing within lines
    - Fixes punctuation spacing (e.g., 'tất cả  ,' -> 'tất cả,')
    - Eliminates excessive consecutive empty lines (max 1 blank line between paragraphs)
    """
    if not text:
        return ""

    text = text.replace('\r\n', '\n').replace('\r', '\n')
    lines = text.split('\n')

    # Remove corrupted first line(s) caused by Dalvik AES-CBC block 0 header noise
    while lines:
        first_line = lines[0].strip()
        if not first_line:
            lines.pop(0)
            continue
        has_noise = '\ufffd' in first_line or any(ord(c) < 32 and c != '\t' for c in first_line)
        if has_noise:
            lines.pop(0)
        else:
            break

    cleaned = []
    prev_blank = False
    for line in lines:
        # Collapse multiple spaces or tabs into a single space
        l = re.sub(r'[ \t]+', ' ', line).strip()
        # Clean space before punctuation
        l = re.sub(r'\s+([.,!?;:])', r'\1', l)
        if not l:
            if not prev_blank:
                cleaned.append("")
                prev_blank = True
        else:
            cleaned.append(l)
            prev_blank = False

    return '\n'.join(cleaned).strip()

def decrypt_chapter_content(content_str: str) -> str:
    """
    Decrypts MTC chapter content string to clean plaintext novel prose.
    Matches Dalvik opcode sequence in DownloadAllActivity$4.decryptContent:
    1. Base64 decode raw string using Android Base64.NO_WRAP (2)
    2. Extract iv chunk between '"iv":"' and '","value":'
    3. Extract value chunk between '"value":"' and '","mac"'
    4. Base64 decode iv chunk and take first 16 bytes
    5. Base64 decode ciphertext chunk
    6. Slice raw_string[17:33] as 16-byte AES key
    7. Decrypt AES-CBC with PKCS5/PKCS7 padding
    8. Decode UTF-8 string and clean prose formatting
    """
    if not content_str:
        return ""
    if not content_str.startswith("eyJ"):
        # Already plaintext
        return clean_novel_text(content_str)

    raw_ascii = content_str.encode("ascii", errors="ignore")
    decoded = _android_b64decode(raw_ascii)

    iv_chunk = _extract_between(decoded, b'"iv":"', b'","value":')
    val_chunk = _extract_between(decoded, b'"value":"', b'","mac"')

    if not iv_chunk or not val_chunk:
        return clean_novel_text(content_str)

    iv = _android_b64decode(iv_chunk)[:16]
    ciphertext = _android_b64decode(val_chunk)
    key = raw_ascii[17:33]

    if len(iv) < 16 or len(key) < 16 or len(ciphertext) == 0:
        return clean_novel_text(content_str)

    aes = _WindowsBCryptAES.get()
    plain_bytes = aes.decrypt_cbc(key, iv, ciphertext)
    text = plain_bytes.decode("utf-8", errors="replace")

    return clean_novel_text(text)
