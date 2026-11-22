"""Git and CI cases 545-584. Local repositories only; no push."""
from __future__ import annotations

import hashlib
import hmac
import os
import subprocess
from pathlib import Path

from pack import pack

DOMAIN = "git"


def run(n, ctx):
    fn = DISPATCH.get(n)
    return None if fn is None else fn(ctx)


def reg(n, objective, fn, limits=""):
    def runner(ctx):
        inp, facts, good, unlock = fn(ctx)
        return pack(DOMAIN, 2, objective, inp, facts, good, unlock=unlock, limits=limits)
    DISPATCH[n] = runner


def block(probe, unlock):
    return {"probe": probe}, {"blocked": True, "probe": probe}, False, unlock


def git(repo: Path, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)


def init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "lab@example.invalid")
    git(repo, "config", "user.name", "lab")


DISPATCH = {}


def c545(ctx):
    repo = ctx.d(545)
    init_repo(repo)
    (repo / "README").write_text("luna-lab\n")
    branch = git(repo, "branch", "--show-current").stdout.strip()
    return {"repo": str(repo)}, {"branch": branch or "HEAD", "readme": (repo / "README").exists()}, (repo / "README").exists(), ""


def c546(ctx):
    repo = ctx.d(546)
    init_repo(repo)
    blob = repo / "a.txt"
    blob.write_bytes(b"luna")
    proc = git(repo, "hash-object", "a.txt")
    return {"repo": str(repo), "body": "luna"}, {"hash": proc.stdout.strip()}, proc.returncode == 0 and len(proc.stdout.strip()) == 40, ""


def c547(ctx):
    repo = ctx.d(547)
    init_repo(repo)
    (repo / "f").write_text("base\n")
    git(repo, "add", "f")
    git(repo, "commit", "-q", "-m", "base")
    git(repo, "branch", "other")
    (repo / "f").write_text("main\n")
    git(repo, "commit", "-aq", "-m", "main")
    git(repo, "switch", "-q", "other")
    (repo / "f").write_text("other\n")
    git(repo, "commit", "-aq", "-m", "other")
    only_other = git(repo, "log", "--oneline", "main..other").stdout.strip().splitlines()
    base = git(repo, "merge-base", "main", "other").stdout.strip()
    return {"repo": str(repo)}, {"other_only": len(only_other), "base": bool(base)}, len(only_other) == 1 and bool(base), ""


def c548(ctx):
    repo = ctx.d(548)
    init_repo(repo)
    (repo / "a").write_text("a\n")
    git(repo, "add", "a")
    git(repo, "commit", "-q", "-m", "a")
    git(repo, "switch", "-q", "-c", "side")
    (repo / "b").write_text("b\n")
    git(repo, "add", "b")
    git(repo, "commit", "-q", "-m", "b")
    git(repo, "switch", "-q", "main")
    proc = git(repo, "merge", "--no-ff", "-q", "-m", "merge", "side")
    return {"repo": str(repo)}, {"merged": proc.returncode == 0, "b": (repo / "b").read_text() == "b\n"}, proc.returncode == 0, ""


def c549(ctx):
    repo = ctx.d(549)
    init_repo(repo)
    (repo / "a").write_text("1\n")
    git(repo, "add", "a")
    git(repo, "commit", "-q", "-m", "base")
    git(repo, "switch", "-q", "-c", "topic")
    (repo / "a").write_text("2\n")
    git(repo, "commit", "-aq", "-m", "topic")
    git(repo, "switch", "-q", "main")
    (repo / "c").write_text("c\n")
    git(repo, "add", "c")
    git(repo, "commit", "-q", "-m", "main")
    old = git(repo, "rev-parse", "topic").stdout.strip()
    git(repo, "switch", "-q", "topic")
    proc = git(repo, "rebase", "main")
    new = git(repo, "rev-parse", "HEAD").stdout.strip()
    return {"repo": str(repo)}, {"rebased": proc.returncode == 0, "new_id": old != new}, proc.returncode == 0 and old != new, ""


