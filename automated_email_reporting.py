# Script simples para envio automatizado de e-mails com anexos
# Utiliza um CSV com email do destinatário,arquivo, arquivo correspontente e status


# Bibliotecas padrão do Python usadas no script
import os
import csv
import smtplib
import ssl
import time
import logging
from email.message import EmailMessage
from dotenv import load_dotenv
load_dotenv("Credenciais.env")
# CONFIGURAÇÕES SMTP GMAIL
# Servidor SMTP do Gmail
SMTP_SERVER = "smtp.gmail.com"

# Porta SSL do Gmail
SMTP_PORT = 465

# Email que será usado para envio e senha de app do .env
EMAIL_REMETENTE = os.getenv("EMAIL_REMETENTE")
SENHA_DE_APP = os.getenv("SENHA_DE_APP")

# CSV contendo email + arquivo. Local onde está no meu computador.
CSV_MAPEAMENTO = r"D:\Documentos\email\arquivos.csv"

# Pasta onde estão os arquivos que serão anexados no meu computador.
PASTA_ARQUIVOS = r"D:\Documentos\email\arquivos"

# Pasta de logs
PASTA_LOGS = r"logs"
# Configuração de logs
logging.basicConfig(
    filename=os.path.join(PASTA_LOGS, "envios.log"),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

#Texto do email
# Assunto do e-mail
ASSUNTO = "Quick observation about your academy"

# Corpo HTML principal
CORPO_HTML = """
<p>Hi,</p>
<br>
<p>We recently looked at your academy from the perspective of a new student trying to get started</p>
<br>
<p>We generated a short report based on this, and it would be best reviewed by the owner, manager, or head coach.</p>
<br>
<p>Happy to share what we found.</p>
<br>
"""

# Assinatura HTML com imagem clicável
ASSINATURA_HTML = """
<br>
<table cellpadding="0" cellspacing="0" border="0">
  <tr>
    <td>
      <a href="https://novodash.com/" target="_blank">
        <img src="https://lh3.googleusercontent.com/d/1vxdeu8xOjjbKl-iRhYiNQfhHKyvQz1PD"
             alt="Novo Dash"
             width="500"
             style="display:block; border:0;">
      </a>
    </td>
  </tr>
</table>
"""


# Modo teste -> True = apenas testa se está tudo certo -> False = Faz os envios

MODO_TESTE = True

# Tempo de espera entre os envios
PAUSA_ENTRE_ENVIOS_SEGUNDOS = 2


# FUNÇÕES AUXILIARES

def garantir_pasta_logs():
    # Cria a pasta de logs caso ela não exista
    os.makedirs(PASTA_LOGS, exist_ok=True)


def carregar_mapeamento(csv_path):
    # Lista que vai armazenar os registros do CSV
    registros = []

    # Abre o CSV
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        # Verifica se o CSV possui as colunas obrigatórias
        if "email" not in reader.fieldnames or "arquivo" not in reader.fieldnames:
            raise ValueError("O CSV precisa ter pelo menos as colunas: email,arquivo")

        # Lê cada linha do CSV
        for linha in reader:

            email = (linha.get("email") or "").strip()
            arquivo = (linha.get("arquivo") or "").strip()
            enviado = (linha.get("enviado") or "").strip()

            # Ignora linhas completamente vazias
            if not email and not arquivo:
                continue

            registros.append({
                "email": email,
                "arquivo": arquivo,
                "enviado": enviado,
            })

    return registros


def salvar_status_csv(csv_path, registros):
    # Salva novamente o CSV atualizando a coluna "enviado"
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        fieldnames = ["email", "arquivo", "enviado"]

        writer = csv.DictWriter(f, fieldnames=fieldnames)

        writer.writeheader()
        writer.writerows(registros)


def criar_email(destinatario, assunto, html_corpo, caminho_arquivo):
    # Cria objeto do e-mail
    msg = EmailMessage()

    # Define remetente
    msg["From"] = EMAIL_REMETENTE

    # Define destinatário
    msg["To"] = destinatario

    # Define assunto
    msg["Subject"] = assunto

    # Corpo simples do e-mail
    msg.set_content("Hi,\n\nPlease find the attached file.")

    # Corpo HTML do e-mail
    msg.add_alternative(html_corpo, subtype="html")

    # Abre o arquivo em modo binário e anexa no e-mail
    with open(caminho_arquivo, "rb") as f:
        msg.add_attachment(
            f.read(),
            maintype="application",
            subtype="octet-stream",
            filename=os.path.basename(caminho_arquivo)
        )

    return msg



# FUNÇÃO PRINCIPAL

def enviar_emails():
    # Garante existência da pasta de logs
    garantir_pasta_logs()
    logging.info("Iniciando processo de envio de emails")
    # Carrega registros do CSV
    registros = carregar_mapeamento(CSV_MAPEAMENTO)

    # Mostra resumo no terminal
    print("Resumo dos envios:")
    for r in registros:
        print(f"{r['email']} -> {r['arquivo']} -> enviado: {r.get('enviado', '')}")

    # Junta corpo + assinatura
    html_final = f"<html><body>{CORPO_HTML}{ASSINATURA_HTML}</body></html>"

    # Impede envio real caso esteja em modo teste
    if MODO_TESTE:
        print("\nMODO_TESTE ativo. Nenhum email enviado.")
        return

    # Abre conexão SMTP SSL
    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=ssl.create_default_context()) as server:

        # Login Gmail
        server.login(EMAIL_REMETENTE, SENHA_DE_APP)

        # Loop principal dos envios
        for r in registros:

            email = r["email"]
            nome_arquivo = r["arquivo"]

            # Monta caminho completo do arquivo
            caminho = os.path.join(PASTA_ARQUIVOS, nome_arquivo)

            # Validação: email vazio
            if not email:
                print(f"[PULADO] Linha sem email. Arquivo: {nome_arquivo}")

                if not r.get("enviado"):
                    r["enviado"] = "NAO"

                continue

            # Validação: arquivo vazio
            if not nome_arquivo:
                print(f"[PULADO] Linha sem arquivo. Email: {email}")

                if not r.get("enviado"):
                    r["enviado"] = "NAO"

                continue

            # Validação: arquivo inexistente
            if not os.path.exists(caminho):
                logging.warning(f"Arquivo não encontrado: {caminho}")

                if not r.get("enviado"):
                    r["enviado"] = "NAO"

                continue

            # Não reenviar caso já esteja marcado como enviado
            if r.get("enviado", "").strip().upper() == "SIM":
                logging.warning(f"Email já marcado como enviado: {email} -> {nome_arquivo}")

                continue

            try:
                # Cria mensagem
                msg = criar_email(email, ASSUNTO, html_final, caminho)

                # Envia e-mail
                server.send_message(msg)

                # Atualiza status
                r["enviado"] = "SIM"

                logging.info(f"Email enviado com sucesso: {email} -> {nome_arquivo}")

            except Exception as e:
                # Caso dê erro
                r["enviado"] = "NAO"

                logging.error(f"Erro ao enviar para {email}: {e}")

            # Atualiza CSV após cada envio
            salvar_status_csv(CSV_MAPEAMENTO, registros)

            # Pausa entre envios
            time.sleep(PAUSA_ENTRE_ENVIOS_SEGUNDOS)

    # Salva novamente ao finalizar
    salvar_status_csv(CSV_MAPEAMENTO, registros)
    logging.info("Processo de envio finalizado")


# Executa apenas se rodar diretamente o arquivo
if __name__ == "__main__":
    enviar_emails()
