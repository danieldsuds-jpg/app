"""
Rotas de perfil de máquina: /machines (RF-05).
Cada usuário pode cadastrar um ou mais PCs; as specs viram contexto do Chip.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Machine, User
from backend.schemas import MachineIn, MachineOut
from backend.security import get_current_user

router = APIRouter(prefix="/machines", tags=["Máquinas"])


def _get_owned_machine(db: Session, user: User, machine_id: str) -> Machine:
    """Busca a máquina e garante que pertence ao usuário logado."""
    machine = db.get(Machine, machine_id)
    if machine is None or machine.user_id != user.id:
        raise HTTPException(status_code=404, detail="Máquina não encontrada.")
    return machine


@router.get("", response_model=list[MachineOut])
def list_machines(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Machine).filter(Machine.user_id == user.id).order_by(Machine.created_at).all()


@router.post("", response_model=MachineOut, status_code=status.HTTP_201_CREATED)
def create_machine(data: MachineIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    machine = Machine(user_id=user.id, name=data.name.strip(), specs=data.specs.model_dump())
    db.add(machine)
    db.commit()
    db.refresh(machine)
    return machine


@router.put("/{machine_id}", response_model=MachineOut)
def update_machine(
    machine_id: str, data: MachineIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    machine = _get_owned_machine(db, user, machine_id)
    machine.name = data.name.strip()
    machine.specs = data.specs.model_dump()
    db.commit()
    db.refresh(machine)
    return machine


@router.delete("/{machine_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_machine(machine_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    machine = _get_owned_machine(db, user, machine_id)
    # As conversas ligadas a ela continuam existindo, só perdem o vínculo (machine_id = NULL).
    for conv in machine.conversations:
        conv.machine_id = None
    db.delete(machine)
    db.commit()