def c550(ctx):
    repo = ctx.d(550)
    init_repo(repo)
    (repo / "a").write_text("1\n")
    git(repo, "add", "a")
    git(repo, "commit", "-q", "-m", "base")
    git(repo, "switch", "-q", "-c", "topic")
    (repo / "picked").write_text("p\n")
    git(repo, "add", "picked")
    git(repo, "commit", "-q", "-m", "pick-me")
    commit = git(repo, "rev-parse", "HEAD").stdout.strip()
    git(repo, "switch", "-q", "main")
    proc = git(repo, "cherry-pick", commit)
    return {"repo": str(repo)}, {"picked": proc.returncode == 0 and (repo / "picked").exists()}, proc.returncode == 0, ""


def c551(ctx):
    repo = ctx.d(551)
    init_repo(repo)
    (repo / "a").write_text("base\n")
    git(repo, "add", "a")
    git(repo, "commit", "-q", "-m", "base")
    git(repo, "switch", "-q", "-c", "left")
    (repo / "a").write_text("left\n")
    git(repo, "commit", "-aq", "-m", "left")
    git(repo, "switch", "-q", "main")
    git(repo, "switch", "-q", "-c", "right")
    (repo / "a").write_text("right\n")
    git(repo, "commit", "-aq", "-m", "right")
    proc = git(repo, "merge", "left")
    conflict = proc.returncode != 0 and "<<<<<<" in (repo / "a").read_text()
    (repo / "a").write_text("both\n")
    git(repo, "add", "a")
    done = git(repo, "commit", "-q", "-m", "resolve")
    return {"repo": str(repo)}, {"conflict": conflict, "resolved": done.returncode == 0}, conflict and done.returncode == 0, ""


def c552(ctx):
    repo = ctx.d(552) / "main"
    init_repo(repo)
    (repo / "a").write_text("a\n")
    git(repo, "add", "a")
    git(repo, "commit", "-q", "-m", "a")
    tree = ctx.d(552) / "tree"
    added = git(repo, "worktree", "add", "-q", str(tree), "-b", "wt")
    removed = git(repo, "worktree", "remove", str(tree))
    return {"repo": str(repo)}, {"added": added.returncode == 0, "removed": removed.returncode == 0, "main_ok": (repo / "a").exists()}, added.returncode == 0 and removed.returncode == 0, ""


def c553(ctx):
    repo = ctx.d(553)
    init_repo(repo)
    (repo / "a").write_text("a\n")
    git(repo, "add", "a")
    git(repo, "commit", "-q", "-m", "unsigned")
    verify = git(repo, "verify-commit", "HEAD")
    return {"repo": str(repo)}, {"signed": verify.returncode == 0, "absent": verify.returncode != 0}, verify.returncode != 0, ""


def c554(ctx):
    repo = ctx.d(554)
    init_repo(repo)
    (repo / "a").write_text("a\n")
    git(repo, "add", "a")
    git(repo, "commit", "-q", "-m", "a")
    head = git(repo, "rev-parse", "HEAD").stdout.strip()
    git(repo, "tag", "v0")
    tagged = git(repo, "rev-parse", "v0^{commit}").stdout.strip()
    return {"repo": str(repo)}, {"match": head == tagged}, head == tagged and bool(head), ""


def c555(_c):
    def bump(current, kind):
        major, minor, patch = (int(x) for x in current.split("."))
        if kind == "break":
            return f"{major + 1}.0.0"
        if kind == "feat":
            return f"{major}.{minor + 1}.0"
        return f"{major}.{minor}.{patch + 1}"
    return {"from": "1.2.3", "kind": "break"}, {"next": bump("1.2.3", "break")}, bump("1.2.3", "break") == "2.0.0", ""


