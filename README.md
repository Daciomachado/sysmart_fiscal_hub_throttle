# Sysmart Fiscal Hub - Tkinter

Versão em Tkinter para evitar erro de DLL do PySide6/QtCore.

## Recursos

- Busca NFC-e e cancelamentos na `tblPDVCupom`.
- Filtro por mês, ano e tipo.
- Marcar todos / desmarcar todos.
- Enviar selecionados.
- Lê `xmlNFCe` e `xmlCancelamento`.
- Não envia cancelamento quando o XML for apenas `retEnvEvento`.
- Grava controle em `tblIntegracaoFiscal`.
- Não altera `statusTransmissao`.

## Como usar

1. Execute `instalar_dependencias.bat`
2. Ajuste `config.ini`
3. Execute `sql/001_tblIntegracaoFiscal.sql`
4. Execute `executar.bat`

## Gerar EXE

Execute `gerar_exe.bat`.


## Versão mantendo a tela original

Esta versão mantém a tela com:

- Mês
- Ano
- Tipo
- Buscar
- Marcar Todos
- Desmarcar
- Enviar Selecionados
- Logs
- Barra inferior

A regra de envio/reenvio foi ajustada:

| Situação | Ação |
|---|---|
| Não existe na `tblIntegracaoFiscal` | Envia |
| `Status = F` | Reenvia |
| `Status = R` | Reenvia |
| `Status = T` | Não envia |
| `Status = E` | Não envia |
| `Status = X` | Não envia |

Quando o Portal retorna HTTP 200:

```text
Status = T
CodigoRetorno = 200
```


## Filtro de Situação

Foi adicionado o filtro **Situação** na tela principal.

Opções:

- **Pendências**: mostra documentos nunca enviados, com falha ou em reenvio.
- **Todos**: mostra todos conforme tipo/mês/ano.
- **Nunca Enviados**: não existe registro na `tblIntegracaoFiscal`.
- **Falhas**: `Status = F`.
- **Reenvio**: `Status = R`.
- **Enviados**: `Status = T`.
- **XML Inválido**: `Status = X`.
- **Enviando**: `Status = E`.

A seleção manual continua funcionando normalmente:

- Marcar Todos
- Desmarcar
- Enviar Selecionados


## Controle de requisições

Para evitar erro 500 no Portal por excesso de requisições, foram adicionados:

```ini
[SINCRONIZADOR]
limite_por_execucao=100
intervalo_entre_envios_segundos=3
pausar_apos_erro_500_segundos=30
```

Recomendado para servidor menor:

```ini
limite_por_execucao=50
intervalo_entre_envios_segundos=5
pausar_apos_erro_500_segundos=60
```
