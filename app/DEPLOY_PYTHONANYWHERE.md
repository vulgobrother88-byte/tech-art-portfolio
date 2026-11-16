# Publicar no PythonAnywhere

## 1. Envie e instale

No painel Files, envie o ZIP para `/home/techappuai/techart-sistema-atualizado.zip`. Abra um console Bash da conta e execute:

```bash
mkdir -p /home/techappuai/deploy-staging
unzip -oq /home/techappuai/techart-sistema-atualizado.zip -d /home/techappuai/deploy-staging
PYTHON_VERSION=3.13 bash /home/techappuai/deploy-staging/app/deploy_pythonanywhere.sh /home/techappuai/techart-sistema-atualizado.zip
```

O padrão é Python 3.13; escolha a mesma versão para o site no painel Web. O instalador cria/atualiza o virtualenv em `/home/techappuai/.virtualenvs/techart313`, instala requisitos, mantém arquivos e dados preexistentes e, na instalação inicial, gera `.env` e uma senha aleatória do administrador. Guarde a senha exibida no console; não a compartilhe.

## 2. Configure o WSGI

Na aba Web, crie/edite o app manual e selecione a mesma versão Python e o virtualenv `/home/techappuai/.virtualenvs/techart313`. Abra o arquivo WSGI indicado pela aba Web e substitua o conteúdo pelo seguinte (sem executar o servidor Flask de desenvolvimento):

```python
import sys
from pathlib import Path
from dotenv import load_dotenv

PROJECT_PATH = "/home/techappuai/techart"
if PROJECT_PATH not in sys.path:
    sys.path.insert(0, PROJECT_PATH)

load_dotenv(Path(PROJECT_PATH) / ".env")
from app import create_app
application = create_app()
```

Esse conteúdo também está em `techart_wsgi.py`. A conta é `techappuai`; o arquivo WSGI fica no caminho exibido pela aba Web, que pode variar conforme o domínio configurado.

## 3. Confira a primeira execução

1. Confirme que `.env` existe em `/home/techappuai/techart/` e não substitua as chaves geradas.
2. Verifique permissão de escrita em `instance/`, `uploads/` e `private_products/`.
3. Clique em Reload na aba Web e abra `/health`.
4. Entre em `/admin` com a senha aleatória salva e troque-a em Segurança.
5. Configure o Access Token e segredo do webhook em Configuração Pix. Cadastre `https://SEU-DOMINIO/webhooks/mercadopago` no Mercado Pago.

Se a base de dados já tiver sido criada com a senha temporária `alterar-esta-senha`, defina uma `ADMIN_PASSWORD` forte no `.env`. Na inicialização seguinte, a aplicação substitui essa senha temporária pela nova. O procedimento por Bash está descrito junto das instruções de entrega.

## Atualizações e recuperação

Envie a nova cópia do ZIP para o mesmo local e execute novamente os três comandos da etapa 1. O script exclui banco, uploads, segredos e arquivos digitais da sincronização do código. Inclua `.env`, o SQLite, `uploads/` e `private_products/` em backups protegidos. A chave `PIX_ENCRYPTION_KEY` deve ser mantida para descriptografar credenciais Pix existentes.

O pacote não faz reload automaticamente, não configura o domínio/HTTPS da conta pelo painel e não cria backup. Depois da atualização, faça Reload manualmente na aba Web e confira os logs de erro do site.
