(() => {
  const letters = ['T', 'E', 'C', 'H', 'A', 'R', 'T'];
  const slots = [{x:8,y:12},{x:25,y:16},{x:48,y:11},{x:68,y:13},{x:82,y:25},{x:14,y:39},{x:35,y:35},{x:57,y:42},{x:76,y:48},{x:10,y:66},{x:29,y:72},{x:49,y:62},{x:67,y:72},{x:83,y:67}];
  const palettes = [
    ['#00eaff','#0066ff'], ['#00ff66','#00eaff'], ['#7f6cff','#00eaff'], ['#00ff9d','#0066ff']
  ];
  const intro = document.querySelector('#intro-screen'), play = document.querySelector('#play-screen'), win = document.querySelector('#win-screen');
  const scene = document.querySelector('#scene'), letterEl = document.querySelector('#hidden-letter'), hit = document.querySelector('#letter-hit'), feedback = document.querySelector('#feedback');
  const progress = document.querySelector('#word-progress'), timerEl = document.querySelector('#timer'), attemptsEl = document.querySelector('#attempts'), instruction = document.querySelector('#instruction');
  const rankingChoice = document.querySelector('#join-ranking'), rankingForm = document.querySelector('#ranking-form'), rankingResult = document.querySelector('#ranking-result');
  let index = 0, attempts = 0, startedAt = 0, timerId = null, slotsForGame = [], finalSeconds = 0;
  const pad = value => String(value).padStart(2, '0');
  const format = seconds => `${pad(Math.floor(seconds / 60))}:${pad(seconds % 60)}`;
  const elapsed = () => Math.floor((Date.now() - startedAt) / 1000);
  const shuffle = values => { const copy = [...values]; for (let i = copy.length - 1; i > 0; i -= 1) { const j = Math.floor(Math.random() * (i + 1)); [copy[i], copy[j]] = [copy[j], copy[i]]; } return copy; };
  function updateProgress() { progress.textContent = letters.map((letter, position) => position < index ? letter : '_').join(' ').replace('H A', 'H   A'); }
  function showFeedback(text, miss = false) { feedback.textContent = text; feedback.className = `feedback show${miss ? ' miss' : ''}`; window.setTimeout(() => { feedback.className = 'feedback'; }, 850); }
  function sceneVariation() { const [first, second] = palettes[Math.floor(Math.random() * palettes.length)]; scene.style.setProperty('--scene-one', first); scene.style.setProperty('--scene-two', second); scene.style.setProperty('--turn', `${Math.floor(Math.random() * 70) - 35}deg`); }
  function placeLetter() {
    const point = slotsForGame[index]; sceneVariation();
    letterEl.className = 'hidden-letter'; letterEl.textContent = letters[index];
    letterEl.style.left = `${point.x}%`; letterEl.style.top = `${point.y}%`;
    hit.style.left = `calc(${point.x}% - 15px)`; hit.style.top = `calc(${point.y}% - 15px)`; hit.disabled = false;
    hit.setAttribute('aria-label', `Selecionar a letra ${letters[index]} escondida no cenário`);
    instruction.textContent = 'Localize o próximo sinal oculto no cenário.';
  }
  function updateTimer() { timerEl.textContent = format(elapsed()); }
  function renderBest() { const stats = JSON.parse(localStorage.getItem('techart-game-stats') || '{}'); const best = document.querySelector('#best-score'); best.textContent = stats.bestTime ? `Seu melhor tempo: ${format(stats.bestTime)} · Partidas concluídas: ${stats.completed}` : 'Seu melhor resultado aparecerá aqui.'; }
  function begin() {
    index = 0; attempts = 0; finalSeconds = 0; slotsForGame = shuffle(slots).slice(0, letters.length); startedAt = Date.now();
    intro.hidden = true; win.hidden = true; play.hidden = false; rankingChoice.checked = false; rankingForm.hidden = true; rankingForm.reset(); rankingResult.textContent = '';
    updateProgress(); attemptsEl.textContent = '0'; timerEl.textContent = '00:00'; placeLetter(); window.clearInterval(timerId); timerId = window.setInterval(updateTimer, 1000);
  }
  function finish() {
    window.clearInterval(timerId); finalSeconds = elapsed(); play.hidden = true; win.hidden = false;
    document.querySelector('#final-time').textContent = format(finalSeconds); document.querySelector('#final-attempts').textContent = attempts;
    const stats = JSON.parse(localStorage.getItem('techart-game-stats') || '{"completed":0}'); stats.completed += 1; if (!stats.bestTime || finalSeconds < stats.bestTime) stats.bestTime = finalSeconds; if (!stats.bestAttempts || attempts < stats.bestAttempts) stats.bestAttempts = attempts; localStorage.setItem('techart-game-stats', JSON.stringify(stats)); renderBest();
  }
  function correct(event) {
    event.stopPropagation(); attempts += 1; attemptsEl.textContent = attempts; hit.disabled = true; letterEl.classList.add('revealed'); showFeedback('Letra encontrada!');
    window.setTimeout(() => { index += 1; updateProgress(); if (index === letters.length) finish(); else placeLetter(); }, 620);
  }
  function miss(event) { if (event.target === hit || hit.disabled) return; attempts += 1; attemptsEl.textContent = attempts; showFeedback('Ainda não... procure com atenção.', true); }
  rankingChoice.addEventListener('change', () => { rankingForm.hidden = !rankingChoice.checked; if (!rankingChoice.checked) rankingResult.textContent = ''; });
  rankingForm.addEventListener('submit', async event => {
    event.preventDefault(); const saveButton = rankingForm.querySelector('button'); saveButton.disabled = true; saveButton.textContent = 'SALVANDO...';
    const data = new FormData(rankingForm); data.append('time_seconds', finalSeconds); data.append('attempts', attempts);
    try { const response = await fetch('/jogo/ranking', { method: 'POST', body: data }); const payload = await response.json(); if (!response.ok) throw new Error(payload.error || 'Não foi possível salvar.'); rankingResult.textContent = `${payload.name}, você ficou na ${payload.position}ª colocação do ranking!`; rankingForm.hidden = true; rankingChoice.checked = false; }
    catch (error) { rankingResult.textContent = error.message; saveButton.disabled = false; saveButton.textContent = 'SALVAR NO RANKING'; }
  });
  document.querySelector('#start-game').addEventListener('click', begin); document.querySelector('#play-again').addEventListener('click', begin); hit.addEventListener('click', correct); scene.addEventListener('click', miss); renderBest();
})();