from typing import List, Optional, Dict
from dataclasses import dataclass, field

@dataclass
class ModelData:
    """Represents a 3D asset with its various states and properties."""
    name: str
    type: str
    ct_number: int
    type_number: int
    bml_version: int
    normal_model: str
    damaged_model: Optional[str]
    destroyed_model: Optional[str]
    left_destroyed_model: Optional[str]
    fixed_model: Optional[str]
    right_destroyed_model: Optional[str]
    both_models_destroyed: Optional[str]
    textures_used: List[str]
    outsourcing: Optional[str]

@dataclass
class ParentData:
    """Represents a parent model with its associated textures and properties."""
    parent_number: int
    bml_version: int
    textures: List[str]
    model_name: str
    model_type: str
    type: str
    ct_number: int
    entity_idx: int
    outsourced: bool = False  # Flag for -1 (outsourced) parents
    pbr: bool = False  # Flag for PBR state

@dataclass
class TextureData:
    """Represents a texture with its associated parent models."""
    texture_id: str
    parent_models: List[ParentData]
    high_res: bool = False
    pbr: List[str] = field(default_factory=list)  # Names of PBR textures found
    pbr_type: List[str] = field(default_factory=list)  # Types of PBR textures (normal/armw)
    availability: bool = True  # Whether the texture file exists in KoreaObj folder 