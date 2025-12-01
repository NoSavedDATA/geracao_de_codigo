import os
import json
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def load_requirements(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def remove_fences(text: str) -> str:
    return "\n".join(
        line for line in text.splitlines()
        if not line.strip().startswith("```")
    )


def generate_code_tasks(requirements):
    """Pede ao modelo para decompor o projeto em arquivos de código."""
    prompt = f"""
Você é um engenheiro de software sênior. Considere as seguintes necessidades:

- não escreva comentários no código
- faça um arquivo contendo as bibliotecas utilizadas (requirements)
- gerar código python para a versão 3.10
- assuma Flask 3.x+.
- lembre de fazer o app.py para backends com python e flask
- Não use funções deprecadas.
- Gere apenas código válido e executável na versão atual das dependências.
- lembre de fazer o index.js, main.jsx e index.html na pasta src para frontends em node.js
- Se usar node.js, gere o código vite e configure de acordo


Com base nos requisitos abaixo, divida o sistema em uma lista de arquivos 
de código a serem implementados. Para cada arquivo descreva:

- nome do arquivo
- propósito
- tecnologias usadas
- responsabilidades

Requisitos:
{requirements}

Responda SOMENTE em JSON no formato:
[
  {{
    "filename": "...",
    "description": "..."
  }}
]
"""

    resp = client.chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": prompt}],
        # se quiser, pode tirar o response_format, não é obrigatório
        # response_format={"type": "json_object"}
    )

    content = resp.choices[0].message.content
    # content é uma string com JSON -> converter para Python
    tasks = json.loads(content)
    return tasks


def generate_code_file(requirements, file_spec):
    """Gera um arquivo de código individualmente."""
    prompt = f"""
Gere o conteúdo completo para o arquivo: {file_spec["filename"]}

Descrição do arquivo:
{file_spec["description"]}

Requisitos gerais do projeto:
{requirements}

Regras:
- Produza apenas código.
- Não explique nada.
"""
    resp = client.chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": prompt}]
    )
    return resp.choices[0].message.content


def main():
    requirements = load_requirements("requisitos.txt")

    print("🔍 Extraindo tarefas...")
    tasks = generate_code_tasks(requirements)

    os.makedirs("output", exist_ok=True)

    print("🧱 Gerando arquivos...")
    for spec in tasks:
        code = generate_code_file(requirements, spec)
        path = os.path.join("output", spec["filename"])
        os.makedirs(os.path.dirname(path), exist_ok=True)

        code = remove_fences(code)
        with open(path, "w", encoding="utf-8") as f:
            f.write(code)

        print(f"✔️ Criado: {spec['filename']}")

    print("🏁 Finalizado. Arquivos em /output")


if __name__ == "__main__":
    main()

