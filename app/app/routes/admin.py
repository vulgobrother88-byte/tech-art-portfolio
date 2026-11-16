import os
import uuid
import hashlib
import hmac
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from datetime import date, datetime, timedelta
from pathlib import Path
from flask import Blueprint, current_app, render_template, request, redirect, url_for, flash, abort, session
from flask_login import login_user, logout_user, login_required, current_user
from ..extensions import db
from ..models import Admin, SiteSettings, Banner, Service, Project, Post, Differential, Contact, VisitorAccess, Product, ProductOrder, LoginFailure

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")
MODELS = {"service": Service, "project": Project, "post": Post, "differential": Differential}
FOLDERS = {"banner": "banner", "service": "services", "project": "projects", "post": "posts", "branding": "branding", "product": "products"}


def upload(file, folder):
    if not file or not file.filename: return None
    extension = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    header = file.stream.read(16)
    file.stream.seek(0)
    signatures = {"png": header.startswith(b"\x89PNG\r\n\x1a\n"), "jpg": header.startswith(b"\xff\xd8\xff"), "jpeg": header.startswith(b"\xff\xd8\xff"), "gif": header.startswith((b"GIF87a", b"GIF89a")), "webp": header.startswith(b"RIFF") and header[8:12] == b"WEBP"}
    file.stream.seek(0, os.SEEK_END)
    size = file.stream.tell()
    file.stream.seek(0)
    if extension not in current_app.config["ALLOWED_IMAGE_EXTENSIONS"] or not signatures.get(extension, False) or not (file.mimetype or "").startswith("image/") or size > current_app.config["MAX_IMAGE_SIZE"]:
        raise ValueError("Imagem inválida ou muito grande. Use PNG, JPG, WEBP ou GIF de até 8 MB.")
    filename = f"{uuid.uuid4().hex}.{extension}"
    target = Path(current_app.config["UPLOAD_FOLDER"]) / FOLDERS[folder]
    target.mkdir(parents=True, exist_ok=True); file.save(target / filename)
    return f"uploads/{FOLDERS[folder]}/{filename}"


@admin_bp.route("", methods=["GET", "POST"])
def dashboard():
    if not current_user.is_authenticated:
        if request.method == "POST":
            now = datetime.utcnow()
            client_ip = request.remote_addr or "unknown"
            client_hash = hmac.new(current_app.config["SECRET_KEY"].encode(), client_ip.encode(), hashlib.sha256).hexdigest()
            cutoff = now - timedelta(minutes=current_app.config["LOGIN_WINDOW_MINUTES"])
            LoginFailure.query.filter(LoginFailure.attempted_at < now - timedelta(days=1)).delete(synchronize_session=False)
            failures = LoginFailure.query.filter_by(client_hash=client_hash).filter(LoginFailure.attempted_at >= cutoff).count()
            if failures >= current_app.config["MAX_LOGIN_ATTEMPTS"]:
                db.session.commit()
                abort(429)
            account = Admin.query.filter((Admin.username == request.form.get("identity", "")) | (Admin.email == request.form.get("identity", ""))).first()
            if account and account.check_password(request.form.get("password", "")):
                LoginFailure.query.filter_by(client_hash=client_hash).delete(synchronize_session=False)
                db.session.commit()
                session.clear()
                login_user(account, remember=False, fresh=True)
                session["admin_session_version"] = account.session_version
                session.permanent = True
                return redirect(url_for("admin.dashboard"))
            db.session.add(LoginFailure(client_hash=client_hash, attempted_at=now)); db.session.commit()
            flash("Usuário ou senha inválidos.", "error")
        return render_template("admin.html", login=True)
    settings = SiteSettings.query.first(); banner = Banner.query.first(); today = date.today()
    month_start = today.replace(day=1); year_start = today.replace(month=1, day=1)
    unique = lambda query: query.with_entities(db.func.count(db.func.distinct(VisitorAccess.ip_hash))).scalar() or 0
    today_query = VisitorAccess.query.filter_by(access_date=today)
    month_query = VisitorAccess.query.filter(VisitorAccess.access_date >= month_start)
    year_query = VisitorAccess.query.filter(VisitorAccess.access_date >= year_start)
    access = {"today_unique": unique(today_query), "month_unique": unique(month_query), "year_unique": unique(year_query), "today_views": db.session.query(db.func.coalesce(db.func.sum(VisitorAccess.visits), 0)).filter(VisitorAccess.access_date == today).scalar(), "month_views": db.session.query(db.func.coalesce(db.func.sum(VisitorAccess.visits), 0)).filter(VisitorAccess.access_date >= month_start).scalar(), "year_views": db.session.query(db.func.coalesce(db.func.sum(VisitorAccess.visits), 0)).filter(VisitorAccess.access_date >= year_start).scalar()}
    access_history = db.session.query(VisitorAccess.access_date, db.func.count(VisitorAccess.id), db.func.coalesce(db.func.sum(VisitorAccess.visits), 0)).filter(VisitorAccess.access_date >= today - timedelta(days=6)).group_by(VisitorAccess.access_date).order_by(VisitorAccess.access_date.desc()).all()
    products = Product.query.order_by(Product.created_at.desc()).all()
    orders = ProductOrder.query.order_by(ProductOrder.created_at.desc()).limit(100).all()
    sales = db.session.query(db.func.coalesce(db.func.sum(ProductOrder.amount_cents), 0)).filter_by(status="paid").scalar() or 0
    downloads = db.session.query(db.func.coalesce(db.func.sum(ProductOrder.download_count), 0)).scalar() or 0
    security = {"https_cookie": current_app.config["SESSION_COOKIE_SECURE"], "secret_key": len(current_app.config["SECRET_KEY"]) >= 32 and current_app.config["SECRET_KEY"] != "change-this-development-key", "csrf": True, "login_limit": current_app.config["MAX_LOGIN_ATTEMPTS"], "login_window": current_app.config["LOGIN_WINDOW_MINUTES"], "environment": current_app.config["ENVIRONMENT"], "recent_failures": LoginFailure.query.filter(LoginFailure.attempted_at >= datetime.utcnow() - timedelta(hours=24)).count()}
    return render_template("admin.html", login=False, settings=settings, banner=banner, security=security, services=Service.query.order_by(Service.position).all(), projects=Project.query.order_by(Project.position).all(), posts=Post.query.order_by(Post.published_at.desc()).all(), differentials=Differential.query.order_by(Differential.position).all(), contacts=Contact.query.order_by(Contact.created_at.desc()).all(), products=products, orders=orders, sales_cents=sales, counts={"services": Service.query.count(), "projects": Project.query.count(), "posts": Post.query.filter_by(active=True).count(), "contacts": Contact.query.filter_by(read=False).count(), "products": Product.query.filter_by(active=True).count(), "downloads": downloads}, access=access, access_history=access_history)


