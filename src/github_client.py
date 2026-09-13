"""Bastiao - GitHub Client

Cliente para interagir com GitHub API.
"""

import os
import requests
from typing import Optional
from dataclasses import dataclass


@dataclass
class GitHubIssue:
    """Issue do GitHub."""
    number: int
    title: str
    body: str
    labels: list[str]
    state: str


class GitHubClient:
    """Cliente GitHub."""

    def __init__(
        self,
        owner: str,
        repo: str,
        token: Optional[str] = None,
    ):
        """Inicializa o cliente.

        Args:
            owner: Owner do repo
            repo: Nome do repo
            token: Token do GitHub (opcional, usa GITHUB_TOKEN do env)
        """
        self.owner = owner
        self.repo = repo
        self.token = token or os.getenv("GITHUB_TOKEN", "")
        self.base_url = "https://api.github.com"

        self.session = requests.Session()
        if self.token:
            self.session.headers["Authorization"] = f"token {self.token}"

    def list_issues(self, state: str = "open") -> list[GitHubIssue]:
        """Lista issues.

        Args:
            state: Estado (open, closed, all)

        Returns:
            Lista de issues
        """
        url = f"{self.base_url}/repos/{self.owner}/{self.repo}/issues"
        params = {"state": state, "per_page": 30}

        response = self.session.get(url, params=params)
        response.raise_for_status()

        issues = []
        for data in response.json():
            # Pula pull requests
            if "pull_request" in data:
                continue

            issues.append(
                GitHubIssue(
                    number=data["number"],
                    title=data["title"],
                    body=data.get("body", ""),
                    labels=[label["name"] for label in data.get("labels", [])],
                    state=data["state"],
                )
            )

        return issues

    def get_issue(self, number: int) -> GitHubIssue:
        """Pega uma issue específica.

        Args:
            number: Número da issue

        Returns:
            Issue
        """
        url = f"{self.base_url}/repos/{self.owner}/{self.repo}/issues/{number}"
        response = self.session.get(url)
        response.raise_for_status()

        data = response.json()
        return GitHubIssue(
            number=data["number"],
            title=data["title"],
            body=data.get("body", ""),
            labels=[label["name"] for label in data.get("labels", [])],
            state=data["state"],
        )

    def add_comment(self, issue_number: int, body: str):
        """Adiciona comentário em issue.

        Args:
            issue_number: Número da issue
            body: Conteudo do comentário
        """
        url = f"{self.base_url}/repos/{self.owner}/{self.repo}/issues/{issue_number}/comments"
        response = self.session.post(url, json={"body": body})
        response.raise_for_status()

    def close_issue(self, issue_number: int):
        """Fecha issue.

        Args:
            issue_number: Número da issue
        """
        url = f"{self.base_url}/repos/{self.owner}/{self.repo}/issues/{issue_number}"
        response = self.session.patch(url, json={"state": "closed", "state_reason": "completed"})
        response.raise_for_status()

    def create_issue(
        self,
        title: str,
        body: str,
        labels: Optional[list[str]] = None,
    ) -> GitHubIssue:
        """Cria nova issue.

        Args:
            title: Titulo
            body: Descricao
            labels: Labels

        Returns:
            Issue criada
        """
        url = f"{self.base_url}/repos/{self.owner}/{self.repo}/issues"
        payload = {"title": title, "body": body}
        if labels:
            payload["labels"] = labels

        response = self.session.post(url, json=payload)
        response.raise_for_status()

        data = response.json()
        return GitHubIssue(
            number=data["number"],
            title=data["title"],
            body=data.get("body", ""),
            labels=[label["name"] for label in data.get("labels", [])],
            state=data["state"],
        )

    def get_repo_files(self, path: str = "") -> list[dict]:
        """Lista arquivos do repo.

        Args:
            path: Caminho (vazio = raiz)

        Returns:
            Lista de arquivos
        """
        url = f"{self.base_url}/repos/{self.owner}/{self.repo}/contents/{path}"
        response = self.session.get(url)
        response.raise_for_status()

        return response.json()

    def get_file_content(self, path: str) -> str:
        """Pega conteudo de arquivo.

        Args:
            path: Caminho do arquivo

        Returns:
            Conteudo
        """
        url = f"{self.base_url}/repos/{self.owner}/{self.repo}/contents/{path}"
        response = self.session.get(url)
        response.raise_for_status()

        import base64
        data = response.json()
        content = base64.b64decode(data["content"]).decode("utf-8")
        return content

    def commit_files(
        self,
        files: list[dict],
        message: str,
        branch: str = "main",
    ):
        """Comita arquivos.

        Args:
            files: Lista de {"path": "...", "content": "..."}
            message: Mensagem do commit
            branch: Branch
        """
        # Pega SHA do ultimo commit
        ref_url = f"{self.base_url}/repos/{self.owner}/{self.repo}/git/refs/heads/{branch}"
        ref_response = self.session.get(ref_url)
        ref_response.raise_for_status()
        commit_sha = ref_response.json()["object"]["sha"]

        # Cria tree
        tree_data = []
        for file in files:
            # Cria blob
            blob_url = f"{self.base_url}/repos/{self.owner}/{self.repo}/git/blobs"
            blob_response = self.session.post(
                blob_url,
                json={"content": file["content"], "encoding": "utf-8"},
            )
            blob_response.raise_for_status()
            blob_sha = blob_response.json()["sha"]

            tree_data.append({"path": file["path"], "mode": "100644", "type": "blob", "sha": blob_sha})

        # Cria tree
        tree_url = f"{self.base_url}/repos/{self.owner}/{self.repo}/git/trees"
        tree_response = self.session.post(
            tree_url,
            json={"base_tree": commit_sha, "tree": tree_data},
        )
        tree_response.raise_for_status()
        tree_sha = tree_response.json()["sha"]

        # Cria commit
        commit_url = f"{self.base_url}/repos/{self.owner}/{self.repo}/git/commits"
        commit_response = self.session.post(
            commit_url,
            json={"message": message, "tree": tree_sha, "parents": [commit_sha]},
        )
        commit_response.raise_for_status()
        new_commit_sha = commit_response.json()["sha"]

        # Atualiza ref
        self.session.patch(ref_url, json={"sha": new_commit_sha})


if __name__ == "__main__":
    # Teste
    client = GitHubClient(owner="IsraelSiq", repo="bastiao-autodidata")

    issues = client.list_issues(state="open")
    print(f"Open issues: {len(issues)}")
    for issue in issues[:5]:
        print(f"  #{issue.number}: {issue.title}")
