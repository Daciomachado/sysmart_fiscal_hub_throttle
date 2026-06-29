import requests

class PortalApi:
    def __init__(self, cfg):
        self.cfg = cfg

    def enviar_xml(self, tipo, chave, xml_bytes):
        endpoint = self.cfg.endpoint_nfce if tipo == "NFCE" else self.cfg.endpoint_evento
        url = self.cfg.base_url.rstrip("/") + "/" + endpoint.lstrip("/")
        try:
            r = requests.post(
                url,
                data={"key": self.cfg.api_key},
                files={"file": (f"{tipo}_{chave}.xml", xml_bytes, "application/xml")},
                timeout=self.cfg.timeout_segundos,
            )
            return r.status_code, r.text
        except Exception as e:
            return "ERRO_HTTP", str(e)
