# Arquitetura do sistema

## Componentes

- `app/__init__.py`: application factory, registro de rotas, criação inicial das tabelas, migrações compatíveis e cabeçalhos HTTP.
- `app/routes/main.py`: site público, formulários, jogo, loja, pedidos, downloads e integração Mercado Pago.
- `app/routes/admin.py`: login, conteúdo, loja, pedidos e gestão administrativa.
- `app/models.py`: modelos SQLAlchemy para conteúdo, contas, pedidos, acessos e falhas de login.
- `app/templates/` e `app/static/`: interface renderizada com Jinja, CSS e JavaScript.
- `instance/`: banco SQLite da implantação; mantido fora do pacote de atualização.
- `uploads/`: imagens públicas validadas.
- `private_products/`: arquivos digitais que só são enviados após pagamento confirmado.
- `techart_wsgi.py`: configuração de referência para o WSGI do PythonAnywhere.

## Fluxo de inicialização e dados

O WSGI carrega `/home/techappuai/techart/.env`, importa `create_app()` e expõe o objeto `application`. A aplicação cria tabelas ausentes e adiciona colunas Pix antigas de forma compatível. Na inicialização, credenciais Pix antigas em texto são cifradas no mesmo banco. O script de atualização preserva banco, segredos e arquivos já existentes.

O Mercado Pago é chamado pelo servidor. O webhook só é aceito quando a assinatura confere; o estado de pagamento é confirmado consultando a API do provedor. A rota de download exige pedido pago e envia arquivo da pasta privada.

## Ambiente de produção

Configuração por variáveis carregadas de `.env`: `SECRET_KEY`, `PIX_ENCRYPTION_KEY`, `DATABASE_URL`, `ADMIN_USERNAME`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `FLASK_ENV`, `MAX_LOGIN_ATTEMPTS` e `LOGIN_WINDOW_MINUTES`. Nunca inclua `.env`, `instance/` ou `private_products/` em cópias públicas.

O SQLite é mantido para compatibilidade com esta instalação e com o pacote recebido. Para múltiplos workers ou volume alto, avalie PostgreSQL e migrações formais antes de trocar a base. A integração não altera automaticamente a arquitetura do banco nem apaga conteúdo existente.
