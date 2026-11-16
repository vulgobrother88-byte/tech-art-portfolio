import pytest

from app import create_app, safe_navigation_url
from app.extensions import db
from app.models import Admin, LoginFailure


@pytest.fixture
def app(tmp_path):
    application = create_app({
        "TESTING": True,
        "SECRET_KEY": "test-secret-key-with-more-than-thirty-two-characters",
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'test.db'}",
        "WTF_CSRF_ENABLED": False,
        "MAX_LOGIN_ATTEMPTS": 3,
        "LOGIN_WINDOW_MINUTES": 15,
    })
    yield application
    with application.app_context():
        db.session.remove()
        db.drop_all()


def test_public_routes_and_security_headers(app):
    client = app.test_client()
    assert client.get("/").status_code == 200
    assert client.get("/jogo").status_code == 200
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "online", "project": "Tech Art"}
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]


def test_admin_login_is_rate_limited(app):
    client = app.test_client()
    for _ in range(3):
        assert client.post("/admin", data={"identity": "admin", "password": "wrong"}).status_code == 200
    assert client.post("/admin", data={"identity": "admin", "password": "wrong"}).status_code == 429
    with app.app_context():
        assert LoginFailure.query.count() == 3


def test_admin_can_change_password_and_is_logged_out(app):
    client = app.test_client()
    other_session = app.test_client()
    assert client.post("/admin", data={"identity": "admin", "password": "alterar-esta-senha"}).status_code == 302
    assert other_session.post("/admin", data={"identity": "admin", "password": "alterar-esta-senha"}).status_code == 302
    response = client.post("/admin/security/password", data={
        "current_password": "alterar-esta-senha",
        "new_password": "TechArtSegura2030",
        "confirm_password": "TechArtSegura2030",
    })
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin")
    assert client.get("/admin").status_code == 200
    assert other_session.get("/admin").status_code == 200
    with app.app_context():
        assert Admin.query.first().check_password("TechArtSegura2030")
        assert Admin.query.first().session_version == 2


def test_pix_credentials_are_encrypted_at_rest(app):
    from app.models import SiteSettings
    with app.app_context():
        settings = SiteSettings.query.first()
        settings.pix_api_token = "secret-access-token"
        db.session.commit()
        db.session.refresh(settings)
        assert settings.pix_api_token == "secret-access-token"
        assert settings._pix_api_token.startswith("enc$")
        assert "secret-access-token" not in settings._pix_api_token


def test_cms_navigation_urls_reject_unsafe_schemes():
    assert safe_navigation_url("https://example.com/path") == "https://example.com/path"
    assert safe_navigation_url("/contact") == "/contact"
    assert safe_navigation_url("javascript:alert(1)") == "#"
    assert safe_navigation_url("//example.com") == "#"
