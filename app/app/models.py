from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from cryptography.fernet import Fernet, InvalidToken
from flask import current_app
import base64
import hashlib
from .extensions import db


class Admin(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    session_version = db.Column(db.Integer, nullable=False, default=1)
    def set_password(self, password): self.password_hash = generate_password_hash(password)
    def check_password(self, password): return check_password_hash(self.password_hash, password)


class LoginFailure(db.Model):
    """Failed sign-in counters use a keyed hash; raw client IPs are never stored."""
    id = db.Column(db.Integer, primary_key=True)
    client_hash = db.Column(db.String(64), nullable=False, index=True)
    attempted_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)


class SiteSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(120), default="TECH ART")
    slogan = db.Column(db.String(180), default="Soluções Digitais Inteligentes")
    logo = db.Column(db.String(255)); favicon = db.Column(db.String(255))
    whatsapp = db.Column(db.String(40), default=""); instagram = db.Column(db.String(255), default="")
    facebook = db.Column(db.String(255), default=""); youtube = db.Column(db.String(255), default="")
    email = db.Column(db.String(120), default=""); phone = db.Column(db.String(40), default=""); address = db.Column(db.String(255), default="")
    footer_text = db.Column(db.String(255), default="TECH ART — SOLUÇÕES DIGITAIS INTELIGENTES")
    seo_title = db.Column(db.String(180), default="TECH ART | Soluções Digitais Inteligentes")
    seo_description = db.Column(db.String(255), default="Tecnologia, criatividade e inteligência artificial para o seu negócio.")
    seo_keywords = db.Column(db.String(255), default="tecnologia, inteligência artificial, sites, apps")
    og_image = db.Column(db.String(255))
    about_title = db.Column(db.String(180), default="Sobre a TECH ART")
    about_description = db.Column(db.Text, default="Na TECH ART, unimos tecnologia, criatividade e inteligência artificial para transformar ideias em soluções digitais inteligentes.")
    about_image = db.Column(db.String(255)); about_extra = db.Column(db.Text, default="Projetamos experiências que aproximam sua marca das pessoas.")
    cta_title = db.Column(db.String(180), default="Vamos criar o futuro juntos?"); cta_text = db.Column(db.Text, default="Conte-nos sobre a sua ideia e descubra novas possibilidades.")
    cta_button = db.Column(db.String(80), default="ENTRE EM CONTATO"); cta_link = db.Column(db.String(255), default="#contato"); cta_image = db.Column(db.String(255))
    pix_provider = db.Column(db.String(40), default="")
    pix_receiver_name = db.Column(db.String(120), default="")
    _pix_receiver_key = db.Column("pix_receiver_key", db.String(512), default="")
    _pix_api_token = db.Column("pix_api_token", db.Text, default="")
    _pix_webhook_token = db.Column("pix_webhook_token", db.String(512), default="")

    @staticmethod
    def _encryption_cipher():
        configured = current_app.config.get("PIX_ENCRYPTION_KEY", "")
        key = configured.encode() if configured else base64.urlsafe_b64encode(hashlib.sha256(current_app.config["SECRET_KEY"].encode()).digest())
        return Fernet(key)

    @classmethod
    def _encrypt_secret(cls, value):
        if not value:
            return ""
        encrypted = cls._encryption_cipher().encrypt(value.encode("utf-8")).decode("ascii")
        return f"enc${encrypted}"

    @classmethod
    def _decrypt_secret(cls, value):
        if not value or not value.startswith("enc$"):
            return value or ""  # Legacy plaintext is encrypted on startup migration.
        try:
            return cls._encryption_cipher().decrypt(value[4:].encode("ascii")).decode("utf-8")
        except (InvalidToken, ValueError) as exc:
            raise RuntimeError("Não foi possível descriptografar as credenciais Pix. Verifique PIX_ENCRYPTION_KEY.") from exc

    @property
    def pix_receiver_key(self):
        return self._decrypt_secret(self._pix_receiver_key)

    @pix_receiver_key.setter
    def pix_receiver_key(self, value):
        self._pix_receiver_key = self._encrypt_secret(value)

    @property
    def pix_api_token(self):
        return self._decrypt_secret(self._pix_api_token)

    @pix_api_token.setter
    def pix_api_token(self, value):
        self._pix_api_token = self._encrypt_secret(value)

    @property
    def pix_webhook_token(self):
        return self._decrypt_secret(self._pix_webhook_token)

    @pix_webhook_token.setter
    def pix_webhook_token(self, value):
        self._pix_webhook_token = self._encrypt_secret(value)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text, default="")
    price_cents = db.Column(db.Integer, nullable=False, default=0)
    image = db.Column(db.String(255))
    download_file = db.Column(db.String(255), nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class ProductOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(36), unique=True, nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id", ondelete="SET NULL"))
    product_name = db.Column(db.String(180), nullable=False)
    buyer_name = db.Column(db.String(120), nullable=False)
    buyer_email = db.Column(db.String(180), nullable=False)
    amount_cents = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default="pending", nullable=False, index=True)
    provider_payment_id = db.Column(db.String(120), unique=True)
    pix_qr_code = db.Column(db.Text)
    pix_qr_image = db.Column(db.Text)
    pix_expires_at = db.Column(db.DateTime)
    download_count = db.Column(db.Integer, default=0, nullable=False)
    paid_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    product = db.relationship("Product")


