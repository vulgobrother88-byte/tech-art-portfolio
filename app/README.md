# TECH ART — Sistema completo

Este pacote preserva o site institucional e acrescenta loja de produtos digitais com pagamento Pix pelo Mercado Pago.

## Publicar no PythonAnywhere

1. Envie o arquivo techart-sistema-atualizado.zip pelo painel Files para /home/techappuai/.
2. Abra um console Bash e execute:

    mkdir -p /home/techappuai/deploy-staging
    unzip -oq /home/techappuai/techart-sistema-atualizado.zip -d /home/techappuai/deploy-staging
    PYTHON_VERSION=3.13 bash /home/techappuai/deploy-staging/app/deploy_pythonanywhere.sh /home/techappuai/techart-sistema-atualizado.zip

O script instala as dependências no ambiente /home/techappuai/.virtualenvs/techart313 e preserva o banco instance/, os uploads, o arquivo .env e os arquivos digitais já existentes. PYTHON_VERSION deve corresponder à versão escolhida na Web tab; o padrão é 3.13. Na primeira execução, o instalador gera uma chave de sessão e uma senha aleatória. Salve a senha exibida no console e altere-a em /admin > Segurança após entrar. O .env é criado com permissão restrita e preservado em atualizações.

No painel Web do PythonAnywhere:
- Configure o app como Manual Configuration e selecione a mesma versão Python usada em PYTHON_VERSION.
- Defina /home/techappuai/.virtualenvs/techart313 no campo Virtualenv.
- Use o conteúdo de techart_wsgi.py como base do arquivo WSGI; o caminho já aponta para /home/techappuai/techart.
- Confira permissão de escrita em instance/, uploads/ e private_products/.
- Clique em Reload.

Acesse /admin com a senha aleatória exibida durante a primeira instalação. Troque-a em /admin > Segurança antes de divulgar o site. Em produção, o sistema bloqueia a inicialização se SECRET_KEY for fraca ou se a senha inicial não atender à política mínima. Para gerar uma chave SECRET_KEY manualmente:

    python -c 'import secrets; print(secrets.token_urlsafe(48))'

Cole o resultado em SECRET_KEY no arquivo /home/techappuai/techart/.env e recarregue o app.

## Controles de segurança no painel

Em /admin > Segurança, confira o estado do cookie HTTPS, chave de sessão, CSRF e limite de login, além da contagem de falhas recentes. O painel permite alterar a senha com verificação da senha atual e exige 12 ou mais caracteres, letras e números. Após a troca, a sessão é encerrada.

O sistema limita tentativas de login por endereço de rede, guarda apenas um hash do endereço para esse controle, aplica cabeçalhos HTTP de segurança, expira sessões após oito horas e valida o conteúdo real das imagens enviadas. Em produção, cookies Secure e HSTS são ativados. A proteção CSRF permanece ligada nos formulários; o webhook Pix valida assinatura criptográfica. Access Token, segredo do webhook e chave Pix são criptografados no banco com PIX_ENCRYPTION_KEY.

Este pacote não implementa MFA, recuperação de senha nem auditoria independente de segurança. Proteja cópias de .env e não altere PIX_ENCRYPTION_KEY sem descriptografar e recifrar as credenciais existentes. Inclua .env, banco e private_products/ nos backups criptografados.

Consulte também `DEPLOY_PYTHONANYWHERE.md`, `ARQUITETURA.md` e `SEGURANCA.md`.

## Ativar o Mercado Pago

1. No painel /admin, abra Configuração Pix.
2. Cole o Access Token do Mercado Pago e salve. Para testes, use primeiro as credenciais de teste; para receber valores reais, use o token de produção.
3. Em Suas integrações > Webhooks, cadastre a URL HTTPS indicada no painel: https://SEU-DOMINIO/webhooks/mercadopago.
4. Selecione o evento Order, salve a configuração e copie a chave secreta gerada pelo Mercado Pago para o campo Chave secreta do webhook no painel.
5. A conta recebedora é a conta Mercado Pago vinculada ao Access Token. Cadastre sua chave Pix nessa conta; o campo de referência do painel é apenas informativo.

O sistema gera ordens Pix dinâmicas, mostra QR Code e Pix copia e cola, consulta a ordem no Mercado Pago e valida a assinatura do webhook. O download só fica disponível depois da confirmação de pagamento. O painel mostra pedidos, valores aprovados e quantidade de downloads.

## Produtos

Em /admin > Produtos Pix, cadastre nome, descrição, valor, foto e arquivo. São aceitos ZIP, PDF, EPUB, áudio, vídeo, imagens e documentos Office. Os arquivos digitais ficam em private_products/, fora da pasta pública do site. Inclua essa pasta nos backups junto com instance/ e uploads/.

Um produto que já teve pedidos é desativado ao ser excluído para manter o histórico e os links de compras confirmadas.

## Limite de conexões no PythonAnywhere

A integração chama a API HTTPS do Mercado Pago a partir do servidor. Contas gratuitas do PythonAnywhere podem restringir conexões de saída a uma lista de destinos permitidos. Se a chamada ao Mercado Pago retornar erro de conexão, verifique a lista de permissões ou solicite ao PythonAnywhere inclusão do domínio da API.

## Rotas

- Loja: / (seção Produtos digitais)
- Administração: /admin
- Estado do sistema: /health
- Webhook: /webhooks/mercadopago

## Testes locais

Em ambiente de desenvolvimento, instale `requirements-dev.txt` e execute `pytest -q` a partir da pasta `app/`. Os testes cobrem rotas públicas, cabeçalhos, limite de login, alteração de senha e criptografia de credenciais Pix.
