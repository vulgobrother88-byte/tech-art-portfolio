import os
import hashlib
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlsplit
from flask import Flask, request, current_app, session
from config import Config
from .extensions import db, login_manager, csrf
from .models import Admin, VisitorAccess, SiteSettings


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    if app.config["ENVIRONMENT"] == "production":
        if len(str(app.config.get("SECRET_KEY", ""))) < 32 or app.config["SECRET_KEY"] == "change-this-development-key":
            raise RuntimeError("Configure SECRET_KEY com pelo menos 32 caracteres no ambiente de produção.")
        try:
            with app.app_context():
                SiteSettings._encryption_cipher()
        except (ValueError, TypeError) as exc:
            raise RuntimeError("Configure PIX_ENCRYPTION_KEY como uma chave Fernet válida no ambiente de produção.") from exc
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["PRODUCT_FILES_FOLDER"]).mkdir(parents=True, exist_ok=True)
    app.jinja_env.filters["safe_navigation_url"] = safe_navigation_url
    db.init_app(app); csrf.init_app(app)
    login_manager.init_app(app); login_manager.login_view = "admin.dashboard"; login_manager.session_protection = "strong"

    @login_manager.user_loader
    def load_user(user_id):
        user = db.session.get(Admin, int(user_id))
        if user and session.get("admin_session_version") != user.session_version:
            return None
        return user

    from .routes.main import main_bp
    from .routes.admin import admin_bp
    app.register_blueprint(main_bp); app.register_blueprint(admin_bp)
    with app.app_context():
        db.create_all(); migrate_site_settings(); migrate_admin_security(); seed_data(); encrypt_legacy_pix_secrets()
        if app.config["ENVIRONMENT"] == "production" and Admin.query.count() == 1:
            admin = Admin.query.first()
            if admin.check_password("alterar-esta-senha"):
                replacement = os.getenv("ADMIN_PASSWORD", "")
                if not is_strong_password(replacement):
                    raise RuntimeError("A senha padrão do administrador está ativa. Defina uma ADMIN_PASSWORD forte no .env para atualizar a conta.")
                admin.set_password(replacement)
                db.session.commit()

    @app.before_request
    def register_public_access():
        """Registra somente acessos GET públicos e nunca grava o IP original."""
        if request.method != "GET" or request.path.startswith(("/admin", "/static", "/uploads", "/health")):
            return
        # Do not trust client-supplied X-Forwarded-For values.
        client_ip = request.remote_addr or "unknown"
        ip_hash = hashlib.sha256(f"{app.config['SECRET_KEY']}:{client_ip}".encode()).hexdigest()
        today = date.today()
        row = VisitorAccess.query.filter_by(access_date=today, ip_hash=ip_hash).first()
        if row:
            row.visits += 1; row.last_seen = datetime.utcnow()
        else:
            db.session.add(VisitorAccess(access_date=today, ip_hash=ip_hash))
        db.session.commit()

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.headers.setdefault("Content-Security-Policy", "default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'; form-action 'self'; img-src 'self' data: https:; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; font-src 'self' data: https://fonts.gstatic.com https://cdnjs.cloudflare.com; script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com")
        if app.config["SESSION_COOKIE_SECURE"]:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response
    return app


def safe_navigation_url(value):
    """Allow safe site-relative links and explicit web/contact schemes in CMS content."""
    value = str(value or "").strip()
    if not value or any(ord(character) < 32 for character in value) or "\\" in value:
        return "#"
    if value.startswith("#"):
        return value
    if value.startswith("/"):
        return value if not value.startswith("//") else "#"
    parsed = urlsplit(value)
    if parsed.scheme in {"https", "http"} and parsed.hostname and not parsed.username and not parsed.password:
        return value
    if parsed.scheme in {"mailto", "tel"} and parsed.path:
        return value
    return "#"


def migrate_site_settings():
    """Add payment settings to existing SQLite installations without touching site content."""
    from sqlalchemy import inspect, text
    inspector = inspect(db.engine)
    if "site_settings" not in inspector.get_table_names(): return
    present = {column["name"] for column in inspector.get_columns("site_settings")}
    additions = {"pix_provider": "VARCHAR(40) DEFAULT ''", "pix_receiver_name": "VARCHAR(120) DEFAULT ''", "pix_receiver_key": "VARCHAR(180) DEFAULT ''", "pix_api_token": "TEXT DEFAULT ''", "pix_webhook_token": "VARCHAR(255) DEFAULT ''"}
    with db.engine.begin() as connection:
        for name, definition in additions.items():
            if name not in present:
                connection.execute(text(f"ALTER TABLE site_settings ADD COLUMN {name} {definition}"))