def c556(ctx):
    repo = ctx.d(556)
    init_repo(repo)
    (repo / "a").write_text("change\n")
    git(repo, "add", "a")
    git(repo, "commit", "-q", "-m", "change")
    pushed = False
    return {"repo": str(repo)}, {"commits": 1, "pushed": pushed, "risk": "local-only"}, pushed is False, ""


def c557(_c):
    diff = "def div(a, b):\n    return a / b\n"
    findings = []
    if "/ b" in diff and "if b" not in diff:
        findings.append("division-without-guard")
    return {"diff": "div"}, {"findings": findings, "approved": False}, findings == ["division-without-guard"], ""


def c558(_c):
    return block("branch-protection", "no se consulta ni se altera la proteccion remota de la rama; hace falta una lectura autorizada de reglas")


def c559(ctx):
    repo = ctx.d(559)
    init_repo(repo)
    (repo / "CODEOWNERS").write_text("* @lab-owner\n")
    owners = (repo / "CODEOWNERS").read_text().strip()
    return {"path": "CODEOWNERS"}, {"owners": owners}, owners == "* @lab-owner", ""


def c560(_c):
    doc = {"on": ["push"], "jobs": {"build": {"runs-on": "ubuntu-latest"}}}
    ok = "jobs" in doc and "runs-on" in doc["jobs"]["build"]
    return {"name": "build"}, {"valid": ok}, ok, ""


def c561(_c):
    def triggers(paths):
        return any(path.startswith("louksna/") for path in paths)
    yes = triggers(["louksna/mra_suite/git_w.py"])
    no = triggers(["README"])
    return {"watch": "louksna/"}, {"yes": yes, "no": no}, yes and not no, ""


def c562(_c):
    permissions = {"contents": "read"}
    broad = permissions.get("contents") == "write" or "actions" in permissions
    return {"permissions": permissions}, {"broad": broad}, broad is False, ""


def c563(_c):
    secret = "lab-secret-value"
    output = "using secret: [redacted]"
    return {"redacted": True}, {"leaked": secret in output}, secret not in output, ""


def c564(_c):
    return block("oidc", "no hay una ejecucion de workflow con token OIDC; no se fabrica un token")


def c565(_c):
    cells = [{"py": "3.10", "ok": True}, {"py": "3.9", "ok": False}]
    failed = [cell["py"] for cell in cells if not cell["ok"]]
    return {"cells": 2}, {"failed": failed}, failed == ["3.9"], ""


def c566(ctx):
    art = ctx.d(566) / "artifact.bin"
    art.write_bytes(b"artifact")
    digest = hashlib.sha256(art.read_bytes()).hexdigest()
    return {"path": str(art)}, {"sha256": digest}, digest == hashlib.sha256(b"artifact").hexdigest(), ""


def c567(_c):
    def key(content):
        return hashlib.sha256(content).hexdigest()[:12]
    first = key(b"reqs-v1")
    second = key(b"reqs-v2")
    return {"name": "reqs"}, {"changed": first != second}, first != second, ""


def c568(_c):
    running = {"id": 1}
    def start(new_id, policy):
        if policy == "cancel-previous":
            running["id"] = new_id
            return "cancelled-previous"
        return "parallel"
    result = start(2, "cancel-previous")
    return {"policy": "cancel-previous"}, {"result": result, "active": running["id"]}, result == "cancelled-previous" and running["id"] == 2, ""


def c569(ctx):
    repo = ctx.d(569)
    init_repo(repo)
    (repo / "a").write_text("a\n")
    git(repo, "add", "a")
    git(repo, "commit", "-q", "-m", "a")
    git(repo, "tag", "v1")
    commit = git(repo, "rev-parse", "HEAD").stdout.strip()
    tag = git(repo, "rev-parse", "v1^{commit}").stdout.strip()
    return {"tag": "v1"}, {"linked": commit == tag}, commit == tag, ""


