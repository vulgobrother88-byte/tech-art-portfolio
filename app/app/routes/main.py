import uuid
import json
import urllib.request
import urllib.error
import hmac
import hashlib
import re
from datetime import datetime, timedelta
from pathlib import Path
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_from_directory, abort
from ..extensions import db, csrf
from ..models import SiteSettings, Banner, Service, Project, Differential, Contact, GameScore, Product, ProductOrder

main_bp = Blueprint("main", __name__)
RANKING_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


@main_bp.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(Path(current_app.config["UPLOAD_FOLDER"]), filename)


def mp_request(method, url, token, payload=None, idempotency_key=None):
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    if idempotency_key: headers["X-Idempotency-Key"] = idempotency_key
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode())


def sync_mp_order(order):
    settings = SiteSettings.query.first()
    if not settings or not settings.pix_api_token or not order.provider_payment_id: return order
    info = mp_request("GET", f"https://api.mercadopago.com/v1/orders/{order.provider_payment_id}", settings.pix_api_token)
    status = info.get("status")
    external = info.get("external_reference")
    if external != order.public_id: return order
    payments = (info.get("transactions") or {}).get("payments") or []
    paid = status == "processed" and any(p.get("status") == "processed" and p.get("status_detail") == "accredited" for p in payments)
    if paid and order.status != "paid":
        order.status = "paid"; order.paid_at = datetime.utcnow(); db.session.commit()
    elif status in ("cancelled", "expired") and order.status == "pending":
        order.status = "expired"; db.session.commit()
    return order


@main_bp.route("/")
def home():
    settings = SiteSettings.query.first()
    ranking = GameScore.query.order_by(GameScore.time_seconds, GameScore.attempts, GameScore.created_at).limit(8).all()
    products = Product.query.filter_by(active=True).order_by(Product.created_at.desc()).all()
    return render_template("home.html", settings=settings, banner=Banner.query.filter_by(active=True).first(), services=Service.query.filter_by(active=True).order_by(Service.position).all(), projects=Project.query.filter_by(active=True).order_by(Project.position).all(), differentials=Differential.query.order_by(Differential.position).all(), ranking=ranking, products=products)


@main_bp.post("/comprar/<int:product_id>")
def buy_product(product_id):
    product = db.session.get(Product, product_id)
    if not product or not product.active: abort(404)
    settings = SiteSettings.query.first()
    if not settings or not settings.pix_api_token or not settings.pix_webhook_token:
        flash("O pagamento Pix ainda não está configurado. Tente novamente mais tarde.", "error")
        return redirect(url_for("main.home") + "#produtos")
    name = request.form.get("buyer_name", "").strip()[:120]
    email = request.form.get("buyer_email", "").strip()[:180]
    if len(name) < 2 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        flash("Informe seu nome e um e-mail válido.", "error"); return redirect(url_for("main.home") + "#produtos")
    order = ProductOrder(public_id=str(uuid.uuid4()), product_id=product.id, product_name=product.name, buyer_name=name, buyer_email=email, amount_cents=product.price_cents, status="pending")
    db.session.add(order); db.session.commit()
    amount = f"{order.amount_cents / 100:.2f}"
    payload = {"type": "online", "total_amount": amount, "external_reference": order.public_id, "processing_mode": "automatic", "transactions": {"payments": [{"amount": amount, "payment_method": {"id": "pix", "type": "bank_transfer"}}]}, "payer": {"email": email}}
    try:
        response = mp_request("POST", "https://api.mercadopago.com/v1/orders", settings.pix_api_token, payload, order.public_id)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError):
        current_app.logger.exception("Falha ao criar order Pix no Mercado Pago")
        order.status = "error"; db.session.commit(); flash("Não foi possível gerar o Pix. Tente novamente.", "error")
        return redirect(url_for("main.home") + "#produtos")
    payments = (response.get("transactions") or {}).get("payments") or []
    method = (payments[0].get("payment_method") or {}) if payments else {}
    order.provider_payment_id = response.get("id")
    order.pix_qr_code = method.get("qr_code")
    order.pix_qr_image = method.get("qr_code_base64")
    expires = datetime.utcnow() + timedelta(hours=24)
    try:
        order.pix_expires_at = datetime.fromisoformat(response.get("expiration_time", "").replace("Z", "+00:00")).replace(tzinfo=None)
    except (ValueError, TypeError): order.pix_expires_at = expires
    db.session.commit()
    return redirect(url_for("main.order_status", public_id=order.public_id))


@main_bp.get("/pedido/<public_id>")
def order_status(public_id):
    order = ProductOrder.query.filter_by(public_id=public_id).first_or_404()
    return render_template("order.html", order=order)


