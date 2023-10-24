import pandas as pd
import pyodbc
import oracledb
import warnings
from credentials import PASS_SQL_SINQIA, USER_SQL_SINQIA, USER_DB_ATIVA, PASS_DB_ATIVA, DSN, SRV_SINQIA


class Dbconn:
    def __init__(self) -> None:
        self.conn_oracle = oracledb.connect(
            user=USER_DB_ATIVA, password=PASS_DB_ATIVA, dsn=DSN)
        self.cur_oracle = self.conn_oracle.cursor()
        self.str_conn_sinqia = f"""Driver={{SQL Server}};Server={SRV_SINQIA};Database=SQCTRL;uid={USER_SQL_SINQIA};pwd={PASS_SQL_SINQIA}"""
        self.conn_sinqia = pyodbc.connect(self.str_conn_sinqia)

    def variacao_cotas_fundos(self, data, variacao):
        
        query = f"""SELECT t1.Carteira AS Fundo, 
                    t1.Data, 
                    t1.Valor AS ValorData,
                    COALESCE(t2.Valor, t1.Valor) AS "ValorData-1",
                    CASE 
                        WHEN t1.Valor = 0 THEN
                            CASE 
                                WHEN COALESCE(t2.Valor, 0) = 0 THEN '0.0%'
                                ELSE CONCAT('-', FORMAT(ABS(COALESCE(t2.Valor, 0) / NULLIF(ABS(t2.Valor), 0) * 100), '0.0'), '%')
                            END
                        ELSE
                            CONCAT(
                                CASE WHEN COALESCE(t2.Valor, t1.Valor) > t1.Valor THEN '-' ELSE '+' END,
                                FORMAT(ABS((t1.Valor - COALESCE(t2.Valor, t1.Valor)) / NULLIF(ABS(t1.Valor), 0) * 100), '0.0'),
                                '%'
                            )
                    END AS Variacao
                FROM MC51 t1
                LEFT JOIN (
                    SELECT Carteira, Indice, Data, Valor
                    FROM MC51
                ) t2 ON t1.Carteira = t2.Carteira
                    AND t1.Indice = t2.Indice
                    AND t1.Data = DATEADD(DAY, 1, t2.Data)
                WHERE t1.Indice = '@VCOTA'
                    AND t1.Data BETWEEN DATEADD(MONTH, -1, '{data}') AND '{data}'
                    AND ABS(COALESCE(t1.Valor - t2.Valor, 0)) >= (t1.Valor * {variacao}*0.01)
                ORDER BY t1.Carteira, t1.Data
                """
        # query = f"""SELECT t1.Carteira AS Fundo, 
        #                 t1.Data, 
        #                 t1.Valor AS ValorData,
        #                 COALESCE(t2.Valor, t1.Valor) AS "ValorData-1",
        #                 CONCAT(
        #                     CASE WHEN COALESCE(t2.Valor, t1.Valor) > t1.Valor THEN '-' ELSE '+' END,
        #                     FORMAT(ABS((t1.Valor - COALESCE(t2.Valor, t1.Valor)) / t1.Valor * 100), '0.0'),
        #                     '%'
        #                 ) AS Variacao
        #             FROM MC51 t1
        #             LEFT JOIN (
        #                 SELECT Carteira, Indice, Data, Valor
        #                 FROM MC51
        #             ) t2 ON t1.Carteira = t2.Carteira
        #                 AND t1.Indice = t2.Indice
        #                 AND t1.Data = DATEADD(DAY, 1, t2.Data)
        #             WHERE t1.Indice = '@VCOTA'
        #                 AND t1.Data BETWEEN DATEADD(MONTH, -1, '{data}') AND '{data}'
        #                 AND ABS(COALESCE(t1.Valor - t2.Valor, 0)) >= (t1.Valor * {variacao}*0.01)
        #             ORDER BY t1.Carteira, t1.Data
        #             """
        
        df_result = pd.read_sql_query(query, self.conn_sinqia)
        df_result['ValorData'] = df_result['ValorData'].round(8)
        df_result['ValorData'] = df_result['ValorData'].map('R$ {:.8f}'.format)
        df_result['ValorData-1'] = df_result['ValorData-1'].map('R$ {:.8f}'.format)

        df_result['Fundo'] = df_result['Fundo'].astype(str)
        
        # Ordenar o dataframe pela coluna 'Data' de forma
        # decrescente para que as últimas atualizações fiquem no topo
        df_result = df_result.sort_values(by=['Fundo', 'Data'], ascending=[True, False])
        
        # Agrupar o dataframe pelo número do fundo e selecionar 
        # a primeira linha de cada grupo (que contém a última atualização
        df_result = df_result.groupby('Fundo').first().reset_index()
        
        df_result = df_result.sort_values(by='Data', ascending=False)
        
        return df_result



    def fundos_ativa(self):
        query = """SELECT 
                    tb_fundo.FC_CPFCGC as CNPJ,
                    MAX(tb_fundo.FC_NMFUNDO) AS Nome_Fundo,
                    --portalativa.risco_patrimonio_cliente.CD_CPFCGC as CNPJ,
                    REGEXP_REPLACE(MAX(portalativa.risco_patrimonio_cliente.CODCLIENTE), '.$') AS Fundo
                FROM tb_fundo
                JOIN portalativa.risco_patrimonio_cliente
                    ON tb_fundo.FC_CPFCGC = portalativa.risco_patrimonio_cliente.CD_CPFCGC
                WHERE tb_fundo.FN_VISIBILIDADE_PORTAL = 1 OR tb_fundo.FN_VISIBILIDADE = 1
                GROUP BY 
                    tb_fundo.FC_CPFCGC,
                    portalativa.risco_patrimonio_cliente.CD_CPFCGC"""
        result = self.cur_oracle.execute(query).fetchall()
        df = pd.DataFrame(result, columns=['CNPJ', 'NOME_FUNDO', 'Fundo'])
        df['CNPJ'] = df['CNPJ'].astype(str)
        return df


    def tb_fundos(self):
        warnings.filterwarnings("ignore", category=FutureWarning)
        query = """SELECT 
                    FC_CPFCGC AS CNPJ,
                    FC_NMFUNDO
                FROM tb_fundo
                WHERE FN_VISIBILIDADE_PORTAL = 1 OR FN_VISIBILIDADE = 1"""
        result = self.cur_oracle.execute(query).fetchall()
        DF_TB_FUNDO = pd.DataFrame(result,
                                columns=['CNPJ',
                                        'FC_NMFUNDO'])
        DF_TB_FUNDO['CNPJ'] = DF_TB_FUNDO['CNPJ'].astype(str)
        return DF_TB_FUNDO


    def get_rentabilidade_fundos(self, carteira): 
        query = f"""WITH LastBusinessDays AS (
                    SELECT t1.Carteira, MAX(t1.Data) AS LastBusinessDay, t1.Valor
                    FROM MC51 t1
                    JOIN (
                        SELECT YEAR(Data) AS Year, MONTH(Data) AS Month, MAX(Data) AS LastDay
                        FROM MC51
                        WHERE Carteira = {carteira}
                        AND Indice = '@VCOTA'
                        AND YEAR(Data) >= 2020
                        GROUP BY YEAR(Data), MONTH(Data)
                    ) last_days ON t1.Data = last_days.LastDay
                    WHERE Carteira = {carteira}
                    AND Indice = '@VCOTA'
                    AND YEAR(t1.Data) >= 2020
                    AND DATEPART(dw, t1.Data) NOT IN (1, 7) -- Exclui Domingos (1) e Sábados (7)
                    GROUP BY t1.Carteira, t1.Valor, YEAR(t1.Data), MONTH(t1.Data)
                )
                SELECT
                    lbd.Carteira,
                    lbd.LastBusinessDay,
                    (
                        SELECT MAX(Data)
                        FROM MC51
                        WHERE Carteira = lbd.Carteira
                        AND Indice = '@VCOTA'
                        AND YEAR(Data) = YEAR(DATEADD(YEAR, 1, lbd.LastBusinessDay))
                        AND MONTH(Data) = MONTH(DATEADD(YEAR, 1, lbd.LastBusinessDay))
                        AND DATEPART(dw, Data) NOT IN (1, 7)
                    ) AS LastBusinessDayPos1year,
                    (
                        SELECT TOP 1 Valor
                        FROM MC51
                        WHERE Carteira = lbd.Carteira
                        AND Indice = '@VCOTA'
                        AND Data = lbd.LastBusinessDay
                    ) AS ValorLastBusinessDay,
                    (
                        SELECT TOP 1 Valor
                        FROM MC51
                        WHERE Carteira = lbd.Carteira
                        AND Indice = '@VCOTA'
                        AND Data = (
                            SELECT MAX(Data)
                            FROM MC51
                            WHERE Carteira = lbd.Carteira
                            AND Indice = '@VCOTA'
                            AND YEAR(Data) = YEAR(DATEADD(YEAR, 1, lbd.LastBusinessDay))
                            AND MONTH(Data) = MONTH(DATEADD(YEAR, 1, lbd.LastBusinessDay))
                            AND DATEPART(dw, Data) NOT IN (1, 7)
                        )
                    ) AS ValorLastBusinessDayPos1year
                FROM LastBusinessDays lbd
                ORDER BY lbd.LastBusinessDay ASC;
                    """

        df_result = pd.read_sql_query(query, self.conn_sinqia)
        df_result.rename(columns={'LastBusinessDay': 'Data_A'}, inplace=True)
        df_result.rename(columns={'LastBusinessDayPos1year': 'Data_B'}, inplace=True)
        df_result.rename(columns={'ValorLastBusinessDay': 'ValorData_A'}, inplace=True)
        df_result.rename(columns={'ValorLastBusinessDayPos1year': 'ValorData_B'}, inplace=True)
        
        df_result['ValorData_A'] = df_result['ValorData_A'].replace(0, 0.00001)
        
        df_result['Rentabilidade_AB'] = ((df_result['ValorData_B'] 
                                    - df_result['ValorData_A'])
                                    / df_result['ValorData_A']) * 100
        return df_result


    def vcf_sinacor_posi_acoes_opc_termo(self):
        query = """SELECT 
                        cod_cli, 
                        idt_ativ, 
                        nome_cli, 
                        cod_isin, 
                        tipo_merc, 
                        cod_neg, 
                        qtde_tot, 
                        qtde_disp
                    FROM corrwin.vcfposicao
                    WHERE cod_cli IN ('1', 
                                    '140145', 
                                    '419572', 
                                    '96144', 
                                    '145837', 
                                    '73899', 
                                    '72402',
                                    '149739', 
                                    '95890',
                                    '96994', 
                                    '98186',
                                    '106824',
                                    '146207',
                                    '101610',
                                    '126087',
                                    '126088',
                                    '421180',
                                    '166654',  '12560', '145837', '49948')"""
                                    
        result = self.cur_oracle.execute(query).fetchall()
        df = pd.DataFrame(result,
                                columns=['cod_cli', 'idt_ativ', 
                                        'nome_cli', 'cod_isin', 
                                        'tipo_merc', 'cod_neg', 
                                        'qtde_tot', 'qtde_disp'])
        return df


    def tcf_sinacor_posi_proventos(self):
        
        query = """SELECT COD_CLI,
                        COD_ISIN,
                        QTDE_PROV, 
                        VAL_PROV, 
                        DATA_DEB_SUBS,
                        DATA_AQUI_TITU
                    FROM corrwin.tcfposi_prov_prev
                        WHERE cod_cli IN ('1', 
                                        '140145', 
                                        '419572', 
                                        '96144', 
                                        '145837', 
                                        '73899', 
                                        '72402', 
                                        '149739', 
                                        '95890', 
                                        '96994', 
                                        '98186', 
                                        '106824', 
                                        '146207', 
                                        '101610', 
                                        '126087', 
                                        '126088', 
                                        '421180', 
                                        '166654', '12560', '145837', '49948')"""
                                        
        result = self.cur_oracle.execute(query).fetchall()
        df = pd.DataFrame(result,
                                columns=['COD_CLI',
                                        'COD_ISIN',
                                        'QTDE_PROV', 
                                        'VAL_PROV', 
                                        'DATA_DEB_SUBS',
                                        'DATA_AQUI_TITU'])
        return df
    
    def sinacor_posicoes_bmf(self):
        query = """SELECT CD_CLIENTE, 
                NM_CLIENTE, 
                CD_COMMOD,
                CD_SERIE, 
                DT_DATMOV,
                QT_POSATU, 
                VL_AJUPOS
                FROM corrwin.vmfposicao
                WHERE CD_CLIENTE IN ('1', 
                                        '140145', 
                                        '419572', 
                                        '96144', 
                                        '145837', 
                                        '73899', 
                                        '72402', 
                                        '149739', 
                                        '95890', 
                                        '96994', 
                                        '98186', 
                                        '106824', 
                                        '146207', 
                                        '101610', 
                                        '126087', 
                                        '126088', 
                                        '421180', 
                                        '166654', '12560', '145837', '49948')"""
                                        
        result = self.cur_oracle.execute(query).fetchall()
        df = pd.DataFrame(result,
                                columns=['CD_CLIENTE', 'NM_CLIENTE', 
                                        'CD_COMMOD',
                                        'CD_SERIE', 
                                        'DT_DATMOV',
                                        'QT_POSATU', 
                                        'VL_AJUPOS'])
        return df
    
    def portalativa_posi_fundos(self):
        query = """SELECT CODIGO AS CD_CLIENTE, 
                            NM_CLIENTE,
                            CODIGOFUNDOSINACOR AS FUNDO,
                            NM_ABREVIADO AS CD_FUNDO,
                            QTDCOTAS, 
                            VALORAPLICACAO, 
                            VALORCORRIGIDO, 
                            VALORRESGATE from portalativa.riscopsct
                        WHERE CODIGO IN ('1', 
                                        '140145', 
                                        '419572', 
                                        '96144', 
                                        '145837', 
                                        '73899', 
                                        '72402', 
                                        '149739', 
                                        '95890', 
                                        '96994', 
                                        '98186', 
                                        '106824', 
                                        '146207', 
                                        '101610', 
                                        '126087', 
                                        '126088', 
                                        '421180', 
                                        '166654', '12560', '145837', '49948')"""
                                        
        result = self.cur_oracle.execute(query).fetchall()
        df = pd.DataFrame(result,
                            columns=['CD_CLIENTE', 
                                    'NM_CLIENTE',
                                    'FUNDO',
                                    'CD_FUNDO',
                                    'QTDCOTAS', 
                                    'VALORAPLICACAO', 
                                    'VALORCORRIGIDO', 
                                    'VALORRESGATE'])
        return df
    
    def portalativa_risco_garantia(self):
        query = """SELECT * from portalativa.risco_garantia
                    WHERE COD_CLI IN ('1', 
                                        '140145', 
                                        '419572', 
                                        '96144', 
                                        '145837', 
                                        '73899', 
                                        '72402', 
                                        '149739', 
                                        '95890', 
                                        '96994', 
                                        '98186', 
                                        '106824', 
                                        '146207', 
                                        '101610', 
                                        '126087', 
                                        '126088', 
                                        '421180', 
                                        '166654', '12560', '145837', '49948')"""
        result = self.cur_oracle.execute(query).fetchall()
        df = pd.DataFrame(result,
                            columns=['ID', 
                                    'COD_CLI', 
                                    'GARANTIA_DEPOSITADA', 
                                    'GARANTIA_REQUERIDA'])
        return df
    
    def portalativa_riscodgar(self):
        query="""SELECT * from portalativa.riscodgar
                    WHERE COD IN ('1', 
                                    '140145', 
                                    '419572', 
                                    '96144', 
                                    '145837', 
                                    '73899', 
                                    '72402', 
                                    '149739', 
                                    '95890', 
                                    '96994', 
                                    '98186', 
                                    '106824', 
                                    '146207', 
                                    '101610', 
                                    '126087', 
                                    '126088', 
                                    '421180', 
                                    '166654', '12560', '145837', '49948')"""
        result = self.cur_oracle.execute(query).fetchall()
        df = pd.DataFrame(result,
                            columns=['ID', 
                                    'DATAPOSICAO', 
                                    'COD', 
                                    'TIPO', 'ATIVO', 'DATADEPOSITO', 'DATAVENCIMENTO',
                                    'CODIGONEGOCIACAO', 'EMPRESA', 'QUANTIDADE', 'VALOR'])
        return df
    
    def tcfposi_btc_doad(self):
        query = """SELECT COD_CLI, 
                            COD_ISIN, 
                            TIPO_MERC_BTC,  
                            TIPO_MERC,
                            QTDE_ACOE,
                            PREC_MED,
                            TAXA_REMU,
                            VAL_BRUT,
                            VAL_IR,
                            VAL_LIQ,
                            VAL_BRUT_DOAD
                            FROM tcfposi_btc_DOAD
                            WHERE COD_CLI IN ('1', 
                                                '140145', 
                                                '419572', 
                                                '96144', 
                                                '145837', 
                                                '73899', 
                                                '72402', 
                                                '149739', 
                                                '95890', 
                                                '96994', 
                                                '98186', 
                                                '106824', 
                                                '146207', 
                                                '101610', 
                                                '126087', 
                                                '126088', 
                                                '421180', 
                                                '166654', '12560', '145837', '49948')"""
        result = self.cur_oracle.execute(query).fetchall()
        df = pd.DataFrame(result,
                            columns=['COD_CLI', 
                            'COD_ISIN', 
                            'TIPO_MERC_BTC',  
                            'TIPO_MERC',
                            'QTDE_ACOE',
                            'PREC_MED',
                            'TAXA_REMU',
                            'VAL_BRUT',
                            'VAL_IR',
                            'VAL_LIQ',
                            'VAL_BRUT_DOAD'])
        return df
    
    def tcfposi_btc_toma(self):
        query = """SELECT COD_CLI,
                            COD_ISIN,
                            PREC_MED,
                            TAXA_REMU,
                            TAXA_COMI,
                            QTDE_ACOE_ORIG,
                            COD_CLI_CANT,
                            VAL_BRUT,
                            VAL_COMI,
                            VAL_BRUT_DOAD,
                            VAL_LIQ,
                            VAL_EMOL_CBLC
                        FROM tcfposi_btc_toma
                        WHERE COD_CLI IN ('1', 
                                        '140145', 
                                        '419572', 
                                        '96144', 
                                        '145837', 
                                        '73899', 
                                        '72402', 
                                        '149739', 
                                        '95890', 
                                        '96994', 
                                        '98186', 
                                        '106824', 
                                        '146207', 
                                        '101610', 
                                        '126087', 
                                        '126088', 
                                        '421180', 
                                        '166654', '12560', '145837', '49948')"""
        result = self.cur_oracle.execute(query).fetchall()
        df = pd.DataFrame(result,
                            columns=['COD_CLI',
                            'COD_ISIN',
                            'PREC_MED',
                            'TAXA_REMU',
                            'TAXA_COMI',
                            'QTDE_ACOE_ORIG',
                            'COD_CLI_CANT',
                            'VAL_BRUT',
                            'VAL_COMI',
                            'VAL_BRUT_DOAD',
                            'VAL_LIQ',
                            'VAL_EMOL_CBLC'])
        return df
    


# def valor_do_fundo_na_data(fundo, data):
#     str_conn_sinqia = f"""Driver={{SQL Server}};Server={SRV_SINQIA};Database=SQCTRL;uid={USER_SQL_SINQIA};pwd={PASS_SQL_SINQIA}"""
#     conn_sinqia = pyodbc.connect(str_conn_sinqia)
        
#     query = f"""SELECT Carteira AS Fundo, 
#                 Data, 
#                 Valor AS ValorData
#             FROM MC51
#             WHERE Indice = '@VCOTA'
#                 AND Data = '{data}'
#                 AND Carteira = '{fundo}'
#             """
#     df_result = pd.read_sql_query(query, conn_sinqia)
#     df_result['ValorData'] = df_result['ValorData'].round(8)
#     df_result['ValorData'] = df_result['ValorData'].map('R$ {:.8f}'.format)

#     df_result['Fundo'] = df_result['Fundo'].astype(str)
#     df_result = df_result.sort_values(by=['Fundo', 'Data'], ascending=[True, False])
#     df_result = df_result.groupby('Fundo').first().reset_index()
    
#     df_result = df_result.sort_values(by='Data', ascending=False)
    
#     return df_result

