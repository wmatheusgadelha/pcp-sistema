from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..core.database import get_db
from ..core.security import get_current_user, require_gestor
from ..models.models import PcpSku, PcpSkuLinha, PcpLinha, PcpFormulacao, PcpInsumo
from ..schemas.schemas import (SkuCreate, SkuUpdate, SkuOut, SkuLinhaCreate, SkuLinhaOut,
                                 InsumoCreate, InsumoUpdate, InsumoOut,
                                 FormulacaoCreate, FormulacaoOut)

router = APIRouter(prefix="/api/skus", tags=["SKUs"])
insumos_router = APIRouter(prefix="/api/insumos", tags=["Insumos"])

# ── SKUs ──────────────────────────────────────────────────────────────────────
@router.get("/", response_model=List[SkuOut])
def list_skus(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return db.query(PcpSku).order_by(PcpSku.descricao).all()

@router.post("/", response_model=SkuOut)
def create_sku(data: SkuCreate, db: Session = Depends(get_db), _=Depends(require_gestor)):
    if db.query(PcpSku).filter(PcpSku.codigo == data.codigo).first():
        raise HTTPException(status_code=400, detail="Código já cadastrado")
    sku = PcpSku(
        codigo=data.codigo, descricao=data.descricao,
        gramatura=data.gramatura, pacotes_fardo=data.pacotes_fardo,
        fardos_palete=data.fardos_palete, kg_fardo=data.kg_fardo,
        marca=data.marca
    )
    db.add(sku); db.flush()
    for l in (data.linhas or []):
        sl = PcpSkuLinha(sku_id=sku.id, linha_id=l.linha_id,
                         velocidade_ppm=l.velocidade_ppm, fardos_hora=l.fardos_hora)
        db.add(sl)
    db.commit(); db.refresh(sku)
    return sku

@router.get("/{sku_id}", response_model=SkuOut)
def get_sku(sku_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    sku = db.query(PcpSku).filter(PcpSku.id == sku_id).first()
    if not sku:
        raise HTTPException(status_code=404, detail="SKU não encontrado")
    return sku

@router.put("/{sku_id}", response_model=SkuOut)
def update_sku(sku_id: int, data: SkuUpdate, db: Session = Depends(get_db), _=Depends(require_gestor)):
    sku = db.query(PcpSku).filter(PcpSku.id == sku_id).first()
    if not sku:
        raise HTTPException(status_code=404, detail="SKU não encontrado")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(sku, field, value)
    db.commit(); db.refresh(sku)
    return sku

@router.delete("/{sku_id}")
def delete_sku(sku_id: int, db: Session = Depends(get_db), _=Depends(require_gestor)):
    sku = db.query(PcpSku).filter(PcpSku.id == sku_id).first()
    if not sku:
        raise HTTPException(status_code=404, detail="SKU não encontrado")
    sku.is_active = False
    db.commit()
    return {"message": "SKU desativado"}

# ── SKU × LINHA ───────────────────────────────────────────────────────────────
@router.post("/{sku_id}/linhas", response_model=SkuLinhaOut)
def add_sku_linha(sku_id: int, data: SkuLinhaCreate, db: Session = Depends(get_db), _=Depends(require_gestor)):
    sku = db.query(PcpSku).filter(PcpSku.id == sku_id).first()
    if not sku:
        raise HTTPException(status_code=404, detail="SKU não encontrado")
    existing = db.query(PcpSkuLinha).filter(
        PcpSkuLinha.sku_id == sku_id, PcpSkuLinha.linha_id == data.linha_id
    ).first()
    if existing:
        existing.velocidade_ppm = data.velocidade_ppm
        existing.fardos_hora = data.fardos_hora
        existing.is_active = True
        db.commit(); db.refresh(existing)
        return existing
    sl = PcpSkuLinha(sku_id=sku_id, linha_id=data.linha_id,
                     velocidade_ppm=data.velocidade_ppm, fardos_hora=data.fardos_hora)
    db.add(sl); db.commit(); db.refresh(sl)
    return sl

@router.delete("/{sku_id}/linhas/{sl_id}")
def remove_sku_linha(sku_id: int, sl_id: int, db: Session = Depends(get_db), _=Depends(require_gestor)):
    sl = db.query(PcpSkuLinha).filter(PcpSkuLinha.id == sl_id, PcpSkuLinha.sku_id == sku_id).first()
    if not sl:
        raise HTTPException(status_code=404, detail="Registro não encontrado")
    sl.is_active = False
    db.commit()
    return {"message": "Linha removida do SKU"}

# ── FORMULAÇÃO ────────────────────────────────────────────────────────────────
@router.get("/{sku_id}/formulacao", response_model=List[FormulacaoOut])
def get_formulacao(sku_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return db.query(PcpFormulacao).filter(PcpFormulacao.sku_id == sku_id).all()

@router.post("/{sku_id}/formulacao", response_model=FormulacaoOut)
def add_formulacao(sku_id: int, data: FormulacaoCreate, db: Session = Depends(get_db), _=Depends(require_gestor)):
    existing = db.query(PcpFormulacao).filter(
        PcpFormulacao.sku_id == sku_id, PcpFormulacao.insumo_id == data.insumo_id
    ).first()
    if existing:
        existing.qtd_por_kg = data.qtd_por_kg
        db.commit(); db.refresh(existing)
        return existing
    f = PcpFormulacao(sku_id=sku_id, insumo_id=data.insumo_id, qtd_por_kg=data.qtd_por_kg)
    db.add(f); db.commit(); db.refresh(f)
    return f

@router.delete("/{sku_id}/formulacao/{f_id}")
def remove_formulacao(sku_id: int, f_id: int, db: Session = Depends(get_db), _=Depends(require_gestor)):
    f = db.query(PcpFormulacao).filter(PcpFormulacao.id == f_id, PcpFormulacao.sku_id == sku_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    db.delete(f); db.commit()
    return {"message": "Item removido"}


# ── INSUMOS ───────────────────────────────────────────────────────────────────
@insumos_router.get("/", response_model=List[InsumoOut])
def list_insumos(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return db.query(PcpInsumo).filter(PcpInsumo.is_active == True).order_by(PcpInsumo.nome).all()

@insumos_router.post("/", response_model=InsumoOut)
def create_insumo(data: InsumoCreate, db: Session = Depends(get_db), _=Depends(require_gestor)):
    insumo = PcpInsumo(codigo=data.codigo, nome=data.nome, unidade=data.unidade)
    db.add(insumo); db.commit(); db.refresh(insumo)
    return insumo

@insumos_router.put("/{insumo_id}", response_model=InsumoOut)
def update_insumo(insumo_id: int, data: InsumoUpdate, db: Session = Depends(get_db), _=Depends(require_gestor)):
    insumo = db.query(PcpInsumo).filter(PcpInsumo.id == insumo_id).first()
    if not insumo:
        raise HTTPException(status_code=404, detail="Insumo não encontrado")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(insumo, field, value)
    db.commit(); db.refresh(insumo)
    return insumo

@insumos_router.delete("/{insumo_id}")
def delete_insumo(insumo_id: int, db: Session = Depends(get_db), _=Depends(require_gestor)):
    insumo = db.query(PcpInsumo).filter(PcpInsumo.id == insumo_id).first()
    if not insumo:
        raise HTTPException(status_code=404, detail="Insumo não encontrado")
    insumo.is_active = False
    db.commit()
    return {"message": "Insumo desativado"}