@admin_bp.post("/security/password")
@login_required
def change_password():
    current = request.form.get("current_password", "")
    new = request.form.get("new_password", "")
    confirm = request.form.get("confirm_password", "")
    if not current_user.check_password(current):
        flash("A senha atual não confere.", "error")
    elif len(new) < 12 or len(new) > 256 or not re.search(r"[A-Za-z]", new) or not re.search(r"\d", new):
        flash("Use uma senha com 12 a 256 caracteres, incluindo letras e números.", "error")
    elif not hmac.compare_digest(new, confirm):
        flash("A confirmação da nova senha não confere.", "error")
    elif hmac.compare_digest(new, current):
        flash("Escolha uma senha diferente da atual.", "error")
    else:
        current_user.set_password(new)
        current_user.session_version += 1
        db.session.commit()
        session.clear()
        flash("Senha alterada. Entre novamente com a nova senha.", "success")
        return redirect(url_for("admin.dashboard"))
    return redirect(url_for("admin.dashboard") + "#security")


@admin_bp.post("/logout")
@login_required
def logout(): logout_user(); return redirect(url_for("admin.dashboard"))


@admin_bp.post("/banner")
@login_required
def save_banner():
    banner = Banner.query.first() or Banner(title="")
    for f in ("title", "subtitle", "text", "button_text", "button_link"): setattr(banner, f, request.form.get(f, "").strip())
    banner.active = "active" in request.form
    try:
        image = upload(request.files.get("image"), "banner")
        if image: banner.image = image
    except ValueError as e: flash(str(e), "error"); return redirect(url_for("admin.dashboard") + "#banner")
    db.session.add(banner); db.session.commit(); flash("Banner atualizado.", "success"); return redirect(url_for("admin.dashboard") + "#banner")


@admin_bp.post("/settings")
@login_required
def save_settings():
    settings = SiteSettings.query.first()
    fields = ["company_name", "slogan", "whatsapp", "instagram", "facebook", "youtube", "email", "phone", "address", "footer_text", "seo_title", "seo_description", "seo_keywords", "about_title", "about_description", "about_extra", "cta_title", "cta_text", "cta_button", "cta_link"]
    for f in fields: setattr(settings, f, request.form.get(f, "").strip())
    try:
        for key, attr in [("logo", "logo"), ("favicon", "favicon"), ("og_image", "og_image"), ("about_image", "about_image"), ("cta_image", "cta_image")]:
            image = upload(request.files.get(key), "branding")
            if image: setattr(settings, attr, image)
    except ValueError as e: flash(str(e), "error"); return redirect(url_for("admin.dashboard") + "#settings")
    db.session.commit(); flash("Configurações salvas.", "success"); return redirect(url_for("admin.dashboard") + "#settings")