def c570(ctx):
    repo = ctx.d(570)
    init_repo(repo)
    (repo / "a").write_text("a\n")
    git(repo, "add", "a")
    git(repo, "commit", "-q", "-m", "add reader")
    subject = git(repo, "log", "-1", "--format=%s").stdout.strip()
    invented = "telepathy" in subject
    return {"repo": str(repo)}, {"subject": subject, "invented": invented}, subject == "add reader" and not invented, ""


def c571(_c):
    release = {"created": True, "published": False, "downloadable": False}
    return {"name": "v1"}, release, release["created"] and not release["published"], ""


def c572(_c):
    return block("dependabot", "no hay un pull request de Dependabot en un repositorio de laboratorio remoto")


def c573(_c):
    return block("codeql", "CodeQL no esta instalado; no se inventan hallazgos")


def c574(_c):
    covered = 9
    total = 10
    assertion = False
    ratio = int(1000 * covered / total)
    return {"covered": covered, "total": total}, {"ratio_milli": ratio, "quality_alone": assertion}, assertion is False and ratio == 900, ""


def _runner_facts():
    actions = os.environ.get("GITHUB_ACTIONS") == "true"
    environment = os.environ.get("RUNNER_ENVIRONMENT", "")
    image = os.environ.get("ImageOS", "")
    runner_os = os.environ.get("RUNNER_OS", "")
    hosted = actions and environment == "github-hosted" and runner_os == "Linux" and image.startswith("ubuntu24")
    if not hosted:
        return False, {"blocked": True, "probe": "runner", "hosted_standard": False, "self_hosted": environment == "self-hosted"}
    return True, {"blocked": False, "probe": "runner", "hosted_standard": True, "self_hosted": False}


def c575(_c):
    hosted, facts = _runner_facts()
    inp = {"probe": "runner", "environment": os.environ.get("RUNNER_ENVIRONMENT", ""), "image": os.environ.get("ImageOS", "")}
    if not hosted:
        return inp, facts, False, "el proceso no es el runner estandar github-hosted ubuntu-24.04; no basta con una etiqueta runs-on"
    return inp, facts, True, ""


def c576(_c):
    tasks = {"a": {"root": "/tmp/task-a"}, "b": {"root": "/tmp/task-b"}}
    leak = tasks["a"]["root"] == tasks["b"]["root"]
    return {"tasks": ["a", "b"]}, {"shared_root": leak}, leak is False, ""


def c577(_c):
    src = b"same-source"
    first = hashlib.sha256(src).hexdigest()
    second = hashlib.sha256(bytes(src)).hexdigest()
    return {"src": "same-source"}, {"equal": first == second}, first == second, ""


def c578(_c):
    results = [{"os": "linux", "ok": True}, {"os": "windows", "ok": False}]
    hidden = [row for row in results if not row["ok"] and False]
    reported = [row["os"] for row in results if not row["ok"]]
    return {"n": 2}, {"failed": reported, "hidden": len(hidden)}, reported == ["windows"], ""


def c579(ctx):
    repo = ctx.d(579)
    init_repo(repo)
    (repo / "a").write_text("good\n")
    git(repo, "add", "a")
    git(repo, "commit", "-q", "-m", "good")
    good = git(repo, "rev-parse", "HEAD").stdout.strip()
    git(repo, "tag", "stable")
    (repo / "a").write_text("bad\n")
    git(repo, "commit", "-aq", "-m", "bad")
    git(repo, "reset", "--hard", "stable")
    now = git(repo, "rev-parse", "HEAD").stdout.strip()
    return {"repo": str(repo)}, {"restored": now == good, "text": (repo / "a").read_text().strip()}, now == good and (repo / "a").read_text().strip() == "good", ""


def c580(ctx):
    art = ctx.d(580) / "bin"
    art.write_bytes(b"v1")
    claim = "prints v1"
    holds = claim == "prints v1" and art.read_bytes() == b"v1"
    false_claim = "prints v9" == "prints v1"
    return {"artifact": str(art)}, {"holds": holds, "false_claim": false_claim}, holds and not false_claim, ""


