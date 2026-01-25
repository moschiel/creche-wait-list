import urllib.request
import urllib.parse
import http.cookiejar
import os

LAST_FILE = "last_position.txt"

BASE = "https://carapicuiba.demandadealunos.com/"
POST_URL = BASE + "resultado_classificacao"

NE = os.environ["CRECHE_NE"]
DA = os.environ["CRECHE_DA"]
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

def send_telegram_message(token: str, chat_id: str, text: str) -> None:
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"

        data = urllib.parse.urlencode({
            "chat_id": chat_id,
            "text": text,
        }).encode("utf-8")

        req = urllib.request.Request(url, data=data, method="POST")

        with urllib.request.urlopen(req, timeout=20) as resp:
            status = getattr(resp, "status", None)
            if status is not None and status != 200:
                raise RuntimeError(f"Telegram HTTP status inesperado: {status}")

    except Exception as e:
        raise RuntimeError(f"Erro ao enviar mensagem Telegram: {e}") from e

def load_last_position() -> int | None:
    if not os.path.exists(LAST_FILE):
        return None
    with open(LAST_FILE, "r", encoding="utf-8") as f:
        s = f.read().strip()
    if s == "":
        return None
    if not s.isdigit():
        raise RuntimeError(f"Arquivo {LAST_FILE} inválido: '{s}'")
    return int(s)

def save_last_position(pos: int) -> None:
    with open(LAST_FILE, "w", encoding="utf-8") as f:
        f.write(str(pos))

def extract_position(html: str) -> int:
    try:
        needle = "Sua posição na fila de espera"

        for line in html.splitlines():
            if needle not in line:
                continue

            #print("[DEBUG] Linha encontrada:")
            #print(line.strip())

            # 1) último '#'
            idx_hash = line.rfind("#")
            if idx_hash == -1:
                raise ValueError("Não encontrei '#' na linha da posição")

            # 2) primeiro </span> após o '#'
            idx_span_end = line.find("</span>", idx_hash)
            if idx_span_end == -1:
                raise ValueError("Não encontrei </span> após '#'")

            # 3) extrai o texto entre
            raw = line[idx_hash + 1 : idx_span_end].strip()

            if not raw.isdigit():
                raise ValueError(f"Conteúdo entre '#' e '</span>' não é numérico: '{raw}'")

            return int(raw)

        # se percorreu tudo e não achou a frase
        raise ValueError("Frase 'Sua posição na fila de espera' não encontrada no HTML")

    except Exception as e:
        # reempacota o erro pra deixar claro de onde veio
        raise RuntimeError(f"Erro ao extrair posição da fila: {e}") from e


def fetch_result_html() -> str:
    try:
        # Cookie jar (simula Session)
        cj = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(cj)
        )

        # Headers com cara de navegador
        opener.addheaders = [
            ("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"),
            ("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"),
            ("Accept-Language", "pt-BR,pt;q=0.9"),
            ("Referer", BASE),
        ]

        # 1) GET inicial (cookies / sessão)
        try:
            opener.open(BASE, timeout=20)
        except Exception as e:
            raise RuntimeError(f"Falha no GET inicial ({BASE})") from e

        # 2) POST do formulário
        data = urllib.parse.urlencode({
            "ne": NE,
            "da": DA,
            "entrar": "Verificar",
        }).encode("utf-8")

        req = urllib.request.Request(POST_URL, data=data, method="POST")

        try:
            with opener.open(req, timeout=20) as resp:
                status = getattr(resp, "status", None)
                if status is not None and status != 200:
                    raise RuntimeError(f"HTTP status inesperado: {status}")

                html = resp.read().decode("utf-8", errors="replace")
                if not html or len(html) < 100:
                    raise RuntimeError("Resposta HTML vazia ou muito curta")

                return html

        except Exception as e:
            raise RuntimeError("Falha no POST do formulário") from e

    except Exception as e:
        # erro final, com contexto claro
        raise RuntimeError(f"Erro ao buscar resultado da creche: {e}") from e


def main():
    try:
        html = fetch_result_html()
        atual = extract_position(html)

        last = load_last_position()

        if last is None:
            save_last_position(atual)
            msg = f"Primeira leitura: posição {atual}"
        elif atual == last:
            msg = f"🔄 Sem mudança: posição continua {atual}"
        elif atual < last:
            msg = f"👶 Diminuiu de {last} para {atual}"
        else:
            msg = f"👶 Aumentou de {last} para {atual}"

        print(msg)
        save_last_position(atual)

        # última ação
        send_telegram_message(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, msg)

    except Exception as e:
        print("[ERRO]", e)

        # tenta avisar no Telegram, se der erro aqui, paciência
        try:
            send_telegram_message(
                TELEGRAM_BOT_TOKEN,
                TELEGRAM_CHAT_ID,
                f"⚠️ Erro no monitor da creche:\n{e}"
            )
        except Exception as te:
            print("[ERRO AO ENVIAR TELEGRAM]", te)
        raise

if __name__ == "__main__":
    main()
