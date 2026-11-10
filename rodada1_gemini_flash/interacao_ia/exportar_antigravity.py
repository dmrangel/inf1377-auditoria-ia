r"""Converte o log de uma conversa do Antigravity em Markdown legível.

O Antigravity grava cada conversa em
%USERPROFILE%\.gemini\antigravity\brain\<id>\.system_generated\logs\transcript_full.jsonl

Uso:
    python exportar_antigravity.py <id-da-conversa> <arquivo-de-saida.md>
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


def cerca(texto):
    return "```\n" + texto.replace("```", "ˋˋˋ") + "\n```"


def main(conversa_id, saida):
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
        elif passo["type"] == "GENERIC" and passo.get("content"):
            texto = passo["content"].strip()
            if len(texto) > LIMITE_SAIDA:
                texto = texto[:LIMITE_SAIDA] + f"\n[... {len(texto) - LIMITE_SAIDA} caracteres omitidos]"
            linhas += ["<details><summary>Resultado da ação</summary>", "", cerca(texto), "",
                       "</details>", ""]
    with open(saida, "w", encoding="utf-8") as arquivo:
        arquivo.write("\n".join(linhas))
    print(f"{len(passos)} passos exportados para {saida}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
