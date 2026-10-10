import { useEffect, useMemo, useState } from "react";
import { invoke } from "@tauri-apps/api/core";

type K="centro"|"repositorios"|"pull-requests"|"evidencia"|"chat-llamada"|"configuracion";
type Settings={offline_mode:boolean;preferred_repo:string;github_owner_filter:string;remote_chat_bridge:string};
type Repo={full_name:string;private:boolean;default_branch:string;updated_at:string;open_issues_count:number};
type PR={number:number;title:string;state:string;draft:boolean;updated_at:string;html_url:string};
type Evidence={id:number;utc:string;operation:string;status:string;detail:string};
type Chat={id:number;utc:string;role:string;content:string;transport:string};
type Conn={connected:boolean;login:string;name:string};

const sections:{key:K,label:string,image:string}[]=[
  {key:"centro",label:"Centro de mando",image:"01_louksna_zona_directiva_centro_de_mando_8k.png"},
  {key:"repositorios",label:"Repositorios",image:"02_louksna_zona_directiva_repositorios_8k.png"},
  {key:"pull-requests",label:"Pull Requests",image:"03_louksna_zona_directiva_pull_requests_8k.png"},
  {key:"evidencia",label:"Evidencia",image:"04_louksna_zona_directiva_evidencia_8k.png"},
  {key:"chat-llamada",label:"Chat / Llamada",image:"05_louksna_zona_directiva_chat_llamada_8k.png"},
  {key:"configuracion",label:"Configuracion",image:"06_louksna_zona_directiva_configuracion_8k.png"}
];

const emptySettings:Settings={offline_mode:false,preferred_repo:"",github_owner_filter:"",remote_chat_bridge:""};

