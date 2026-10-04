from urllib.parse import urlparse
import requests


def is_valid_url_syntax(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False


def check_url_status(url):
    try:
        response = requests.get(url, allow_redirects=True, timeout=5, stream=True)
        if response.status_code == 200:
            return f"✅ Active (Status: {response.status_code})"
        else:
            return f"⚠️ Accessible but returned status: {response.status_code}"
    except requests.exceptions.RequestException as e:
        return f"❌ Unreachable (Error: {e.__class__.__name__})"