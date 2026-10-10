const SUGGESTIONS = ['AI agents', 'Climate tech', 'Space exploration', 'Global markets', 'Formula 1', 'Health & science'];
const STAGES = ['plan', 'search', 'curate', 'write', 'review', 'design'];
const STORAGE_KEY = 'gpt-newspaper:v2';
const KEYS_STORAGE_KEY = 'gpt-newspaper:keys';

const PROVIDER_NAMES = {
    openai: 'OpenAI', anthropic: 'Anthropic', google_genai: 'Google', groq: 'Groq', mistralai: 'Mistral',
    xai: 'xAI', deepseek: 'DeepSeek', openrouter: 'OpenRouter', together: 'Together', fireworks: 'Fireworks', ollama: 'Ollama',
};
const NAME_PREFIXES = [
    ['gpt-', 'openai'], ['o1', 'openai'], ['o3', 'openai'], ['o4', 'openai'],
    ['claude', 'anthropic'], ['gemini', 'google_genai'], ['mistral', 'mistralai'], ['grok', 'xai'],
];

const state = {
    topics: [],
    maxTopics: 6,
    defaultModel: '',
    serverKeys: {},
    keys: { tavily: '', providers: {} },
};

const $ = (id) => document.getElementById(id);

// ---------- persistence (best effort) ----------

function loadPrefs() {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {}; } catch { return {}; }
}

function savePrefs(prefs) {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs)); } catch { /* private mode */ }
}

function loadKeys() {
    try {
        const saved = JSON.parse(localStorage.getItem(KEYS_STORAGE_KEY));
        if (saved) return { tavily: saved.tavily || '', providers: saved.providers || {} };
    } catch { /* storage unavailable */ }
    return { tavily: '', providers: {} };
}

function persistKeys() {
    try {
        if ($('rememberKeys').checked) localStorage.setItem(KEYS_STORAGE_KEY, JSON.stringify(state.keys));
        else localStorage.removeItem(KEYS_STORAGE_KEY);
    } catch { /* storage unavailable */ }
}

// ---------- model & keys ----------

function currentModel() {
    return $('modelInput').value.trim() || state.defaultModel;
}

function inferProvider(model) {
    if (model.includes(':')) return model.split(':', 1)[0];
    const match = NAME_PREFIXES.find(([prefix]) => model.toLowerCase().startsWith(prefix));
    return match ? match[1] : null;
}

function providerName(provider) {
    return PROVIDER_NAMES[provider] || provider || 'Model';
}

/** Which keys are still missing for the current model (server env or browser). */
function missingKeys() {
    const missing = [];
    if (!state.keys.tavily && !state.serverKeys.tavily) missing.push('tavily');
    const provider = inferProvider(currentModel());
    const known = provider in state.serverKeys;
    if (known && !state.serverKeys[provider] && !state.keys.providers[provider]) missing.push('provider');
    return missing;
}

function currentImages() {
    return document.querySelector('input[name="images"]:checked')?.value || 'photos';
}

/** Illustrations need an OpenAI key; show a field for it when the chat model's key isn't one. */
function renderImageKey() {
    const illustrated = currentImages() !== 'photos';
    const needsOwnKey = illustrated && inferProvider(currentModel()) !== 'openai' && !state.serverKeys.openai;
    $('imageKeyField').hidden = !needsOwnKey;
    $('imageKey').value = state.keys.providers.openai || '';
    const hasKey = state.serverKeys.openai || state.keys.providers.openai;
    $('imagesHelp').textContent = !illustrated
        ? "Photos from the news sources. Quality varies by outlet."
        : hasKey
            ? "AI illustrations in the paper's house style, always labeled as such."
            : 'Needs an OpenAI API key (add it under “Model & API keys”). Without one, the paper uses news photos.';
}

function renderKeys() {
    renderImageKey();
    const provider = inferProvider(currentModel());
    const name = providerName(provider);
    const missing = missingKeys();
    // Tavily
    const tavily = $('tavilyKey');
    tavily.placeholder = state.serverKeys.tavily ? "Using the server's key" : 'tvly-…';
    tavily.classList.toggle('missing', missing.includes('tavily'));
    $('tavilyHelp').innerHTML = state.serverKeys.tavily
        ? 'Optional. A key here overrides the server key.'
        : 'Required. Get a free key at <a href="https://app.tavily.com" target="_blank" rel="noopener">tavily.com</a>.';

    // Model provider
    const field = $('providerKeyField');
    const input = $('providerKey');
    field.hidden = provider === 'ollama';
    $('providerKeyLabel').textContent = `${name} API key`;
    input.value = state.keys.providers[provider] || '';
    input.dataset.provider = provider || '';
    input.classList.toggle('missing', missing.includes('provider'));
    if (state.serverKeys[provider]) {
        input.placeholder = "Using the server's key";
        $('providerKeyHelp').textContent = 'Optional. A key here overrides the server key.';
    } else if (provider in state.serverKeys) {
        input.placeholder = 'Required';
        $('providerKeyHelp').textContent = `Required for ${name} models. It is saved per provider, so switching models keeps your other keys.`;
    } else {
        input.placeholder = 'Optional';
        $('providerKeyHelp').textContent = 'Only needed if this provider expects an API key.';
    }

    renderStatus();
}

