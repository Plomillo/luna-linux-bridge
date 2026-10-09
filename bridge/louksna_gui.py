#!/usr/bin/python3
"""Louksna Linux Bridge desktop control panel.

This UI controls only the packaged read-only mTLS service. It does not expose
remote ingress, execute arbitrary commands, or create trust material silently.
"""
import subprocess
import tkinter as tk
from tkinter import messagebox
from pathlib import Path

SERVICE = "louksna-mtls-readonly.service"
CONFIG = Path("/etc/louksna/remote-bridge/mtls.json")
DOC = Path("/usr/share/louksna/MTLS_READONLY_GATEWAY.md")
LOG_DOC = Path("/usr/share/louksna/LIVE_TRANSPORT.md")


def run(args, timeout=8):
    try:
        p = subprocess.run(args, text=True, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=timeout, check=False)
        return p.returncode, p.stdout.strip()
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, str(exc)


class LouksnaUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Louksna — Linux Bridge")
        self.geometry("680x440")
        self.minsize(580, 380)
        self.configure(padx=20, pady=18)
        tk.Label(self, text="LOUKSNA", font=("Sans", 22, "bold")).pack(anchor="w")
        tk.Label(self, text="Puente local de solo lectura · mTLS", font=("Sans", 11)).pack(anchor="w", pady=(0, 14))
        self.status = tk.StringVar(value="Consultando estado…")
        tk.Label(self, textvariable=self.status, font=("Sans", 12, "bold"),
                 anchor="w", justify="left", wraplength=630).pack(fill="x", pady=5)
        self.details = tk.StringVar()
        tk.Label(self, textvariable=self.details, anchor="w", justify="left",
                 wraplength=630).pack(fill="x", pady=(0, 14))
        actions = tk.Frame(self)
        actions.pack(anchor="w", pady=4)
        tk.Button(actions, text="Actualizar estado", command=self.refresh).pack(side="left", padx=(0, 8))
        tk.Button(actions, text="Iniciar servicio", command=lambda: self.control("start")).pack(side="left", padx=8)
        tk.Button(actions, text="Detener servicio", command=lambda: self.control("stop")).pack(side="left", padx=8)
        tk.Button(actions, text="Ver registros", command=self.logs).pack(side="left", padx=8)
        tk.Label(self, text="Seguridad: esta interfaz no activa acceso remoto. El servicio requiere configuración mTLS provisionada explícitamente.",
                 wraplength=630, justify="left", anchor="w").pack(fill="x", pady=(18, 8))
        tk.Label(self, text="La instalación no crea certificados ni habilita el servicio automáticamente.",
                 wraplength=630, justify="left", anchor="w").pack(fill="x")
        self.refresh()

    def refresh(self):
        _, active = run(["systemctl", "is-active", SERVICE])
        _, enabled = run(["systemctl", "is-enabled", SERVICE])
        has_config = CONFIG.is_file()
        if active == "active":
            state = "Servicio: ACTIVO"
        elif active == "failed":
            state = "Servicio: FALLÓ"
        else:
            state = "Servicio: INACTIVO"
        self.status.set(state)
        self.details.set(
            f"Arranque automático: {enabled or 'desconocido'}\n"
            f"Configuración mTLS: {'presente' if has_config else 'no encontrada'}\n"
            + ("" if has_config else "Acción necesaria: provisionar la configuración mTLS antes de iniciar el servicio.")
        )

    def control(self, action):
        if action == "start" and not CONFIG.is_file():
            messagebox.showwarning("Falta configuración mTLS",
                "No se iniciará el servicio: falta /etc/louksna/remote-bridge/mtls.json.\n\n"
                "La provisión de certificados debe realizarse explícitamente y revisando la política local.")
            return
        answer = messagebox.askyesno("Confirmar acción",
            ("¿Iniciar" if action == "start" else "¿Detener") + " el servicio Louksna?")
        if not answer:
            return
        code, out = run(["pkexec", "/usr/bin/systemctl", action, SERVICE], timeout=60)
        if code != 0:
            messagebox.showerror("No se pudo completar la acción", out or "La operación fue rechazada.")
        self.after(250, self.refresh)

    def logs(self):
        code, out = run(["journalctl", "-u", SERVICE, "-n", "80", "--no-pager"], timeout=10)
        win = tk.Toplevel(self)
        win.title("Louksna — Registros del servicio")
        win.geometry("760x480")
        box = tk.Text(win, wrap="word")
        box.pack(fill="both", expand=True)
        box.insert("1.0", out or "No hay registros disponibles.")
        box.configure(state="disabled")


if __name__ == "__main__":
    LouksnaUI().mainloop()
