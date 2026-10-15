#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Robô completo de teste do HOC — versão Python
=============================================

Exercita, num só robô, tudo o que o HOC precisa provar:

  • Fila de Processamento: PUBLICA itens, CONSOME (o item já vem reservado), e MUDA o status para "concluido"
    (ou "erro" quando o item falha).
  • Passos de API:        consulta e envia dados a uma API pública (JSONPlaceholder) e confere a ida e a volta dos acentos.
  • Passos de navegação:  abre páginas num navegador de verdade (Playwright). Sem Playwright, usa o Microsoft Edge em
                          modo headless, que já vem no Windows — o log diz qual dos dois foi usado.
  • Passos de Windows:    informações do sistema, registro, arquivo em %TEMP% (gravar e ler com acentos) e lista de processos.
  • Logs com acentos:     todas as mensagens têm acentuação, para conferir o popup de Logs (UTF-8).

Como rodar (campo "Arquivo principal / comando" do cadastro do robô no HOC):
    python main.py                  tudo: publica 6 itens, consome todos e conclui
    python main.py --publicar 10    só publica 10 itens na fila
    python main.py --consumir       só consome a fila até esvaziar
    python main.py --simular-erro   o 4º item falha de propósito (testa o status "erro")
    python main.py --sem-web        pula os passos de navegação (máquina sem navegador)
    python main.py --janela         também abre o Bloco de Notas com o resultado (precisa de sessão com tela)

