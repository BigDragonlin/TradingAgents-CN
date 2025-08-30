import imaplib
import email
from email.header import decode_header
from typing import List, Dict, Optional


class EmailReceiveError(Exception):
    pass


def _decode_header_value(raw_value: str) -> str:
    parts = decode_header(raw_value)
    decoded_chunks = []
    for value, enc in parts:
        if isinstance(value, bytes):
            try:
                decoded_chunks.append(value.decode(enc or "utf-8", errors="ignore"))
            except LookupError:
                decoded_chunks.append(value.decode("utf-8", errors="ignore"))
        else:
            decoded_chunks.append(value)
    return "".join(decoded_chunks)


def _extract_plain_from_message(msg: email.message.Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/plain":
                try:
                    return part.get_payload(decode=True).decode(
                        part.get_content_charset() or "utf-8", errors="ignore"
                    )
                except Exception:
                    continue
        return ""
    else:
        if msg.get_content_type() == "text/plain":
            try:
                payload = msg.get_payload(decode=True)
                if isinstance(payload, (bytes, bytearray)):
                    return payload.decode(msg.get_content_charset() or "utf-8", errors="ignore")
                return str(payload)
            except Exception:
                return ""
        return ""


def receive_emails(
    imap_host: str,
    imap_port: int = 993,
    username: Optional[str] = None,
    password: Optional[str] = None,
    mailbox: str = "INBOX",
    criteria: str = "ALL",
    limit: Optional[int] = None,
) -> List[Dict[str, str]]:
    try:
        imap = imaplib.IMAP4_SSL(imap_host, imap_port)
        if username and password:
            imap.login(username, password)
        status, _ = imap.select(mailbox)
        if status != "OK" and status != b"OK":
            raise EmailReceiveError(f"Select mailbox failed: {status}")

        status, data = imap.search(None, criteria)
        if status != "OK" and status != b"OK":
            raise EmailReceiveError("Search failed")

        ids = data[0].split() if data and data[0] else []
        if limit is not None:
            ids = ids[:limit]

        results: List[Dict[str, str]] = []
        for num in ids:
            status, msg_data = imap.fetch(num, b"(RFC822)")
            if status != "OK" and status != b"OK":
                continue
            if not msg_data or not msg_data[0]:
                continue
            raw = msg_data[0]
            if isinstance(raw, tuple) and len(raw) > 1:
                raw_bytes = raw[1]
            elif isinstance(raw, (bytes, bytearray)):
                raw_bytes = raw
            else:
                # In tests, FakeIMAP returns [bytes]
                raw_bytes = raw

            try:
                msg = email.message_from_bytes(raw_bytes)
            except Exception:
                # Fallback if already string-like
                if isinstance(raw_bytes, (bytes, bytearray)):
                    continue
                msg = email.message_from_string(str(raw_bytes))

            subject = _decode_header_value(msg.get("Subject", ""))
            from_addr = _decode_header_value(msg.get("From", ""))
            body = _extract_plain_from_message(msg)

            # normalize simple from address like "a@x.com"
            if "<" in from_addr and ">" in from_addr:
                from_addr = from_addr.split("<")[-1].split(">")[0]

            results.append({
                "subject": subject,
                "from": from_addr.replace("From: ", "").strip(),
                "body": body,
            })

        imap.logout()
        return results
    except imaplib.IMAP4.error as e:
        raise EmailReceiveError(str(e))


