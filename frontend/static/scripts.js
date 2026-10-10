const SUGGESTIONS = ['AI agents', 'Climate tech', 'Space exploration', 'Global markets', 'Formula 1', 'Health & science'];
const STAGES = ['search', 'curate', 'write', 'review', 'design'];
const STORAGE_KEY = 'gpt-newspaper:v2';

const state = {
    topics: [],
    maxTopics: 6,
    defaultModel: '',
};

const $ = (id) => document.getElementById(id);

// ---------- persistence (best effort) ----------

function loadPrefs() {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {}; } catch { return {}; }
}

function savePrefs(prefs) {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs)); } catch { /* private mode */ }
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

    if (stage === 'skipped') {
        desk.classList.add('is-skipped');
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

function showNewsroom(topics, model) {
    $('composer').hidden = true;
    $('newsroom').hidden = false;
    $('result').hidden = true;
    $('press').textContent = '';
    $('modelTag').textContent = model;
    return createDesks(topics);
}

function showComposer() {
    $('newsroom').hidden = true;
    $('composer').hidden = false;
    $('submitButton').disabled = false;
}

function showResult(url, count) {
    $('resultTitle').textContent = `Your ${count === 1 ? 'one-story' : `${count}-story`} edition is ready`;
    $('readLink').href = url;
    $('result').hidden = false;
    $('readLink').focus();
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

    const layout = document.querySelector('input[name="layout"]:checked').value;
    const model = $('modelInput').value.trim() || state.defaultModel;
    const topics = [...state.topics];
    savePrefs({ topics, layout, model: model === state.defaultModel ? '' : model });

    $('submitButton').disabled = true;
    hideError();

    let response;
    try {
        response = await fetch('/api/newspaper', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ topics, layout, model }),
        });
    } catch {
        showError('Could not reach the server. Is it still running?');
        $('submitButton').disabled = false;
        return;
    }

    if (!response.ok) {
        showError(await readError(response));
        $('submitButton').disabled = false;
        return;
    }

    const desks = showNewsroom(topics, model);
    try {
        for await (const message of readEvents(response)) {
            if (message.type === 'progress') {
                if (message.index != null) updateDesk(desks[message.index], message.stage, message.message);
                else $('press').textContent = message.message;
            } else if (message.type === 'done') {
                $('press').textContent = 'Hot off the press.';
                showResult(message.url, message.articles);
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
        $('modelInput').placeholder = config.model;
        $('advanced').hidden = !config.allow_model_override;
    } catch {
        /* the form still works with server defaults */
    }
}

window.addEventListener('DOMContentLoaded', async () => {
    const now = new Date();
    $('today').textContent = now.toLocaleDateString(undefined, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });

    setupTopics();
    $('composer').addEventListener('submit', produceNewspaper);
    $('againButton').addEventListener('click', showComposer);

    await loadConfig();

    const prefs = loadPrefs();
    (prefs.topics || []).forEach(addTopic);
    if (prefs.layout) {
        const radio = document.querySelector(`input[name="layout"][value="${prefs.layout}"]`);
        if (radio) radio.checked = true;
    }
    if (prefs.model) $('modelInput').value = prefs.model;
    renderTopics();
});
