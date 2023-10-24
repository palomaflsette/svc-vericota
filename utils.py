import win32com.client as win32
import pandas as pd
# -*- coding: utf-8 -*-
import smtplib
import pandas as pd
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText

def replace_html(html_path: str, texto: str):
    with open(html_path, 'r', encoding='utf-8') as template_file:
        template = template_file.read()
    html_com_parametro = template.replace('{texto}', texto)
    return html_com_parametro

def send_mail(sender: str, dest: str,  subject: str, mail_body: str, dest_cop: str = None, file_attach: str = None) -> None:
        """
        Examples:
        sender = "example@ativainvestimentos.com.br"
        dest = "dest1@ativainvestimentos.com.br; dest2@ativainvestimentos.com.br"
        subject = "Mail example subject"
        mail_body = ("<p>Line 1</p> <p>Line 2</p> <p>...</p>")
        dest_cop = "dest1@ativainvestimentos.com.br; dest2@ativainvestimentos.com.br"
        file_attach = insert complete path
        """  
        outlook = win32.Dispatch('outlook.application')
        mail = outlook.CreateItem(0) 
        oacctouse = None
        for oacc in outlook.Session.Accounts:
            if oacc.SmtpAddress == sender:
                oacctouse = oacc
                break
        if oacctouse:
            # Msg.SendUsingAccount = oacctouse
            mail._oleobj_.Invoke(*(64209, 0, 8, 0, oacctouse))
        pd.options.display.float_format = '{:.0f}'.format
        mail.To = dest
        if dest_cop is not None:
            mail.CC = dest_cop
        mail.Subject = subject
        mail.GetInspector
        index = mail.HTMLbody.find('>', mail.HTMLbody.find('<body'))
        mail.HTMLBody = mail.HTMLbody[:index + 1] + mail_body + mail.HTMLbody[index + 1:]
        if file_attach is not None:
            mail.Attachments.Add(file_attach)        
        mail.Display()
        mail.Send()
        print("e-mail disparado!")
        
        
# função genérica para envio de emails utilizando smtplib
def send_mail_smtplib(from_email: str, password: str, 
                      to_emails: list,  subject: str, 
                      html_content: str, 
                      cc_emails: list, attach_paths: list = None) -> None:

    # Configurações do servidor SMTP
    smtp_server  = "smtp.office365.com" # fixo
    smtp_port = "587"                   # fixo

    # Criando o objeto MIMEMultipart para o email
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = ', '.join(to_emails)
    msg['Cc'] = ', '.join(cc_emails)
    msg['Subject'] = subject
    
    # with open(html_path, 'r', encoding='utf-8') as arquivo:
    # html_content = arquivo.read()
    # # Adicionando o conteúdo HTML à mensagem
    html_part = MIMEText(html_content, 'html')
    msg.attach(html_part)
    
    if attach_paths is not None:
        for attach_path in attach_paths:
            with open(attach_path, 'rb') as arquivo:
                fl = MIMEApplication(arquivo.read(), Name=attach_path)
                fl['Content-Disposition'] = f'attachment; filename="{attach_path}"'
                msg.attach(fl)
        
    # Conectando ao servidor SMTP e enviando o email
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(from_email, password)
        all_recipients = to_emails + cc_emails
        server.sendmail(from_email, all_recipients, msg.as_string())
    except Exception as e:
        print("Erro ao enviar o email com smtplib:", str(e))
    