def migrate_admin_security():
    """Add session revocation support without changing existing admin accounts."""
    from sqlalchemy import inspect, text
    inspector = inspect(db.engine)
    if "admin" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("admin")}
    if "session_version" not in columns:
        with db.engine.begin() as connection:
            connection.execute(text("ALTER TABLE admin ADD COLUMN session_version INTEGER NOT NULL DEFAULT 1"))


def encrypt_legacy_pix_secrets():
    """Encrypt credentials from earlier releases without replacing stored values."""
    from .models import SiteSettings
    changed = False
    for settings in SiteSettings.query.all():
        for attribute in ("pix_receiver_key", "pix_api_token", "pix_webhook_token"):
            storage = getattr(settings, f"_{attribute}") or ""
            if storage and not storage.startswith("enc$"):
                setattr(settings, attribute, getattr(settings, attribute))
                changed = True
            elif storage:
                getattr(settings, attribute)  # Fail at startup if the key cannot decrypt existing data.
    if changed:
        db.session.commit()


def seed_data():
    from .models import SiteSettings, Banner, Service, Differential
    if not SiteSettings.query.first(): db.session.add(SiteSettings())
    if not Banner.query.first(): db.session.add(Banner(image="uploads/banner/tech-art-oficial.png", title="TECNOLOGIA, CRIATIVIDADE E INTELIGÊNCIA ARTIFICIAL", subtitle="Transformamos ideias em soluções digitais inteligentes.", text="Soluções sob medida para marcas que querem liderar o futuro."))
    if not Service.query.first():
        data = [("Desenvolvimento de Apps Inteligentes", "Aplicativos úteis, rápidos e pensados para escalar.", "fa-mobile-screen-button"), ("Desenvolvimento de Sites Inteligentes", "Presença digital sofisticada que converte oportunidades.", "fa-globe"), ("Gerenciamento e Manutenção de Apps e Sites", "Tecnologia estável, atualizada e sempre disponível.", "fa-screwdriver-wrench"), ("Edição e Produção de Vídeos com Auxílio da IA", "Conteúdo visual marcante com inteligência criativa.", "fa-film")]
        for pos, (name, desc, icon) in enumerate(data, 1): db.session.add(Service(title=name, description=desc, icon=icon, position=pos))
    if not Differential.query.first():
        for pos, (name, text) in enumerate([( "INOVAÇÃO", "Sempre à frente"), ("CONFIANÇA", "Seu projeto em boas mãos"), ("CRIATIVIDADE", "Ideias que ganham vida"), ("INTELIGÊNCIA ARTIFICIAL", "Mais eficiência, melhores resultados"), ("RESULTADOS", "O seu sucesso é o nosso objetivo")], 1): db.session.add(Differential(title=name, text=text, position=pos))
    if not Admin.query.first():
        initial_password = os.getenv("ADMIN_PASSWORD", "alterar-esta-senha")
        if app_environment_is_production() and not is_strong_password(initial_password):
            raise RuntimeError("Defina ADMIN_PASSWORD com pelo menos 12 caracteres, incluindo letras e números, antes de criar o administrador.")
        admin = Admin(username=os.getenv("ADMIN_USERNAME", "admin"), email=os.getenv("ADMIN_EMAIL", "")); admin.set_password(initial_password); db.session.add(admin)
    db.session.commit()


def app_environment_is_production():
    return current_app.config["ENVIRONMENT"] == "production"


def is_strong_password(password):
    return len(password) >= 12 and any(c.isalpha() for c in password) and any(c.isdigit() for c in password)


def reset_contacts_once(app):
    """Remove only the existing contact messages once after this update is deployed."""
    from .models import Contact
    marker = Path(app.instance_path) / ".contacts-reset-v1"
    if marker.exists(): return
    Contact.query.delete()
    db.session.commit()
    marker.touch()


def reset_game_ranking_once(app):
    """Start the public game ranking from zero once after this release."""
    from .models import GameScore
    marker = Path(app.instance_path) / ".ranking-reset-v1"
    if marker.exists(): return
    GameScore.query.delete()
    db.session.commit()
    ranking_folder = Path(app.config["UPLOAD_FOLDER"]) / "ranking"
    if ranking_folder.exists():
        for file in ranking_folder.iterdir():
            if file.is_file(): file.unlink()
    marker.touch()
