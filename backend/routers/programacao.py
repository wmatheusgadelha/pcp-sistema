from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import date, timedelta
import calendar
from ..core.database import get_db
from ..core.security import get_current_user, require_gestor
from ..models.models import PcpProgramacao, PcpDemanda, PcpSku, PcpSkuLinha, PcpLinha
from ..schemas.schemas import ProgramacaoCreate, ProgramacaoUpdate, ProgramacaoOut, SugestaoRequest

router = APIRouter(prefix="/api/programacao", tags=["Programação"])

def dias_uteis_mes(ano: int, mes: int):
    """Retorna lista de dias úteis (seg-sab) do mês"""
    _, num_dias = calendar.monthrange(ano, mes)
    dias = []
    for d in range(1, num_dias + 1):
        dt = date(ano, mes, d)
        if dt.weekday() != 6:  # exclui domingo
            dias.append(dt)
    return dias

def horas_ocupadas_linha_dia(db: Session, linha_id: int, data: date) -> float:
    """Soma de horas já alocadas para uma linha em um dia"""
    prog = db.query(PcpProgramacao).filter(
        PcpProgramacao.linha_id == linha_id,
        PcpProgramacao.data_programada == data,
        PcpProgramacao.status != "cancelado"
    ).all()
    total_horas = 0.0
    for p in prog:
        dem = db.query(PcpDemanda).filter(PcpDemanda.id == p.demanda_id).first()
        if not dem:
            continue
        sl = db.query(PcpSkuLinha).filter(
            PcpSkuLinha.sku_id == dem.sku_id,
            PcpSkuLinha.linha_id == linha_id,
            PcpSkuLinha.is_active == True
        ).first()
        if sl and sl.fardos_hora > 0:
            total_horas += p.fardos_programados / sl.fardos_hora
    return total_horas

@router.get("/", response_model=List[ProgramacaoOut])
def list_programacao(
    mes_ref: Optional[str] = None,
    linha_id: Optional[int] = None,
    db: Session = Depends(get_db),
    _=Depends(get_current_user)
):
    q = db.query(PcpProgramacao)
    if mes_ref:
        ano, mes = int(mes_ref[:4]), int(mes_ref[5:7])
        inicio = date(ano, mes, 1)
        _, nd = calendar.monthrange(ano, mes)
        fim = date(ano, mes, nd)
        q = q.filter(PcpProgramacao.data_programada >= inicio,
                     PcpProgramacao.data_programada <= fim)
    if linha_id:
        q = q.filter(PcpProgramacao.linha_id == linha_id)
    return q.order_by(PcpProgramacao.data_programada, PcpProgramacao.linha_id).all()

@router.post("/", response_model=ProgramacaoOut)
def create_programacao(data: ProgramacaoCreate, db: Session = Depends(get_db), _=Depends(require_gestor)):
    # Valida se a linha pode produzir o SKU
    dem = db.query(PcpDemanda).filter(PcpDemanda.id == data.demanda_id).first()
    if not dem:
        raise HTTPException(status_code=404, detail="Demanda não encontrada")
    sl = db.query(PcpSkuLinha).filter(
        PcpSkuLinha.sku_id == dem.sku_id,
        PcpSkuLinha.linha_id == data.linha_id,
        PcpSkuLinha.is_active == True
    ).first()
    if not sl:
        raise HTTPException(status_code=400, detail="Esta linha não produz este SKU")
    prog = PcpProgramacao(**data.model_dump())
    db.add(prog); db.commit(); db.refresh(prog)
    return prog

@router.put("/{prog_id}", response_model=ProgramacaoOut)
def update_programacao(prog_id: int, data: ProgramacaoUpdate, db: Session = Depends(get_db), _=Depends(require_gestor)):
    prog = db.query(PcpProgramacao).filter(PcpProgramacao.id == prog_id).first()
    if not prog:
        raise HTTPException(status_code=404, detail="Programação não encontrada")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(prog, field, value)
    db.commit(); db.refresh(prog)
    return prog

@router.delete("/{prog_id}")
def delete_programacao(prog_id: int, db: Session = Depends(get_db), _=Depends(require_gestor)):
    prog = db.query(PcpProgramacao).filter(PcpProgramacao.id == prog_id).first()
    if not prog:
        raise HTTPException(status_code=404, detail="Programação não encontrada")
    db.delete(prog); db.commit()
    return {"message": "Programação excluída"}

