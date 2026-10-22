from __future__ import annotations
import json, os, platform, queue, subprocess, sys, threading, tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

NAVY="#183247"; PAPER="#F5F3EE"; CARD="#FFFFFF"; INK="#1E2A30"; MUTED="#61727B"; GOLD="#B28A52"

class WorkbenchGUI(tk.Tk):
    """Local desktop interface; no file upload, cloud call, or shell-based execution."""
    def __init__(self):
        super().__init__()
        self.title("Louksna Document Workbench · Laboratorio editorial")
        self.geometry("1040x730"); self.minsize(860,600); self.configure(bg=PAPER)
        self.source=tk.StringVar(); self.outdir=tk.StringVar()
        self.status=tk.StringVar(value="Listo · selecciona un PDF")
        self.events=queue.Queue(); self.busy=False; self.last_output=None
        self._style(); self._layout(); self.after(100,self._poll)

    def _style(self):
        s=ttk.Style(self)
        try: s.theme_use("clam")
        except tk.TclError: pass
        s.configure("TFrame",background=PAPER); s.configure("Card.TFrame",background=CARD)
        s.configure("TLabel",background=PAPER,foreground=INK,font=("Segoe UI",10))
        s.configure("CardTitle.TLabel",background=CARD,foreground=NAVY,font=("Segoe UI Semibold",12))
        s.configure("Muted.TLabel",background=PAPER,foreground=MUTED,font=("Segoe UI",9))
        s.configure("TEntry",padding=7); s.configure("TButton",padding=(11,8),font=("Segoe UI Semibold",9))
        s.configure("Primary.TButton",background=NAVY,foreground="#FFFFFF")
        s.map("Primary.TButton",background=[("active","#24475D"),("disabled","#A8B3B9")])
        s.configure("Gold.TButton",background=GOLD,foreground="#FFFFFF")
        s.map("Gold.TButton",background=[("active","#9E7645")])
        s.configure("Secondary.TButton",background="#E7ECEE",foreground=NAVY)

    def _layout(self):
        head=tk.Frame(self,bg=NAVY,padx=26,pady=20); head.pack(fill="x")
        tk.Label(head,text="LOUKSNA DOCUMENT WORKBENCH",bg=NAVY,fg="#FFFFFF",font=("Segoe UI Semibold",20)).pack(anchor="w")
        tk.Label(head,text="Laboratorio editorial · PDF académico · procesamiento local",bg=NAVY,fg="#DDE6EA",font=("Segoe UI",10)).pack(anchor="w",pady=(5,0))
        body=ttk.Frame(self,padding=(22,16,22,12)); body.pack(fill="both",expand=True)
        src=ttk.Frame(body,style="Card.TFrame",padding=14); src.pack(fill="x",pady=(0,12))
        ttk.Label(src,text="Documento de trabajo",style="CardTitle.TLabel").grid(row=0,column=0,columnspan=3,sticky="w",pady=(0,8))
        ttk.Label(src,text="Archivo PDF").grid(row=1,column=0,sticky="w",padx=(0,8))
        ttk.Entry(src,textvariable=self.source).grid(row=1,column=1,sticky="ew",padx=(0,8))
        ttk.Button(src,text="Examinar…",command=self._browse).grid(row=1,column=2)
        ttk.Label(src,text="Carpeta de salida").grid(row=2,column=0,sticky="w",padx=(0,8),pady=(8,0))
        ttk.Entry(src,textvariable=self.outdir).grid(row=2,column=1,sticky="ew",padx=(0,8),pady=(8,0))
        ttk.Button(src,text="Elegir…",command=self._browse_out).grid(row=2,column=2,pady=(8,0)); src.columnconfigure(1,weight=1)
        cards=ttk.Frame(body); cards.pack(fill="x",pady=(0,12))
        for n in range(3): cards.columnconfigure(n,weight=1,uniform="a")
        self._card(cards,0,"01 · DIAGNÓSTICO","Detecta folios y continuidad; no mueve páginas.","Analizar orden",self._analyse,"Secondary.TButton")
        self._card(cards,1,"02 · ORDEN SEGURO","Reordena solo si los folios prueban una permutación completa.","Verificar y ordenar",self._order,"Primary.TButton")
        self._card(cards,2,"03 · LECTURA ACADÉMICA","PDF con jerarquía tipográfica, índice y referencias al original.","Crear edición",self._academic,"Gold.TButton")
        row=ttk.Frame(body); row.pack(fill="x",pady=(0,8))
        self.progress=ttk.Progressbar(row,mode="indeterminate"); self.progress.pack(side="left",fill="x",expand=True,padx=(0,8))
        ttk.Button(row,text="Abrir último resultado",command=self._open,style="Secondary.TButton").pack(side="right")
        ttk.Label(body,textvariable=self.status,foreground=NAVY,font=("Segoe UI Semibold",10)).pack(anchor="w",pady=(0,7))
        log_card=ttk.Frame(body,style="Card.TFrame",padding=11); log_card.pack(fill="both",expand=True)
        ttk.Label(log_card,text="Registro de operaciones",style="CardTitle.TLabel").pack(anchor="w",pady=(0,6))
        self.log=tk.Text(log_card,wrap="word",bg="#FBFCFB",fg=INK,relief="flat",padx=10,pady=9,font=("Consolas",9),state="disabled")
        self.log.pack(fill="both",expand=True); self.log.tag_configure("error",foreground="#A13737")
        ttk.Label(body,text="Privacidad: los documentos permanecen en el equipo; no se cargan a servicios externos.",style="Muted.TLabel").pack(anchor="w",pady=(7,0))

    def _card(self,parent,n,title,desc,label,callback,style):
        card=ttk.Frame(parent,style="Card.TFrame",padding=12)
        card.grid(row=0,column=n,sticky="nsew",padx=(0 if n==0 else 6,6 if n<2 else 0))
        ttk.Label(card,text=title,style="CardTitle.TLabel").pack(anchor="w",pady=(0,6))
        ttk.Label(card,text=desc,background=CARD,foreground=MUTED,wraplength=225,justify="left").pack(anchor="w",fill="x",pady=(0,12))
        button=ttk.Button(card,text=label,command=callback,style=style); button.pack(fill="x"); setattr(self,f"b{n}",button)

    def _browse(self):
        path=filedialog.askopenfilename(title="Seleccionar PDF",filetypes=[("PDF","*.pdf")])
        if path:
            self.source.set(path)
            if not self.outdir.get(): self.outdir.set(str(Path(path).resolve().parent/"louksna-output"))

    def _browse_out(self):
        path=filedialog.askdirectory(title="Carpeta de salida")
        if path: self.outdir.set(path)

    def _paths(self):
        src=Path(self.source.get()).expanduser().resolve()
        if not src.is_file() or src.suffix.lower()!=".pdf": raise ValueError("Selecciona un PDF existente.")
        dest=Path(self.outdir.get()).expanduser().resolve() if self.outdir.get() else src.parent/"louksna-output"
        dest.mkdir(parents=True,exist_ok=True); return src,dest

    def _unique(self,path):
        if not path.exists(): return path
        for n in range(2,10000):
            candidate=path.with_name(f"{path.stem}_{n}{path.suffix}")
            if not candidate.exists(): return candidate
        raise FileExistsError("No hay un nombre de salida libre.")

    def _cli(self,*args):
        result=subprocess.run([sys.executable,"-m","louksna_docworkbench.cli",*args],capture_output=True,text=True,timeout=3600,shell=False)
        out=result.stdout.strip()
        if result.returncode: raise RuntimeError((result.stderr.strip() or out or "La operación falló.")[-4000:])
        return json.loads(out)

    def _launch(self,label,worker):
        if self.busy: return
        self.busy=True; self.progress.start(10); self.status.set("En curso · "+label)
        for n in range(3): getattr(self,f"b{n}").configure(state="disabled")
        def run():
            try: self.events.put(("ok",(label,*worker())))
            except Exception as exc: self.events.put(("error",(label,str(exc))))
        threading.Thread(target=run,daemon=True).start()

    def _analyse(self):
        def work():
            src,d=self._paths(); report=self._unique(d/f"{src.stem}_analisis_orden.json")
            r=self._cli("analyze-order",str(src),"--audit",str(report))
            return report,f"Estado: {r['status']}\nRecomendación: {r['recommendation']} · {r['confidence']}\nFolios: {r['printed_folio_detection']['detected_pages']}/{r['page_count']}\n{r['explanation']}"
        self._launch("análisis de orden",work)

    def _order(self):
        def work():
            src,d=self._paths(); analysis=self._unique(d/f"{src.stem}_analisis_orden.json")
            audit=self._unique(d/f"{src.stem}_aplicacion_orden.json"); pdf=self._unique(d/f"{src.stem}_orden_verificado.pdf")
            a=self._cli("analyze-order",str(src),"--audit",str(analysis))
            r=self._cli("order-from-folios",str(src),str(pdf),"--analysis",str(analysis),"--audit",str(audit))
            return pdf,f"Análisis: {a['recommendation']}\nResultado: {r['status']}\nPáginas movidas: {r['page_order_changed']}\nSHA-256: {r['output_sha256']}\n{r['order_evidence']['explanation']}"
        self._launch("verificación del orden",work)

    def _academic(self):
        def work():
            src,d=self._paths(); analysis=self._unique(d/f"{src.stem}_analisis_orden.json")
            audit=self._unique(d/f"{src.stem}_edicion_lectura.audit.json"); pdf=self._unique(d/f"{src.stem}_edicion_lectura.pdf")
            self._cli("analyze-order",str(src),"--audit",str(analysis))
            r=self._cli("academic-edition",str(src),str(pdf),"--analysis",str(analysis),"--audit",str(audit))
            return pdf,f"Estado: {r['status']}\nReferencias cruzadas: {r['source_page_markers_verified']}/{r['input_page_count']}\nEntradas de índice: {r['chapter_and_part_navigation_entries']}\nPáginas de lectura: {r['output_page_count']}\nSHA-256: {r['output_sha256']}\nTraducción y terminología clínica: revisión humana pendiente."
        self._launch("edición académica",work)

    def _open(self):
        if not self.last_output or not self.last_output.exists():
            messagebox.showinfo("Sin resultado","Genera primero un resultado."); return
        try:
            if os.name=="nt": os.startfile(str(self.last_output))
            elif platform.system()=="Darwin": subprocess.Popen(["open",str(self.last_output)],shell=False)
            else: subprocess.Popen(["xdg-open",str(self.last_output)],shell=False)
        except Exception as exc: messagebox.showerror("No se pudo abrir",str(exc))

    def _log(self,text,tag=""):
        self.log.configure(state="normal"); self.log.insert("end",text+"\n\n",tag); self.log.see("end"); self.log.configure(state="disabled")

    def _poll(self):
        try:
            while True:
                kind,payload=self.events.get_nowait(); self.busy=False; self.progress.stop()
                for n in range(3): getattr(self,f"b{n}").configure(state="normal")
                if kind=="ok":
                    label,output,summary=payload; self.last_output=output; self.status.set("Terminado · "+label)
                    self._log(label.upper()+"\n"+summary+"\nSalida: "+str(output))
                else:
                    label,detail=payload; self.status.set("Falló · "+label); self._log(label.upper()+"\n"+detail,"error")
        except queue.Empty: pass
        self.after(100,self._poll)

def main() -> int:
    WorkbenchGUI().mainloop()
    return 0

if __name__=="__main__":
    raise SystemExit(main())