function renderStatus() {
    const missing = missingKeys();
    const status = $('settingsStatus');
    status.textContent = missing.length ? '· keys needed' : '· ready';
    status.className = `settings-status ${missing.length ? 'needs-keys' : 'ready'}`;
}

function setupKeys() {
    state.keys = loadKeys();
    $('tavilyKey').value = state.keys.tavily;

    $('tavilyKey').addEventListener('input', (event) => {
        state.keys.tavily = event.target.value.trim();
        persistKeys();
        $('tavilyKey').classList.toggle('missing', missingKeys().includes('tavily'));
        renderStatus();
    });
    $('providerKey').addEventListener('input', (event) => {
        const provider = event.target.dataset.provider;
        if (!provider) return;
        const value = event.target.value.trim();
        if (value) state.keys.providers[provider] = value;
        else delete state.keys.providers[provider];
        persistKeys();
        $('providerKey').classList.toggle('missing', missingKeys().includes('provider'));
        renderStatus();
    });
    $('modelInput').addEventListener('input', renderKeys);
    document.querySelectorAll('input[name="images"]').forEach((radio) => radio.addEventListener('change', renderKeys));
    $('imageKey').addEventListener('input', (event) => {
        const value = event.target.value.trim();
        if (value) state.keys.providers.openai = value;
        else delete state.keys.providers.openai;
        persistKeys();
        renderImageKey();
    });
    $('rememberKeys').addEventListener('change', persistKeys);
}

function openSettingsAt(missing) {
    $('settings').open = true;
    (missing[0] === 'provider' ? $('providerKey') : $('tavilyKey')).focus();
}

// ---------- topics ----------

function addTopic(raw) {
    const topic = raw.trim().replace(/\s+/g, ' ');
    if (!topic) return false;
    if (state.topics.some((t) => t.toLowerCase() === topic.toLowerCase())) return false;
    if (state.topics.length >= state.maxTopics) {
        showError(`You can cover up to ${state.maxTopics} topics per edition.`);
        return false;
    }
    state.topics.push(topic);
    renderTopics();
    return true;
}

function removeTopic(index) {
    state.topics.splice(index, 1);
    renderTopics();
    $('topicInput').focus();
}

function renderTopics() {
    const chips = $('chips');
    chips.replaceChildren(...state.topics.map((topic, i) => {
        const li = document.createElement('li');
        li.className = 'chip';
        li.textContent = topic;
        const remove = document.createElement('button');
        remove.type = 'button';
        remove.textContent = '×';
        remove.setAttribute('aria-label', `Remove ${topic}`);
        remove.addEventListener('click', () => removeTopic(i));
        li.append(remove);
        return li;
    }));

    $('topicInput').placeholder = state.topics.length
        ? (state.topics.length < state.maxTopics ? 'Add another topic…' : '')
        : 'Type a topic and press Enter';

    document.querySelectorAll('.suggestion').forEach((button) => {
        button.hidden = state.topics.some((t) => t.toLowerCase() === button.dataset.topic.toLowerCase());
    });
    hideError();
}

function setupTopics() {
    const input = $('topicInput');
    input.addEventListener('keydown', (event) => {
        if ((event.key === 'Enter' || event.key === ',') && input.value.trim()) {
            event.preventDefault();
            if (addTopic(input.value)) input.value = '';
        } else if (event.key === 'Backspace' && !input.value && state.topics.length) {
            removeTopic(state.topics.length - 1);
        }
    });
    $('topicBox').addEventListener('click', (event) => {
        if (event.target.id === 'topicBox') input.focus();
    });

    const suggestions = $('suggestions');
    for (const topic of SUGGESTIONS) {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'suggestion';
        button.dataset.topic = topic;
        button.textContent = topic;
        button.addEventListener('click', () => addTopic(topic));
        suggestions.append(button);
    }
}

// ---------- errors ----------

function showError(message) {
    const el = $('formError');
    el.textContent = message;
    el.hidden = false;
}

function hideError() {
    $('formError').hidden = true;
}

// ---------- newsroom (live progress) ----------

function createDesks(topics) {
    const template = $('deskTemplate');
    const desks = topics.map((topic) => {
        const desk = template.content.firstElementChild.cloneNode(true);
        desk.querySelector('.desk-topic').textContent = topic;
        return desk;
    });
    $('desks').replaceChildren(...desks);
    return desks;
}

