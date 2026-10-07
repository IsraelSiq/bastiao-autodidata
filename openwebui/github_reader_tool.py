"""
title: GitHub Reader (somente leitura)
description: Permite ao chat ler links, issues, PRs, arquivos e o roadmap de repositorios GitHub permitidos.
requirements: requests
version: 0.1.0
"""

import re
from typing import Optional

import requests
from pydantic import BaseModel, Field

API = "https://api.github.com"
URL_RE = re.compile(
    r"github\.com/(?P<owner>[\w.-]+)/(?P<repo>[\w.-]+)"
    r"(?:/(?P<kind>issues|pull|blob|tree)/(?P<rest>[^\s?#]*))?"
)


def parse_github_url(url: str) -> Optional[dict]:
    match = URL_RE.search(url or "")
    if not match:
        return None
    data = match.groupdict()
    data["repo"] = data["repo"].removesuffix(".git")
    return data


class Tools:
    class Valves(BaseModel):
        github_token: str = Field("", description="Token com permissao somente leitura (opcional para repos publicos)")
        allowed_repos: str = Field(
            "IsraelSiq/bastiao-autodidata,IsraelSiq/bastiao",
            description="Repositorios permitidos (owner/repo), separados por virgula",
        )
        default_repo: str = Field("IsraelSiq/bastiao-autodidata", description="Repositorio padrao")
        max_chars: int = Field(8000, description="Limite de caracteres por resposta")
        timeout: int = Field(15, description="Timeout em segundos")

    def __init__(self):
        self.valves = self.Valves()

    def _allowed(self, repo: str) -> bool:
        allowed = {r.strip().lower() for r in self.valves.allowed_repos.split(",") if r.strip()}
        return repo.lower() in allowed

    def _get(self, path: str, raw: bool = False):
        headers = {"Accept": "application/vnd.github.raw+json" if raw else "application/vnd.github+json"}
        if self.valves.github_token:
            headers["Authorization"] = f"Bearer {self.valves.github_token}"
        response = requests.get(f"{API}{path}", headers=headers, timeout=self.valves.timeout)
        response.raise_for_status()
        return response.text if raw else response.json()

    def _cut(self, text: str) -> str:
        limit = self.valves.max_chars
        return text if len(text) <= limit else text[:limit] + "\n...[truncado]"

    def _repo(self, repo: str) -> str:
        repo = repo or self.valves.default_repo
        if not self._allowed(repo):
            raise PermissionError(f"Repositorio nao permitido: {repo}")
        return repo

    def list_issues(self, state: str = "open", repo: str = "") -> str:
        """Lista issues (sem PRs). state: open, closed ou all."""
        try:
            repo = self._repo(repo)
            items = self._get(f"/repos/{repo}/issues?state={state}&per_page=50")
            lines = [
                f"#{i['number']} [{i['state']}] {i['title']}"
                for i in items
                if "pull_request" not in i
            ]
            return self._cut("\n".join(lines) or "Nenhuma issue.")
        except Exception as exc:
            return f"Erro: {exc}"

    def get_issue(self, number: int, repo: str = "") -> str:
        """Le uma issue ou PR com corpo e comentarios."""
        try:
            repo = self._repo(repo)
            issue = self._get(f"/repos/{repo}/issues/{int(number)}")
            comments = self._get(f"/repos/{repo}/issues/{int(number)}/comments?per_page=20")
            text = f"#{issue['number']} [{issue['state']}] {issue['title']}\n\n{issue.get('body') or ''}"
            for comment in comments:
                text += f"\n\n--- {comment['user']['login']}:\n{comment.get('body') or ''}"
            return self._cut(text)
        except Exception as exc:
            return f"Erro: {exc}"

    def list_pull_requests(self, state: str = "open", repo: str = "") -> str:
        """Lista pull requests."""
        try:
            repo = self._repo(repo)
            items = self._get(f"/repos/{repo}/pulls?state={state}&per_page=30")
            lines = [f"#{p['number']} [{p['state']}] {p['title']} ({p['head']['ref']})" for p in items]
            return self._cut("\n".join(lines) or "Nenhum PR.")
        except Exception as exc:
            return f"Erro: {exc}"

    def read_file(self, path: str, ref: str = "", repo: str = "") -> str:
        """Le um arquivo do repositorio (ex.: ROADMAP.md) ou lista um diretorio."""
        try:
            repo = self._repo(repo)
            query = f"?ref={ref}" if ref else ""
            path = path.lstrip("/")
            data = self._get(f"/repos/{repo}/contents/{path}{query}")
            if isinstance(data, list):
                return self._cut("\n".join(f"{e['type']}: {e['path']}" for e in data))
            return self._cut(self._get(f"/repos/{repo}/contents/{path}{query}", raw=True))
        except Exception as exc:
            return f"Erro: {exc}"

    def read_github_link(self, url: str) -> str:
        """Le o conteudo apontado por um link do GitHub (issue, PR, arquivo ou repositorio)."""
        info = parse_github_url(url)
        if not info:
            return "Erro: link do GitHub invalido."
        repo = f"{info['owner']}/{info['repo']}"
        kind, rest = info.get("kind"), info.get("rest") or ""
        if kind in ("issues", "pull") and rest.split("/")[0].isdigit():
            return self.get_issue(int(rest.split("/")[0]), repo)
        if kind == "blob":
            ref, _, path = rest.partition("/")
            return self.read_file(path, ref, repo)
        if kind == "tree":
            _, _, path = rest.partition("/")
            return self.read_file(path, "", repo)
        return self.read_file("README.md", "", repo)
