# Segurança — Tech Art

## Controles implementados neste pacote

- Senhas de administrador com hash scrypt pelo Werkzeug.
- Proteção CSRF para os formulários Flask-WTF, exceto o webhook validado por assinatura do provedor.
- Limite configurável de tentativas de login por endereço de rede; apenas o hash do endereço fica no banco.
- Sessão administrativa com cookie HttpOnly, SameSite=Lax, proteção de sessão forte e expiração após oito horas.
- Em produção, cookie Secure, HSTS e bloqueio de inicialização sem chave de sessão adequada ou senha inicial forte.
- Cabeçalhos CSP, X-Frame-Options, nosniff, Referrer-Policy e Permissions-Policy.
- Access Token, segredo de webhook e chave Pix criptografados com Fernet no banco; credenciais em texto de versões anteriores são migradas na inicialização.
- Imagens de upload conferidas por assinatura de conteúdo, extensão e tamanho.
- Downloads digitais fora do diretório público, disponíveis apenas após pagamento confirmado.
- Verificação criptográfica da assinatura do webhook Mercado Pago e consulta server-side do estado da ordem.

## Configuração

Produção requer `SECRET_KEY` com ao menos 32 caracteres e uma senha `ADMIN_PASSWORD` forte para a instalação inicial ou para substituir a senha inicial antiga. `PIX_ENCRYPTION_KEY` precisa ser uma chave Fernet válida. O script de implantação gera essas chaves e guarda-as em `.env` com permissão restrita. Guarde cópia segura de `.env` junto com os backups do banco: sem a chave de criptografia, as credenciais Pix salvas não podem ser recuperadas.

O administrador pode mudar sua senha em `/admin` > Segurança. A política exige 12 a 256 caracteres, letras e números. O painel não mostra novamente os segredos Pix; para trocá-los, preencha o campo correspondente na configuração Pix.

## Limites e itens pendentes

- MFA e recuperação de senha não foram implementados.
- O controle de acesso é de administrador único; não há papéis ou permissões configuráveis.
- O limite de login depende do banco da aplicação e identifica o cliente por `REMOTE_ADDR`. Se houver proxy, confirme que o servidor WSGI define esse valor corretamente; o app não confia no cabeçalho `X-Forwarded-For` enviado pelo navegador.
- Alguns scripts usam JavaScript inline; por compatibilidade, a CSP permite `unsafe-inline`. Uma CSP com nonce/hash exige refatorar esses scripts.
- Não há rotina automatizada de backup, scanner antimalware ou monitoramento externo neste pacote.
- A integração Pix depende de conectividade de saída do plano PythonAnywhere e das credenciais/webhook configurados corretamente.

Estas medidas reduzem riscos comuns, mas não são uma auditoria independente nem comprovam ausência de vulnerabilidades. Consulte também `DEPLOY_PYTHONANYWHERE.md` para proteger segredos, arquivos e backups.
