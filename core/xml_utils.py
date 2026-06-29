import binascii
import xml.etree.ElementTree as ET

class XmlDocumentoInvalido(Exception):
    pass

def normalizar_xml_bytes(xml_bytes):
    if xml_bytes is None:
        return b""
    if isinstance(xml_bytes, memoryview):
        xml_bytes = xml_bytes.tobytes()
    if not isinstance(xml_bytes, bytes):
        xml_bytes = bytes(xml_bytes)
    limpo = xml_bytes.strip()
    if limpo[:2].lower() == b"0x":
        try:
            return binascii.unhexlify(limpo[2:].decode("ascii", errors="ignore"))
        except Exception:
            return xml_bytes
    return xml_bytes

def obter_raiz_xml(xml_bytes):
    xml_bytes = normalizar_xml_bytes(xml_bytes)
    try:
        root = ET.fromstring(xml_bytes)
        tag = root.tag or ""
        return tag.split("}", 1)[1] if "}" in tag else tag
    except Exception:
        texto = xml_bytes[:300].decode("utf-8", errors="ignore").strip()
        for raiz in ["retEnvEvento", "procEventoNFe", "evento", "nfeProc", "NFe"]:
            if texto.startswith("<" + raiz):
                return raiz
        return ""

def validar_xml_para_envio(tipo, chave, xml_bytes):
    xml = normalizar_xml_bytes(xml_bytes)
    raiz = obter_raiz_xml(xml)
    if tipo == "CANCELAMENTO":
        if raiz == "retEnvEvento":
            raise XmlDocumentoInvalido("XML de cancelamento contém apenas retorno da SEFAZ (retEnvEvento). O portal espera procEventoNFe ou evento.")
        if raiz not in ("procEventoNFe", "evento"):
            raise XmlDocumentoInvalido(f"XML de cancelamento com estrutura não reconhecida. Raiz: {raiz or 'vazia'}.")
    return xml