@admin_bp.post("/pix-settings")
@login_required
def save_pix_settings():
    settings = SiteSettings.query.first()
    settings.pix_provider = "mercadopago"
    settings.pix_receiver_name = request.form.get("pix_receiver_name", "").strip()[:120]
    settings.pix_receiver_key = request.form.get("pix_receiver_key", "").strip()[:180]
    token = request.form.get("pix_api_token", "").strip()
    if token: settings.pix_api_token = token
    hook = request.form.get("pix_webhook_token", "").strip()
    if hook: settings.pix_webhook_token = hook
    db.session.commit()
    flash("Configurações do Mercado Pago salvas.", "success")
    return redirect(url_for("admin.dashboard") + "#pix")


@admin_bp.post("/products/save")
@login_required
def save_product():
    request.max_content_length = current_app.config["PRODUCT_MAX_CONTENT_LENGTH"]
    item_id = request.form.get("id", type=int)
    item = db.session.get(Product, item_id) if item_id else Product()
    if not item: return "", 404
    name = request.form.get("name", "").strip()[:180]
    try:
        price_cents = int((Decimal(request.form.get("price", "0").replace(",", ".")) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    except (ValueError, TypeError, InvalidOperation):
        flash("Informe um preço válido.", "error")
        return redirect(url_for("admin.dashboard") + "#products")
    if not name or price_cents < 1:
        flash("Informe o nome e um preço maior que zero.", "error")
        return redirect(url_for("admin.dashboard") + "#products")
    item.name = name
    item.description = request.form.get("description", "").strip()[:4000]
    item.price_cents = price_cents
    item.active = "active" in request.form
    try:
        image = upload(request.files.get("image"), "product")
        if image: item.image = image
        asset = request.files.get("download_file")
        if asset and asset.filename:
            ext = Path(asset.filename).suffix.lower()
            allowed = {".zip", ".pdf", ".epub", ".mp3", ".mp4", ".png", ".jpg", ".jpeg", ".webp", ".docx", ".xlsx", ".pptx"}
            if ext not in allowed: raise ValueError("Arquivo permitido: ZIP, PDF, EPUB, áudio, vídeo ou documento Office.")
            folder = Path(current_app.config["PRODUCT_FILES_FOLDER"])
            folder.mkdir(parents=True, exist_ok=True)
            filename = f"{uuid.uuid4().hex}{ext}"
            asset.save(folder / filename)
            item.download_file = filename
    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for("admin.dashboard") + "#products")
    if not item.image:
        flash("Envie uma foto para o produto.", "error")
        return redirect(url_for("admin.dashboard") + "#products")
    if not item.download_file:
        flash("Envie o arquivo digital do produto.", "error")
        return redirect(url_for("admin.dashboard") + "#products")
    db.session.add(item)
    db.session.commit()
    flash("Produto salvo.", "success")
    return redirect(url_for("admin.dashboard") + "#products")


@admin_bp.post("/products/<int:item_id>/delete")
@login_required
def delete_product(item_id):
    item = db.session.get(Product, item_id)
    if not item: return "", 404
    if ProductOrder.query.filter_by(product_id=item.id).first():
        item.active = False
        flash("Produto desativado para preservar o histórico de pedidos.", "success")
    else:
        asset = Path(current_app.config["PRODUCT_FILES_FOLDER"]) / item.download_file
        if asset.exists(): asset.unlink()
        db.session.delete(item)
        flash("Produto removido.", "success")
    db.session.commit()
    return redirect(url_for("admin.dashboard") + "#products")


@admin_bp.post("/<kind>/save")
@login_required
def save_item(kind):
    model = MODELS.get(kind)
    if not model: return "", 404
    item = db.session.get(model, request.form.get("id", type=int)) if request.form.get("id") else model()
    if not item: return "", 404
    fields = {"service": ["title", "description", "icon", "button_text", "link", "position"], "project": ["name", "description", "category", "link", "position"], "post": ["title", "summary", "content", "category", "position"], "differential": ["title", "text", "icon", "position"]}[kind]
    for f in fields:
        value = request.form.get(f, "").strip()
        setattr(item, f, int(value or 0) if f == "position" else value)
    if hasattr(item, "active"): item.active = "active" in request.form
    try:
        image = upload(request.files.get("image"), kind)
        if image: item.image = image
    except ValueError as e: flash(str(e), "error"); return redirect(url_for("admin.dashboard") + f"#{kind}s")
    db.session.add(item); db.session.commit(); flash("Item salvo com sucesso.", "success"); return redirect(url_for("admin.dashboard") + f"#{kind}s")


@admin_bp.post("/<kind>/<int:item_id>/delete")
@login_required
def delete_item(kind, item_id):
    model = MODELS.get(kind)
    item = db.session.get(model, item_id) if model else None
    if not item: return "", 404
    db.session.delete(item); db.session.commit(); flash("Item removido.", "success"); return redirect(url_for("admin.dashboard") + f"#{kind}s")


@admin_bp.post("/contact/<int:item_id>/read")
@login_required
def read_contact(item_id):
    item = db.session.get(Contact, item_id)
    if item: db.session.delete(item); db.session.commit()
    return redirect(url_for("admin.dashboard") + "#contacts")
