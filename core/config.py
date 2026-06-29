import configparser
from dataclasses import dataclass
from pathlib import Path

@dataclass
class SqlConfig:
    server: str
    database: str
    user: str
    password: str
    driver: str
    trust_server_certificate: str

@dataclass
class SyncConfig:
    auto_verificar: bool
    intervalo_minutos: int
    enviar_automatico: bool
    max_tentativas: int
    limite_por_execucao: int
    intervalo_entre_envios_segundos: int
    pausar_apos_erro_500_segundos: int

@dataclass
class PortalConfig:
    base_url: str
    api_key: str
    endpoint_nfce: str
    endpoint_evento: str
    timeout_segundos: int

@dataclass
class LogConfig:
    nivel: str
    arquivo: str

@dataclass
class AppConfig:
    sql: SqlConfig
    sync: SyncConfig
    portal: PortalConfig
    log: LogConfig

def _bool(v):
    return str(v).strip().lower() in ("sim", "s", "yes", "true", "1")

def carregar_config(caminho="config.ini"):
    p = configparser.ConfigParser()
    p.read(Path(caminho), encoding="utf-8")
    return AppConfig(
        sql=SqlConfig(
            server=p.get("SQLSERVER", "server", fallback="localhost"),
            database=p.get("SQLSERVER", "database", fallback=""),
            user=p.get("SQLSERVER", "user", fallback=""),
            password=p.get("SQLSERVER", "password", fallback=""),
            driver=p.get("SQLSERVER", "driver", fallback="ODBC Driver 13 for SQL Server"),
            trust_server_certificate=p.get("SQLSERVER", "trust_server_certificate", fallback="yes"),
        ),
        sync=SyncConfig(
            auto_verificar=_bool(p.get("SINCRONIZADOR", "auto_verificar", fallback="sim")),
            intervalo_minutos=p.getint("SINCRONIZADOR", "intervalo_minutos", fallback=10),
            enviar_automatico=_bool(p.get("SINCRONIZADOR", "enviar_automatico", fallback="sim")),
            max_tentativas=p.getint("SINCRONIZADOR", "max_tentativas", fallback=20),
            limite_por_execucao=p.getint("SINCRONIZADOR", "limite_por_execucao", fallback=100),
            intervalo_entre_envios_segundos=p.getint("SINCRONIZADOR", "intervalo_entre_envios_segundos", fallback=3),
            pausar_apos_erro_500_segundos=p.getint("SINCRONIZADOR", "pausar_apos_erro_500_segundos", fallback=30),
        ),
        portal=PortalConfig(
            base_url=p.get("PORTAL_CONTADOR", "base_url", fallback="").rstrip("/"),
            api_key=p.get("PORTAL_CONTADOR", "api_key", fallback="Sistema"),
            endpoint_nfce=p.get("PORTAL_CONTADOR", "endpoint_nfce", fallback="/api/docs/nfenfce/upload"),
            endpoint_evento=p.get("PORTAL_CONTADOR", "endpoint_evento", fallback="/api/docs/eventos/nfenfce/upload"),
            timeout_segundos=p.getint("PORTAL_CONTADOR", "timeout_segundos", fallback=60),
        ),
        log=LogConfig(
            nivel=p.get("LOG", "nivel", fallback="INFO"),
            arquivo=p.get("LOG", "arquivo", fallback="logs/fiscal_hub.log"),
        )
    )