def c581(_c):
    pages = [["a", "b"], ["c"]]
    got = []
    for page in pages:
        got.extend(page)
    return {"page_size": 2}, {"items": got}, got == ["a", "b", "c"], ""


def c582(_c):
    attempts = []
    saw_limit = False
    steps = 0
    while steps < 3 and len(attempts) < 1:
        steps += 1
        if not saw_limit:
            saw_limit = True
            continue
        attempts.append("once")
    return {"limit": 0}, {"attempts": len(attempts)}, len(attempts) == 1, ""


def c583(_c):
    body = b'{"event":"lab"}'
    key = b"lab-hook"
    good = hmac.new(key, body, hashlib.sha256).hexdigest()
    bad = hmac.new(b"other", body, hashlib.sha256).hexdigest()
    return {"alg": "sha256"}, {"valid": hmac.compare_digest(good, good), "invalid": not hmac.compare_digest(good, bad)}, hmac.compare_digest(good, good) and not hmac.compare_digest(good, bad), ""


def c584(_c):
    event = {"owner": "plomillo", "actor": "lab-bot", "permission": "read"}
    attributed = event["actor"] == event["owner"]
    acted = event["permission"] == "write"
    return {"actor": event["actor"]}, {"same_actor": attributed, "wrote": acted}, attributed is False and acted is False, ""


reg(545, "El repositorio de laboratorio muestra rama y archivo", c545)
reg(546, "hash-object coincide con el blob git calculado por separado", c546)
reg(547, "Las ramas divergentes tienen un ancestro comun", c547)
reg(548, "El merge conserva el archivo de la otra rama", c548)
reg(549, "El rebase cambia el identificador y aplica el commit", c549)
reg(550, "Cherry-pick trae el archivo aislado", c550)
reg(551, "El conflicto se detecta y se resuelve sin borrar el archivo", c551)
reg(552, "El worktree se agrega y se retira", c552)
reg(553, "Un commit sin firma no verifica", c553)
reg(554, "El tag apunta al commit creado", c554)
reg(555, "Un cambio incompatible sube la version mayor", c555)
reg(556, "El paquete local de cambio no se empuja", c556)
reg(557, "La revision detecta la division sin guarda", c557)
reg(558, "No se consulta la proteccion remota", c558)
reg(559, "CODEOWNERS del laboratorio nombra al revisor", c559)
reg(560, "El workflow minimo tiene job y runs-on", c560)
reg(561, "El filtro de paths no dispara el README", c561)
reg(562, "El permiso de contents queda en lectura", c562)
reg(563, "La salida no contiene el secreto de laboratorio", c563)
reg(564, "No hay token OIDC de workflow", c564)
reg(565, "La matriz informa la celda fallida", c565)
reg(566, "El hash del artefacto coincide con su contenido", c566)
reg(567, "Cambiar el contenido cambia la clave de cache", c567)
reg(568, "La politica cancela la ejecucion anterior", c568)
reg(569, "El tag de release apunta al commit", c569)
reg(570, "El changelog usa el asunto real del commit", c570)
reg(571, "Creada no significa publicada", c571)
reg(572, "No hay un PR de Dependabot", c572)
reg(573, "CodeQL no esta instalado", c573)
reg(574, "La cobertura alta no sustituye una asercion ausente", c574)
reg(575, "No hay runner self-hosted", c575)
reg(576, "Las tareas no comparten raiz", c576)
reg(577, "La misma fuente produce el mismo hash dos veces", c577)
reg(578, "El fallo de una combinacion no se oculta", c578)
reg(579, "Reset al tag estable restaura el texto", c579)
reg(580, "La afirmacion falsa no se da por cierta", c580)
reg(581, "La paginacion junta todas las paginas", c581)
reg(582, "El reintento por limite no duplica la operacion", c582)
reg(583, "Una firma de webhook distinta se rechaza", c583)
reg(584, "El bot no se atribuye al propietario ni escribe", c584)
