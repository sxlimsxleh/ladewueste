"""Pydantic response models. They are the API contract: OpenAPI (and from it the web app's
TypeScript types) is generated from these classes."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class AppConfig(BaseModel):
    """The coverage parameters, so the browser applies exactly the planner's rules."""

    hpc_threshold_kw: float = Field(description="A charging point is HPC at or above this power.")
    desert_radius_km: float = Field(description="A cell is desert if no HPC hub is within this distance.")
    hub_min_hpc_points: int = Field(description="A site with at least this many HPC points is a hub.")
    h3_res_map: int
    h3_res_detail: int
    attribution: str
    licence: str
    licence_url: str
    data_file: str | None = Field(description="The register file the data was built from.")


class Hex(BaseModel):
    cell: str = Field(description="H3 cell index.")
    lat: float
    lon: float
    area_km2: float
    n_stations: int
    n_points: int
    total_kw: float
    n_hpc_points: int
    hpc_kw: float = Field(description="Sum of HPC point power in the cell: the map's elevation.")
    top_operators: list[str] = Field(description="Up to three operators with the most points in the cell.")
    nearest_hpc_km: float = Field(description="Distance from the cell centre to the nearest HPC point.")
    nearest_hub_km: float = Field(description="Distance from the cell centre to the nearest HPC hub.")
    is_desert: bool


class HexesResponse(BaseModel):
    res: int
    min_kw: float | None
    operator: str | None
    desert_km2: float = Field(description="Desert area among the returned cells.")
    total_km2: float = Field(description="Area of the returned cells.")
    hexes: list[Hex]


class Station(BaseModel):
    station_id: str
    site_id: str
    operator: str
    display_name: str | None
    lat: float
    lon: float
    n_points: int
    n_hpc_points: int
    max_point_kw: float
    plug_types: list[str]
    street: str | None
    house_no: str | None
    postcode: str | None
    town: str | None
    commissioned_on: date | None


class StationsResponse(BaseModel):
    bbox: list[float] = Field(description="[min_lon, min_lat, max_lon, max_lat]")
    limit: int
    truncated: bool = Field(description="True if more stations are in the box than were returned.")
    stations: list[Station]


class Operator(BaseModel):
    operator: str
    n_stations: int
    n_sites: int
    n_points: int
    n_hpc_points: int
    hpc_kw: float


class PlanSite(BaseModel):
    rank: int
    cell: str
    lat: float
    lon: float
    desert_km2_removed: float
    desert_km2_remaining: float


class PlanResponse(BaseModel):
    n: int
    radius_km: float
    desert_km2_before: float
    desert_km2_after: float
    sites: list[PlanSite]


class QualitySource(BaseModel):
    file: str | None
    sha256: str | None
    licence: str
    attribution: str


class QualityFunnel(BaseModel):
    raw_records: int
    stations: int
    stations_usable: int
    stations_duplicate: int
    operators_as_registered: int
    operators_canonical: int
    charging_points: int
    charging_points_usable: int
    hpc_points_usable: int


Action = Literal["fixed", "flagged", "accepted"]


class QualityExample(BaseModel):
    station_id: str | None
    point_no: int | None
    action: Action
    before: str | None
    after: str | None


class QualityRule(BaseModel):
    rule_id: str
    title: str
    why: str
    model: str
    rows_affected: int = Field(description="Distinct register records touched by the rule.")
    finding_rows: int = Field(description="Rows in the rule model (a record can have several, e.g. per point).")
    actions: dict[Action, int]
    examples: list[QualityExample]


class QualityReport(BaseModel):
    generated_at: datetime
    source: QualitySource
    funnel: QualityFunnel
    rules: list[QualityRule]


class ErrorResponse(BaseModel):
    detail: str
