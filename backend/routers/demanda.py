from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from ..core.database import get_db
from ..core.security import get_current_user, require_gestor
from ..models.models import PcpDemanda, PcpSku, PcpFormulacao, PcpInsumo, PcpProgramacao
from ..schemas.schemas import DemandaCreate, DemandaUpdate, DemandaOut

router = APIRouter(prefix="/api/demanda", tags=["Demanda"])

@router.get("/", response_model=List[DemandaOut])
def list_demanda(
    mes_ref: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    _=Depends(get_current_user)
):
    q = db.query(PcpDemanda)
    if mes_ref:
        q = q.filter(PcpDemanda.mes_ref == mes_ref)
    if status:
        q = q.filter(PcpDemanda.status == status)
    return q.order_by(PcpDemanda.prazo_entrega, PcpDemanda.id).all()

@router.post("/", response_model=DemandaOut)
def create_demanda(data: DemandaCreate, db: Session = Depends(get_db), current=Depends(get_current_user)):
    sku = db.query(PcpSku).filter(PcpSku.id == data.sku_id).first()
    if not sku:
        raise HTTPException(status_code=404, detail="SKU não encontrado")
    dem = PcpDemanda(**data.model_dump(), created_by=current.id)
    db.add(dem); db.commit(); db.refresh(dem)
    return dem

@router.get("/{dem_id}", response_model=DemandaOut)
def get_demanda(dem_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    dem = db.query(PcpDemanda).filter(PcpDemanda.id == dem_id).first()
    if not dem:
        raise HTTPException(status_code=404, detail="Demanda não encontrada")
    return dem

@router.put("/{dem_id}", response_model=DemandaOut)
def update_demanda(dem_id: int, data: DemandaUpdate, db: Session = Depends(get_db), _=Depends(require_gestor)):
    dem = db.query(PcpDemanda).filter(PcpDemanda.id == dem_id).first()
    if not dem:
        raise HTTPException(status_code=404, detail="Demanda não encontrada")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(dem, field, value)
    db.commit(); db.refresh(dem)
    return dem

@router.delete("/{dem_id}")
def delete_demanda(dem_id: int, db: Session = Depends(get_db), _=Depends(require_gestor)):
    dem = db.query(PcpDemanda).filter(PcpDemanda.id == dem_id).first()
    if not dem:
        raise HTTPException(status_code=404, detail="Demanda não encontrada")
    # remove programações vinculadas
    db.query(PcpProgramacao).filter(PcpProgramacao.demanda_id == dem_id).delete()
    db.delete(dem); db.commit()
    return {"message": "Demanda excluída"}

@router.get("/{dem_id}/insumos")
def calcular_insumos(dem_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    """Calcula quantitativo de insumos/MP necessários para atender a demanda"""
    dem = db.query(PcpDemanda).filter(PcpDemanda.id == dem_id).first()
    if not dem:
        raise HTTPException(status_code=404, detail="Demanda não encontrada")
    sku = db.query(PcpSku).filter(PcpSku.id == dem.sku_id).first()
    total_kg = dem.qtd_fardos * sku.kg_fardo
    formulacao = db.query(PcpFormulacao).filter(PcpFormulacao.sku_id == dem.sku_id).all()
    resultado = []
    for f in formulacao:
        insumo = db.query(PcpInsumo).filter(PcpInsumo.id == f.insumo_id).first()
        resultado.append({
            "insumo_id": insumo.id,
            "insumo": insumo.nome,
            "unidade": insumo.unidade,
            "qtd_por_kg": f.qtd_por_kg,
            "total_necessario": round(total_kg * f.qtd_por_kg, 2)
        })
    return {
        "demanda_id": dem_id,
        "sku": sku.descricao,
        "qtd_fardos": dem.qtd_fardos,
        "total_kg_produto": round(total_kg, 2),
        "insumos": resultado
    }

@router.get("/mes/{mes_ref}/resumo-insumos")
def resumo_insumos_mes(mes_ref: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    """Consolida todos os insumos necessários para o mês inteiro"""
    demandas = db.query(PcpDemanda).filter(
        PcpDemanda.mes_ref == mes_ref,
        PcpDemanda.status != "concluido"
    ).all()
    totais = {}
    for dem in demandas:
        sku = db.query(PcpSku).filter(PcpSku.id == dem.sku_id).first()
        pendente = dem.qtd_fardos - dem.qtd_produzida
        if pendente <= 0:
            continue
        total_kg = pendente * sku.kg_fardo
        formulacao = db.query(PcpFormulacao).filter(PcpFormulacao.sku_id == dem.sku_id).all()
        for f in formulacao:
            insumo = db.query(PcpInsumo).filter(PcpInsumo.id == f.insumo_id).first()
            key = insumo.id
            if key not in totais:
                totais[key] = {"insumo": insumo.nome, "unidade": insumo.unidade, "total": 0}
            totais[key]["total"] += total_kg * f.qtd_por_kg
    return [{"insumo_id": k, **v, "total": round(v["total"], 2)} for k, v in totais.items()]
