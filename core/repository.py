from datetime import datetime
from dateutil.relativedelta import relativedelta

def periodo_mes(ano, mes):
    ini = datetime(ano, mes, 1)
    return ini, ini + relativedelta(months=1)

def listar_documentos(conn, ano, mes, tipo="TODOS", situacao="PENDENCIAS", max_tentativas=20):
    ini, fim = periodo_mes(ano, mes)

    sql = '''
SELECT *
FROM
(
    SELECT
        'NFCE' AS TipoDocumento,
        c.chaveNfce AS ChaveDocumento,
        c.numNFCe,
        c.numCupom,
        c.dataEmissao,
        c.codLoja,
        c.numCaixa,
        c.nomeConsumidor,
        c.valorTotal,
        c.statusNfce,
        i.ID AS IntegracaoID,
        ISNULL(i.Status, 'P') AS PortalStatus,
        ISNULL(i.Tentativas, 0) AS Tentativas,
        ISNULL(i.CodigoRetorno, '') AS CodigoRetorno,
        DATALENGTH(c.xmlNFCe) AS TamanhoXml
    FROM dbo.tblPDVCupom c
    OUTER APPLY
    (
        SELECT TOP 1 *
        FROM dbo.tblIntegracaoFiscal i
        WHERE i.SistemaDestino = 'Portal Contador'
          AND i.TipoDocumento = 'NFCE'
          AND i.ChaveDocumento = c.chaveNfce
        ORDER BY i.ID DESC
    ) i
    WHERE c.xmlNFCe IS NOT NULL
      AND c.chaveNfce IS NOT NULL
      AND ISNULL(c.cupomCancelado, 'N') <> 'S'
      AND c.dataEmissao >= ?
      AND c.dataEmissao < ?
      AND (
            i.ID IS NULL
            OR ISNULL(i.Status, '') IN ('F','R')
          )
      AND ISNULL(i.Tentativas, 0) < ?

    UNION ALL

    SELECT
        'CANCELAMENTO' AS TipoDocumento,
        c.chaveNfce AS ChaveDocumento,
        c.numNFCe,
        c.numCupom,
        c.dataEmissao,
        c.codLoja,
        c.numCaixa,
        c.nomeConsumidor,
        c.valorTotal,
        c.statusNfce,
        i.ID AS IntegracaoID,
        ISNULL(i.Status, 'P') AS PortalStatus,
        ISNULL(i.Tentativas, 0) AS Tentativas,
        ISNULL(i.CodigoRetorno, '') AS CodigoRetorno,
        DATALENGTH(c.xmlCancelamento) AS TamanhoXml
    FROM dbo.tblPDVCupom c
    OUTER APPLY
    (
        SELECT TOP 1 *
        FROM dbo.tblIntegracaoFiscal i
        WHERE i.SistemaDestino = 'Portal Contador'
          AND i.TipoDocumento = 'CANCELAMENTO'
          AND i.ChaveDocumento = c.chaveNfce
        ORDER BY i.ID DESC
    ) i
    WHERE c.xmlCancelamento IS NOT NULL
      AND c.chaveNfce IS NOT NULL
      AND c.dataEmissao >= ?
      AND c.dataEmissao < ?
      AND (
            i.ID IS NULL
            OR ISNULL(i.Status, '') IN ('F','R')
          )
      AND ISNULL(i.Tentativas, 0) < ?
) X
WHERE (? = 'TODOS' OR X.TipoDocumento = ?)
  AND
  (
      ? = 'TODOS'
      OR (? = 'PENDENCIAS' AND (X.IntegracaoID IS NULL OR X.PortalStatus IN ('F','R')))
      OR (? = 'NUNCA' AND X.IntegracaoID IS NULL)
      OR (? = 'FALHAS' AND X.PortalStatus = 'F')
      OR (? = 'REENVIO' AND X.PortalStatus = 'R')
      OR (? = 'ENVIADOS' AND X.PortalStatus = 'T')
      OR (? = 'INVALIDOS' AND X.PortalStatus = 'X')
      OR (? = 'ENVIANDO' AND X.PortalStatus = 'E')
  )
ORDER BY X.dataEmissao, X.numCupom
'''
    rows = conn.cursor().execute(sql, [ini, fim, max_tentativas, ini, fim, max_tentativas, tipo, tipo, situacao, situacao, situacao, situacao, situacao, situacao, situacao, situacao]).fetchall()

    docs = []
    for r in rows:
        docs.append({
            "marcado": False,
            "tipo": str(r.TipoDocumento),
            "chave": str(r.ChaveDocumento),
            "num_nfce": r.numNFCe,
            "num_cupom": r.numCupom,
            "data_emissao": r.dataEmissao,
            "cod_loja": r.codLoja,
            "num_caixa": r.numCaixa,
            "nome_consumidor": r.nomeConsumidor,
            "valor_total": float(r.valorTotal or 0),
            "status_nfce": r.statusNfce,
            "integracao_id": r.IntegracaoID,
            "portal_status": r.PortalStatus,
            "tentativas": int(r.Tentativas or 0),
            "codigo_retorno": r.CodigoRetorno,
            "tamanho_xml": int(r.TamanhoXml or 0),
        })
    return docs