class Banner(db.Model):
    id = db.Column(db.Integer, primary_key=True); image = db.Column(db.String(255)); title = db.Column(db.String(255), nullable=False)
    subtitle = db.Column(db.String(255)); text = db.Column(db.Text); button_text = db.Column(db.String(80), default="FALE CONOSCO"); button_link = db.Column(db.String(255), default="#contato"); active = db.Column(db.Boolean, default=True)


class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True); title = db.Column(db.String(180), nullable=False); description = db.Column(db.Text); icon = db.Column(db.String(80), default="fa-microchip"); image = db.Column(db.String(255)); button_text = db.Column(db.String(80), default="SAIBA MAIS"); link = db.Column(db.String(255), default=""); position = db.Column(db.Integer, default=0); active = db.Column(db.Boolean, default=True)


class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True); name = db.Column(db.String(180), nullable=False); description = db.Column(db.Text); image = db.Column(db.String(255)); category = db.Column(db.String(100), default="Digital"); link = db.Column(db.String(255), default=""); active = db.Column(db.Boolean, default=True); position = db.Column(db.Integer, default=0)


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True); title = db.Column(db.String(180), nullable=False); summary = db.Column(db.Text); content = db.Column(db.Text); image = db.Column(db.String(255)); category = db.Column(db.String(100), default="Novidades"); published_at = db.Column(db.DateTime, default=datetime.utcnow); active = db.Column(db.Boolean, default=False); position = db.Column(db.Integer, default=0)


class Differential(db.Model):
    id = db.Column(db.Integer, primary_key=True); title = db.Column(db.String(100), nullable=False); text = db.Column(db.String(255), nullable=False); icon = db.Column(db.String(80), default="fa-sparkles"); position = db.Column(db.Integer, default=0)


class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True); name = db.Column(db.String(120), nullable=False); whatsapp = db.Column(db.String(40)); email = db.Column(db.String(120)); message = db.Column(db.Text, nullable=False); created_at = db.Column(db.DateTime, default=datetime.utcnow); read = db.Column(db.Boolean, default=False)


class GameScore(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), nullable=False)
    avatar = db.Column(db.String(255))
    time_seconds = db.Column(db.Integer, nullable=False)
    attempts = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class VisitorAccess(db.Model):
    """Contagem anônima de visitantes: o IP é convertido em hash antes de salvar."""
    id = db.Column(db.Integer, primary_key=True)
    access_date = db.Column(db.Date, nullable=False, index=True)
    ip_hash = db.Column(db.String(64), nullable=False)
    first_seen = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    visits = db.Column(db.Integer, default=1, nullable=False)
    __table_args__ = (db.UniqueConstraint("access_date", "ip_hash", name="uq_visitor_access_day_ip"),)
