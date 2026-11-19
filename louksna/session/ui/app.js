const sections = [
  {key:"centro", label:"Centro de mando", image:"01_louksna_zona_directiva_centro_de_mando_8k.png"},
  {key:"repositorios", label:"Repositorios", image:"02_louksna_zona_directiva_repositorios_8k.png"},
  {key:"pull-requests", label:"Pull Requests", image:"03_louksna_zona_directiva_pull_requests_8k.png"},
  {key:"evidencia", label:"Evidencia", image:"04_louksna_zona_directiva_evidencia_8k.png"},
  {key:"chat-llamada", label:"Chat / Llamada", image:"05_louksna_zona_directiva_chat_llamada_8k.png"},
  {key:"configuracion", label:"Configuracion", image:"06_louksna_zona_directiva_configuracion_8k.png"}
];
const state = {active:"centro", settings:{offline_mode:false,preferred_repo:"",github_owner_filter:"",remote_chat_bridge:""}, token:"", conn:null, repos:[], prs:[], evidence:[], chats:[], msg:"", busy:"", notice:"", plans:null, sessions:null, probe:null};
const headers = {"Content-Type":"application/json","X-Louksna-Client":"luna"};
async function api(path, opts){
  const res = await fetch(path, Object.assign({headers}, opts||{}));
  const body = await res.json().catch(()=>({error:"JSON"}));
  if(!res.ok || body.error) throw new Error(body.error || ("HTTP "+res.status));
  return body;
}
function el(html){ const t=document.createElement("template"); t.innerHTML=html.trim(); return t.content.firstChild; }
function esc(s){ return String(s??"").replace(/[&<>"']/g, c => ({'&':'&','<':'<','>':'>','"':'"',"'":'&#39;'}[c])); }
async function refreshEvidence(){ state.evidence = await api("/api/evidence"); }
async function refreshConnection(){
  state.busy="Conectando GitHub..."; state.notice=""; render();
  try{ state.conn=await api("/api/github/connection"); state.notice="GitHub API respondio correctamente."; }
  catch(e){ state.conn=null; state.notice="GitHub desconectado: "+e.message; }
  finally{ state.busy=""; await refreshEvidence(); render(); }
}
async function refreshRepos(){
  state.busy="Leyendo repositorios..."; state.notice=""; render();
  try{ state.repos=await api("/api/github/repos"); state.notice=state.repos.length+" repositorios obtenidos desde GitHub API."; }
  catch(e){ state.notice="No se pudieron leer repositorios: "+e.message; }
  finally{ state.busy=""; await refreshEvidence(); render(); }
}
async function refreshPrs(){
  const repo=state.settings.preferred_repo||state.repos[0]?.full_name||"";
  if(!repo){ state.notice="Selecciona un repositorio primero."; render(); return; }
  state.busy="Leyendo Pull Requests..."; state.notice=""; render();
  try{ state.prs=await api("/api/github/pulls?repo="+encodeURIComponent(repo)); state.notice=state.prs.length+" PR abiertos leidos de "+repo+"."; }
  catch(e){ state.notice="No se pudieron leer PR: "+e.message; }
  finally{ state.busy=""; await refreshEvidence(); render(); }
}
async function loadChat(){ state.chats=await api("/api/chat"); }
async function sendChat(){
  if(!state.msg.trim()) return;
  state.busy="Enviando mensaje..."; state.notice=""; render();
  try{ await api("/api/chat",{method:"POST",body:JSON.stringify({message:state.msg})}); state.msg=""; await loadChat(); }
  catch(e){ state.notice="Chat: "+e.message; }
  finally{ state.busy=""; await refreshEvidence(); render(); }
}
async function saveSettingsNow(){
  state.busy="Guardando configuracion..."; state.notice=""; render();
  try{ await api("/api/settings",{method:"POST",body:JSON.stringify(state.settings)}); state.notice="Configuracion persistida localmente."; }
  catch(e){ state.notice="Configuracion: "+e.message; }
  finally{ state.busy=""; await refreshEvidence(); render(); }
}
async function saveToken(){
  if(!state.token.trim()){ state.notice="Introduce un token de instalacion ghs_ o una clave PEM de GitHub App."; render(); return; }
  state.busy="Guardando credencial..."; state.notice=""; render();
  try{ await api("/api/token",{method:"POST",body:JSON.stringify({token:state.token})}); state.token=""; state.notice="Credencial guardada fuera de SQLite con modo 0600. Un PAT permanente es rechazado."; await refreshConnection(); }
  catch(e){ state.notice="Credencial: "+e.message; state.busy=""; await refreshEvidence(); render(); }
}
async function disconnect(){
  state.busy="Desconectando..."; render();
  try{ await api("/api/token/remove",{method:"POST",body:"{}"}); state.conn=null; state.repos=[]; state.prs=[]; state.notice="Credencial GitHub eliminada."; }
  catch(e){ state.notice="Desconexion: "+e.message; }
  finally{ state.busy=""; await refreshEvidence(); render(); }
}
async function voice(action){
  state.busy="Voz..."; render();
  try{
    if(action==="start") await api("/api/voice/session",{method:"POST",body:JSON.stringify({state:"ACTIVE"})});
    if(action==="stop") await api("/api/voice/session",{method:"POST",body:JSON.stringify({state:"STOPPED"})});
    if(action==="speak") await api("/api/voice/speak",{method:"POST",body:JSON.stringify({text:state.msg||"Hola. Soy Luna."})});
    state.sessions=await api("/api/sessions");
    state.notice="Sesion de voz operativa. Speaker 1 obligatorio.";
  }catch(e){ state.notice="Voz: "+e.message; }
  finally{ state.busy=""; await refreshEvidence(); render(); }
}
async function plan(action){
  state.busy="Plan..."; render();
  try{
    if(action==="create") await api("/api/plans",{method:"POST",body:JSON.stringify({title:"operacion",scope:["record"]})});
    if(action==="list") state.plans=await api("/api/plans");
    state.notice="Plan persistido. La aprobacion es unica por plan.";
  }catch(e){ state.notice="Plan: "+e.message; }
  finally{ state.busy=""; render(); }
}
function render(){
  const s=sections.find(x=>x.key===state.active);
  const root=document.getElementById("app");
  const cards=[
    {title:"Sistema",value:state.probe?.status||"…",detail:"Backend local real"},
    {title:"GitHub",value:state.conn?.connected?"CONECTADO":"DESCONECTADO",detail:state.conn?.connected?"API · "+state.conn.login:"Sin afirmar sincronizacion"},
    {title:"Evidencia",value:String(state.evidence.length)+" EVENTOS",detail:"Ledger SQLite real"},
    {title:"Modo",value:state.settings.offline_mode?"OFFLINE":"ONLINE",detail:"Control explicito"}
  ];
  root.innerHTML=`
    <aside class="sidebar">
      <div class="brand"><div class="orb"></div><div><b>LOUKSNA</b><span>ZONA DIRECTIVA</span></div></div>
      <nav>${sections.map(x=>`<button data-k="${x.key}" class="${state.active===x.key?"active":""}">${x.label}</button>`).join("")}</nav>
      <div class="guard">V0.3 FUNCTIONAL · LUNA 3.0 · NOT CERTIFIED</div>
    </aside>
    <section class="workspace">
      <header><div><p class="eyebrow">GitHub Interface V0.3 FUNCTIONAL</p><h1>${s.label}</h1></div><div class="status">Backend local operativo</div></header>
      ${state.notice?`<div class="notice">${esc(state.notice)}</div>`:""}
      ${state.busy?`<div class="busy">${esc(state.busy)}</div>`:""}
      <div id="view"></div>
    </section>`;
  root.querySelectorAll("nav button").forEach(b=>b.onclick=()=>{state.active=b.dataset.k; render();});
  const view=root.querySelector("#view");
  if(state.active==="centro"){
    view.append(el(`<section class="hero"><div class="hero-copy"><p class="eyebrow">LOUKSNA ONLY</p><h2>Estado real, no decorativo.</h2><p>GitHub solo figura conectado despues de una respuesta API autenticada. Evidencia y configuracion nacen del backend local. Identidad unica: LUNA.</p></div><img src="/reference/${s.image}" alt="Referencia visual"/></section>`));
    view.append(el(`<section class="cards">${cards.map(c=>`<article><span>${c.title}</span><strong>${esc(c.value)}</strong><small>${esc(c.detail)}</small></article>`).join("")}</section>`));
    const panel=el(`<section class="grid"><article class="panel"><h3>Acciones</h3><div class="actions"><button id="gh">Probar GitHub</button><button id="plan">Crear plan</button><button id="plans">Ver planes</button></div><pre class="muted">${esc(JSON.stringify(state.plans||{},null,2))}</pre></article><article class="panel"><h3>Capas</h3><p>${state.probe?esc(state.probe.layers)+" capas · "+esc(state.probe.voice_primary):""}</p><p>Certificacion: ${esc(state.probe?.certification||"NOT_CERTIFIED")}</p></article></section>`);
    view.append(panel);
    panel.querySelector("#gh").onclick=refreshConnection;
    panel.querySelector("#plan").onclick=()=>plan("create");
    panel.querySelector("#plans").onclick=()=>plan("list");
  }
  if(state.active==="repositorios"){
    const panel=el(`<section class="panel"><div class="actions"><button id="r">Leer repositorios</button></div><div class="table">${state.repos.map(r=>`<div class="row"><b>${esc(r.full_name)}</b><span>${esc(r.default_branch)}</span><span class="muted">${esc(r.updated_at)}</span></div>`).join("")||"<p class=\"muted\">Sin datos de API.</p>"}</div></section>`);
    view.append(panel); panel.querySelector("#r").onclick=refreshRepos;
  }
  if(state.active==="pull-requests"){
    const panel=el(`<section class="panel"><div class="actions"><button id="p">Leer Pull Requests</button></div><div class="table">${state.prs.map(r=>`<div class="row"><b>#${esc(r.number)} ${esc(r.title)}</b><span>${esc(r.state)}</span></div>`).join("")||"<p class=\"muted\">Sin PR leidos.</p>"}</div></section>`);
    view.append(panel); panel.querySelector("#p").onclick=refreshPrs;
  }
  if(state.active==="evidencia"){
    view.append(el(`<section class="panel"><div class="actions"><button id="e">Actualizar</button></div><div class="evidence">${state.evidence.map(e=>`<div class="e-row"><b>${esc(e.operation)}</b><span class="${e.status==="PASS"?"ok":"warn"}">${esc(e.status)}</span><small>${esc(e.utc)}</small><p>${esc(e.detail)}</p></div>`).join("")}</div></section>`));
    view.querySelector("#e").onclick=async()=>{await refreshEvidence(); render();};
  }
  if(state.active==="chat-llamada"){
    const panel=el(`<section class="chat-grid"><article class="panel"><div class="messages">${state.chats.map(c=>`<div class="bubble ${c.role==="user"?"user":""}"><small>${esc(c.role)} · ${esc(c.transport)}</small><p>${esc(c.content)}</p></div>`).join("")}</div><div class="composer"><textarea id="msg">${esc(state.msg)}</textarea><button id="send">Enviar</button></div></article><article class="panel"><h3>Llamada persistente</h3><p>La sesion de voz permanece mientras hay tareas. Piper Sharvard, speaker 1. Sin respuesta simulada.</p><div class="actions"><button id="vs">Iniciar voz</button><button id="sp">Hablar</button><button id="vx">Cerrar voz</button></div><pre class="muted">${esc(JSON.stringify(state.sessions||{},null,2))}</pre></article></section>`);
    view.append(panel);
    const msg=panel.querySelector("#msg");
    msg.oninput=()=>{state.msg=msg.value;};
    panel.querySelector("#send").onclick=sendChat;
    panel.querySelector("#vs").onclick=()=>voice("start");
    panel.querySelector("#sp").onclick=()=>voice("speak");
    panel.querySelector("#vx").onclick=()=>voice("stop");
  }
  if(state.active==="configuracion"){
    const panel=el(`<section class="grid"><article class="panel"><h3>Configuracion</h3><div class="form">
      <label><input id="off" type="checkbox" ${state.settings.offline_mode?"checked":""}/> Modo offline</label>
      <label>Repositorio preferido<input id="repo" value="${esc(state.settings.preferred_repo)}" placeholder="owner/repo"/></label>
      <label>Filtro de propietario<input id="own" value="${esc(state.settings.github_owner_filter)}" placeholder="Plomillo"/></label>
      <label>Bridge remoto de chat<input id="br" value="${esc(state.settings.remote_chat_bridge)}" placeholder="https://..."/></label>
      <button id="sv">Guardar</button></div></article>
      <article class="panel"><h3>GitHub App</h3><div class="form"><label>Token de instalacion o PEM<input id="tk" type="password" autocomplete="off" value="${esc(state.token)}"/></label><button id="st">Guardar credencial</button><button id="rm" class="danger">Eliminar credencial</button></div><p class="muted">No se acepta un PAT permanente. El valor no entra en SQLite.</p></article></section>`);
    view.append(panel);
    panel.querySelector("#off").onchange=e=>{state.settings.offline_mode=e.target.checked;};
    panel.querySelector("#repo").oninput=e=>{state.settings.preferred_repo=e.target.value;};
    panel.querySelector("#own").oninput=e=>{state.settings.github_owner_filter=e.target.value;};
    panel.querySelector("#br").oninput=e=>{state.settings.remote_chat_bridge=e.target.value;};
    panel.querySelector("#tk").oninput=e=>{state.token=e.target.value;};
    panel.querySelector("#sv").onclick=saveSettingsNow;
    panel.querySelector("#st").onclick=saveToken;
    panel.querySelector("#rm").onclick=disconnect;
  }
}
async function boot(){
  try{
    state.settings=await api("/api/settings");
    state.probe=await api("/api/probe");
    await refreshEvidence();
    await loadChat();
  }catch(e){ state.notice="Backend local: "+e.message; }
  render();
}
boot();
