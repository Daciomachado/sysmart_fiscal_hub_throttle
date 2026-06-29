import pyodbc

def conectar(cfg):
    parts = [
        f"DRIVER={{{cfg.driver}}}",
        f"SERVER={cfg.server}",
        f"DATABASE={cfg.database}",
    ]
    if cfg.user:
        parts += [f"UID={cfg.user}", f"PWD={cfg.password}"]
    else:
        parts.append("Trusted_Connection=yes")
    if cfg.trust_server_certificate:
        parts.append(f"TrustServerCertificate={cfg.trust_server_certificate}")
    return pyodbc.connect(";".join(parts) + ";", timeout=10)

def garantir_tabela_integracao(conn):
    sql = '''
IF OBJECT_ID('dbo.tblIntegracaoFiscal', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.tblIntegracaoFiscal
    (
        ID INT IDENTITY(1,1) PRIMARY KEY,
        SistemaDestino VARCHAR(50) NOT NULL,
        TipoDocumento VARCHAR(20) NOT NULL,
        ChaveDocumento VARCHAR(60) NOT NULL,
        NumCupom INT NULL,
        NumNFCe INT NULL,
        CodLoja VARCHAR(3) NULL,
        NumCaixa INT NULL,
        DataEmissao DATETIME NULL,
        Status CHAR(1) NOT NULL DEFAULT('P'),
        Tentativas INT NOT NULL DEFAULT(0),
        CodigoRetorno VARCHAR(50) NULL,
        MensagemRetorno VARCHAR(MAX) NULL,
        DataCadastro DATETIME NOT NULL DEFAULT(GETDATE()),
        DataEnvio DATETIME NULL,
        DataUltimaTentativa DATETIME NULL
    );
END
'''
    conn.cursor().execute(sql)
    conn.commit()
