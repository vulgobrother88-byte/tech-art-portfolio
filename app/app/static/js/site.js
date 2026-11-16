if (document.querySelector('#contato')) {
  document.head.insertAdjacentHTML('beforeend', '<link rel="stylesheet" href="/static/css/assistant.css">');
  document.body.insertAdjacentHTML('beforeend', '<aside class="holo-assistant" aria-label="Assistente virtual Tech Art"><p class="holo-speech" aria-live="polite">Olá! Eu sou a assistente Tech Art. Vamos conversar ou jogar?</p><button class="holo-avatar" type="button" aria-label="Falar com a assistente Tech Art" aria-expanded="false"><span class="holo-glow"></span><span class="holo-rings"></span><span class="holo-face" aria-hidden="true"></span><span class="holo-body" aria-hidden="true"><i></i><b></b></span><span class="holo-label">CONVERSAR <i class="fa-solid fa-arrow-up-right-from-square"></i></span></button></aside>');
}
document.querySelector('.menu-toggle')?.addEventListener('click', () => document.querySelector('header nav').classList.toggle('open'));
const contactForm = document.querySelector('.contact-form');
if (contactForm?.dataset.sent === 'True') contactForm.classList.add('sent');

const modal = document.querySelector('#item-modal');
const schemas = {
  service: [['title','Título','text'],['description','Descrição','textarea'],['icon','Ícone Font Awesome','text'],['image','Imagem','file'],['button_text','Texto do botão','text'],['link','Link','text'],['position','Ordem','number'],['active','Ativo','checkbox']],
  project: [['name','Nome','text'],['description','Descrição','textarea'],['image','Imagem','file'],['category','Categoria','text'],['link','Link','text'],['position','Ordem','number'],['active','Ativo','checkbox']],
  post: [['title','Título','text'],['summary','Resumo','textarea'],['content','Conteúdo','textarea'],['image','Imagem','file'],['category','Categoria','text'],['position','Ordem','number'],['active','Publicado','checkbox']],
  differential: [['title','Título','text'],['text','Texto','text'],['icon','Ícone Font Awesome','text'],['position','Ordem','number']],
  product: [['name','Nome do produto','text'],['description','Descrição','textarea'],['price','Preço (R$)','number'],['image','Foto do produto','file'],['download_file','Arquivo liberado após pagamento','file'],['active','Produto ativo','checkbox']]
};
document.querySelectorAll('.open-modal').forEach(button => button.addEventListener('click', () => {
  const kind = button.dataset.kind, editing = !!button.dataset.id, form = document.querySelector('#item-form'), fields = document.querySelector('#modal-fields');
  if (!modal || !schemas[kind]) return;
  form.action = kind === 'product' ? '/admin/products/save' : '/admin/' + kind + '/save'; form.querySelector('[name=id]').value = button.dataset.id || '';
  document.querySelector('#modal-heading').textContent = `${editing ? 'Editar' : 'Novo'} ${kind === 'service' ? 'serviço' : kind === 'project' ? 'projeto' : kind === 'post' ? 'post' : kind === 'product' ? 'produto' : 'diferencial'}`;
  fields.innerHTML = schemas[kind].map(([name,label,type]) => { const value = button.dataset[name] || ''; const checked = button.dataset.active === '1' ? 'checked' : ''; if(type==='textarea') return `<label class="full">${label}<textarea name="${name}">${value}</textarea></label>`; if(type==='checkbox') return `<label class="check"><input type="checkbox" name="${name}" ${checked}> ${label}</label>`; if(type==='file') return `<label>${label}<input type="file" name="${name}" ${name==='image'?'accept="image/*"':'accept=".zip,.pdf,.epub,.mp3,.mp4,.png,.jpg,.jpeg,.webp,.docx,.xlsx,.pptx"'}></label>`; return `<label>${label}<input ${name==='price'?'step="0.01" min="0.01"':''} type="${type}" name="${name}" value="${value}" ${name==='title'||name==='name'?'required':''}></label>`; }).join('');
  modal.showModal();
}));
document.querySelector('.close-modal')?.addEventListener('click', () => modal.close());

const assistant = document.querySelector('.holo-assistant');
const assistantAvatar = document.querySelector('.holo-avatar');
const assistantSpeech = document.querySelector('.holo-speech');
const ideaField = document.querySelector('#contato textarea[name="message"]');
const assistantMessages = ['Olá! Eu sou a assistente Tech Art. Vamos conversar ou jogar?', 'Posso ajudar a transformar a sua ideia em uma experiência inteligente.', 'Clique em mim e me conte o que você imagina criar.'];
if (assistant && assistantAvatar && assistantSpeech && ideaField) {
  let messageIndex = 0, lastScroll = window.scrollY, scrollTimer;
  const setMessage = () => { assistantSpeech.classList.remove('is-visible'); window.setTimeout(() => { assistantSpeech.textContent = assistantMessages[messageIndex]; assistantSpeech.classList.add('is-visible'); }, 160); };
  window.setTimeout(() => assistantSpeech.classList.add('is-visible'), 500);
  window.setInterval(() => { if (!assistant.classList.contains('is-hugging')) { messageIndex = (messageIndex + 1) % assistantMessages.length; setMessage(); } }, 8500);
  window.addEventListener('scroll', () => { const delta = Math.max(-26, Math.min(26, window.scrollY - lastScroll)); lastScroll = window.scrollY; assistant.style.setProperty('--scroll-shift', `${delta}px`); window.clearTimeout(scrollTimer); scrollTimer = window.setTimeout(() => assistant.style.setProperty('--scroll-shift', '0px'), 220); }, { passive: true });
  assistantAvatar.addEventListener('click', () => { assistant.classList.add('is-hugging'); assistantAvatar.setAttribute('aria-expanded', 'true'); assistantSpeech.textContent = 'Um abraço da Tech Art! Agora me conte a sua ideia.'; assistantSpeech.classList.add('is-visible'); document.querySelector('#contato').scrollIntoView({ behavior: 'smooth', block: 'center' }); window.setTimeout(() => ideaField.focus({ preventScroll: true }), 720); window.setTimeout(() => { assistant.classList.remove('is-hugging'); assistantAvatar.setAttribute('aria-expanded', 'false'); }, 1800); });
}
