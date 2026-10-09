#!/usr/bin/python3
"""LOUKSNA Linux Bridge desktop control panel.

This is a local status/diagnostics GUI for the bridge package, not a chat client
and not a certification interface. It never executes arbitrary shell commands.
"""
from __future__ import annotations

import subprocess
import tkinter as tk
from tkinter import messagebox
from pathlib import Path
import os
import shutil

APP_NAME = "LOUKSNA Linux Bridge"
VERSION = "0.4.0-3"
SERVICE = "louksna-mtls-readonly.service"
CONFIG = Path("/etc/louksna/remote-bridge/mtls.json")
DOCS = Path("/usr/share/louksna/MTLS_READONLY_GATEWAY.md")
LIVE_DOCS = Path("/usr/share/louksna/LIVE_TRANSPORT.md")


def command(args: list[str], timeout: int = 4) -> tuple[int, str]:
    try:
        result = subprocess.run(args, capture_output=True, text=True,
                                timeout=timeout, check=False)
        return result.returncode, (result.stdout + result.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, str(exc)


class LouksnaApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_NAME} · {VERSION}")
        self.geometry("900x610")
        self.minsize(760, 520)
        self.configure(bg="#101722")
        self._build()
        self.refresh()

    def _build(self) -> None:
        header = tk.Frame(self, bg="#172334", padx=28, pady=22)
        header.pack(fill="x")
        tk.Label(header, text="LOUKSNA", font=("TkDefaultFont", 24, "bold"),
                 fg="#f1f5f9", bg="#172334").pack(anchor="w")
        tk.Label(header, text="Linux Bridge  ·  Panel local  ·  versión " + VERSION,
                 font=("TkDefaultFont", 11), fg="#9fb4ca", bg="#172334").pack(anchor="w", pady=(4, 0))

        body = tk.Frame(self, bg="#101722", padx=28, pady=22)
        body.pack(fill="both", expand=True)
        tk.Label(body, text="Estado del sistema", font=("TkDefaultFont", 16, "bold"),
                 fg="#f1f5f9", bg="#101722").pack(anchor="w", pady=(0, 12))

        self.cards: dict[str, tk.Label] = {}
        grid = tk.Frame(body, bg="#101722")
        grid.pack(fill="x")
        for idx, (key, title) in enumerate((
            ("service", "Servicio mTLS"),
            ("config", "Configuración mTLS"),
            ("cert", "Estado de certificación"),
        )):
            card = tk.Frame(grid, bg="#1c2939", padx=16, pady=14,
                            highlightthickness=1, highlightbackground="#2c4057")
            card.grid(row=0, column=idx, sticky="nsew", padx=(0 if idx == 0 else 10, 0))
            grid.columnconfigure(idx, weight=1)
            tk.Label(card, text=title, font=("TkDefaultFont", 10),
                     fg="#9fb4ca", bg="#1c2939").pack(anchor="w")
            label = tk.Label(card, text="Comprobando…", font=("TkDefaultFont", 12, "bold"),
                             fg="#f1f5f9", bg="#1c2939", wraplength=210, justify="left")
            label.pack(anchor="w", pady=(9, 0))
            self.cards[key] = label

        tk.Label(body, text="Diagnóstico", font=("TkDefaultFont", 16, "bold"),
                 fg="#f1f5f9", bg="#101722").pack(anchor="w", pady=(24, 8))
        self.details = tk.Text(body, height=8, wrap="word", state="disabled",
                               bg="#0b111a", fg="#cbd5e1", insertbackground="#f1f5f9",
                               relief="flat", padx=12, pady=10,
                               font=("TkFixedFont", 10))
        self.details.pack(fill="both", expand=True)

        actions = tk.Frame(body, bg="#101722")
        actions.pack(fill="x", pady=(16, 0))
        self._button(actions, "Actualizar estado", self.refresh, primary=True).pack(side="left")
        self._button(actions, "Ver registros", self.show_logs).pack(side="left", padx=(8, 0))
        self._button(actions, "Guía mTLS", lambda: self.open_doc(DOCS)).pack(side="left", padx=(8, 0))
        self._button(actions, "Transporte local", lambda: self.open_doc(LIVE_DOCS)).pack(side="left", padx=(8, 0))

        tk.Label(body, text="Modo de solo lectura · Sin certificación G23/G24 · Sin control remoto privilegiado",
                 font=("TkDefaultFont", 9), fg="#8295aa", bg="#101722").pack(anchor="w", pady=(12, 0))

    def _button(self, parent, text, callback, primary=False):
        return tk.Button(parent, text=text, command=callback, cursor="hand2",
                         bg="#2d6cdf" if primary else "#253447",
                         fg="#ffffff", activebackground="#3978e8" if primary else "#31465e",
                         activeforeground="#ffffff", relief="flat", padx=12, pady=8,
                         font=("TkDefaultFont", 10, "bold" if primary else "normal"))

    def refresh(self) -> None:
        active_rc, active_out = command(["systemctl", "is-active", SERVICE])
        enabled_rc, enabled_out = command(["systemctl", "is-enabled", SERVICE])
        active = active_out.strip() if active_rc == 0 else "inactivo"
        enabled = enabled_out.strip() if enabled_rc == 0 else "deshabilitado"
        config_ok = CONFIG.is_file()
        self.cards["service"].configure(
            text=f"{active}\nInicio: {enabled}",
            fg="#86efac" if active == "active" else "#fbbf24")
        self.cards["config"].configure(
            text="Presente" if config_ok else "No configurada",
            fg="#86efac" if config_ok else "#fbbf24")
        self.cards["cert"].configure(text="NO CERTIFICADO · G23/G24 pendientes", fg="#fbbf24")

        lines = [
            f"Paquete: louksna-linux-bridge {VERSION}",
            f"Servicio: {SERVICE}",
            f"Estado systemd: {active_out or 'sin respuesta'}",
            f"Inicio automático: {enabled_out or 'sin respuesta'}",
            f"Configuración: {CONFIG} — {'presente' if config_ok else 'ausente'}",
            "",
        ]
        if not config_ok:
            lines += [
                "El servicio mTLS no puede arrancar hasta que exista una configuración válida.",
                "La preparación mTLS es una acción explícita y separada; esta interfaz no la ejecuta automáticamente.",
                "Los archivos de confianza existentes no se modifican desde este panel.",
            ]
        else:
            lines += [
                "La configuración existe. El estado del servicio no demuestra conectividad mTLS.",
                "G23, G24, pruebas de host y validación posarranque siguen siendo independientes.",
            ]
        self.details.configure(state="normal")
        self.details.delete("1.0", "end")
        self.details.insert("1.0", "\n".join(lines))
        self.details.configure(state="disabled")

    def show_logs(self) -> None:
        _, output = command(["journalctl", "-u", SERVICE, "-n", "40", "--no-pager"], timeout=6)
        if not output:
            output = "No hay registros disponibles para este servicio."
        window = tk.Toplevel(self)
        window.title("Registros del servicio · LOUKSNA")
        window.geometry("820x440")
        box = tk.Text(window, wrap="word", bg="#0b111a", fg="#cbd5e1",
                      padx=12, pady=12, font=("TkFixedFont", 10))
        box.pack(fill="both", expand=True)
        box.insert("1.0", output)
        box.configure(state="disabled")

    def open_doc(self, path: Path) -> None:
        target = path if path.is_file() else None
        if target is None:
            messagebox.showwarning("Documento no disponible", f"No se encontró el archivo:\n{path}")
            return
        opener = shutil.which("xdg-open")
        if not opener:
            messagebox.showerror("No disponible", "No se encontró xdg-open en este sistema.")
            return
        try:
            subprocess.Popen([opener, str(target)], stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True)
        except OSError as exc:
            messagebox.showerror("No se pudo abrir", str(exc))


def main() -> None:
    try:
        LouksnaApp().mainloop()
    except tk.TclError as exc:
        print(f"No se pudo abrir la interfaz gráfica: {exc}", file=__import__("sys").stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