function updateDesk(desk, stage, message) {
    if (!desk) return;
    const status = desk.querySelector('.desk-status');
    const steps = desk.querySelectorAll('.steps li');

    if (stage === 'skipped' || stage === 'failed') {
        desk.classList.add(`is-${stage}`);
        desk.querySelectorAll('.steps li.active').forEach((step) => step.classList.remove('active'));
        status.textContent = message;
        return;
    }

    const position = stage === 'done' ? STAGES.length : STAGES.indexOf(stage);
    steps.forEach((step, i) => {
        step.classList.toggle('complete', i < position);
        step.classList.toggle('active', i === position);
    });
    desk.classList.toggle('is-done', stage === 'done');

    // Quote what the editor and writer say to each other
    const quote = message.match(/^(Editor|Writer): (.*)$/s);
    if (quote) {
        status.replaceChildren(`${quote[1]}: `, Object.assign(document.createElement('q'), { textContent: quote[2] }));
    } else {
        status.textContent = message;
    }
}

function image(src, onFail) {
    const img = document.createElement('img');
    img.alt = '';
    img.loading = 'lazy';
    img.referrerPolicy = 'no-referrer';
    img.addEventListener('error', onFail || (() => img.remove()));
    img.src = src;
    return img;
}

function addFreshCard(article) {
    const card = Object.assign(document.createElement('a'), { className: 'fresh-card', href: article.url, target: '_blank' });
    if (article.image) card.append(Object.assign(image(article.image), { loading: 'eager' }));
    card.append(
        Object.assign(document.createElement('h3'), { textContent: article.title, dir: 'auto' }),
        Object.assign(document.createElement('p'), { textContent: `${article.reading_minutes} min read` }),
    );
    $('freshGrid').append(card);
    $('fresh').hidden = false;
}

let timer = null;

function startTimer() {
    const started = Date.now();
    const tick = () => {
        const seconds = Math.floor((Date.now() - started) / 1000);
        $('elapsed').textContent = `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`;
    };
    tick();
    timer = setInterval(tick, 1000);
}

function stopTimer() {
    clearInterval(timer);
}

function showNewsroom(topics, model) {
    $('composer').hidden = true;
    $('newsroom').hidden = false;
    $('result').hidden = true;
    $('fresh').hidden = true;
    $('freshGrid').replaceChildren();
    $('press').textContent = '';
    $('modelTag').textContent = model;
    document.title = 'Printing… · The GPT Newspaper';
    startTimer();
    return createDesks(topics);
}

function showComposer() {
    stopTimer();
    document.title = 'The GPT Newspaper';
    $('newsroom').hidden = true;
    $('composer').hidden = false;
    $('submitButton').disabled = false;
}

function showResult({ url, articles, failed }) {
    stopTimer();
    document.title = '✓ Your edition is ready · The GPT Newspaper';
    const stories = articles === 1 ? 'one-story' : `${articles}-story`;
    $('resultTitle').textContent = `Your ${stories} edition is ready` + (failed ? ` (${failed} didn't make it)` : '');
    $('readLink').href = url;
    $('result').hidden = false;
    $('readLink').focus();
    loadArchive();
}

async function copyLink() {
    const url = new URL($('readLink').getAttribute('href'), location.href).href;
    try {
        await navigator.clipboard.writeText(url);
        $('copyButton').textContent = 'Copied ✓';
    } catch {
        $('copyButton').textContent = 'Copy failed';
    }
    setTimeout(() => { $('copyButton').textContent = 'Copy link'; }, 1800);
}

// ---------- archive ----------

async function loadArchive() {
    let editions = [];
    try {
        editions = await (await fetch('/api/editions')).json();
    } catch {
        return;
    }
    const cards = editions.map((edition) => {
        const card = Object.assign(document.createElement('a'), { className: 'edition-card', href: edition.url });
        if (edition.image) card.append(image(edition.image));
        const when = edition.created_at ? new Date(edition.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : edition.date;
        card.append(
            Object.assign(document.createElement('h3'), { textContent: edition.title, dir: 'auto' }),
            Object.assign(document.createElement('span'), {
                className: 'edition-meta',
                textContent: `${when} · ${(edition.topics || []).join(', ')}`,
            }),
        );
        return card;
    });
    $('archiveGrid').replaceChildren(...cards);
    $('archive').hidden = cards.length === 0;
}

// ---------- streaming ----------

async function* readEvents(response) {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop();
        for (const line of lines) if (line.trim()) yield JSON.parse(line);
    }
    if (buffer.trim()) yield JSON.parse(buffer);
}

