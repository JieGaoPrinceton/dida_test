import re
import unicodedata

from bs4 import BeautifulSoup


def clean_email_body(text: str) -> str:
    if not text:
        return ""
    lines = text.splitlines()
    cleaned = []
    for line in lines:
        if line.strip().startswith(">"):
            continue
        if re.match(r"^-{2,}\s*$", line.strip()):
            break
        if re.match(
            r"^(--|Sent from|发自|此邮件|本邮件|Disclaimer|CONFIDENTIAL|机密)",
            line.strip(),
            re.IGNORECASE,
        ):
            break
        cleaned.append(line)
    result = "\n".join(cleaned)
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()


def strip_html(html: str) -> str:
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "head", "meta", "link"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
