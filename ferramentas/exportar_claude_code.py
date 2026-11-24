r"""Converte o log de uma conversa do Claude Code em Markdown legível.

O Claude Code grava cada conversa do app no computador em
%USERPROFILE%\.claude\projects\<pasta-do-projeto>\<id-da-conversa>.jsonl

O nome da pasta é o caminho do repositório com os separadores trocados por "-".
Para este repositório: C--Users-<usuario>-inf1377-auditoria-ia

Uso:
    python exportar_claude_code.py <id-da-conversa> <arquivo-de-saida.md> [limite]

O limite é quantos caracteres mostrar de cada resultado de ferramenta
(padrão 2000; use 0 para não cortar nada).
"""
import json
import os
import sys

LIMITE_SAIDA = 2000  # caracteres mostrados de cada resultado de ferramenta


def achar_log(conversa_id):
    """Procura <conversa_id>.jsonl em todas as pastas de projeto do Claude Code."""
    raiz = os.path.join(os.path.expanduser("~"), ".claude", "projects")
    for pasta in os.listdir(raiz):
        caminho = os.path.join(raiz, pasta, f"{conversa_id}.jsonl")
        if os.path.exists(caminho):
            return caminho
    raise SystemExit(f"Conversa {conversa_id} não encontrada em {raiz}")


def texto_de(conteudo):
    """O conteúdo de uma mensagem pode ser uma string ou uma lista de blocos."""
    if isinstance(conteudo, str):
        return conteudo
    if isinstance(conteudo, list):
        partes = [b.get("text", "") for b in conteudo if isinstance(b, dict)]
        return "\n".join(p for p in partes if p)
    return ""


def resumir_chamada(bloco):
    args = bloco.get("input", {}) or {}
    alvo = (args.get("command") or args.get("file_path") or args.get("path")
            or args.get("pattern") or args.get("prompt") or args.get("skill") or "")
    alvo = " ".join(str(alvo).split())
    if len(alvo) > 300:
        alvo = alvo[:300] + "..."
    return f"`{bloco.get('name', '?')}` {alvo}".strip()


def cerca(texto):
    return "```\n" + texto.replace("```", "ˋˋˋ") + "\n```"


def cortar(texto, limite):
    if limite and len(texto) > limite:
        return texto[:limite] + f"\n[... {len(texto) - limite} caracteres omitidos]"
    return texto


def main(conversa_id, saida, limite=LIMITE_SAIDA):
    caminho = achar_log(conversa_id)
    entradas = []
    for linha in open(caminho, encoding="utf-8"):
        if not linha.strip():
            continue
        try:
            entradas.append(json.loads(linha))
        except ValueError:
            continue

    # Só o que é conversa de verdade: o resto é registro interno do app.
    conversa = [e for e in entradas if e.get("type") in ("user", "assistant")]
    datas = [e.get("timestamp", "") for e in conversa if e.get("timestamp")]
    linhas = [f"# Conversa no Claude Code ({conversa_id})", "",
              f"Exportada de `{os.path.basename(caminho)}`: {len(conversa)} mensagens, "
              f"de {datas[0]} a {datas[-1]} (UTC).", ""]

    for entrada in conversa:
        hora = entrada.get("timestamp", "")[11:19]
        mensagem = entrada.get("message", {}) or {}
        conteudo = mensagem.get("content")

        if entrada["type"] == "user":
            # Uma mensagem do usuário é texto; as outras são devoluções de ferramenta.
            if isinstance(conteudo, str) and conteudo.strip():
                linhas += ["---", "", f"## Usuário ({hora})", "", conteudo.strip(), ""]
                continue
            for bloco in conteudo if isinstance(conteudo, list) else []:
                if not isinstance(bloco, dict):
                    continue
                if bloco.get("type") == "text" and bloco.get("text", "").strip():
                    linhas += ["---", "", f"## Usuário ({hora})", "",
                               bloco["text"].strip(), ""]
                elif bloco.get("type") == "tool_result":
                    texto = texto_de(bloco.get("content")).strip()
                    if texto:
                        linhas += ["<details><summary>Resultado da ação</summary>", "",
                                   cerca(cortar(texto, limite)), "", "</details>", ""]
            continue

        for bloco in conteudo if isinstance(conteudo, list) else []:
            if not isinstance(bloco, dict):
                continue
            tipo = bloco.get("type")
            if tipo == "thinking" and bloco.get("thinking", "").strip():
                linhas += ["<details><summary>Raciocínio da IA</summary>", "",
                           bloco["thinking"].strip(), "", "</details>", ""]
            elif tipo == "text" and bloco.get("text", "").strip():
                linhas += [f"### IA ({hora})", "", bloco["text"].strip(), ""]
            elif tipo == "tool_use":
                linhas += [f"- Ação: {resumir_chamada(bloco)}", ""]

    with open(saida, "w", encoding="utf-8") as arquivo:
        arquivo.write("\n".join(linhas))
    print(f"{len(conversa)} mensagens exportadas para {saida}")


if __name__ == "__main__":
    limite = int(sys.argv[3]) if len(sys.argv) > 3 else LIMITE_SAIDA
    main(sys.argv[1], sys.argv[2], limite)
