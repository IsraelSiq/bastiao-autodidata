"""Bastiao - Coder

Escreve codigo baseado em tasks.
"""

from typing import Optional
from dataclasses import dataclass

from .planner import Task


@dataclass
class CodeFile:
    """Arquivo de codigo."""
    path: str
    content: str
    description: str


class Coder:
    """Escreve codigo baseado em tasks."""

    def __init__(self):
        """Inicializa o coder."""
        pass

    def generate_code(self, task: Task) -> list[CodeFile]:
        """Gera codigo para uma task.

        Args:
            task: Task

        Returns:
            Lista de arquivos
        """
        # Isso aqui vai usar LLM pra gerar o codigo
        # Por enquanto, gera codigo basico

        files = []

        # Cria arquivos que precisam ser criados
        for filepath in task.files_to_create:
            content = self._generate_file_content(filepath, task)
            files.append(
                CodeFile(
                    path=filepath,
                    content=content,
                    description=task.description,
                )
            )

        return files

    def _generate_file_content(self, filepath: str, task: Task) -> str:
        """Gera conteudo de arquivo.

        Args:
            filepath: Caminho do arquivo
            task: Task

        Returns:
            Conteudo
        """
        # Heuristica simples
        if filepath.endswith(".py"):
            return self._generate_python_file(filepath, task)
        elif filepath.endswith(".md"):
            return self._generate_markdown_file(filepath, task)
        else:
            return f"# TODO: Implement {filepath}\n"

    def _generate_python_file(self, filepath: str, task: Task) -> str:
        """Gera arquivo Python."""
        filename = filepath.split("/")[-1].replace(".py", "")

        return f'''"""Bastiao - {filename.title()}

{task.description}
"""

# TODO: Implement {filename}

def main():
    """Main function."""
    print("TODO: Implement {filename}")


if __name__ == "__main__":
    main()
'''

    def _generate_markdown_file(self, filepath: str, task: Task) -> str:
        """Gera arquivo Markdown."""
        return f"""# {task.title}

{task.description}

## TODO

- [ ] Implement
"""


if __name__ == "__main__":
    # Teste
    from .planner import Task

    task = Task(
        title="Criar modulo test",
        description="Criar arquivo test.py",
        files_to_create=["src/test.py"],
        files_to_modify=[],
        tests_needed=[],
    )

    coder = Coder()
    files = coder.generate_code(task)

    print(f"Files: {len(files)}")
    for file in files:
        print(f"  - {file.path}")
        print(f"    {file.content[:100]}...")
