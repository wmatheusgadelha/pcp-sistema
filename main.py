from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from datetime import date
import os

from backend.core.database import engine, Base, SessionLocal
from backend.core.security import get_password_hash
from backend.models.models import (
    PcpUser, PcpLinha, PcpSku, PcpSkuLinha,
    PcpInsumo, PcpFormulacao, PcpDemanda
)
from backend.routers import auth, users, skus, demanda, programacao, producao, dashboard


def seed_data(db):
    # ── Usuários ──────────────────────────────────────────────────────────────
    if not db.query(PcpUser).first():
        usuarios = [
            PcpUser(nome="Administrador PCP", email="admin@pcp.com",
                    hashed_password=get_password_hash("admin123"),
                    role="admin", cargo="Administrador do Sistema"),
            PcpUser(nome="Gestor de Produção", email="gestor@pcp.com",
                    hashed_password=get_password_hash("gestor123"),
                    role="gestor", cargo="Gerente de Produção"),
            PcpUser(nome="Técnico PCP", email="tecnico@pcp.com",
                    hashed_password=get_password_hash("tecnico123"),
                    role="tecnico", cargo="Técnico de PCP"),
        ]
        db.add_all(usuarios); db.flush()
        print("✅ Usuários criados")

    # ── Linhas ────────────────────────────────────────────────────────────────
    if not db.query(PcpLinha).first():
        linhas = [
            PcpLinha(nome="L1 - DG4",      maquina="DG4",      turnos=1, horas_turno=8.46, misturador=1),
            PcpLinha(nome="L2 - NORIMAQ",  maquina="NORIMAQ",  turnos=1, horas_turno=8.46, misturador=1),
            PcpLinha(nome="L3 - MG8000",   maquina="MG8000",   turnos=1, horas_turno=8.46, misturador=2),
            PcpLinha(nome="L4 - ALFATECH", maquina="ALFATECH", turnos=1, horas_turno=8.80, misturador=2),
        ]
        db.add_all(linhas); db.flush()
        print("✅ Linhas criadas")

    # ── SKUs ──────────────────────────────────────────────────────────────────
    if not db.query(PcpSku).first():
        skus_data = [
            # (codigo, descricao, gramatura, pacotes_fardo, fardos_palete, kg_fardo, marca)
            ("BONNY-0.4", "BONNY 0,4KG",   0.4, 50, 54,  20.0,  "BONNY"),
            ("BONNY-0.8", "BONNY 0,8KG",   0.8, 20, 63,  16.0,  "BONNY"),
            ("BONNY-1.0", "BONNY 1KG",     1.0, 20, 54,  20.0,  "BONNY"),
            ("BONNY-1.6", "BONNY 1,6KG",   1.6, 12, 56,  19.2,  "BONNY"),
            ("BONNY-4.0", "BONNY 4KG",     4.0,  4, 72,  16.0,  "BONNY"),
            ("QLIMP-0.8", "QUALIMPEL 0,8KG",   0.8, 20, 63, 16.0,  "QUALIMPEL"),
            ("QLIMP-COCO","QUALIMPEL COCO 0,8KG", 0.8, 20, 63, 16.0, "QUALIMPEL"),
            ("QLIMP-1.6", "QUALIMPEL 1,6KG",   1.6, 12, 56, 19.2, "QUALIMPEL"),
            ("QLIMP-4.0", "QUALIMPEL 4KG",     4.0,  4, 72, 16.0, "QUALIMPEL"),
            ("ULIMP-0.8", "UNI LIMP 0,8KG",    0.8, 20, 63, 16.0, "UNI LIMP"),
            ("ULIMP-1.6", "UNI LIMP 1,6KG",    1.6, 10, 56, 16.0, "UNI LIMP"),
            ("FELT-0.8",  "FELITÁ 0,8KG",      0.8, 20, 63, 16.0, "FELITÁ"),
            ("FELT-1.6",  "FELITÁ 1,6KG",      1.6, 10, 56, 16.0, "FELITÁ"),
            ("SHINE-4.0", "MULTISHINE 4KG",     4.0,  4, 72, 16.0, "MULTISHINE"),
            ("AROS-COCO", "AROMASIL COCO 0,4KG",0.4, 50, 54, 20.0, "AROMASIL"),
            ("AROS-0.8",  "AROMASIL 0,8KG",    0.8, 20, 63, 16.0, "AROMASIL"),
            ("AMTP-0.4",  "AMACITEL TOQUE POESIA 0,4KG",  0.4, 24, 100, 9.6,  "AMACITEL"),
            ("AMTP-0.8",  "AMACITEL TOQUE POESIA 0,8KG",  0.8, 16,  64, 12.8, "AMACITEL"),
            ("AMTP-1.6",  "AMACITEL TOQUE POESIA 1,6KG",  1.6,  7,  72, 11.2, "AMACITEL"),
            ("AMTP-2.4",  "AMACITEL TOQUE POESIA 2,4KG",  2.4,  7,  72, 16.8, "AMACITEL"),
            ("AMTP-4.0",  "AMACITEL TOQUE POESIA 4KG",    4.0,  4,  72, 16.0, "AMACITEL"),
            ("AMAE-0.4",  "AMACITEL ALEGRES ENCANTOS 0,4KG", 0.4, 24, 100, 9.6,  "AMACITEL"),
            ("AMAE-0.8",  "AMACITEL ALEGRES ENCANTOS 0,8KG", 0.8, 16,  64, 12.8, "AMACITEL"),
            ("AMAE-1.6",  "AMACITEL ALEGRES ENCANTOS 1,6KG", 1.6,  7,  72, 11.2, "AMACITEL"),
            ("AMAE-2.4",  "AMACITEL ALEGRES ENCANTOS 2,4KG", 2.4,  7,  72, 16.8, "AMACITEL"),
            ("AMAE-4.0",  "AMACITEL ALEGRES ENCANTOS 4KG",   4.0,  4,  72, 16.0, "AMACITEL"),
        ]
        sku_objs = {}
        for codigo, desc, gram, pf, fp, kgf, marca in skus_data:
            s = PcpSku(codigo=codigo, descricao=desc, gramatura=gram,
                       pacotes_fardo=pf, fardos_palete=fp, kg_fardo=kgf, marca=marca)
            db.add(s); db.flush()
            sku_objs[codigo] = s
        print(f"✅ {len(sku_objs)} SKUs criados")

        # ── SKU × Linha (quem produz o quê e velocidade) ─────────────────────
        linhas_db = {l.maquina: l for l in db.query(PcpLinha).all()}
        L1 = linhas_db["DG4"]
        L2 = linhas_db["NORIMAQ"]
        L3 = linhas_db["MG8000"]
        L4 = linhas_db["ALFATECH"]

        # formato: (sku_codigo, linha_obj, ppm, fardos_hora)
        sku_linha_data = [
            # LINHA 1 - DG4
            ("BONNY-0.4", L1, 35, 42.0), ("BONNY-0.8", L1, 30, 58.5), ("BONNY-1.0", L1, 30, 58.5),
            ("QLIMP-0.8", L1, 30, 58.5), ("QLIMP-COCO", L1, 30, 58.5),
            ("ULIMP-0.8", L1, 30, 58.5), ("FELT-0.8", L1, 30, 58.5),
            ("AROS-COCO", L1, 35, 27.3), ("AROS-0.8", L1, 30, 58.5),
            ("AMTP-0.4", L1, 32, 52.0), ("AMTP-0.8", L1, 30, 73.125),
            ("AMAE-0.4", L1, 32, 52.0), ("AMAE-0.8", L1, 30, 73.125),
            # LINHA 2 - NORIMAQ
            ("BONNY-0.8", L2, 30, 58.5), ("BONNY-1.0", L2, 30, 58.5), ("BONNY-1.6", L2, 21, 68.25),
            ("QLIMP-0.8", L2, 30, 58.5), ("QLIMP-COCO", L2, 30, 58.5), ("QLIMP-1.6", L2, 21, 68.25),
            ("ULIMP-0.8", L2, 30, 58.5), ("ULIMP-1.6", L2, 21, 81.9),
            ("FELT-0.8", L2, 30, 58.5), ("FELT-1.6", L2, 21, 81.9),
            ("AROS-0.8", L2, 30, 58.5),
            ("AMTP-0.8", L2, 30, 73.125), ("AMTP-1.6", L2, 21, 117.0), ("AMTP-2.4", L2, 18, 100.29),
            ("AMAE-0.8", L2, 30, 73.125), ("AMAE-1.6", L2, 21, 117.0), ("AMAE-2.4", L2, 18, 100.29),
            # LINHA 3 - MG8000
            ("BONNY-1.0", L3, 30, 58.5), ("BONNY-1.6", L3, 20, 65.0), ("BONNY-4.0", L3, 12, 117.0),
            ("QLIMP-1.6", L3, 21, 68.25), ("QLIMP-4.0", L3, 12, 117.0),
            ("ULIMP-1.6", L3, 20, 78.0), ("FELT-1.6", L3, 20, 78.0),
            ("SHINE-4.0", L3, 12, 117.0),
            ("AMTP-1.6", L3, 20, 111.43), ("AMTP-2.4", L3, 18, 100.29), ("AMTP-4.0", L3, 12, 117.0),
            ("AMAE-1.6", L3, 20, 111.43), ("AMAE-2.4", L3, 18, 100.29), ("AMAE-4.0", L3, 12, 117.0),
            # LINHA 4 - ALFATECH
            ("BONNY-0.8", L4, 35, 68.25), ("BONNY-1.0", L4, 35, 68.25), ("BONNY-1.6", L4, 25, 81.25),
            ("QLIMP-0.8", L4, 35, 68.25), ("QLIMP-COCO", L4, 35, 68.25), ("QLIMP-1.6", L4, 25, 81.25),
            ("ULIMP-0.8", L4, 35, 68.25), ("ULIMP-1.6", L4, 25, 81.25),
            ("FELT-0.8", L4, 35, 68.25), ("FELT-1.6", L4, 25, 97.5),
            ("AROS-0.8", L4, 35, 68.25),
            ("AMTP-0.8", L4, 35, 85.31), ("AMTP-1.6", L4, 25, 139.29), ("AMTP-2.4", L4, 25, 139.29),
            ("AMAE-0.8", L4, 35, 85.31), ("AMAE-1.6", L4, 25, 139.29), ("AMAE-2.4", L4, 25, 139.29),
        ]
        for codigo, linha, ppm, fph in sku_linha_data:
            if codigo in sku_objs:
                sl = PcpSkuLinha(sku_id=sku_objs[codigo].id, linha_id=linha.id,
                                 velocidade_ppm=ppm, fardos_hora=fph)
                db.add(sl)
        db.flush()
        print("✅ SKU × Linha configurados")

        # ── Insumos demo ─────────────────────────────────────────────────────
        insumos_data = [
            ("BASE-SABAO",   "Base Sabão em Pó",    "kg"),
            ("TENSO-ATIVO",  "Tensoativo",           "kg"),
            ("COAD-ALCAL",   "Coadjuvante Alcalino", "kg"),
            ("BRANQ-OPT",    "Branqueador Óptico",   "kg"),
            ("FRAGR-FLORAL", "Fragrância Floral",    "kg"),
            ("FRAGR-COCO",   "Fragrância Coco",      "kg"),
            ("EMB-SACO-0.4", "Embalagem Saco 400g",  "un"),
            ("EMB-SACO-0.8", "Embalagem Saco 800g",  "un"),
            ("EMB-SACO-1.6", "Embalagem Saco 1,6kg", "un"),
            ("EMB-SACO-4.0", "Embalagem Saco 4kg",   "un"),
            ("EMB-FARDO",    "Embalagem Fardo",      "un"),
        ]
        insumo_objs = {}
        for cod, nome, un in insumos_data:
            ins = PcpInsumo(codigo=cod, nome=nome, unidade=un)
            db.add(ins); db.flush()
            insumo_objs[cod] = ins
        print(f"✅ {len(insumo_objs)} insumos criados")

        # ── Formulação demo (QUALIMPEL 0,8KG como exemplo) ───────────────────
        qlimp_08 = sku_objs.get("QLIMP-0.8")
        if qlimp_08:
            form = [
                PcpFormulacao(sku_id=qlimp_08.id, insumo_id=insumo_objs["BASE-SABAO"].id, qtd_por_kg=0.70),
                PcpFormulacao(sku_id=qlimp_08.id, insumo_id=insumo_objs["TENSO-ATIVO"].id, qtd_por_kg=0.15),
                PcpFormulacao(sku_id=qlimp_08.id, insumo_id=insumo_objs["COAD-ALCAL"].id, qtd_por_kg=0.10),
                PcpFormulacao(sku_id=qlimp_08.id, insumo_id=insumo_objs["BRANQ-OPT"].id, qtd_por_kg=0.02),
                PcpFormulacao(sku_id=qlimp_08.id, insumo_id=insumo_objs["FRAGR-FLORAL"].id, qtd_por_kg=0.03),
            ]
            db.add_all(form)
        print("✅ Formulação demo criada")

        # ── Demanda demo (Julho/2026) ─────────────────────────────────────────
        mes_demo = "2026-07"
        demandas_demo = [
            PcpDemanda(mes_ref=mes_demo, sku_id=sku_objs["QLIMP-COCO"].id,
                       cliente="Estoque", prazo_entrega=date(2026, 7, 31),
                       qtd_fardos=63, qtd_produzida=0, status="pendente", created_by=1),
            PcpDemanda(mes_ref=mes_demo, sku_id=sku_objs["QLIMP-1.6"].id,
                       cliente="Estoque", prazo_entrega=date(2026, 7, 31),
                       qtd_fardos=112, qtd_produzida=56, status="andamento", created_by=1),
            PcpDemanda(mes_ref=mes_demo, sku_id=sku_objs["QLIMP-4.0"].id,
                       cliente="Estoque", prazo_entrega=date(2026, 7, 31),
                       qtd_fardos=288, qtd_produzida=216, status="andamento", created_by=1),
            PcpDemanda(mes_ref=mes_demo, sku_id=sku_objs["AROS-0.8"].id,
                       cliente="Aromasil", prazo_entrega=date(2026, 7, 15),
                       qtd_fardos=1512, qtd_produzida=0, status="pendente", created_by=1),
        ]
        db.add_all(demandas_demo)
        db.flush()
        print(f"✅ {len(demandas_demo)} demandas demo criadas")

    db.commit()
    print("🚀 Seed concluído com sucesso!")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        reset = os.getenv("RESET_SEED", "false").lower() == "true"
        if reset:
            print("⚠️  RESET_SEED=true — limpando banco...")
            from backend.models.models import (PcpFormulacao, PcpSkuLinha, PcpDemanda,
                                                PcpProgramacao, PcpProducaoReal)
            for model in [PcpProducaoReal, PcpProgramacao, PcpFormulacao,
                          PcpSkuLinha, PcpDemanda, PcpInsumo, PcpSku,
                          PcpLinha, PcpUser]:
                db.query(model).delete()
            db.commit()
        seed_data(db)
    except Exception as e:
        print(f"❌ Erro no seed: {e}")
        db.rollback()
    finally:
        db.close()
    yield


app = FastAPI(
    title="PCP — Qualimpel Indústria Química",
    description="Sistema de Planejamento e Controle da Produção",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(skus.router)
app.include_router(skus.insumos_router)
app.include_router(demanda.router)
app.include_router(programacao.router)
app.include_router(producao.router)
app.include_router(dashboard.router)

app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
