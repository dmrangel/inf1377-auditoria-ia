r"""Converte o log de uma conversa do Antigravity em Markdown legível.

O Antigravity grava cada conversa em
%USERPROFILE%\.gemini\antigravity\brain\<id>\.system_generated\logs\transcript_full.jsonl

Uso:
    python exportar_antigravity.py <id-da-conversa> <arquivo-de-saida.md> [limite]

O limite é quantos caracteres mostrar de cada resultado de ferramenta
(padrão 2000; use 0 para não cortar nada).
"""
import json
import os
import re
import sys

LIMITE_SAIDA = 2000  # caracteres mostrados de cada resultado de ferramenta


def limpar_pedido(texto):
    pedido = re.search(r"<USER_REQUEST>\s*(.*?)\s*</USER_REQUEST>", texto, re.S)
    modelo = re.search(r"`Model Selection` from (.+?) to (.+?)\. No need", texto)
    corpo = pedido.group(1) if pedido else texto
    nota = f"\n\n*(modelo trocado para {modelo.group(2)})*" if modelo else ""
    return corpo + nota


def resumir_chamada(chamada):
    args = chamada.get("args", {})
    alvo = (args.get("CommandLine") or args.get("TargetFile") or args.get("Path")
            or args.get("AbsolutePath") or args.get("SearchPath") or "")
    return f"`{chamada['name']}` {alvo}".strip()


def cortar(texto, limite):
    if limite and len(texto) > limite:
        return texto[:limite] + f"\n[... {len(texto) - limite} caracteres omitidos]"
    return texto


def cerca(texto):
    return "```\n" + texto.replace("```", "ˋˋˋ") + "\n```"


def main(conversa_id, saida, limite=LIMITE_SAIDA):
    caminho = os.path.join(os.path.expanduser("~"), ".gemini", "antigravity", "brain",
                           conversa_id, ".system_generated", "logs", "transcript_full.jsonl")
    passos = [json.loads(linha) for linha in open(caminho, encoding="utf-8") if linha.strip()]
    linhas = [f"# Conversa no Antigravity ({conversa_id})", "",
              f"Exportada de `transcript_full.jsonl`: {len(passos)} passos, "
              f"de {passos[0]['created_at']} a {passos[-1]['created_at']} (UTC).", ""]
    for passo in passos:
        hora = passo["created_at"][11:19]
        if passo["type"] == "USER_INPUT":
            linhas += ["---", "", f"## Usuário ({hora})", "", limpar_pedido(passo["content"]), ""]
        elif passo["type"] == "PLANNER_RESPONSE":
            if passo.get("thinking"):
                linhas += ["<details><summary>Raciocínio da IA</summary>", "",
                           passo["thinking"].strip(), "", "</details>", ""]
            if passo.get("content"):
                linhas += [f"### IA ({hora})", "", passo["content"].strip(), ""]
            for chamada in passo.get("tool_calls", []):
                linhas.append(f"- Ação: {resumir_chamada(chamada)}")
            if passo.get("tool_calls"):
                linhas.append("")
        elif passo["type"] == "SYSTEM_MESSAGE" and passo.get("content"):
            texto = cortar(passo["content"].strip(), limite)
            linhas += ["<details><summary>Mensagem do sistema "
                       "(resultado de tarefa em segundo plano)</summary>", "",
                       cerca(texto), "", "</details>", ""]
        elif passo["type"] == "GENERIC" and passo.get("content"):
            texto = passo["content"].strip()
            texto = cortar(texto, limite)
            linhas += ["<details><summary>Resultado da ação</summary>", "", cerca(texto), "",
                       "</details>", ""]
    with open(saida, "w", encoding="utf-8") as arquivo:
        arquivo.write("\n".join(linhas))
    print(f"{len(passos)} passos exportados para {saida}")


if __name__ == "__main__":
    limite = int(sys.argv[3]) if len(sys.argv) > 3 else LIMITE_SAIDA
    main(sys.argv[1], sys.argv[2], limite)
