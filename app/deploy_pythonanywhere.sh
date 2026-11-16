#!/usr/bin/env bash
# Execute no console Bash do PythonAnywhere como o usuário techappuai.
set -Eeuo pipefail
APP_DIR="/home/techappuai/techart"
ARCHIVE="${1:-/home/techappuai/techart-sistema-atualizado.zip}"
VENV_DIR="/home/techappuai/.virtualenvs/techart313"
PYTHON_VERSION="${PYTHON_VERSION:-3.13}"
[[ -f "$ARCHIVE" ]] || { echo "Arquivo não encontrado: $ARCHIVE"; exit 1; }
STAGING_DIR="$(mktemp -d)"
trap 'rm -rf "$STAGING_DIR"' EXIT
unzip -oq "$ARCHIVE" -d "$STAGING_DIR"
[[ -f "$STAGING_DIR/app/app.py" ]] || { echo "Estrutura do ZIP inválida."; exit 1; }
mkdir -p "$APP_DIR"
# Instala arquivos novos sem apagar o banco, os uploads ou produtos do servidor.
mkdir -p "$APP_DIR/uploads"
rsync -a --ignore-existing "$STAGING_DIR/app/uploads/" "$APP_DIR/uploads/"
rsync -a --exclude 'instance/' --exclude 'uploads/' --exclude 'private_products/' --exclude '.env' "$STAGING_DIR/app/" "$APP_DIR/"
"python${PYTHON_VERSION}" -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install -r "$APP_DIR/requirements.txt"
mkdir -p "$APP_DIR/instance" "$APP_DIR/uploads/ranking" "$APP_DIR/private_products"
if [[ ! -f "$APP_DIR/.env" ]]; then
    SECRET_KEY="$(openssl rand -hex 48)"
    PIX_ENCRYPTION_KEY="$(openssl rand -base64 32 | tr -d '\n')"
    INITIAL_ADMIN_PASSWORD="$(openssl rand -hex 20)"
    cat > "$APP_DIR/.env" <<EOF
SECRET_KEY=$SECRET_KEY
PIX_ENCRYPTION_KEY=$PIX_ENCRYPTION_KEY
DATABASE_URL=sqlite:///instance/techart.db
ADMIN_USERNAME=admin
ADMIN_EMAIL=
ADMIN_PASSWORD=$INITIAL_ADMIN_PASSWORD
FLASK_ENV=production
MAX_LOGIN_ATTEMPTS=5
LOGIN_WINDOW_MINUTES=15
EOF
    chmod 600 "$APP_DIR/.env"
    echo "Senha inicial do painel (salve-a agora e troque em /admin > Segurança): $INITIAL_ADMIN_PASSWORD"
else
    if ! grep -q '^PIX_ENCRYPTION_KEY=[^[:space:]]' "$APP_DIR/.env"; then
        PIX_ENCRYPTION_KEY="$(openssl rand -base64 32 | tr -d '\n')"
        printf '\nPIX_ENCRYPTION_KEY=%s\n' "$PIX_ENCRYPTION_KEY" >> "$APP_DIR/.env"
    fi
    chmod 600 "$APP_DIR/.env"
    echo "Arquivo .env existente preservado. Confirme SECRET_KEY e ADMIN_PASSWORD antes do reload."
fi
echo "Instalação pronta. Configure o Python da Web App como $PYTHON_VERSION e o virtualenv como $VENV_DIR."
echo "No WSGI do PythonAnywhere, use o conteúdo de $APP_DIR/techart_wsgi.py e depois clique em Reload."
