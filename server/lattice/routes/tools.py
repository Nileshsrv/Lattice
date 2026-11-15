from fastapi import APIRouter, Depends, HTTPException

from ..deps import current_user
from ..models import User
from ..tools import registry

router = APIRouter(prefix="/api/tools", tags=["tools"])


@router.get("")
def list_tools(_user: User = Depends(current_user)):
    return [c.model_dump() for c in registry.contracts()]


@router.get("/{tool_id}")
def tool_detail(tool_id: str, _user: User = Depends(current_user)):
    try:
        contract, _fn = registry.get(tool_id)
    except KeyError:
        raise HTTPException(404, "unknown tool")
    return contract.model_dump()
