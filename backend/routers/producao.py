from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
import calendar
from ..core.database import get_db
from ..core.security import get_current_user, require_gestor
from ..models.models import PcpProducaoReal, PcpProgramacao, PcpDemanda, PcpSku, PcpLinha
from ..schemas.schemas import ProducaoCreate, ProducaoUpdate, ProducaoOut

router = APIRouter(prefix="/api/producao", tags=["Produção Real"])

@router.get("/", response_model=List[ProducaoOut])
def list_producao(
    mes_ref: Optional[str] = None,
    linha_id: Optional[int] = None,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    db: Session = Depends(get_db),
    _=Depends(get_current_user)
):
    q = db.query(PcpProducaoReal)
    if mes_ref:
        ano, mes = int(mes_ref[:4]), int(mes_ref[5:7])
        inicio = date(ano, mes, 1)
        _, nd = calendar.monthrange(ano, mes)
        fim = date(ano, mes, nd)
        q = q.filter(PcpProducaoReal.data >= inicio, PcpProducaoReal.data <= fim)
    if linha_id:
        q = q.filter(PcpProducaoReal.linha_id == linha_id)
    if data_inicio:
        q = q.filter(PcpProducaoReal.data >= data_inicio)
    if data_fim:
        q = q.filter(PcpProducaoReal.data <= data_fim)
    return q.order_by(PcpProducaoReal.data.desc(), PcpProducaoReal.linha_id).all()

@router.post("/", response_model=ProducaoOut)
def create_producao(data: ProducaoCreate, db: Session = Depends(get_db), current=Depends(get_current_user)):
    prod = PcpProducaoReal(**data.model_dump(), operador_id=current.id)
    db.add(prod)
    # Atualiza qtd_produzida na demanda correspondente (pelo mês + SKU)
    mes_ref = data.data.strftime("%Y-%m")
    demanda = db.query(PcpDemanda).filter(
        PcpDemanda.mes_ref == mes_ref,
        PcpDemanda.sku_id == data.sku_id,
        PcpDemanda.status != "concluido"
    ).first()
    if demanda:
        demanda.qtd_produzida = (demanda.qtd_produzida or 0) + data.fardos_produzidos
        if demanda.qtd_produzida >= demanda.qtd_fardos:
            demanda.status = "concluido"
        elif demanda.qtd_produzida > 0:
            demanda.status = "andamento"
    db.commit(); db.refresh(prod)
    return prod

@router.put("/{prod_id}", response_model=ProducaoOut)
def update_producao(prod_id: int, data: ProducaoUpdate, db: Session = Depends(get_db), _=Depends(require_gestor)):
    prod = db.query(PcpProducaoReal).filter(PcpProducaoReal.id == prod_id).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Registro não encontrado")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(prod, field, value)
    db.commit(); db.refresh(prod)
    return prod

@router.delete("/{prod_id}")
def delete_producao(prod_id: int, db: Session = Depends(get_db), _=Depends(require_gestor)):
    prod = db.query(PcpProducaoReal).filter(PcpProducaoReal.id == prod_id).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Registro não encontrado")
    db.delete(prod); db.commit()
    return {"message": "Registro excluído"}

@router.get("/diario/{data_str}")
def producao_diaria(data_str: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    """Retorna comparativo programado vs. realizado para um dia"""
    try:
        dt = date.fromisoformat(data_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Data inválida (use YYYY-MM-DD)")

    linhas = db.query(PcpLinha).filter(PcpLinha.is_active == True).all()
    resultado = []

    for linha in linhas:
        # programado
        progs = db.query(PcpProgramacao).filter(
            PcpProgramacao.linha_id == linha.id,
            PcpProgramacao.data_programada == dt,
            PcpProgramacao.status != "cancelado"
        ).all()
        fardos_prog = sum(p.fardos_programados for p in progs)
        skus_prog = []
        for p in progs:
            dem = db.query(PcpDemanda).filter(PcpDemanda.id == p.demanda_id).first()
            if dem:
                sku = db.query(PcpSku).filter(PcpSku.id == dem.sku_id).first()
                if sku:
                    skus_prog.append({"sku": sku.descricao, "fardos": p.fardos_programados})
        # realizado
        reais = db.query(PcpProducaoReal).filter(
            PcpProducaoReal.linha_id == linha.id,
            PcpProducaoReal.data == dt
        ).all()
        fardos_real = sum(r.fardos_produzidos for r in reais)
        skus_real = []
        for r in reais:
            sku = db.query(PcpSku).filter(PcpSku.id == r.sku_id).first()
            if sku:
                skus_real.append({"sku": sku.descricao, "fardos": r.fardos_produzidos})

        eficiencia = round(fardos_real / fardos_prog * 100, 1) if fardos_prog > 0 else None
        resultado.append({
            "linha_id": linha.id,
            "linha_nome": linha.nome,
            "fardos_programados": fardos_prog,
            "fardos_realizados": fardos_real,
            "eficiencia_pct": eficiencia,
            "skus_programados": skus_prog,
            "skus_realizados": skus_real
        })
    return {"data": data_str, "linhas": resultado}
