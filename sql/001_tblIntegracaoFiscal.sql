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
GO