export default function App(){
  const[active,setActive]=useState<K>("centro");
  const[settings,setSettings]=useState<Settings>(emptySettings);
  const[token,setToken]=useState("");
  const[conn,setConn]=useState<Conn|null>(null);
  const[repos,setRepos]=useState<Repo[]>([]);
  const[prs,setPrs]=useState<PR[]>([]);
  const[evidence,setEvidence]=useState<Evidence[]>([]);
  const[chats,setChats]=useState<Chat[]>([]);
  const[msg,setMsg]=useState("");
  const[busy,setBusy]=useState("");
  const[notice,setNotice]=useState("");
  const s=useMemo(()=>sections.find(x=>x.key===active)!,[active]);

  const call=async<T,>(name:string,args?:Record<string,unknown>):Promise<T>=>{
    try{return await invoke<T>(name,args||{})}
    catch(e){throw new Error(String(e))}
  };

  const refreshEvidence=async()=>setEvidence(await call<Evidence[]>("evidence_recent",{limit:100}));

  const refreshConnection=async()=>{
    setBusy("Conectando GitHub...");setNotice("");
    try{
      const c=await call<Conn>("github_connection");
      setConn(c);
      setNotice("GitHub API respondio correctamente.");
    }catch(e){
      setConn(null);
      setNotice("GitHub desconectado: "+(e as Error).message);
    }finally{
      setBusy("");
      await refreshEvidence();
    }
  };

  const refreshRepos=async()=>{
    setBusy("Leyendo repositorios...");setNotice("");
    try{
      const x=await call<Repo[]>("github_repositories");
      setRepos(x);
      setNotice(x.length+" repositorios obtenidos desde GitHub API.");
    }catch(e){
      setNotice("No se pudieron leer repositorios: "+(e as Error).message);
    }finally{
      setBusy("");
      await refreshEvidence();
    }
  };

  const refreshPrs=async()=>{
    const repo=settings.preferred_repo||repos[0]?.full_name||"";
    if(!repo){setNotice("Selecciona un repositorio primero.");return}
    setBusy("Leyendo Pull Requests...");setNotice("");
    try{
      const x=await call<PR[]>("github_pull_requests",{repo});
      setPrs(x);
      setNotice(x.length+" PR abiertos leidos de "+repo+".");
    }catch(e){
      setNotice("No se pudieron leer PR: "+(e as Error).message);
    }finally{
      setBusy("");
      await refreshEvidence();
    }
  };

  const loadChat=async()=>setChats(await call<Chat[]>("chat_history",{limit:100}));

  const sendChat=async()=>{
    if(!msg.trim())return;
    setBusy("Enviando mensaje...");setNotice("");
    try{
      await call<string>("chat_send",{message:msg});
      setMsg("");
      await loadChat();
    }catch(e){
      setNotice("Chat: "+(e as Error).message);
    }finally{
      setBusy("");
      await refreshEvidence();
    }
  };

  const saveSettingsNow=async()=>{
    setBusy("Guardando configuracion...");setNotice("");
    try{
      await call("save_settings",{settings});
      setNotice("Configuracion persistida localmente.");
    }catch(e){
      setNotice("Configuracion: "+(e as Error).message);
    }finally{
      setBusy("");
      await refreshEvidence();
    }
  };

  const saveToken=async()=>{
    if(!token.trim()){setNotice("Introduce un token fine-grained de GitHub.");return}
    setBusy("Guardando credencial...");setNotice("");
    try{
      await call("store_github_token",{token});
      setToken("");
      setNotice("Token guardado en Secret Service. No se almacena en SQLite.");
      await refreshConnection();
    }catch(e){
      setNotice("Credencial: "+(e as Error).message);
    }finally{
      setBusy("");
      await refreshEvidence();
    }
  };

  const disconnect=async()=>{
    setBusy("Desconectando...");
    try{
      await call("remove_github_token");
      setConn(null);
      setRepos([]);
      setPrs([]);
      setNotice("Credencial GitHub eliminada.");
    }catch(e){
      setNotice("Desconexion: "+(e as Error).message);
    }finally{
      setBusy("");
      await refreshEvidence();
    }
  };

  useEffect(()=>{
    (async()=>{
      try{
        setSettings(await call<Settings>("get_settings"));
        await refreshEvidence();
        await loadChat();
      }catch(e){
        setNotice("Backend local: "+String(e));
      }
    })();
  },[]);

  const cards=[
    {title:"Sistema",value:"OPERATIVO",detail:"Backend local real"},
    {title:"GitHub",value:conn?.connected?"CONECTADO":"DESCONECTADO",detail:conn?.connected?"API · "+conn.login:"Sin afirmar sincronizacion"},
    {title:"Evidencia",value:String(evidence.length)+" EVENTOS",detail:"Ledger SQLite real"},
    {title:"Modo",value:settings.offline_mode?"OFFLINE":"ONLINE",detail:"Control explicito"}
  ];

  return <main className="shell">
    <aside className="sidebar">
      <div className="brand"><div className="orb">L</div><div><b>LOUKSNA</b><span>ZONA DIRECTIVA</span></div></div>
      <nav>{sections.map(x=><button key={x.key} onClick={()=>setActive(x.key)} className={active===x.key?"active":""}>{x.label}</button>)}</nav>
      <div className="guard">V0.3 FUNCTIONAL · FAIL CLOSED</div>
    </aside>

    <section className="workspace">
      <header>
        <div><p className="eyebrow">GitHub Interface V0.3 FUNCTIONAL CANDIDATE</p><h1>{s.label}</h1></div>
        <div className="status"><i/> Backend local operativo</div>
      </header>

      {notice&&<div className="notice">{notice}</div>}
      {busy&&<div className="busy">{busy}</div>}

      {active==="centro"&&<>
        <section className="hero">
          <div className="hero-copy">
            <p className="eyebrow">LOUKSNA ONLY</p>
            <h2>Estado real, no decorativo.</h2>
            <p>GitHub solo figura conectado despues de una respuesta API autenticada. Evidencia y configuracion nacen del backend local.</p>
          </div>
          <img src={"/reference/"+s.image} alt="Referencia visual"/>
        </section>
        <section className="cards">{cards.map(c=><article key={c.title}><span>{c.title}</span><strong>{c.value}</strong><small>{c.detail}</small></article>)}</section>
        <section className="grid">
          <article className="panel">
            <h3>Acciones</h3>
            <div className="actions">
              <button onClick={refreshConnection}>Probar GitHub</button>
              <button onClick={refreshRepos}>Actualizar repositorios</button>
              <button onClick={refreshEvidence}>Actualizar evidencia</button>
            </div>
          </article>
          <article className="panel">
            <h3>Identidad</h3>
            <p>LOUKSNA es la unica identidad visible. Los componentes internos no se presentan como personas ni autoridades.</p>
          </article>
        </section>
      </>}

      {active==="repositorios"&&<section className="panel">
        <div className="panel-head">
          <div><h3>Repositorios reales</h3><p>Fuente: GitHub REST API autenticada.</p></div>
          <button onClick={refreshRepos}>Actualizar</button>
        </div>
        <div className="table">
          {repos.length?repos.map(r=><button className="row" key={r.full_name} onClick={()=>setSettings({...settings,preferred_repo:r.full_name})}>
            <b>{r.full_name}</b><span>{r.private?"privado":"publico"}</span><span>{r.default_branch}</span><span>{r.updated_at}</span>
          </button>):<p className="muted">No hay datos cargados. No se simulan repositorios.</p>}
        </div>
      </section>}

      {active==="pull-requests"&&<section className="panel">
        <div className="panel-head">
          <div><h3>Pull Requests reales</h3><p>Repositorio: {settings.preferred_repo||"no seleccionado"}</p></div>
          <button onClick={refreshPrs}>Actualizar</button>
        </div>
        <div className="table">
          {prs.length?prs.map(p=><div className="row" key={p.number}><b>#{p.number} · {p.title}</b><span>{p.draft?"draft":p.state}</span><span>{p.updated_at}</span></div>):<p className="muted">No hay PR cargados.</p>}
        </div>
      </section>}

      {active==="evidencia"&&<section className="panel">
        <div className="panel-head">
          <div><h3>Ledger local</h3><p>Eventos escritos por el backend. No es telemetria simulada.</p></div>
          <button onClick={refreshEvidence}>Actualizar</button>
        </div>
        <div className="evidence">
          {evidence.map(e=><div className="e-row" key={e.id}><b>{e.operation}</b><span className={e.status==="PASS"?"ok":"warn"}>{e.status}</span><small>{e.utc}</small><p>{e.detail}</p></div>)}
        </div>
      </section>}

      {active==="chat-llamada"&&<section className="chat-grid">
        <article className="panel chat">
          <h3>Chat gobernado</h3>
          <div className="messages">
            {chats.map(c=><div key={c.id} className={"bubble "+c.role}><b>{c.role==="user"?"Tu":"LOUKSNA"}</b><p>{c.content}</p><small>{c.transport}</small></div>)}
          </div>
          <div className="composer">
            <textarea value={msg} onChange={e=>setMsg(e.target.value)} placeholder="Escribe a LOUKSNA..."/>
            <button onClick={sendChat}>Enviar</button>
          </div>
        </article>
        <article className="panel">
          <h3>Llamada / voz</h3>
          <p>La pila de voz end-to-end todavia no esta certificada. No se presenta como activa.</p>
          <button disabled>Microfono — gate abierto</button>
          <h3>Bridge remoto</h3>
          <p>{settings.remote_chat_bridge?"Configurado: el round-trip se valida por mensaje.":"No configurado. El chat seguira local y lo declarara explicitamente."}</p>
        </article>
      </section>}

      {active==="configuracion"&&<section className="grid">
        <article className="panel form">
          <h3>Configuracion persistente</h3>
          <label><input type="checkbox" checked={settings.offline_mode} onChange={e=>setSettings({...settings,offline_mode:e.target.checked})}/> Modo offline</label>
          <label>Repositorio preferido<input value={settings.preferred_repo} onChange={e=>setSettings({...settings,preferred_repo:e.target.value})} placeholder="owner/repo"/></label>
          <label>Filtro de propietario<input value={settings.github_owner_filter} onChange={e=>setSettings({...settings,github_owner_filter:e.target.value})} placeholder="Plomillo"/></label>
          <label>Bridge remoto de chat<input value={settings.remote_chat_bridge} onChange={e=>setSettings({...settings,remote_chat_bridge:e.target.value})} placeholder="https://..."/></label>
          <button onClick={saveSettingsNow}>Guardar configuracion</button>
        </article>
        <article className="panel form">
          <h3>GitHub</h3>
          <p>El token se guarda mediante Secret Service/libsecret y nunca se recupera hacia la interfaz.</p>
          <label>Fine-grained token<input type="password" value={token} onChange={e=>setToken(e.target.value)} autoComplete="off"/></label>
          <button onClick={saveToken}>Guardar token seguro</button>
          <button className="danger" onClick={disconnect}>Eliminar token / desconectar</button>
          <p className="muted">Permisos iniciales recomendados: metadata/read, contents/read, pull_requests/read, actions/read.</p>
        </article>
      </section>}
    </section>
  </main>
}
