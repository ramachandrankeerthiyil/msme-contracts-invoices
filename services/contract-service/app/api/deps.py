import uuid
from typing import Annotated

from fastapi import Depends

from app.core.errors import AppError


def contract_not_found() -> AppError:
    return AppError("NOT_FOUND", "We couldn't find that contract.", status=404)


def parse_contract_id(contract_id: str) -> uuid.UUID:
    """A malformed id in a link is just a contract we can't find: 404, not a validation error."""
    try:
        return uuid.UUID(contract_id)
    except ValueError:
        raise contract_not_found() from None


ContractId = Annotated[uuid.UUID, Depends(parse_contract_id)]
