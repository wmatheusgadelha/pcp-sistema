from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import date, datetime


# ── AUTH ──────────────────────────────────────────────────────────────────────
class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict

class ChangePassword(BaseModel):
    senha_atual: str
    nova_senha: str


# ── USERS ─────────────────────────────────────────────────────────────────────
class UserCreate(BaseModel):
    nome: str
    email: EmailStr
    senha: str
    role: str = "tecnico"
    cargo: Optional[str] = None
    matricula: Optional[str] = None
    telefone: Optional[str] = None

class UserUpdate(BaseModel):
    nome: Optional[str] = None
    role: Optional[str] = None
    cargo: Optional[str] = None
    matricula: Optional[str] = None
    telefone: Optional[str] = None
    is_active: Optional[bool] = None

class UserOut(BaseModel):
    id: int
    nome: str
    email: str
    role: str
    cargo: Optional[str]
    matricula: Optional[str]
    telefone: Optional[str]
    is_active: bool
    model_config = {"from_attributes": True}


# ── LINHAS ────────────────────────────────────────────────────────────────────
class LinhaCreate(BaseModel):
    nome: str
    maquina: Optional[str] = None
    turnos: int = 1
    horas_turno: float = 8.8
    misturador: int = 1

class LinhaUpdate(BaseModel):
    nome: Optional[str] = None
    maquina: Optional[str] = None
    turnos: Optional[int] = None
    horas_turno: Optional[float] = None
    misturador: Optional[int] = None
    is_active: Optional[bool] = None

class LinhaOut(BaseModel):
    id: int
    nome: str
    maquina: Optional[str]
    turnos: int
    horas_turno: float
    misturador: int
    is_active: bool
    model_config = {"from_attributes": True}


# ── SKU LINHA ─────────────────────────────────────────────────────────────────
class SkuLinhaCreate(BaseModel):
    linha_id: int
    velocidade_ppm: float
    fardos_hora: float

class SkuLinhaOut(BaseModel):
    id: int
    linha_id: int
    sku_id: int
    velocidade_ppm: float
    fardos_hora: float
    is_active: bool
    linha: Optional[LinhaOut] = None
    model_config = {"from_attributes": True}


# ── SKUS ──────────────────────────────────────────────────────────────────────
class SkuCreate(BaseModel):
    codigo: str
    descricao: str
    gramatura: float
    pacotes_fardo: int
    fardos_palete: int
    kg_fardo: float
    marca: Optional[str] = None
    linhas: Optional[List[SkuLinhaCreate]] = []

class SkuUpdate(BaseModel):
    descricao: Optional[str] = None
    gramatura: Optional[float] = None
    pacotes_fardo: Optional[int] = None
    fardos_palete: Optional[int] = None
    kg_fardo: Optional[float] = None
    marca: Optional[str] = None
    is_active: Optional[bool] = None

class SkuOut(BaseModel):
    id: int
    codigo: str
    descricao: str
    gramatura: float
    pacotes_fardo: int
    fardos_palete: int
    kg_fardo: float
    marca: Optional[str]
    is_active: bool
    linhas: List[SkuLinhaOut] = []
    model_config = {"from_attributes": True}


# ── INSUMOS ───────────────────────────────────────────────────────────────────
class InsumoCreate(BaseModel):
    codigo: Optional[str] = None
    nome: str
    unidade: str = "kg"

class InsumoUpdate(BaseModel):
    nome: Optional[str] = None
    unidade: Optional[str] = None
    is_active: Optional[bool] = None

class InsumoOut(BaseModel):
    id: int
    codigo: Optional[str]
    nome: str
    unidade: str
    is_active: bool
    model_config = {"from_attributes": True}


# ── FORMULAÇÃO ────────────────────────────────────────────────────────────────
class FormulacaoCreate(BaseModel):
    insumo_id: int
    qtd_por_kg: float

class FormulacaoOut(BaseModel):
    id: int
    sku_id: int
    insumo_id: int
    qtd_por_kg: float
    insumo: Optional[InsumoOut] = None
    model_config = {"from_attributes": True}


# ── DEMANDA ───────────────────────────────────────────────────────────────────
class DemandaCreate(BaseModel):
    mes_ref: str          # "2026-07"
    sku_id: int
    cliente: Optional[str] = None
    prazo_entrega: Optional[date] = None
    qtd_fardos: int
    obs: Optional[str] = None

class DemandaUpdate(BaseModel):
    cliente: Optional[str] = None
    prazo_entrega: Optional[date] = None
    qtd_fardos: Optional[int] = None
    qtd_produzida: Optional[int] = None
    status: Optional[str] = None
    obs: Optional[str] = None

class DemandaOut(BaseModel):
    id: int
    mes_ref: str
    sku_id: int
    cliente: Optional[str]
    prazo_entrega: Optional[date]
    qtd_fardos: int
    qtd_produzida: int
    status: str
    obs: Optional[str]
    created_at: datetime
    sku: Optional[SkuOut] = None
    model_config = {"from_attributes": True}


# ── PROGRAMAÇÃO ───────────────────────────────────────────────────────────────
class ProgramacaoCreate(BaseModel):
    demanda_id: int
    linha_id: int
    data_programada: date
    fardos_programados: int
    turno: int = 1
    obs: Optional[str] = None

class ProgramacaoUpdate(BaseModel):
    fardos_programados: Optional[int] = None
    status: Optional[str] = None
    obs: Optional[str] = None

class ProgramacaoOut(BaseModel):
    id: int
    demanda_id: int
    linha_id: int
    data_programada: date
    fardos_programados: float
    turno: int
    status: str
    obs: Optional[str]
    linha: Optional[LinhaOut] = None
    demanda: Optional[DemandaOut] = None
    model_config = {"from_attributes": True}

class SugestaoRequest(BaseModel):
    demanda_id: int
    linha_id: Optional[int] = None   # se None, sistema escolhe a melhor


# ── PRODUÇÃO REAL ─────────────────────────────────────────────────────────────
class ProducaoCreate(BaseModel):
    linha_id: int
    sku_id: int
    data: date
    fardos_produzidos: int
    turno: int = 1
    obs: Optional[str] = None

class ProducaoUpdate(BaseModel):
    fardos_produzidos: Optional[int] = None
    obs: Optional[str] = None

class ProducaoOut(BaseModel):
    id: int
    linha_id: int
    sku_id: int
    data: date
    fardos_produzidos: int
    turno: int
    obs: Optional[str]
    created_at: datetime
    linha: Optional[LinhaOut] = None
    sku: Optional[SkuOut] = None
    model_config = {"from_attributes": True}
