(() => {
  function headers(apiKey) {
    const h = { 'content-type': 'application/json' };
    if (apiKey) h['x-api-key'] = apiKey;
    return h;
  }

  async function savePreset(base, name, apiKey, note = '') {
    const r = await fetch(`${base}/config/preset/save`, {
      method: 'POST', headers: headers(apiKey),
      body: JSON.stringify({ name, note })
    });
    return await r.json();
  }

  async function loadPreset(base, name, apiKey) {
    const r = await fetch(`${base}/config/preset/load`, {
      method: 'POST', headers: headers(apiKey),
      body: JSON.stringify({ name })
    });
    return await r.json();
  }

  async function listPresets(base, apiKey) {
    const r = await fetch(`${base}/config/presets`, { headers: headers(apiKey) });
    return await r.json();
  }

  function mountPresetUI(opts = {}) {
    const base = opts.base || '';
    const apiKeyEl = opts.apiKeyEl || document.getElementById('apikey');
    const getKey = () => (apiKeyEl && apiKeyEl.value) || '';

    const row = document.createElement('div');
    row.className = 'row';
    row.style.gap = '8px';
    row.innerHTML = `
      <input id="presetName" type="text" placeholder="preset name" style="width:160px;"/>
      <button id="presetSave">Save preset</button>
      <button id="presetLoad">Load preset</button>
      <button id="presetList">List presets</button>
      <span id="presetOut" class="badge"></span>
    `;
    (opts.anchor || document.body).appendChild(row);

    const out = row.querySelector('#presetOut');
    const nameEl = row.querySelector('#presetName');
    const nameVal = () => (nameEl.value || 'preset').trim();
    const toast = (t) => { out.textContent = (typeof t === 'string' ? t : JSON.stringify(t)); setTimeout(() => out.textContent = '', 3500); };

    row.querySelector('#presetSave').onclick = async () => {
      try { const j = await savePreset(base, nameVal(), getKey()); toast(j.ok ? `saved ${nameVal()}` : j); } catch { toast('save error'); }
    };
    row.querySelector('#presetLoad').onclick = async () => {
      try { const j = await loadPreset(base, nameVal(), getKey()); toast(j.ok ? `loaded ${nameVal()}` : j); } catch { toast('load error'); }
    };
    row.querySelector('#presetList').onclick = async () => {
      try { const j = await listPresets(base, getKey()); const names = (j.items||[]).map(x=>x.name).join(', ') || 'no presets'; toast(names); } catch { toast('list error'); }
    };
  }

  // Expose globally
  window.PresetUI = { mountPresetUI };
})();