@router.post("/sugerir")
def sugerir_programacao(req: SugestaoRequest, db: Session = Depends(get_db), _=Depends(get_current_user)):
    """
    Sugere a melhor distribuição de dias/linhas para atender uma demanda.
    Considera: linhas compatíveis, capacidade disponível, menor ocupação acumulada,
    agrupa por gramatura para minimizar setup, respeita prazo de entrega.
    """
    dem = db.query(PcpDemanda).filter(PcpDemanda.id == req.demanda_id).first()
    if not dem:
        raise HTTPException(status_code=404, detail="Demanda não encontrada")

    sku = db.query(PcpSku).filter(PcpSku.id == dem.sku_id).first()

    # Fardos pendentes (descontando o já programado)
    ja_prog = db.query(func.sum(PcpProgramacao.fardos_programados)).filter(
        PcpProgramacao.demanda_id == dem.id,
        PcpProgramacao.status != "cancelado"
    ).scalar() or 0
    fardos_pendentes = dem.qtd_fardos - int(ja_prog)

    if fardos_pendentes <= 0:
        return {"message": "Demanda já completamente programada", "sugestoes": []}

    # Linhas compatíveis
    if req.linha_id:
        sku_linhas = db.query(PcpSkuLinha).filter(
            PcpSkuLinha.sku_id == dem.sku_id,
            PcpSkuLinha.linha_id == req.linha_id,
            PcpSkuLinha.is_active == True
        ).all()
    else:
        sku_linhas = db.query(PcpSkuLinha).filter(
            PcpSkuLinha.sku_id == dem.sku_id,
            PcpSkuLinha.is_active == True
        ).all()

    if not sku_linhas:
        raise HTTPException(status_code=400, detail="Nenhuma linha compatível com este SKU")

    # Determina mês de referência
    ano, mes = int(dem.mes_ref[:4]), int(dem.mes_ref[5:7])
    dias_uteis = dias_uteis_mes(ano, mes)

    # Filtra dias até o prazo
    if dem.prazo_entrega:
        dias_uteis = [d for d in dias_uteis if d <= dem.prazo_entrega]

    # Filtra somente dias futuros (a partir de hoje)
    hoje = date.today()
    dias_futuros = [d for d in dias_uteis if d >= hoje]
    if not dias_futuros:
        dias_futuros = dias_uteis  # se não houver, usa todos

    sugestoes = []
    fardos_restantes = fardos_pendentes

    # Para cada linha compatível, calcula ocupação atual e disponibilidade
    for sl in sku_linhas:
        linha = db.query(PcpLinha).filter(PcpLinha.id == sl.linha_id).first()
        horas_disponiveis_dia = linha.horas_turno * linha.turnos

        for dia in dias_futuros:
            if fardos_restantes <= 0:
                break
            horas_usadas = horas_ocupadas_linha_dia(db, sl.linha_id, dia)
            horas_livres = horas_disponiveis_dia - horas_usadas
            if horas_livres <= 0.1:
                continue
            fardos_possiveis = int(horas_livres * sl.fardos_hora)
            if fardos_possiveis <= 0:
                continue
            alocar = min(fardos_possiveis, fardos_restantes)
            horas_necessarias = alocar / sl.fardos_hora
            ocupacao_pct = round((horas_usadas + horas_necessarias) / horas_disponiveis_dia * 100, 1)

            sugestoes.append({
                "linha_id": sl.linha_id,
                "linha_nome": linha.nome,
                "data_programada": dia.isoformat(),
                "fardos_programados": alocar,
                "horas_necessarias": round(horas_necessarias, 2),
                "ocupacao_dia_pct": ocupacao_pct,
                "fardos_hora": sl.fardos_hora
            })
            fardos_restantes -= alocar

        if fardos_restantes <= 0:
            break

    return {
        "demanda_id": dem.id,
        "sku": sku.descricao,
        "qtd_total": dem.qtd_fardos,
        "ja_programado": int(ja_prog),
        "fardos_a_programar": fardos_pendentes,
        "fardos_sugeridos": sum(s["fardos_programados"] for s in sugestoes),
        "fardos_sem_vaga": max(0, fardos_restantes),
        "sugestoes": sugestoes
    }

@router.post("/confirmar-sugestao")
def confirmar_sugestao(sugestoes: List[ProgramacaoCreate], db: Session = Depends(get_db), _=Depends(require_gestor)):
    """Confirma e salva um conjunto de sugestões de programação"""
    criados = []
    for s in sugestoes:
        prog = PcpProgramacao(**s.model_dump())
        db.add(prog)
        criados.append(prog)
    db.commit()
    return {"message": f"{len(criados)} programações criadas com sucesso"}

@router.get("/ocupacao/{mes_ref}")
def ocupacao_mes(mes_ref: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    """Retorna ocupação de cada linha no mês (horas usadas vs. disponíveis)"""
    ano, mes = int(mes_ref[:4]), int(mes_ref[5:7])
    _, nd = calendar.monthrange(ano, mes)
    inicio = date(ano, mes, 1)
    fim = date(ano, mes, nd)
    dias_uteis = len([d for d in dias_uteis_mes(ano, mes)])

    linhas = db.query(PcpLinha).filter(PcpLinha.is_active == True).all()
    resultado = []

    for linha in linhas:
        horas_disponiveis = linha.horas_turno * linha.turnos * dias_uteis
        # Calcula horas usadas pela programação do mês
        progs = db.query(PcpProgramacao).filter(
            PcpProgramacao.linha_id == linha.id,
            PcpProgramacao.data_programada >= inicio,
            PcpProgramacao.data_programada <= fim,
            PcpProgramacao.status != "cancelado"
        ).all()
        horas_usadas = 0.0
        fardos_programados = 0
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
            fardos_programados += p.fardos_programados

        pct = round(horas_usadas / horas_disponiveis * 100, 1) if horas_disponiveis > 0 else 0
        resultado.append({
            "linha_id": linha.id,
            "linha_nome": linha.nome,
            "maquina": linha.maquina,
            "horas_disponiveis": round(horas_disponiveis, 1),
            "horas_usadas": round(horas_usadas, 1),
            "horas_livres": round(horas_disponiveis - horas_usadas, 1),
            "ocupacao_pct": pct,
            "fardos_programados": fardos_programados
        })

    return resultado