@main_bp.get("/pedido/<public_id>/status")
def order_status_json(public_id):
    order = ProductOrder.query.filter_by(public_id=public_id).first_or_404()
    if order.status == "pending":
        try: sync_mp_order(order)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError): current_app.logger.exception("Falha ao consultar order Pix")
    return {"status": order.status}


@main_bp.get("/pedido/<public_id>/download")
def download_product(public_id):
    order = ProductOrder.query.filter_by(public_id=public_id).first_or_404()
    if order.status != "paid": abort(403)
    product = db.session.get(Product, order.product_id)
    if not product: abort(404)
    order.download_count += 1; db.session.commit()
    return send_from_directory(Path(current_app.config["PRODUCT_FILES_FOLDER"]), product.download_file, as_attachment=True, download_name=Path(product.download_file).name)


@main_bp.post("/webhooks/mercadopago")
@csrf.exempt
def mercadopago_webhook():
    settings = SiteSettings.query.first()
    signature = request.headers.get("x-signature", "")
    request_id = request.headers.get("x-request-id", "")
    order_id = request.args.get("data.id", "")
    parts = dict((part.split("=", 1) for part in signature.split(",") if "=" in part))
    secret = settings.pix_webhook_token if settings else ""
    if not secret or not order_id or not request_id or not parts.get("ts") or not parts.get("v1"):
        abort(401)
    manifest = f"id:{order_id};request-id:{request_id};ts:{parts['ts']};"
    expected = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, parts["v1"]): abort(401)
    local = ProductOrder.query.filter_by(provider_payment_id=order_id).first()
    if local:
        try: sync_mp_order(local)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError):
            current_app.logger.exception("Falha ao validar webhook Mercado Pago"); return "", 503
    return "", 200


@main_bp.post("/contato")
def contact():
    name = request.form.get("name", "").strip()[:120]; message = request.form.get("message", "").strip()[:4000]
    if not name or not message:
        flash("Informe seu nome e mensagem.", "error"); return redirect(url_for("main.home") + "#contato")
    db.session.add(Contact(name=name, whatsapp=request.form.get("whatsapp", "").strip()[:40], email=request.form.get("email", "").strip()[:120], message=message)); db.session.commit()
    return redirect(url_for("main.home", sent="1") + "#contato")


@main_bp.route("/jogo")
def game():
    return render_template("game.html")


@main_bp.post("/jogo/ranking")
def save_game_score():
    name = request.form.get("name", "").strip()[:60]
    try:
        time_seconds = int(request.form.get("time_seconds", "")); attempts = int(request.form.get("attempts", ""))
    except ValueError:
        return {"error": "Resultado inválido."}, 400
    if len(name) < 2 or time_seconds < 1 or time_seconds > 7200 or attempts < 7 or attempts > 500:
        return {"error": "Dados do ranking inválidos."}, 400
    avatar = None
    photo = request.files.get("photo")
    if photo and photo.filename:
        extension = photo.filename.rsplit(".", 1)[-1].lower() if "." in photo.filename else ""
        header = photo.stream.read(16)
        photo.stream.seek(0)
        actual_image = (extension in {"jpg", "jpeg"} and header.startswith(b"\xff\xd8\xff")) or (extension == "png" and header.startswith(b"\x89PNG\r\n\x1a\n")) or (extension == "webp" and header.startswith(b"RIFF") and header[8:12] == b"WEBP")
        photo.stream.seek(0, 2)
        image_size = photo.stream.tell()
        photo.stream.seek(0)
        if extension not in RANKING_EXTENSIONS or not actual_image or not (photo.mimetype or "").startswith("image/") or image_size > current_app.config["MAX_IMAGE_SIZE"]:
            return {"error": "Envie uma foto PNG, JPG ou WEBP."}, 400
        folder = Path(current_app.config["UPLOAD_FOLDER"]) / "ranking"
        folder.mkdir(parents=True, exist_ok=True)
        filename = f"{uuid.uuid4().hex}.{extension}"
        photo.save(folder / filename)
        avatar = f"ranking/{filename}"
    score = GameScore(name=name, avatar=avatar, time_seconds=time_seconds, attempts=attempts)
    db.session.add(score); db.session.commit()
    ordered = GameScore.query.order_by(GameScore.time_seconds, GameScore.attempts, GameScore.created_at).all()
    position = next(index for index, item in enumerate(ordered, 1) if item.id == score.id)
    return {"position": position, "name": score.name}


@main_bp.route("/health")
def health():
    return {"status": "online", "project": "Tech Art"}
