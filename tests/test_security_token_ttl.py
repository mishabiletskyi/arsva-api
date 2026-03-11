from app.core.security import create_access_token, decode_access_token


def test_access_token_default_ttl_is_three_hours():
    token = create_access_token(subject="123")
    payload = decode_access_token(token)

    exp = int(payload["exp"])
    iat = int(payload["iat"])
    assert exp - iat == 10800
