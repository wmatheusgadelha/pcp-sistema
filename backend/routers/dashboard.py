from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import date, timedelta
import calendar
from ..core.database import get_db
from ..core.security import get_current_user
from ..models.models import PcpDemanda, PcpProgramacao, PcpProducaoReal, PcpLinha, PcpSku, PcpSkuLinha

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

@router.get("/stats")
def dashboard_stats(
    mes_ref: Optional[str] = None,
    db: Session = Depends(get_db),
    _=Depends(get_current_user)
):
    if not mes_ref:
        mes_ref = date.today().strftime("%Y-%m")

    ano, mes = int(mes_ref[:4]), int(mes_ref[5:7])
    _, nd = calendar.monthrange(ano, mes)
    inicio = date(ano, mes, 1)
    fim = date(ano, mes, nd)

    # KPIs de demanda
    demandas = db.query(PcpDemanda).filter(PcpDemanda.mes_ref == mes_ref).all()
    total_demandado = sum(d.qtd_fardos for d in demandas)
    total_produzido = sum(d.qtd_produzida for d in demandas)
    total_pendente = total_demandado - total_produzido
    qtd_concluidos = len([d for d in demandas if d.status == "concluido"])
    qtd_andamento = len([d for d in demandas if d.status == "andamento"])
    qtd_pendente = len([d for d in demandas if d.status == "pendente"])

    # Produção real do mês
    producao_mes = db.query(
        func.sum(PcpProducaoReal.fardos_produzidos)
    ).filter(
        PcpProducaoReal.data >= inicio,
        PcpProducaoReal.data <= fim
    ).scalar() or 0

    # Ocupação das linhas
    linhas = db.query(PcpLinha).filter(PcpLinha.is_active == True).all()
    dias_uteis = len([date(ano, mes, d) for d in range(1, nd+1)
                      if date(ano, mes, d).weekday() != 6])
    ocupacao_linhas = []
    for linha in linhas:
        horas_disp = linha.horas_turno * linha.turnos * dias_uteis
        progs = db.query(PcpProgramacao).filter(
            PcpProgramacao.linha_id == linha.id,
            PcpProgramacao.data_programada >= inicio,
            PcpProgramacao.data_programada <= fim,
            PcpProgramacao.status != "cancelado"
        ).all()
        horas_usadas = 0.0
        for p in progs:
            dem = db.query(PcpDemanda).filter(PcpDemanda.id == p.demanda_id).first()
            if not dem:
                continue
            sl = db.query(PcpSkuLinha).filter(
                PcpSkuLinha.sku_id == dem.sku_id,
                PcpSkuLinha.linha_id == linha.id,
                PcpSkuLinha.is_active == True
            ).first()
            if sl and sl.fardos_hora > 0:
                horas_usadas += p.fardos_programados / sl.fardos_hora
        pct = round(horas_usadas / horas_disp * 100, 1) if horas_disp > 0 else 0
        ocupacao_linhas.append({
            "linha": linha.nome,
            "maquina": linha.maquina,
            "ocupacao_pct": pct,
            "horas_usadas": round(horas_usadas, 1),
            "horas_disponiveis": round(horas_disp, 1)
        })

    # Produção por dia (últimos 15 dias)
    hoje = date.today()
    quinze_dias = [hoje - timedelta(days=i) for i in range(14, -1, -1)]
    producao_diaria = []
    for dia in quinze_dias:
        total_dia = db.query(func.sum(PcpProducaoReal.fardos_produzidos)).filter(
            PcpProducaoReal.data == dia
        ).scalar() or 0
        prog_dia = db.query(func.sum(PcpProgramacao.fardos_programados)).filter(
            PcpProgramacao.data_programada == dia,
            PcpProgramacao.status != "cancelado"
        ).scalar() or 0
        producao_diaria.append({
            "data": dia.isoformat(),
            "realizado": int(total_dia),
            "programado": int(prog_dia)
        })

    # Top SKUs por demanda
    top_skus = []
    sku_totais = {}
    for d in demandas:
        sku = db.query(PcpSku).filter(PcpSku.id == d.sku_id).first()
        if sku:
            if sku.descricao not in sku_totais:
                sku_totais[sku.descricao] = {"demandado": 0, "produzido": 0}
            sku_totais[sku.descricao]["demandado"] += d.qtd_fardos
            sku_totais[sku.descricao]["produzido"] += d.qtd_produzida
    top_skus = sorted(
        [{"sku": k, **v} for k, v in sku_totais.items()],
        key=lambda x: x["demandado"], reverse=True
    )[:10]

    return {
        "mes_ref": mes_ref,
        "kpis": {
            "total_demandado_fardos": total_demandado,
            "total_produzido_fardos": total_produzido,
            "total_pendente_fardos": total_pendente,
            "producao_real_mes": int(producao_mes),
            "pct_atendimento": round(total_produzido / total_demandado * 100, 1) if total_demandado > 0 else 0,
            "qtd_pedidos": len(demandas),
            "pedidos_concluidos": qtd_concluidos,
            "pedidos_andamento": qtd_andamento,
            "pedidos_pendentes": qtd_pendente,
        },
        "ocupacao_linhas": ocupacao_linhas,
        "producao_diaria": producao_diaria,
        "top_skus": top_skus
    }