async function readError(response) {
    try {
        const body = await response.json();
        if (typeof body.detail === 'string') return body.detail;
        if (Array.isArray(body.detail)) return body.detail.map((d) => d.msg).join('\n');
    } catch { /* not JSON */ }
    return `The server returned ${response.status}.`;
}

async function produceNewspaper(event) {
    event.preventDefault();

    const pending = $('topicInput').value;
    if (pending.trim() && addTopic(pending)) $('topicInput').value = '';
    if (!state.topics.length) {
        showError('Add at least one topic to cover.');
        $('topicInput').focus();
        return;
    }

    const missing = missingKeys();
    if (missing.length) {
        const what = missing.map((k) => (k === 'tavily' ? 'Tavily' : providerName(inferProvider(currentModel())))).join(' and ');
        showError(`Add your ${what} API key to print an edition.`);
        renderKeys();
        openSettingsAt(missing);
        return;
    }

    const layout = document.querySelector('input[name="layout"]:checked').value;
    const model = currentModel();
    const topics = [...state.topics];
    const provider = inferProvider(model);
    const keys = {};
    if (state.keys.tavily) keys.tavily_api_key = state.keys.tavily;
    if (state.keys.providers[provider]) keys.api_key = state.keys.providers[provider];
    const images = currentImages();
    if (images !== 'photos' && state.keys.providers.openai) keys.image_api_key = state.keys.providers.openai;
    const language = $('languageSelect').value;
    savePrefs({ topics, layout, language, images, model: model === state.defaultModel ? '' : model });

    $('submitButton').disabled = true;
    hideError();

    let response;
    try {
        response = await fetch('/api/newspaper', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ topics, layout, language, images, model, ...keys }),
        });
    } catch {
        showError('Could not reach the server. Is it still running?');
        $('submitButton').disabled = false;
        return;
    }

    if (!response.ok) {
        const message = await readError(response);
        showError(message);
        if (/api key/i.test(message)) $('settings').open = true;
        $('submitButton').disabled = false;
        return;
    }

    const desks = showNewsroom(topics, model);
    try {
        for await (const message of readEvents(response)) {
            if (message.type === 'progress') {
                if (message.index != null) updateDesk(desks[message.index], message.stage, message.message);
                else $('press').textContent = message.message;
                if (message.article) addFreshCard(message.article);
            } else if (message.type === 'done') {
                $('press').textContent = 'Hot off the press.';
                showResult(message);
                return;
            } else if (message.type === 'error') {
                throw new Error(message.message);
            }
        }
        throw new Error('The connection closed before the newspaper was finished.');
    } catch (error) {
        showComposer();
        showError(error.message);
    }
}

// ---------- init ----------

async function loadConfig() {
    try {
        const config = await (await fetch('/api/config')).json();
        state.defaultModel = config.model;
        state.maxTopics = config.max_topics;
        state.serverKeys = config.server_keys || {};
        $('modelInput').placeholder = config.model;
        const defaultImages = document.querySelector(`input[name="images"][value="${config.images?.default}"]`);
        if (defaultImages) defaultImages.checked = true;
        $('languageSelect').replaceChildren(...Object.entries(config.languages || { en: 'English' }).map(
            ([code, name]) => Object.assign(document.createElement('option'), { value: code, textContent: name }),
        ));
        $('modelField').hidden = !config.allow_model_override;
    } catch {
        /* the form still works with server defaults */
    }
}

window.addEventListener('DOMContentLoaded', async () => {
    const now = new Date();
    $('today').textContent = now.toLocaleDateString(undefined, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });

    setupTopics();
    setupKeys();
    $('composer').addEventListener('submit', produceNewspaper);
    $('againButton').addEventListener('click', showComposer);
    $('copyButton').addEventListener('click', copyLink);

    const isMac = /Mac|iPhone|iPad/.test(navigator.platform);
    $('shortcutHint').textContent = isMac ? '⌘ Enter' : 'Ctrl Enter';
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' && (event.metaKey || event.ctrlKey) && !$('composer').hidden) {
            event.preventDefault();
            $('composer').requestSubmit();
        }
    });

    await loadConfig();

    const prefs = loadPrefs();
    (prefs.topics || []).forEach(addTopic);
    if (prefs.layout) {
        const radio = document.querySelector(`input[name="layout"][value="${prefs.layout}"]`);
        if (radio) radio.checked = true;
    }
    if (prefs.model) $('modelInput').value = prefs.model;
    const savedImages = prefs.images && document.querySelector(`input[name="images"][value="${prefs.images}"]`);
    if (savedImages) savedImages.checked = true;
    if (prefs.language && $('languageSelect').querySelector(`option[value="${prefs.language}"]`)) {
        $('languageSelect').value = prefs.language;
    }
    renderTopics();
    renderKeys();
    if (missingKeys().length) $('settings').open = true;
    loadArchive();
});
