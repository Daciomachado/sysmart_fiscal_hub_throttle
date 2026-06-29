import tkinter as tk
from tkinter import ttk, messagebox
import threading, datetime, logging, time # <-- CORREÇÃO: import time adicionado
from pathlib import Path

from core.config import carregar_config
from core.database import conectar, garantir_tabela_integracao
from core.repository import listar_documentos, obter_xml, registrar_resultado
from core.portal_api import PortalApi
from core.xml_utils import validar_xml_para_envio, XmlDocumentoInvalido

MESES = [("Janeiro",1),("Fevereiro",2),("Março",3),("Abril",4),("Maio",5),("Junho",6),("Julho",7),("Agosto",8),("Setembro",9),("Outubro",10),("Novembro",11),("Dezembro",12)]

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Sysmart Fiscal Hub - Portal Contador")
        self.root.geometry("1350x760")
        self.cfg = carregar_config()
        self.docs = []
        self.enviando = False
        self.auto_em_execucao = False
        Path(self.cfg.log.arquivo).parent.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(filename=self.cfg.log.arquivo, level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", encoding="utf-8")
        self.ui()
        self.log("Sysmart Fiscal Hub iniciado.")
        if self.cfg.sync.auto_verificar:
            self.log(f"Verificação automática ativada a cada {self.cfg.sync.intervalo_minutos} minuto(s).")
            self.agendar_auto_verificacao()

    def ui(self):
        self.root.configure(bg="#f3f6fb")
        header = tk.Frame(self.root, bg="#0f4c81", height=58)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="🚀 Sysmart Fiscal Hub", bg="#0f4c81", fg="white", font=("Segoe UI",20,"bold")).pack(side="left", padx=18)
        tk.Label(header, text=f"Portal: {self.cfg.portal.base_url}", bg="#0f4c81", fg="white", font=("Segoe UI",10)).pack(side="right", padx=18)

        info = tk.Frame(self.root, bg="#e9eef7", height=32)
        info.pack(fill="x")
        info.pack_propagate(False)
        tk.Label(info, text=f"SQL Server: {self.cfg.sql.server}     Banco: {self.cfg.sql.database}", bg="#e9eef7", font=("Segoe UI",10,"bold")).pack(side="left", padx=18)

        f = ttk.LabelFrame(self.root, text="Filtros")
        f.pack(fill="x", padx=10, pady=8)
        hoje = datetime.date.today()

        ttk.Label(f, text="Mês:").pack(side="left", padx=5)
        self.cmb_mes = ttk.Combobox(f, state="readonly", width=14, values=[m[0] for m in MESES])
        self.cmb_mes.current(hoje.month-1)
        self.cmb_mes.pack(side="left")

        ttk.Label(f, text="Ano:").pack(side="left", padx=5)
        self.cmb_ano = ttk.Combobox(f, state="readonly", width=8, values=[str(a) for a in range(hoje.year-5, hoje.year+2)])
        self.cmb_ano.set(str(hoje.year))
        self.cmb_ano.pack(side="left")

        ttk.Label(f, text="Tipo:").pack(side="left", padx=5)
        self.cmb_tipo = ttk.Combobox(f, state="readonly", width=16, values=["Todos","NFC-e","Cancelamento"])
        self.cmb_tipo.current(0)
        self.cmb_tipo.pack(side="left")

        ttk.Label(f, text="Situação:").pack(side="left", padx=5)
        self.cmb_situacao = ttk.Combobox(
            f,
            state="readonly",
            width=18,
            values=["Pendências", "Todos", "Nunca Enviados", "Falhas", "Reenvio", "Enviados", "XML Inválido", "Enviando"]
        )
        self.cmb_situacao.current(0)
        self.cmb_situacao.pack(side="left")

        ttk.Button(f, text="🔍 Buscar", command=self.buscar).pack(side="left", padx=10)
        ttk.Button(f, text="🚀 Enviar Selecionados", command=self.enviar).pack(side="right", padx=5)
        ttk.Button(f, text="☐ Desmarcar", command=lambda:self.marcar(False)).pack(side="right", padx=5)
        ttk.Button(f, text="☑ Marcar Todos", command=lambda:self.marcar(True)).pack(side="right", padx=5)

        cols = ("sel","tipo","data","nfce","cupom","cliente","loja","caixa","valor","status","portal","tent","xml","chave")
        self.tree = ttk.Treeview(self.root, columns=cols, show="headings", selectmode="extended")
        self.tree.pack(fill="both", expand=True, padx=10)
        headings = ["✓","Tipo","Data","NFC-e","Cupom","Cliente","Loja","Caixa","Valor","Status","Portal","Tent.","XML","Chave"]
        widths = [36,110,130,80,80,220,60,60,90,90,110,55,75,340]
        for c,h,w in zip(cols, headings, widths):
            self.tree.heading(c, text=h)
            self.tree.column(c, width=w, anchor="center" if c not in ("cliente","chave") else "w")
        self.tree.bind("<Double-1>", self.toggle)
        self.tree.bind("<space>", self.toggle)

        lf = ttk.LabelFrame(self.root, text="Logs")
        lf.pack(fill="x", padx=10, pady=8)
        self.txt = tk.Text(lf, height=8, bg="#111827", fg="#d1d5db", font=("Consolas",9))
        self.txt.pack(fill="both", expand=True)

        self.lbl = tk.Label(self.root, text="", bg="#0f4c81", fg="white", anchor="w")
        self.lbl.pack(fill="x")
        self.status()

    def log(self, msg):
        s = datetime.datetime.now().strftime("%H:%M:%S") + "  " + msg
        self.txt.insert("end", s+"\n")
        self.txt.see("end")
        logging.info(msg)

    def buscar(self):
        threading.Thread(target=self._buscar, daemon=True).start()

    def _buscar(self):
        conn = None # <-- CORREÇÃO: Inicializa a variável antes do try
        try:
            self.log("Conectando ao SQL Server...")
            conn = conectar(self.cfg.sql)
            garantir_tabela_integracao(conn)
            mes = dict(MESES)[self.cmb_mes.get()]
            ano = int(self.cmb_ano.get())
            tipo = {"Todos":"TODOS","NFC-e":"NFCE","Cancelamento":"CANCELAMENTO"}[self.cmb_tipo.get()]
            situacao = {
                "Pendências": "PENDENCIAS",
                "Todos": "TODOS",
                "Nunca Enviados": "NUNCA",
                "Falhas": "FALHAS",
                "Reenvio": "REENVIO",
                "Enviados": "ENVIADOS",
                "XML Inválido": "INVALIDOS",
                "Enviando": "ENVIANDO",
            }[self.cmb_situacao.get()]
            self.log(f"Buscando documentos {mes:02d}/{ano} tipo {tipo} situação {situacao}...")
            self.docs = listar_documentos(conn, ano, mes, tipo, situacao, self.cfg.sync.max_tentativas)
            self.root.after(0, self.grade)
            self.log(f"Documentos encontrados: {len(self.docs)}")
        except Exception as e:
            self.log(f"ERRO: {e}")
            self.root.after(0, lambda: messagebox.showerror("Erro", str(e)))
        finally:
            if conn: # <-- CORREÇÃO: Garante o fechamento mesmo com erro
                conn.close()

    def grade(self):
        for x in self.tree.get_children():
            self.tree.delete(x)
        for i,d in enumerate(self.docs):
            data = d["data_emissao"].strftime("%d/%m/%Y %H:%M") if d["data_emissao"] else ""
            valor = f'{d["valor_total"]:,.2f}'.replace(",", "X").replace(".", ",").replace("X", ".")
            tam = f'{d["tamanho_xml"]/1024:.1f} KB' if d["tamanho_xml"] else "0 KB"
            portal = {"P":"Nunca Enviado","T":"Enviado","F":"Falha","E":"Enviando","R":"Reenvio","X":"XML Inválido"}.get(d["portal_status"], d["portal_status"])
            self.tree.insert("", "end", iid=str(i), values=("☐",d["tipo"],data,d["num_nfce"] or "",d["num_cupom"] or "",d["nome_consumidor"] or "",d["cod_loja"] or "",d["num_caixa"] or "",valor,d["status_nfce"] or "",portal,d["tentativas"],tam,d["chave"]))
        self.status()

    def toggle(self, event=None):
        for iid in self.tree.selection():
            i = int(iid)
            self.docs[i]["marcado"] = not self.docs[i]["marcado"]
            vals = list(self.tree.item(iid, "values"))
            vals[0] = "☑" if self.docs[i]["marcado"] else "☐"
            self.tree.item(iid, values=vals)
        self.status()

    def marcar(self, marcado):
        for i,d in enumerate(self.docs):
            d["marcado"] = marcado
            if self.tree.exists(str(i)):
                vals = list(self.tree.item(str(i), "values"))
                vals[0] = "☑" if marcado else "☐"
                self.tree.item(str(i), values=vals)
        self.status()

    def marcados(self):
        return [d for d in self.docs if d.get("marcado")]

    def enviar(self):
        docs = self.marcados()
        if not docs:
            messagebox.showwarning("Atenção", "Nenhum documento selecionado.")
            return
        if messagebox.askyesno("Confirmar", f"Deseja enviar {len(docs)} documento(s)?"):
            threading.Thread(target=self._enviar, args=(docs,), daemon=True).start()

    def aplicar_pausa_envio(self, codigo=None):
        if str(codigo) == "500":
            pausa_500 = int(getattr(self.cfg.sync, "pausar_apos_erro_500_segundos", 30))
            self.log(f"Servidor retornou 500. Aguardando {pausa_500} segundo(s) antes de continuar...")
            time.sleep(pausa_500)

        pausa = int(getattr(self.cfg.sync, "intervalo_entre_envios_segundos", 3))
        if pausa > 0:
            time.sleep(pausa)

    def _enviar(self, docs):
        limite = int(getattr(self.cfg.sync, "limite_por_execucao", 100))
        if len(docs) > limite:
            self.log(f"Limite por execução aplicado: {limite} de {len(docs)} documento(s).")
            docs = docs[:limite]

        if self.enviando:
            self.log("Envio ignorado: já existe envio em andamento.")
            return
        
        self.enviando = True
        ok = 0
        falha = 0
        conn = None # <-- CORREÇÃO: Inicializa a variável
        try:
            conn = conectar(self.cfg.sql)
            garantir_tabela_integracao(conn)
            api = PortalApi(self.cfg.portal)
            for n,d in enumerate(docs, 1):
                self.log(f"Enviando {n}/{len(docs)} {d['tipo']} chave {d['chave']} cupom {d['num_cupom']}...")
                try:
                    xml = obter_xml(conn, d["chave"], d["tipo"])
                    xml = validar_xml_para_envio(d["tipo"], d["chave"], xml)
                except XmlDocumentoInvalido as e:
                    falha += 1
                    registrar_resultado(conn, d, False, "XML_INVALIDO", str(e))
                    self.log(f"FALHA {d['tipo']} {d['chave']} XML_INVALIDO: {e}")
                    continue
                codigo, msg = api.enviar_xml(d["tipo"], d["chave"], xml)
                sucesso = isinstance(codigo, int) and 200 <= codigo < 300
                registrar_resultado(conn, d, sucesso, str(codigo), msg)
                if sucesso:
                    ok += 1
                    self.log(f"OK {d['tipo']} {d['chave']} HTTP {codigo}")
                else:
                    falha += 1
                    self.log(f"FALHA {d['tipo']} {d['chave']} Código {codigo}: {str(msg)[:300]}")

                self.aplicar_pausa_envio(codigo)
            
            self.log(f"Envio finalizado. Sucesso: {ok} | Falhas: {falha}")
            self.root.after(0, lambda: messagebox.showinfo("Finalizado", f"Sucesso: {ok}\nFalhas: {falha}"))
            self.buscar()
        except Exception as e:
            self.log(f"ERRO no envio: {e}")
            self.root.after(0, lambda: messagebox.showerror("Erro", str(e)))
        finally:
            if conn: # <-- CORREÇÃO: Fecha a conexão de forma segura
                conn.close()
            self.enviando = False

    def agendar_auto_verificacao(self):
        intervalo_ms = max(1, int(self.cfg.sync.intervalo_minutos)) * 60 * 1000
        self.root.after(intervalo_ms, self.auto_verificar)

    def auto_verificar(self):
        if self.enviando or self.auto_em_execucao:
            self.log("Auto verificação ignorada: envio em andamento.")
            self.agendar_auto_verificacao()
            return
        self.auto_em_execucao = True
        threading.Thread(target=self._auto_verificar_thread, daemon=True).start()

    def _auto_verificar_thread(self):
        conn = None # <-- CORREÇÃO: Inicializa a variável
        try:
            self.log("Auto verificação: consultando XMLs pendentes ou com falha...")
            conn = conectar(self.cfg.sql)
            garantir_tabela_integracao(conn)
            mes = dict(MESES)[self.cmb_mes.get()]
            ano = int(self.cmb_ano.get())
            tipo = {"Todos":"TODOS","NFC-e":"NFCE","Cancelamento":"CANCELAMENTO"}[self.cmb_tipo.get()]
            
            # No automático sempre processa pendências: nunca enviados, falhas e reenvio.
            situacao = "PENDENCIAS"
            docs = listar_documentos(conn, ano, mes, tipo, situacao, self.cfg.sync.max_tentativas)
            self.docs = docs
            self.root.after(0, self.grade)
            
            if not docs:
                self.log("Auto verificação: nenhum XML pendente ou com falha encontrado.")
                return
            
            self.log(f"Auto verificação: {len(docs)} XML(s) para envio/reenvio.")
            if self.cfg.sync.enviar_automatico:
                self._enviar(docs)
        except Exception as e:
            self.log(f"ERRO na auto verificação: {e}")
        finally:
            if conn: # <-- CORREÇÃO: Fecha a conexão em segurança
                conn.close()
            self.auto_em_execucao = False
            self.agendar_auto_verificacao()

    def status(self):
        total = len(self.docs)
        marc = len(self.marcados())
        nfce = sum(1 for d in self.docs if d["tipo"] == "NFCE")
        canc = sum(1 for d in self.docs if d["tipo"] == "CANCELAMENTO")
        env = sum(1 for d in self.docs if d["portal_status"] == "T")
        fal = sum(1 for d in self.docs if d["portal_status"] == "F")
        self.lbl.config(text=f"Total: {total} | Marcados: {marc} | NFC-e: {nfce} | Cancelamentos: {canc} | Enviados: {env} | Falhas: {fal}")

if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