def obter_xml(conn, chave, tipo):
    coluna = "xmlNFCe" if tipo == "NFCE" else "xmlCancelamento"
    row = conn.cursor().execute(
        f"SELECT {coluna} FROM dbo.tblPDVCupom WHERE chaveNfce = ? AND {coluna} IS NOT NULL",
        chave
    ).fetchone()

    if not row:
        raise Exception("XML não encontrado")

    data = row[0]
    if isinstance(data, memoryview):
        return data.tobytes()
    if isinstance(data, bytes):
        return data
    return bytes(data)

def registrar_resultado(conn, doc, sucesso, codigo, mensagem):
    status = "T" if sucesso else "F"

    sql = '''
DECLARE @ID INT;

SELECT @ID = ID
FROM dbo.tblIntegracaoFiscal
WHERE ID = (
    SELECT TOP 1 ID
    FROM dbo.tblIntegracaoFiscal
    WHERE SistemaDestino = 'Portal Contador'
      AND TipoDocumento = ?
      AND ChaveDocumento = ?
    ORDER BY ID DESC
);

IF @ID IS NULL
BEGIN
    INSERT INTO dbo.tblIntegracaoFiscal
    (
        SistemaDestino,
        TipoDocumento,
        ChaveDocumento,
        NumCupom,
        NumNFCe,
        CodLoja,
        NumCaixa,
        DataEmissao,
        Status,
        Tentativas,
        CodigoRetorno,
        MensagemRetorno,
        DataEnvio,
        DataUltimaTentativa
    )
    VALUES
    (
        'Portal Contador',
        ?, ?, ?, ?, ?, ?, ?,
        ?,
        CASE WHEN ? = 'T' THEN 0 ELSE 1 END,
        ?, ?,
        CASE WHEN ? = 'T' THEN GETDATE() ELSE NULL END,
        GETDATE()
    );
END
ELSE
BEGIN
    UPDATE dbo.tblIntegracaoFiscal
    SET Status = ?,
        Tentativas = CASE WHEN ? = 'T' THEN Tentativas ELSE Tentativas + 1 END,
        CodigoRetorno = ?,
        MensagemRetorno = ?,
        DataEnvio = CASE WHEN ? = 'T' THEN GETDATE() ELSE DataEnvio END,
        DataUltimaTentativa = GETDATE()
    WHERE ID = @ID;
END
'''
    codigo_texto = "200" if sucesso else str(codigo)
    conn.cursor().execute(
        sql,
        doc["tipo"], doc["chave"],
        doc["tipo"], doc["chave"], doc["num_cupom"], doc["num_nfce"], doc["cod_loja"], doc["num_caixa"], doc["data_emissao"],
        status, status, codigo_texto, str(mensagem)[:4000], status,
        status, status, codigo_texto, str(mensagem)[:4000], status
    )
    conn.commit()
