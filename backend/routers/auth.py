from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..core.security import verify_password, create_access_token, get_password_hash, get_current_user
from ..models.models import PcpUser
from ..schemas.schemas import Token, ChangePassword

router = APIRouter(prefix="/api/auth", tags=["Auth"])

@router.post("/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(PcpUser).filter(PcpUser.email == form_data.username, PcpUser.is_active == True).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos")
    token = create_access_token({"sub": user.email})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": user.id, "nome": user.nome, "email": user.email, "role": user.role}
    }

@router.post("/change-password")
def change_password(data: ChangePassword, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(data.senha_atual, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Senha atual incorreta")
    current_user.hashed_password = get_password_hash(data.nova_senha)
    db.commit()
    return {"message": "Senha alterada com sucesso"}
