from dbconn import Dbconn
from datetime import timedelta, date, datetime
import pandas as pd
from functools import reduce
import os
import numpy as np
import sys
from utils import send_mail_smtplib, replace_html
from credentials import PASS_CENTRAL_OP

global data
data = None

class Vericota:
    def __init__(self):
        global data
        self.root_dir = os.getcwd()
        self.sender = "central.operacao@ativainvestimentos.com.br"
        self.variacao_percent = 3
        
        if date.today().weekday() == 0:  # se hoje é segunda-feira
            # yestesday_date <= sexta-feira
            data = (date.today() - timedelta(3)).strftime("%Y-%m-%d")
        else:
            data = (date.today() - timedelta(1)).strftime("%Y-%m-%d")
        self.todos_os_fundos_cotas = Dbconn().variacao_cotas_fundos(data,0)
        #self.todos_os_fundos_cotas = get_sinqia_conn(self.conn_sinqia, data, 0)
        self.df_fundos = self.fundos_cnpj_cod()  # Base tb_fundos + tsclibol

    def atualizacao_britech(self):
        FROM_MAIL = self.sender
        TO_MAIL = ['tBPO@britech.com.br',
                   'adm.fiduciaria@ativainvestimentos.com.br']
        CC_MAIL = ['mateus.silva@ativainvestimentos.com.br', 'paloma.sette@ativainvestimentos.com.br']
        SUBJECT = 'Cotas atuais dos fundos + Posições (BM&F, TCF, VCF e garantias)'
        MESSAGE = """<head>
                        <style>
                            body {
                                font-family: Arial, sans-serif;
                            }
                            .mensagem {
                                font-weight: bold;
                                font-size: 15px;
                                margin-bottom: 0px;
                            }
                            .saudacao {
                                margin-bottom: 0px;
                            }
                            .lista {
                                margin-left: 5px;
                            }
                            .item-lista {
                                margin-bottom: 0px;
                            }
                        </style>
                    </head>

                    <body>
                        <div class="mensagem">[MENSAGEM AUTOMÁTICA]</div><br>
                        <div class="saudacao">Bom dia, prezados</div>
                        <div class="corpo-email">
                            <p>Segue, em anexo, o documento referente às cotas atualizadas dos fundos de investimento. Além deste, outros documentos anexados:</p>
                            <ul class="lista">
                                <li class="item-lista">Posições em fundos;</li>
                                <li class="item-lista">Posições em TCF (Proventos);</li>
                                <li class="item-lista">Posições em VCF (Ações, OPC e termo);</li>
                                <li class="item-lista">Posições em BM&F;</li>
                                <li class="item-lista">Garantia (depositada e requerida);</li>
                                <li class="item-lista">BTC (Tomador e Doador).</li><br>
                            </ul>
                        </div>
                    </body>"""               
        HTML_CONTENT = replace_html('signature_template.html', MESSAGE)
        PATHS_ATTACHS = []
        
        # substituindo o cod (V8 Cash) 98531 (Sinqia) por 135750 (Portal)
        self.adjust_fund_code(self.todos_os_fundos_cotas, 'Fundo', '98531', '135750')

        df_list = [self.todos_os_fundos_cotas.reset_index(drop=True), self.df_fundos]
        fundos_cotas_com_cnpj =  reduce(lambda left, right: pd.merge(left, right, on=['Fundo'],
                                                                how='outer'), df_list).fillna("")
        fundos_cotas_com_cnpj.dropna(subset=['Data', 
                                            'ValorData', 
                                            'ValorData-1', 
                                            'Variacao'], how='any', inplace=True)
        del fundos_cotas_com_cnpj['ValorData-1']
        del fundos_cotas_com_cnpj['Variacao']
        del fundos_cotas_com_cnpj['Fundo']
        fundos_cotas_com_cnpj.replace('', np.nan, inplace=True)

        novo_nome_colunas = {
            'Data': 'ultima_atualização',
            'ValorData': 'valor_atual',
            'NOME_FUNDO': 'nome_fundo'
        }
        fundos_cotas_com_cnpj.rename(columns=novo_nome_colunas, inplace=True)
        fundos_cotas_com_cnpj= fundos_cotas_com_cnpj.dropna(subset=['CNPJ'])
        # Salvando os arquivos para enviar por e-mail
        dic = {
                'docs\\fundos_cotasAtuais.xlsx':        fundos_cotas_com_cnpj,
                'docs\\tcf_posi_proventos.xlsx':        Dbconn().tcf_sinacor_posi_proventos(),
                'docs\\vcf_posi_acoes_opc_termo.xlsx':  Dbconn().vcf_sinacor_posi_acoes_opc_termo(),
                'docs\\posicoes_bmf.xlsx':              Dbconn().sinacor_posicoes_bmf(),
                'docs\\posicoes_cli_fundos.xlsx':       Dbconn().portalativa_posi_fundos(),
                'docs\\garantias_req_dep.xlsx':         Dbconn().portalativa_risco_garantia(),
                'docs\\portalativa_riscodgar.xlsx':     Dbconn().portalativa_riscodgar(),
                'docs\\tcfposi_btc_doad.xlsx':          Dbconn().tcfposi_btc_doad(),
                'docs\\tcfposi_btc_toma.xlsx':          Dbconn().tcfposi_btc_toma()
               }
        for path, df in dic.items():
            df.to_excel(path, index=False)
            PATHS_ATTACHS.append(path)
        
        send_mail_smtplib(FROM_MAIL,
                  PASS_CENTRAL_OP, 
                  TO_MAIL,
                  SUBJECT,
                  HTML_CONTENT,
                  CC_MAIL,
                  PATHS_ATTACHS)
        print("Email Britech enviado!")

    def atualicao_variacao_cota(self):
        global data
        FROM_MAIL = self.sender
        TO_MAIL = ["backofficefundos@ativainvestimentos.com.br"] 
        CC_MAIL = ['mateus.silva@ativainvestimentos.com.br', 'paloma.sette@ativainvestimentos.com.br']
        SUBJECT = 'Atualização de Variação de Cota'                
        
        data_atual = datetime.now().strftime("%d-%m-%Y_%H-%M")
        # Fundos com variação específica de cota  atualizada
        fundos_cotas = Dbconn().variacao_cotas_fundos( data, self.variacao_percent).reset_index(drop=True)  # Base de dados da Sinqia
        fundos_cotas_atuali =  self.fundos_cotas_atualizadas(fundos_cotas, data)

        # fundos com cota desatualizada
        fundos_cotas_desatual = self.fundos_cotas_desatualizadas(
            self.todos_os_fundos_cotas).reset_index(drop=True)
        del fundos_cotas_desatual['ValorData']
        del fundos_cotas_desatual['ValorData-1']
        del fundos_cotas_desatual['Variacao']

        data_frames_at = [fundos_cotas_atuali, self.df_fundos]
        data_frames_desat = [fundos_cotas_desatual, self.df_fundos]

        # fazendo o merge apenas para inserir o CNPJ
        merged_atualizados = reduce(lambda left, right: pd.merge(left, right, on=['Fundo'],
                                                                how='inner'), data_frames_at).fillna(0)
        merged_desatualizados = reduce(lambda left, right: pd.merge(left, right, on=['Fundo'],
                                                                    how='inner'), data_frames_desat).fillna(0)
        qtd_fundos_desat = len(fundos_cotas_desatual)

        print("\nSalvando a planilha...\n")
        hist_dir = "docs\\historico_variacota"
        file_name = hist_dir+"\\ATUALIZACAO_"+data_atual+".xlsx"

        file = pd.ExcelWriter(file_name, engine='openpyxl')
        merged_atualizados.to_excel(file, sheet_name='Cotas_Atualiz_E_Com_Variacao', index=False)
        merged_desatualizados.to_excel(file, sheet_name='Cotas_Desatualizadas', index=False)
        file.close()

        data_date = date.fromisoformat(data)
        data_formatada = data_date.strftime("%d/%m/%Y")

        MESSAGE = """<head>
                        <style>
                            body {
                                font-family: Arial, sans-serif;
                            }
                            .mensagem {
                                font-weight: bold;
                                font-size: 15px;
                                margin-bottom: 0px;
                            }
                            .saudacao {
                                margin-bottom: 0px;
                            }
                            .lista {
                                margin-left: 5px;
                            }
                            .item-lista {
                                margin-bottom: 0px;
                            }
                        </style>
                    </head>

                    <body>
                        <div class="mensagem">[MENSAGEM AUTOMÁTICA]</div><br>
                        <div class="saudacao">Prezados,</div>
                        <div class="corpo-email">
                        """+f"""
                        <p>Segue as cotas cuja variação foi >= {self.variacao_percent}% em um período de 24h, considerando a data de {data_formatada}:</p>
                            {fundos_cotas_atuali.to_html(index=False).replace(
                                '<td>', '<td align="center">')}
                                """+f"""
                                <p>Abaixo, segue os {qtd_fundos_desat} fundos com cotas desatualizadas, isto é, cujas últimas atualizações foram anteriores a D-2 dentro do período de 1 mês.</p>
                                """+f"""
                                {fundos_cotas_desatual.to_html(index=False).replace('<td>', '<td align="center">')}
                                <p>Apenas com o intuito de facilitar vosso processo de análise, \
                                    o robô gerou um arquivo excel (em anexo) com as duas \
                                        tabelas apresentadas acima e adicionou o \
                                            CNPJ respectivo de cada fundo. \
                                                Ressalto que se algum fundo \
                                                    apresentado acima estiver \
                                                        em falta nas planilhas anexadas, \
                                                            é possível que este esteja cadastrado \
                                                                com um código na Ativa que difere\
                                                                    do código na Sinqia. \
                                                                        Portanto, recomenda-se \
                                                                            priorizar os dados do corpo do \
                                                                                e-mail. </p>
                        </div>
                    </body><br><br>"""               
        HTML_CONTENT = replace_html('signature_template.html', MESSAGE)
        PATHS_ATTACHS = [file_name]
        print("Email de variação de cotas enviado!")
        send_mail_smtplib(FROM_MAIL,
                  PASS_CENTRAL_OP, 
                  TO_MAIL,
                  SUBJECT,
                  HTML_CONTENT,
                  CC_MAIL,
                  PATHS_ATTACHS)
        #os.execl(sys.executable, os.path.abspath(__file__), *sys.argv)

    def fundos_cnpj_cod(self):
        data_frames = [Dbconn().fundos_ativa(), Dbconn().tb_fundos()]
        df_mg = reduce(lambda left, right: pd.merge(left, right, on=['CNPJ'],
                                                    how='inner'), data_frames).fillna(0)
        #del df_mg['NOME_FUNDO']
        del df_mg['FC_NMFUNDO']

        return df_mg

    # Função temporária para substituição de codigos de fundos num df
    # Há fundos que estão com código diferente na Sinqia, isso faz com que
    # dados se percam durante as interseções de informações
    def adjust_fund_code(self, df, col_name, cod_ant, cod_new):
        if (df[col_name] == cod_ant).any():
        # Substituir '98531' por '135750' em todas as células da coluna "Fundo"
            df[col_name] = df[col_name].replace(cod_ant, cod_new)

    def fundos_cotas_desatualizadas(self,df):
        # Converter a coluna 'Data' para o formato de data (caso ela não esteja no formato correto).
        df['Data'] = pd.to_datetime(df['Data'])
        # Ordenar o DataFrame pela coluna 'Data' em ordem decrescente.
        df.sort_values(by='Data', ascending=False, inplace=True)
        # Selecionar as duas primeiras datas após a classificação.
        duas_datas_mais_recentes = df['Data'].unique()[:2]
        # Remover as linhas com as duas datas mais recentes.
        df2 = df[~df['Data'].isin(duas_datas_mais_recentes)]
        # Resetar o índice do DataFrame após a remoção.
        df2.reset_index(drop=True, inplace=True)
        
        return df2


    def fundos_cotas_atualizadas(self,df, specific_date):
        global data
        # Verificar se a coluna 'Data' já está no formato datetime
        if not pd.api.types.is_datetime64_any_dtype(df['Data']):
            df['Data'] = pd.to_datetime(df['Data'])

        filtered_df = df[df['Data'] == specific_date]

        return filtered_df