Variáveis que o Agent injeta: HOC_SERVER, HOC_ROBOT_KEY, HOC_ROBO_ID, HOC_EXEC_ID, HOC_ROBO_NOME.
Sem elas (rodando na sua máquina, fora do HOC) a fila é simulada em memória, e o resto funciona igual.
"""
import argparse
import json
import os
import platform
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime

# Os acentos dos logs dependem disto: sem UTF-8 o Windows imprime em cp1252.
for _fluxo in (sys.stdout, sys.stderr):
    try:
        _fluxo.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SERVER = os.environ.get("HOC_SERVER", "").rstrip("/")
ROBOT_KEY = os.environ.get("HOC_ROBOT_KEY", "")
ROBO_ID = os.environ.get("HOC_ROBO_ID", "")
API_PUBLICA = "https://jsonplaceholder.typicode.com"
PAGINAS = ["https://example.com", "https://httpbin.org/html", "https://www.iana.org/help/example-domains"]
PASTA_TEMP = os.path.join(tempfile.gettempdir(), "hoc-robo-completo")
PARAR = False
FILA_LOCAL = []          # usada só fora do HOC


def log(msg, nivel="info"):
    print(f"[{datetime.now():%H:%M:%S}] [{nivel.upper():7}] {msg}", flush=True)


def ao_receber_sinal(signum, frame):
    global PARAR
    PARAR = True
    log("Recebi o pedido de encerramento do HOC. Vou terminar o item atual e parar.", "aviso")


for _nome in ("SIGBREAK", "SIGTERM", "SIGINT"):
    _sig = getattr(signal, _nome, None)
    if _sig is not None:
        try:
            signal.signal(_sig, ao_receber_sinal)
        except Exception:
            pass


# ---------------------------------------------------------------- HTTP
def http(metodo, url, corpo=None, cabecalhos=None, timeout=25):
    dados = json.dumps(corpo).encode("utf-8") if corpo is not None else None
    req = urllib.request.Request(url, data=dados, method=metodo, headers={"Content-Type": "application/json; charset=utf-8", **(cabecalhos or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            texto = r.read().decode("utf-8")
            return json.loads(texto) if texto else None
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} em {metodo} {url}: {e.read().decode('utf-8', 'replace')[:200]}")


def api_hoc(metodo, caminho, corpo=None):
    return http(metodo, SERVER + caminho, corpo, {"x-robot-key": ROBOT_KEY})


# ---------------------------------------------------------------- fila
def usar_fila_do_hoc():
    return bool(SERVER and ROBOT_KEY and ROBO_ID)


def publicar(qtd):
    log(f"FILA — publicando {qtd} itens na Fila de Processamento…")
    for i in range(1, qtd + 1):
        conteudo = {
            "numero": i,
            "postId": i,
            "descricao": f"Conferência da ação nº {i} — validação de acentuação (ç ã é ü õ)",
            "criadoEm": datetime.now().isoformat(timespec="seconds"),
        }
        nome = f"Item {i:03d} — conferência"
        if usar_fila_do_hoc():
            api_hoc("POST", f"/api/robos/{ROBO_ID}/fila", {"nome": nome, "conteudo": conteudo})
        else:
            FILA_LOCAL.append({"_id": f"local-{i}", "nome": nome, "conteudo": conteudo, "status": "aguardando"})
    log(f"FILA — {qtd} itens publicados ✓ ({'HOC' if usar_fila_do_hoc() else 'memória local, fora do HOC'})")


def proximo_item():
    """O item já vem reservado (status em_execucao): dois robôs nunca pegam o mesmo."""
    if usar_fila_do_hoc():
        return api_hoc("GET", f"/api/robos/{ROBO_ID}/fila/proximo")
    for item in FILA_LOCAL:
        if item["status"] == "aguardando":
            item["status"] = "em_execucao"
            return item
    return None


def mudar_status(item, status, conteudo=None):
    corpo = {"status": status}
    if conteudo is not None:
        corpo["conteudo"] = conteudo
    if usar_fila_do_hoc():
        api_hoc("PATCH", f"/api/robos/{ROBO_ID}/fila/{item['_id']}", corpo)
    else:
        item["status"] = status
        if conteudo is not None:
            item["conteudo"] = conteudo


# ---------------------------------------------------------------- passos de API
def passo_api(item):
    pid = int(item["conteudo"].get("postId", 1))
    post = http("GET", f"{API_PUBLICA}/posts/{pid}")
    usuario = http("GET", f"{API_PUBLICA}/users/{post['userId']}")
    log(f"API — post {pid} consultado; autor: {usuario['name']} ({usuario['email']}) ✓")
    enviado = f"Ação concluída — conferência nº {pid} (ç ã é ü)"
    resposta = http("POST", f"{API_PUBLICA}/posts", {"title": enviado, "body": "validação de acentos", "userId": post["userId"]})
    if resposta.get("title") != enviado:
        raise RuntimeError(f"Os acentos não voltaram iguais da API: enviei «{enviado}» e recebi «{resposta.get('title')}»")
    log("API — POST enviado e a acentuação voltou idêntica (UTF-8 ok) ✓")
    return {"autor": usuario["name"], "titulo_post": post["title"][:60]}


# ---------------------------------------------------------------- passos de navegação
def acha_edge():
    for caminho in (shutil.which("msedge"),
                    os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Microsoft", "Edge", "Application", "msedge.exe"),
                    os.path.join(os.environ.get("ProgramFiles", ""), "Microsoft", "Edge", "Application", "msedge.exe")):
        if caminho and os.path.exists(caminho):
            return caminho
    return None


def titulo_com_playwright(url):
    from playwright.sync_api import sync_playwright  # noqa: import tardio: é opcional
    with sync_playwright() as p:
        navegador = p.chromium.launch(headless=True)
        try:
            pagina = navegador.new_page()
            pagina.goto(url, timeout=30000)
            return pagina.title() or pagina.inner_text("h1")[:80], "Playwright (Chromium)"
        finally:
            navegador.close()


def titulo_com_edge(url):
    edge = acha_edge()
    if not edge:
        raise RuntimeError("Nem o Playwright nem o Microsoft Edge estão disponíveis nesta máquina.")
    perfil = tempfile.mkdtemp(prefix="hoc-edge-")
    try:
        r = subprocess.run([edge, "--headless=new", "--disable-gpu", f"--user-data-dir={perfil}", "--dump-dom", url],
                           capture_output=True, timeout=60)
        html = r.stdout.decode("utf-8", "replace")
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I) or re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S | re.I)
        if not m:
            raise RuntimeError("Não achei o título da página no HTML devolvido pelo Edge.")
        return re.sub(r"\s+", " ", m.group(1)).strip(), "Microsoft Edge (headless)"
    finally:
        shutil.rmtree(perfil, ignore_errors=True)


def passo_web(item):
    url = PAGINAS[(int(item["conteudo"].get("numero", 1)) - 1) % len(PAGINAS)]
    try:
        titulo, via = titulo_com_playwright(url)
    except Exception as e:
        log(f"WEB — Playwright indisponível ({type(e).__name__}); usando o Edge.", "aviso")
        titulo, via = titulo_com_edge(url)
    log(f"WEB — abri {url} com {via}; título: «{titulo}» ✓")
    return {"pagina": url, "titulo_pagina": titulo, "navegador": via}


# ---------------------------------------------------------------- passos de Windows
def powershell(comando):
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                        "[Console]::OutputEncoding=[Text.Encoding]::UTF8; " + comando], capture_output=True, timeout=60)
    if r.returncode != 0:
        raise RuntimeError(f"PowerShell falhou ({r.returncode}): {r.stderr.decode('utf-8', 'replace')[:200]}")
    return r.stdout.decode("utf-8", "replace").strip()


def passo_windows(item, abrir_janela):
    if os.name != "nt":
        log("WINDOWS — este passo só roda no Windows; pulado.", "aviso")
        return {"windows": "pulado (não é Windows)"}
    info = json.loads(powershell(
        "$o = Get-CimInstance Win32_OperatingSystem; "
        r"$v = (Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion').DisplayVersion; "
        "@{ versao = $o.Caption; produto = $v; processos = (Get-Process).Count } | ConvertTo-Json -Compress"))
    versao, produto, processos = info["versao"], info["produto"], info["processos"]
    log(f"WINDOWS — {versao} (versão {produto}); {processos} processos em execução; usuário {os.environ.get('USERNAME')} ✓")
    os.makedirs(PASTA_TEMP, exist_ok=True)
    arquivo = os.path.join(PASTA_TEMP, f"resultado-{item['conteudo'].get('numero', 0):03d}.txt")
    texto = f"Resultado da conferência nº {item['conteudo'].get('numero')}\nEmitido em {datetime.now():%d/%m/%Y %H:%M:%S}\nAcentuação: ç ã é ü õ ñ — ✓\n"
    with open(arquivo, "w", encoding="utf-8") as f:
        f.write(texto)
    lido = powershell(f"Get-Content -Raw -Encoding UTF8 -LiteralPath '{arquivo}'")
    if "ç ã é ü õ ñ" not in lido:
        raise RuntimeError("O arquivo gravado e relido pelo Windows perdeu a acentuação.")
    log(f"WINDOWS — arquivo gravado e relido com acentos em {arquivo} ✓")
    if abrir_janela:
        p = subprocess.Popen(["notepad.exe", arquivo])
        time.sleep(3)
        p.terminate()
        log("WINDOWS — Bloco de Notas aberto e fechado (passo com janela) ✓")
    return {"windows": versao, "arquivo": arquivo}


# ---------------------------------------------------------------- orquestração
def tratar_item(item, args, n):
    conteudo = dict(item.get("conteudo") or {})
    log(f"ITEM — «{item.get('nome')}» reservado; iniciando o processamento…")
    if args.simular_erro and n == 4:
        raise RuntimeError("Erro simulado de propósito (--simular-erro): o item deve ficar com status «erro».")
    conteudo.update(passo_api(item))
    if not args.sem_web:
        conteudo.update(passo_web(item))
    conteudo.update(passo_windows(item, args.janela))
    conteudo["processadoEm"] = datetime.now().isoformat(timespec="seconds")
    return conteudo


def consumir(args):
    log("FILA — consumindo a Fila de Processamento até esvaziar…")
    n = ok = erro = 0
    while not PARAR:
        item = proximo_item()
        if not item:
            break
        n += 1
        try:
            resultado = tratar_item(item, args, n)
            mudar_status(item, "concluido", resultado)
            ok += 1
            log(f"FILA — item «{item.get('nome')}» → concluido ✓")
        except Exception as e:
            erro += 1
            mudar_status(item, "erro", {**(item.get("conteudo") or {}), "erro": str(e)[:300]})
            log(f"FILA — item «{item.get('nome')}» → erro: {e}", "erro")
    if PARAR:
        log("Execução interrompida a pedido do HOC.", "aviso")
    log(f"RESUMO — {n} item(ns) processado(s): {ok} concluído(s), {erro} com erro.")
    return ok, erro


def main():
    p = argparse.ArgumentParser(description="Robô completo de teste do HOC (Python)")
    p.add_argument("--publicar", type=int, metavar="N", help="só publica N itens na fila")
    p.add_argument("--consumir", action="store_true", help="só consome a fila")
    p.add_argument("--simular-erro", action="store_true", help="o 4º item falha de propósito")
    p.add_argument("--sem-web", action="store_true", help="pula os passos de navegação")
    p.add_argument("--janela", action="store_true", help="abre o Bloco de Notas no passo de Windows")
    args = p.parse_args()
    log(f"Robô completo (Python {platform.python_version()}) iniciando em {platform.node()} — acentuação: ação, conexão, emissão, não ✓")
    log(f"Ambiente: HOC_SERVER {'definido' if SERVER else 'ausente'}, chave de API {'definida' if ROBOT_KEY else 'ausente'}, robô {ROBO_ID or '—'}")
    try:
        if args.publicar:
            publicar(args.publicar)
        elif args.consumir:
            consumir(args)
        else:
            publicar(6)
            ok, erro = consumir(args)
            if erro and not args.simular_erro:
                sys.exit(1)
    except Exception as e:
        log(f"Falha inesperada: {e}", "erro")
        sys.exit(1)
    log("Fim da execução — tudo certo ✓")


if __name__ == "__main__":
    main()
