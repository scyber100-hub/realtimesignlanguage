(() => {
  function DashboardInit() {
    const logEl = document.getElementById('log');
    const statusEl = document.getElementById('status');
    const apikeyInput = document.getElementById('apikey');
    try { const saved = localStorage.getItem('pipeline_apikey'); if (saved && apikeyInput) apikeyInput.value = saved; } catch {}

    let ws = null;
    const cfg = { latency_p90_warn_ms: 1200, replace_ratio_warn: 0.5, rate_limit_ratio_warn: 0.1 };
    const hist = document.getElementById('hist');
    const spark = document.getElementById('spark');
    const repSpark = document.getElementById('repSpark');
    const hctx = hist.getContext('2d');
    const sctx = spark.getContext('2d');
    const rctx = repSpark.getContext('2d');
    const latRecent = [];
    const repRecent = [];
    let lastBins = [];

    function log(t){ try{ logEl.textContent += (typeof t==='string'?t:JSON.stringify(t)) + "\n"; logEl.scrollTop = logEl.scrollHeight; }catch(e){} }
    function getHeaders(){ const h={'content-type':'application/json'}; const k = apikeyInput.value; if(k) h['x-api-key']=k; try{ localStorage.setItem('pipeline_apikey', k||''); }catch{} return h; }

    // Config handlers
    document.getElementById('cfgBtn').onclick = async () => {
      const res = await fetch('/config', { headers: getHeaders() });
      const data = await res.json();
      document.getElementById('cfgOut').textContent = JSON.stringify(data);
      if (typeof data.include_aux_channels !== 'undefined') document.getElementById('auxToggle').checked = !!data.include_aux_channels;
      if (typeof data.max_ingest_rps !== 'undefined') document.getElementById('rpsInput').value = data.max_ingest_rps;
      log('GET /config');
    };
    document.getElementById('cfgUpdate').onclick = async () => {
      const body = { include_aux_channels: document.getElementById('auxToggle').checked, max_ingest_rps: parseInt(document.getElementById('rpsInput').value||'0')||undefined };
      const res = await fetch('/config/update', { method: 'POST', headers: getHeaders(), body: JSON.stringify(body) });
      const data = await res.json();
      log('POST /config/update => ' + JSON.stringify(data));
    };
    document.getElementById('thUpdate').onclick = async () => {
      const body = {
        latency_p90_warn_ms: parseInt(document.getElementById('latWarn').value||'0')||0,
        replace_ratio_warn: parseFloat(document.getElementById('repWarn').value||'0')||0,
        rate_limit_ratio_warn: parseFloat(document.getElementById('rlWarn').value||'0')||0,
      };
      const res = await fetch('/config/update', { method: 'POST', headers: getHeaders(), body: JSON.stringify(body) });
      const data = await res.json();
      log('POST /config/update thresholds => ' + JSON.stringify(data));
    };

    // Presets UI mount
    try { PresetUI.mountPresetUI({ anchor: document.getElementById('presetMount'), apiKeyEl: apikeyInput }); } catch {}

    function drawHist(ms){
      const w = hist.width, h = hist.height;
      hctx.clearRect(0,0,w,h);
      const bins = (ms && ms.hist) || [];
      lastBins = bins;
      const maxV = bins.reduce((m,x)=>Math.max(m,x||0),1);
      const barW = Math.max(1, Math.floor((w-10)/Math.max(1,bins.length)));
      hctx.fillStyle = '#4aa3ff';
      for (let i=0;i<bins.length;i++){
        const v = bins[i]||0; const bh = Math.round((v/maxV)*(h-20));
        hctx.fillRect(5 + i*barW, h-5-bh, barW-1, bh);
      }
      // axis & label
      hctx.strokeStyle = '#333'; hctx.beginPath(); hctx.moveTo(5,h-5); hctx.lineTo(w-5,h-5); hctx.stroke();
      hctx.fillStyle = '#aaa'; hctx.fillText('latency histogram', 10, 12);
      hctx.fillText(`max ${maxV}`, w-70, 12);
    }
    function drawSparkline(values, ctx, label){
      const w = ctx.canvas.width, h = ctx.canvas.height;
      ctx.clearRect(0,0,w,h);
      if (!values.length) return;
      const minV = Math.min(...values), maxV = Math.max(...values);
      ctx.strokeStyle = '#ffaa00'; ctx.beginPath();
      for (let i=0;i<values.length;i++){
        const x = Math.round((i/(values.length-1))*(w-10))+5;
        const y = h - 5 - Math.round(((values[i]-minV)/(maxV-minV || 1))*(h-10));
        if (i===0) ctx.moveTo(x,y); else ctx.lineTo(x,y);
      }
      ctx.stroke(); ctx.fillStyle = '#aaa'; ctx.fillText(label, 10, 12);
    }

    function updateBadgesFromStats(s){
      const p90 = Number((s.latency_ms && s.latency_ms.p90) || 0);
      const rep = Number(s.timeline_replace_ratio || 0);
      const rl  = Number(s.rate_limit_ratio || 0);
      const latBad = (p90 > (cfg.latency_p90_warn_ms||1200));
      const repBad = (rep > (cfg.replace_ratio_warn||0.5));
      const rlBad  = (rl  > (cfg.rate_limit_ratio_warn||0.1));
      const setBg = (id,bad)=>{ const el=document.getElementById(id); if(!el) return; el.classList.remove('ok','bad'); el.classList.add(bad?'bad':'ok'); };
      setBg('badgeLat', latBad); setBg('badgeRep', repBad); setBg('badgeRL', rlBad);
      // visuals & summary
      drawHist(s.latency_ms);
      latRecent.push(p90); if (latRecent.length>60) latRecent.shift();
      drawSparkline(latRecent, sctx, 'latency p90');
      repRecent.push(rep); if (repRecent.length>60) repRecent.shift();
      drawSparkline(repRecent, rctx, 'replace ratio');
      const setTxt=(id,txt)=>{ const el=document.getElementById(id); if(el) el.textContent = txt; };
      setTxt('sumTl', `timeline total: ${s.timeline_broadcast_total ?? 0}`);
      setTxt('sumTlRate', `timeline rate(1m): ${s.timeline_rate_per_sec_1m ?? 0}/s`);
      setTxt('sumIngestRate', `ingest rate(1m): ${s.ingest_rate_per_sec_1m ?? 0}/s`);
      setTxt('sumSess', `sessions: ${s.session_count ?? 0}`);
      setTxt('sumWs', `ws clients: ${s.ws_clients ?? 0}`);
    }

    function connect(){
      if (ws) return;
      ws = new WebSocket((location.protocol==='https:'?'wss://':'ws://') + location.host + '/ws/timeline');
      ws.onopen = () => { statusEl.textContent = 'connected'; ws.send('hello'); };
      ws.onclose = () => { statusEl.textContent = 'disconnected'; ws = null; };
      ws.onmessage = (ev) => { try { const msg = JSON.parse(ev.data); if (msg.type === 'stats') updateBadgesFromStats(msg.data||{}); } catch {} };
    }
    connect();

    // Tooltip for canvases
    const tip = document.createElement('div'); tip.className = 'tooltip'; document.body.appendChild(tip);
    function showTip(x, y, text){ tip.textContent = text; tip.style.left = x + 'px'; tip.style.top = y + 'px'; tip.style.display = 'block'; }
    function hideTip(){ tip.style.display = 'none'; }
    hist.addEventListener('mousemove', (e) => {
      const rect = hist.getBoundingClientRect(); const x = e.clientX - rect.left; const y = e.clientY - rect.top;
      const w = hist.width; const bins = lastBins||[]; if (!bins.length) return hideTip();
      const idx = Math.max(0, Math.min(bins.length-1, Math.floor((x-5)/Math.max(1, (w-10)/bins.length))));
      showTip(e.clientX, e.clientY, `bin ${idx}: ${bins[idx]||0}`);
    });
    hist.addEventListener('mouseleave', hideTip);
    spark.addEventListener('mousemove', (e)=>{
      const rect = spark.getBoundingClientRect(); const x = e.clientX - rect.left; const w = spark.width; if (!latRecent.length) return hideTip();
      const idx = Math.max(0, Math.min(latRecent.length-1, Math.round((x-5)/(w-10)*(latRecent.length-1))));
      showTip(e.clientX, e.clientY, `p90: ${latRecent[idx]||0}`);
    });
    spark.addEventListener('mouseleave', hideTip);
    repSpark.addEventListener('mousemove', (e)=>{
      const rect = repSpark.getBoundingClientRect(); const x = e.clientX - rect.left; const w = repSpark.width; if (!repRecent.length) return hideTip();
      const idx = Math.max(0, Math.min(repRecent.length-1, Math.round((x-5)/(w-10)*(repRecent.length-1))));
      showTip(e.clientX, e.clientY, `replace: ${repRecent[idx]??0}`);
    });
    repSpark.addEventListener('mouseleave', hideTip);

    // Alerts UI
    (function(){
      let timer = null;
      async function refreshAlerts(){
        try {
          const n = parseInt(document.getElementById('alertsN').value||'30')||30;
          const res = await fetch(`/stats/alerts/history?n=${n}`, { headers: getHeaders() });
          const data = await res.json();
          document.getElementById('alertsCount').textContent = (data.items||[]).length || 0;
          const ul = document.getElementById('alertsList');
          ul.innerHTML = '';
          (data.items||[]).forEach(a => { const li = document.createElement('li'); li.textContent = `${a.ts||''} ${a.type||''}`; ul.appendChild(li); });
        } catch {}
      }
      document.getElementById('alertsRefresh').onclick = refreshAlerts;
      document.getElementById('alertsAuto').onchange = (e)=>{ if (e.target.checked) { const s = Math.max(2, parseInt(document.getElementById('alertsInt').value||'7')); timer = setInterval(refreshAlerts, s*1000); } else if (timer) { clearInterval(timer); timer = null; } };
    })();

    // Sessions UI
    (function(){
      let timer = null; let sortKey='last_update_ms', sortDir=-1; let page=1; let pageSize=20;
      function pageControls(total){
        const totalPages = Math.max(1, Math.ceil(total / pageSize));
        if (page > totalPages) page = totalPages;
        document.getElementById('sessPage').value = String(page);
        document.getElementById('sessPageInfo').textContent = `page ${page}/${totalPages}`;
      }
      async function loadSessions(){
        try {
          const res = await fetch('/sessions_full');
          const data = await res.json();
          const tb = document.querySelector('#sessTable tbody'); tb.innerHTML = '';
          let rows = (data.items||[]);
          const f = (document.getElementById('sessFilter').value||'').trim(); if (f) rows = rows.filter(x => x.session_id === f);
          rows.sort((a,b)=>{ const av=a[sortKey]??0, bv=b[sortKey]??0; if (av===bv) return 0; return av>bv? sortDir : -sortDir; });
          pageSize = Math.max(1, parseInt(document.getElementById('sessPageSize').value||'20'));
          pageControls(rows.length);
          const start = (page-1)*pageSize; const end = start + pageSize;
          rows.slice(start, end).forEach(r => { const tr = document.createElement('tr'); const meta = r.meta ? JSON.stringify(r.meta) : ''; const lastTxt = r.last_text_preview || ''; tr.innerHTML = `<td>${r.session_id}</td><td style="text-align:right">${r.events}</td><td style="text-align:right">${r.text_len}</td><td style="text-align:right">${r.last_update_ms||''}</td><td>${lastTxt}</td><td>${meta}</td>`; tb.appendChild(tr); });
        } catch {}
      }
      document.querySelectorAll('#sessTable thead th[data-sort]').forEach(th => th.addEventListener('click', () => { const key = th.getAttribute('data-sort'); if (sortKey===key) sortDir*=-1; else { sortKey=key; sortDir=-1; } loadSessions(); }));
      document.getElementById('sessList').onclick = loadSessions;
      document.getElementById('sessDetailBtn').onclick = async ()=>{
        try {
          const sid = (document.getElementById('sessDetailId').value||'').trim();
          const n = Math.max(0, parseInt(document.getElementById('sessDetailN').value||'20'));
          if (!sid) { document.getElementById('sessDetailOut').textContent = 'enter session id'; return; }
          const res = await fetch(`/sessions/${encodeURIComponent(sid)}?n_events=${n}`, { headers: getHeaders() });
          const data = await res.json();
          document.getElementById('sessDetailOut').textContent = JSON.stringify(data, null, 2);
        } catch (e) { document.getElementById('sessDetailOut').textContent = 'error'; }
      };
      document.getElementById('sessPrev').onclick = ()=>{ page = Math.max(1, page-1); loadSessions(); };
      document.getElementById('sessNext').onclick = ()=>{ page = Math.max(1, parseInt(document.getElementById('sessPage').value||'1')) + 1; loadSessions(); };
      document.getElementById('sessPage').addEventListener('change', ()=>{ const v = Math.max(1, parseInt(document.getElementById('sessPage').value||'1')); page=v; loadSessions(); });
      document.getElementById('sessPageSize').addEventListener('change', ()=>{ page=1; loadSessions(); });
      document.getElementById('autoSess').onchange = (e)=>{ if (e.target.checked) { const s = Math.max(1, parseInt(document.getElementById('sessInt').value||'5')); timer = setInterval(loadSessions, s*1000); } else if (timer) { clearInterval(timer); timer = null; } };
    })();

    // Events UI
    (function(){
      let timer=null; let page=1; let pageSize=50;
      function pageInfo(total){ const totalPages = Math.max(1, Math.ceil(total / pageSize)); if (page>totalPages) page=totalPages; document.getElementById('evPage').value=String(page); document.getElementById('evPageInfo').textContent = `page ${page}/${totalPages}`; }
      async function loadEvents(){
        try {
          const headers = getHeaders();
          pageSize = Math.max(1, parseInt(document.getElementById('evPageSize').value||'50'));
          const n = pageSize;
          const offset = (page-1)*pageSize;
          const sid = (document.getElementById('evSessFilter').value||'').trim();
          const res = await fetch(`/events/recent?n=${n}&offset=${offset}${sid?`&session_id=${encodeURIComponent(sid)}`:''}`, { headers });
          const data = await res.json();
          const items = data.items||[]; pageInfo(offset + items.length);
          document.getElementById('evOut').textContent = JSON.stringify({ count: items.length, items }, null, 2);
          const sum = await (await fetch(`/events/summary?n=${n}&offset=${offset}${sid?`&session_id=${encodeURIComponent(sid)}`:''}`, { headers })).json();
          document.getElementById('evSummary').textContent = `summary: total=${sum.total} replace=${sum.replaces} ratio=${sum.ratio}`;
        } catch {}
      }
      document.getElementById('evFetch').onclick = loadEvents;
      document.getElementById('evPrev').onclick = ()=>{ page=Math.max(1, page-1); loadEvents(); };
      document.getElementById('evNext').onclick = ()=>{ page = Math.max(1, parseInt(document.getElementById('evPage').value||'1')) + 1; loadEvents(); };
      document.getElementById('evPage').addEventListener('change', ()=>{ const v = Math.max(1, parseInt(document.getElementById('evPage').value||'1')); page=v; loadEvents(); });
      document.getElementById('evPageSize').addEventListener('change', ()=>{ page=1; loadEvents(); });
      const alertsAuto = document.getElementById('alertsAuto'); const alertsInt = document.getElementById('alertsInt');
      alertsAuto.addEventListener('change', ()=>{ if (alertsAuto.checked) { const s = Math.max(2, parseInt(alertsInt.value||'7')); timer=setInterval(loadEvents, s*1000); } else if (timer) { clearInterval(timer); timer=null; } });
    })();

    // Timeline logs UI
    (function(){
      async function loadLogs(){
        try {
          const n = parseInt(document.getElementById('logN').value||'50');
          const t = document.getElementById('logType').value || '';
          const q = `/logs/timeline?n=${n}${t?`&type=${encodeURIComponent(t)}`:''}`;
          const res = await fetch(q, { headers: getHeaders() });
          const data = await res.json();
          document.getElementById('logOut').textContent = JSON.stringify(data, null, 2);
        } catch {}
      }
      document.getElementById('logFetch').onclick = loadLogs;

      async function downloadCsv(){
        try {
          const n = parseInt(document.getElementById('logN').value||'50');
          const t = document.getElementById('logType').value || '';
          const q = `/logs/timeline.csv?n=${n}${t?`&type=${encodeURIComponent(t)}`:''}`;
          const res = await fetch(q, { headers: getHeaders() });
          const blob = await res.blob();
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url; a.download = 'timeline_logs.csv'; document.body.appendChild(a); a.click(); a.remove();
          URL.revokeObjectURL(url);
        } catch {}
      }
      const dl = document.getElementById('logDownloadCsv'); if (dl) dl.onclick = downloadCsv;
    })();
  }

  window.Dashboard = { init: DashboardInit };
})();
