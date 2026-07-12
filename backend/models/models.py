from sqlalchemy import Column, Integer, String, Float, Boolean, Date, DateTime, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from ..core.database import Base
import enum


class PcpUser(Base):
    __tablename__ = "pcp_users"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(200), nullable=False)
    role = Column(String(20), default="tecnico")  # admin, gestor, tecnico
    cargo = Column(String(100))
    matricula = Column(String(30))
    telefone = Column(String(20))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class PcpLinha(Base):
    __tablename__ = "pcp_linhas"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(50), nullable=False)       # "L1 - DG4"
    maquina = Column(String(50))                    # "DG4"
    turnos = Column(Integer, default=1)
    horas_turno = Column(Float, default=8.8)
    misturador = Column(Integer, default=1)         # 1 ou 2
    is_active = Column(Boolean, default=True)

    sku_linhas = relationship("PcpSkuLinha", back_populates="linha")
    programacoes = relationship("PcpProgramacao", back_populates="linha")
    producoes = relationship("PcpProducaoReal", back_populates="linha")


class PcpSku(Base):
    __tablename__ = "pcp_skus"
    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(50), unique=True, nullable=False)
    descricao = Column(String(150), nullable=False)
    gramatura = Column(Float, nullable=False)        # em kg
    pacotes_fardo = Column(Integer, nullable=False)
    fardos_palete = Column(Integer, nullable=False)
    kg_fardo = Column(Float, nullable=False)
    marca = Column(String(50))
    is_active = Column(Boolean, default=True)

    linhas = relationship("PcpSkuLinha", back_populates="sku")
    formulacao = relationship("PcpFormulacao", back_populates="sku")
    demandas = relationship("PcpDemanda", back_populates="sku")
    producoes = relationship("PcpProducaoReal", back_populates="sku")


class PcpSkuLinha(Base):
    """Quais SKUs cada linha produz e a velocidade"""
    __tablename__ = "pcp_sku_linhas"
    id = Column(Integer, primary_key=True, index=True)
    sku_id = Column(Integer, ForeignKey("pcp_skus.id"), nullable=False)
    linha_id = Column(Integer, ForeignKey("pcp_linhas.id"), nullable=False)
    velocidade_ppm = Column(Float, nullable=False)
    fardos_hora = Column(Float, nullable=False)
    is_active = Column(Boolean, default=True)

    sku = relationship("PcpSku", back_populates="linhas")
    linha = relationship("PcpLinha", back_populates="sku_linhas")


class PcpInsumo(Base):
    __tablename__ = "pcp_insumos"
    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(50), unique=True)
    nome = Column(String(150), nullable=False)
    unidade = Column(String(10), default="kg")      # kg, l, un
    is_active = Column(Boolean, default=True)

    formulacoes = relationship("PcpFormulacao", back_populates="insumo")


class PcpFormulacao(Base):
    """Composição de cada SKU: quanto de cada insumo por kg de produto"""
    __tablename__ = "pcp_formulacao"
    id = Column(Integer, primary_key=True, index=True)
    sku_id = Column(Integer, ForeignKey("pcp_skus.id"), nullable=False)
    insumo_id = Column(Integer, ForeignKey("pcp_insumos.id"), nullable=False)
    qtd_por_kg = Column(Float, nullable=False)      # kg de insumo por kg de produto

    sku = relationship("PcpSku", back_populates="formulacao")
    insumo = relationship("PcpInsumo", back_populates="formulacoes")


class PcpDemanda(Base):
    __tablename__ = "pcp_demanda"
    id = Column(Integer, primary_key=True, index=True)
    mes_ref = Column(String(7), nullable=False)     # "2026-07"
    sku_id = Column(Integer, ForeignKey("pcp_skus.id"), nullable=False)
    cliente = Column(String(150))
    prazo_entrega = Column(Date)
    qtd_fardos = Column(Integer, nullable=False)
    qtd_produzida = Column(Integer, default=0)
    status = Column(String(20), default="pendente")  # pendente, andamento, concluido
    obs = Column(Text)
    created_by = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

    sku = relationship("PcpSku", back_populates="demandas")
    programacoes = relationship("PcpProgramacao", back_populates="demanda")


class PcpProgramacao(Base):
    __tablename__ = "pcp_programacao"
    id = Column(Integer, primary_key=True, index=True)
    demanda_id = Column(Integer, ForeignKey("pcp_demanda.id"), nullable=False)
    linha_id = Column(Integer, ForeignKey("pcp_linhas.id"), nullable=False)
    data_programada = Column(Date, nullable=False)
    fardos_programados = Column(Integer, nullable=False)
    turno = Column(Integer, default=1)
    status = Column(String(20), default="programado")  # programado, realizado, cancelado
    obs = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    demanda = relationship("PcpDemanda", back_populates="programacoes")
    linha = relationship("PcpLinha", back_populates="programacoes")


class PcpProducaoReal(Base):
    __tablename__ = "pcp_producao_real"
    id = Column(Integer, primary_key=True, index=True)
    linha_id = Column(Integer, ForeignKey("pcp_linhas.id"), nullable=False)
    sku_id = Column(Integer, ForeignKey("pcp_skus.id"), nullable=False)
    data = Column(Date, nullable=False)
    fardos_produzidos = Column(Integer, nullable=False)
    turno = Column(Integer, default=1)
    operador_id = Column(Integer)
    obs = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    linha = relationship("PcpLinha", back_populates="producoes")
    sku = relationship("PcpSku", back_populates="producoes")
