# HOC — robô completo de teste (Python)

Robô de teste do HOC que exercita, de uma vez, o que costuma dar problema na prática:

| O quê | Como |
| --- | --- |
| **Fila de Processamento** | publica itens, consome (o item já vem reservado) e muda o status para `concluido` (ou `erro`) |
| **Passos de API** | consulta e envia dados à API pública JSONPlaceholder e confere que os acentos voltam idênticos |
| **Passos de navegação web** | abre páginas num navegador de verdade (Playwright) ou, se não houver, no Microsoft Edge headless |
| **Passos de Windows** | versão do Windows, registro, processos, arquivo em `%TEMP%` gravado e relido com acentos |
| **Logs com acentos** | todas as mensagens têm acentuação (ação, conexão, emissão, não, ç ã é ü) para conferir o popup de Logs |

Usa só a biblioteca padrão do Python 3.8+. O Playwright é opcional.

## Como cadastrar no HOC

Operações › Robôs › **Cadastrar Robô** › fonte **Git**.

- **URL do repositório:** a deste repositório · **Branch:** `main`
- **Arquivo principal / comando:** `python main.py`
- **Pacotes pip:** (opcional) `playwright`, e em **Comando de pré-execução** `python -m playwright install chromium` para usar o Chromium real. Sem isso o robô cai no Edge automaticamente.

Depois é só rodar (Produção ou Teste). O robô precisa da chave de API do HOC, que o Agent injeta sozinho (`HOC_SERVER`, `HOC_ROBOT_KEY`, `HOC_ROBO_ID`).

## Variações de comando

| Comando | O que faz |
| --- | --- |
| `python main.py` | publica 6 itens, consome todos e conclui |
| `python main.py --publicar 10` | só publica 10 itens |
| `python main.py --consumir` | só consome a fila até esvaziar |
| `python main.py --simular-erro` | o 4º item falha de propósito (status `erro` na fila) |
| `python main.py --sem-web` | pula os passos de navegação |
| `python main.py --janela` | abre o Bloco de Notas no passo de Windows (precisa de sessão com tela) |

Para testar vários cenários, cadastre o mesmo repositório mais de uma vez, mudando só o comando.

## O que conferir

- Execuções: status **Concluído**; logs com acentos corretos.
- Fila de Processamento do robô: 6 itens `concluido` (com `--simular-erro`: 5 concluídos e 1 `erro`).
- Cada item concluído guarda o resultado (autor da API, título da página, versão do Windows).
- Rodar o robô **fora do HOC** (`python main.py`) também funciona: a fila é simulada em memória.
