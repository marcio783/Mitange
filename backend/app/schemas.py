import re
from decimal import Decimal
from enum import Enum
from typing import Annotated, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    PlainSerializer,
    field_validator,
    model_validator,
)


class StatusOS(str, Enum):
    PENDENTE = "PENDENTE"
    EM_ANALISE = "EM_ANALISE"
    AGUARDANDO_PECA = "AGUARDANDO_PECA"
    CONCLUIDO = "CONCLUIDO"
    ENTREGUE = "ENTREGUE"


# Valores monetários: Decimal com 2 casas na entrada; número JSON na saída.
_to_float = PlainSerializer(lambda v: float(v), return_type=float, when_used="json")
MoneyIn = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2), _to_float]
MoneyOut = Annotated[Decimal, _to_float]

_PHONE_CHARS = re.compile(r"^\+?[\d\s().-]+$")


def validar_telefone(v: str) -> str:
    v = v.strip()
    if not _PHONE_CHARS.match(v):
        raise ValueError("Telefone contém caracteres inválidos")
    digitos = re.sub(r"\D", "", v)
    if not 9 <= len(digitos) <= 15:
        raise ValueError("Telefone deve ter entre 9 e 15 dígitos")
    return v


class Base(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


# ---------------------------------------------------------------- Clientes
class ClienteIn(Base):
    nome: str = Field(min_length=2, max_length=120)
    telefone: str
    email: Optional[EmailStr] = None

    @field_validator("telefone")
    @classmethod
    def _telefone(cls, v: str) -> str:
        return validar_telefone(v)

    @field_validator("email", mode="before")
    @classmethod
    def _email_vazio(cls, v):
        return None if v in ("", None) else v


class ClienteOut(BaseModel):
    id: int
    nome: str
    telefone: str
    email: Optional[str] = None
    created_at: str


# ------------------------------------------------------------ Equipamentos
class EquipamentoIn(Base):
    cliente_id: int = Field(gt=0)
    tipo: str = Field(min_length=2, max_length=60)
    marca_modelo: str = Field(min_length=1, max_length=120)
    numero_serie: Optional[str] = Field(default=None, max_length=80)

    @field_validator("numero_serie", mode="before")
    @classmethod
    def _serie_vazia(cls, v):
        return None if v == "" else v


class EquipamentoOut(BaseModel):
    id: int
    cliente_id: int
    cliente_nome: Optional[str] = None
    tipo: str
    marca_modelo: str
    numero_serie: Optional[str] = None


# ------------------------------------------------------------------- Peças
class PecaIn(Base):
    nome: str = Field(min_length=2, max_length=120)
    preco_custo: MoneyIn
    preco_venda: MoneyIn
    quantidade_estoque: int = Field(default=0, ge=0)
    estoque_minimo: int = Field(default=0, ge=0)


class PecaOut(BaseModel):
    id: int
    nome: str
    preco_custo: MoneyOut
    preco_venda: MoneyOut
    quantidade_estoque: int
    estoque_minimo: int


# --------------------------------------------------------- Ordens de serviço
class OSCreate(Base):
    equipamento_id: int = Field(gt=0)
    defeito_relatado: str = Field(min_length=3, max_length=2000)
    diagnostico_tecnico: Optional[str] = Field(default=None, max_length=4000)
    valor_mao_de_obra: MoneyIn = Decimal("0")


class OSUpdate(Base):
    diagnostico_tecnico: Optional[str] = Field(default=None, max_length=4000)
    valor_mao_de_obra: Optional[MoneyIn] = None

    @model_validator(mode="after")
    def _ao_menos_um(self):
        if not self.model_fields_set:
            raise ValueError("Informe ao menos um campo para atualizar")
        if "valor_mao_de_obra" in self.model_fields_set and self.valor_mao_de_obra is None:
            raise ValueError("valor_mao_de_obra não pode ser nulo")
        return self


class OSStatusUpdate(Base):
    status: StatusOS


class OSPecaAdd(Base):
    peca_id: int = Field(gt=0)
    quantidade: int = Field(gt=0, le=10000)


class OSPecaOut(BaseModel):
    id: int
    peca_id: int
    peca_nome: str
    quantidade_utilizada: int
    preco_unitario_aplicado: MoneyOut
    subtotal: MoneyOut


class OSResumo(BaseModel):
    id: int
    status: StatusOS
    cliente_id: int
    cliente_nome: str
    equipamento_id: int
    equipamento: str
    defeito_relatado: str
    valor_mao_de_obra: MoneyOut
    total_pecas: MoneyOut
    total: MoneyOut
    created_at: str
    updated_at: str


class OSDetalhe(OSResumo):
    diagnostico_tecnico: Optional[str] = None
    cliente_telefone: str
    numero_serie: Optional[str] = None
    itens: list[OSPecaOut]


class Fatura(BaseModel):
    os_id: int
    valor_mao_de_obra: MoneyOut
    total_pecas: MoneyOut
    total: MoneyOut
    itens: list[OSPecaOut]


class Dashboard(BaseModel):
    os_abertas: int
    os_concluidas_mes: int
    faturamento_mes: MoneyOut
    por_status: dict[str, int]
    alertas_estoque: list[PecaOut]
