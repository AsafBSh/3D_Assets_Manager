import os
import xml.etree.ElementTree as ET
import glob
from loguru import logger
from typing import List, Optional, Dict
from data_classes import ModelData, ParentData, TextureData
import json

# Configure logger
logger.remove()  # Remove any existing handlers
logger.add(
    "logs/data_manager.log",
    rotation="10 MB",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {function}:{line} | {message}",
    level="INFO",  # Change to INFO level to reduce debug messages
    enqueue=True,  # Enable thread-safe logging
    backtrace=True,  # Include backtrace for errors
    diagnose=True   # Include diagnostic information
)

class DataManager:
    def __init__(self):
        self.ct_file = None
        self.pdr_file = None
        self.models: Dict[int, ModelData] = {}  # Key: CT number
        self.parents: Dict[int, ParentData] = {}  # Key: Parent number
        self.textures: Dict[str, TextureData] = {}  # Key: Texture ID
        self.fcd_data: Dict[int, str] = {}  # EntityIdx to Name mapping for Features
        self.wcd_data: Dict[int, str] = {}  # EntityIdx to Name mapping for Weapons
        self.vcd_data: Dict[int, str] = {}  # EntityIdx to Name mapping for Vehicles
        self.unused_textures: List[int] = []  # List of unused texture IDs
        self.korea_obj_path = None
        self.korea_obj_hires_path = None
        self.base_folder = None  # Base folder for BMS data
        self.bml2_textures: Dict[int, List[Dict[str, str]]] = {}  # Key: Parent number, Value: List of texture info
    
    def set_texture_paths(self, base_path: str):
        """Set paths to KoreaObj folders."""
        self.korea_obj_path = os.path.join(os.path.dirname(base_path), "KoreaObj")
        self.korea_obj_hires_path = os.path.join(os.path.dirname(base_path), "KoreaObj_HiRes")
        
    
    def check_texture_files(self, texture_id: str) -> tuple:
        """Check texture files in KoreaObj folders and return TextureData."""
        texture_data = TextureData(texture_id=texture_id, parent_models=[])
        
        if not self.korea_obj_path or not self.korea_obj_hires_path:
            logger.warning("KoreaObj paths not set")
            return texture_data, False
        
        # Check base texture in KoreaObj
        base_exists = False
        base_pattern = os.path.join(self.korea_obj_path, f"{texture_id}.dds")
        if os.path.exists(base_pattern):
            base_exists = True
        
        # Check KoreaObj_HiRes for high-res texture
        hires_pattern = os.path.join(self.korea_obj_hires_path, f"{texture_id}.dds")
        texture_data.high_res = os.path.exists(hires_pattern)
        
        # Check for PBR textures in KoreaObj
        normal_file = os.path.join(self.korea_obj_path, f"{texture_id}_normal.dds")
        armw_file = os.path.join(self.korea_obj_path, f"{texture_id}_armw.dds")
        
        # Check for PBR textures in KoreaObj_HiRes
        hires_normal = os.path.join(self.korea_obj_hires_path, f"{texture_id}_normal.dds")
        hires_armw = os.path.join(self.korea_obj_hires_path, f"{texture_id}_armw.dds")
        
        # Add found PBR files
        if os.path.exists(normal_file):
            texture_data.pbr.append(f"{texture_id}_normal")
            texture_data.pbr_type.append("normal")
        
        if os.path.exists(armw_file):
            texture_data.pbr.append(f"{texture_id}_armw")
            texture_data.pbr_type.append("armw")
        
        # Add high-res PBR files
        if os.path.exists(hires_normal):
            texture_data.high_res = True
        
        if os.path.exists(hires_armw):
            texture_data.high_res = True
        
        return texture_data, base_exists
    
    def load_class_data(self, file_path: str, data_dict: Dict[int, str], class_type: str) -> bool:
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Clear existing data
            data_dict.clear()
            
            # Process each entry
            for element in root:
                try:
                    num = int(element.get("Num", "-1"))
                    name = element.find("Name")
                    if num >= 0 and name is not None:
                        data_dict[num] = name.text or ""
                except (ValueError, AttributeError) as e:
                    logger.debug(f"Error processing {class_type} entry: {str(e)}")
                    continue
            
            logger.info(f"Loaded {len(data_dict)} {class_type} entries")
            return True
            
        except Exception as e:
            logger.error(f"Error loading {class_type} file: {str(e)}")
            return False
    
    def load_ct_file(self, file_path: str) -> bool:
        try:
            # Clear existing data
            self.models.clear()
            self.parents.clear()
            self.textures.clear()
            self.unused_textures.clear()  # Clear unused textures list
            self.pdr_file = None  # Clear PDR file path
            
            # Reset loading flags to ensure fresh data loading
            if hasattr(self, 'parents_loaded_from_models'):
                delattr(self, 'parents_loaded_from_models')
            if hasattr(self, 'cockpit_parents_loaded'):
                delattr(self, 'cockpit_parents_loaded')
            if hasattr(self, 'parents_consolidated'):
                delattr(self, 'parents_consolidated')
            
            # Load associated data files from the same directory
            base_dir = os.path.dirname(file_path)
            self.load_class_data(os.path.join(base_dir, "Falcon4_FCD.xml"), self.fcd_data, "Feature")
            self.load_class_data(os.path.join(base_dir, "Falcon4_WCD.xml"), self.wcd_data, "Weapon")
            self.load_class_data(os.path.join(base_dir, "Falcon4_VCD.xml"), self.vcd_data, "Vehicle")
            
            # Parse the CT file
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Process CT elements
            models_found = 0
            models_loaded = 0
            
            # First, count total valid models for progress tracking
            total_models = len(root.findall(".//CT"))
            logger.info(f"Found {total_models} total CT elements")
            
            # Process CT elements in batches
            batch_size = 100
            current_batch = []
            
            for ct_element in root.findall(".//CT"):
                try:
                    models_found += 1
                    
                    # Get CT number
                    try:
                        ct_number = int(ct_element.get("Num", "0"))
                    except (ValueError, TypeError):
                        logger.debug(f"Invalid CT number: {ct_element.get('Num')}")
                        continue
                    
                    # Get EntityType
                    entity_type = -1
                    entity_type_element = ct_element.find("EntityType")
                    if entity_type_element is not None and entity_type_element.text:
                        try:
                            entity_type = int(entity_type_element.text)
                        except (ValueError, TypeError):
                            logger.debug(f"CT {ct_number} - Invalid EntityType value: {entity_type_element.text}")
                            continue
                    else:
                        logger.debug(f"CT {ct_number} - No EntityType element found")
                        continue
                    
                    # Only process EntityTypes 1, 5, and 6
                    if entity_type not in [1, 5, 6] or ct_number == 0:
                        continue
                    
                    # Get entity index
                    entity_idx = -1
                    entity_element = ct_element.find("EntityIdx")
                    if entity_element is not None and entity_element.text:
                        try:
                            entity_idx = int(entity_element.text)
                        except (ValueError, TypeError):
                            logger.debug(f"CT {ct_number} - Invalid entity index: {entity_element.text}")
                            continue
                    
                    # Get name based on EntityType
                    name = ""
                    try:
                        if entity_type == 1 and entity_idx in self.fcd_data:
                            name = self.fcd_data[entity_idx]
                        elif entity_type == 5 and entity_idx in self.vcd_data:
                            name = self.vcd_data[entity_idx]
                        elif entity_type == 6 and entity_idx in self.wcd_data:
                            name = self.wcd_data[entity_idx]
                    except Exception as e:
                        logger.debug(f"CT {ct_number} - Error in name lookup: {str(e)}")
                        continue
                    
                    # Create ModelData object
                    try:
                        model_data = ModelData(
                            name=name,
                            type=self._get_type_name(entity_type),
                            ct_number=ct_number,
                            type_number=entity_idx,
                            bml_version=1,  # Default for now
                            normal_model=ct_element.find("GraphicsNormal").text if ct_element.find("GraphicsNormal") is not None else "",
                            damaged_model=ct_element.find("GraphicsDamaged").text if ct_element.find("GraphicsDamaged") is not None else None,
                            destroyed_model=ct_element.find("GraphicsDestroyed").text if ct_element.find("GraphicsDestroyed") is not None else None,
                            left_destroyed_model=ct_element.find("GraphicsLeftDestroyed").text if ct_element.find("GraphicsLeftDestroyed") is not None else None,
                            fixed_model=ct_element.find("GraphicsRepaired").text if ct_element.find("GraphicsRepaired") is not None else None,
                            right_destroyed_model=ct_element.find("GraphicsRightDestroyed").text if ct_element.find("GraphicsRightDestroyed") is not None else None,
                            both_models_destroyed=ct_element.find("GraphicsBothDestroyed").text if ct_element.find("GraphicsBothDestroyed") is not None else None,
                            textures_used=[],
                            outsourcing=None
                        )
                        
                        current_batch.append((ct_number, model_data))
                        models_loaded += 1
                        
                        # Process batch when it reaches the batch size
                        if len(current_batch) >= batch_size:
                            for ct_num, model in current_batch:
                                self.models[ct_num] = model
                            current_batch.clear()
                            
                            # Log progress every 1000 models
                            if models_loaded % 1000 == 0:
                                logger.info(f"Processed {models_loaded} valid models ({(models_found/total_models)*100:.1f}% complete)")
                        
                    except Exception:
                        continue
                    
                except Exception as e:
                    logger.error(f"Error processing CT element: {str(e)}")
                    continue
            
            # Process any remaining models in the last batch
            for ct_num, model in current_batch:
                self.models[ct_num] = model
            
            self.ct_file = file_path
            logger.info(f"Successfully loaded {models_loaded} valid models from CT file")
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading CT file: {str(e)}")
            return False
    
    def _get_type_name(self, entity_type: int) -> str:
        """Get the type name based on EntityType."""
        if entity_type == 1:
            return "Feature"
        elif entity_type == 5:
            return "Vehicle"
        elif entity_type == 6:
            return "Weapon"
        return "Unknown"
    
    def load_pdr_file(self, file_path: str) -> bool:
        try:
            current_parent = None
            current_bml = None
            current_textures = []
            expected_parent = 1  # Start from 1 to skip parent 0
            last_valid_parent = 0  # Track the last non-negative parent number
            
            with open(file_path, 'r') as f:
                lines = f.readlines()
                
                for i, line in enumerate(lines):
                    line = line.strip()
                    if not line:
                        continue
                    
                    if line.startswith("Parent Number:"):
                        # Process previous parent if exists
                        if current_parent is not None and current_bml is not None:
                            self._process_parent_data(current_parent, current_bml, current_textures, current_parent == -1)
                        
                        # Get parent number
                        parent_num = int(line.split(":")[1].strip())
                        
                        if parent_num == -1:
                            # For -1 cases, use the expected parent number
                            current_parent = expected_parent
                            current_bml = -1  # Set BML version to -1 for non-existing parents
                            current_textures = []  # No textures for non-existing parents
                            expected_parent += 1
                        else:
                            current_parent = parent_num
                            current_bml = None
                            current_textures = []
                            last_valid_parent = parent_num
                            expected_parent = parent_num + 1
                    
                    elif line.startswith("BML Version:"):
                        # Only update BML version if not a -1 parent case
                        if current_bml != -1:
                            current_bml = int(line.split(":")[1].strip())
                    
                    elif line.startswith("Textures used by LOD0:"):
                        # Only process textures if not a -1 parent case
                        if current_bml != -1:
                            textures = line.split(":")[1].strip()
                            if textures:
                                current_textures = [t.strip() for t in textures.split(",") if t.strip()]
                
                # Process last parent
                if current_parent is not None and current_bml is not None:
                    self._process_parent_data(current_parent, current_bml, current_textures, current_parent == -1)
            
            # After processing parents, check all textures
            if self.korea_obj_path and self.korea_obj_hires_path:
                for texture_id in self.textures.keys():
                    texture_data, _ = self.check_texture_files(texture_id)
                    self.textures[texture_id].high_res = texture_data.high_res
                    self.textures[texture_id].pbr = texture_data.pbr
                    self.textures[texture_id].pbr_type = texture_data.pbr_type
            
            self.pdr_file = file_path
            logger.info(f"Successfully loaded texture data from PDR file")
            logger.info(f"Total unique valid textures loaded: {len(self.textures)}")
            
            # Remove parent 0 if it exists
            if 0 in self.parents:
                del self.parents[0]
            
            # Reset consolidation flag since new parent data was loaded
            if hasattr(self, 'parents_consolidated'):
                delattr(self, 'parents_consolidated')
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading PDR file: {str(e)}")
            return False
    
    def _process_parent_data(self, parent_number: int, bml_version: int, textures: List[str], is_outsourced: bool = False):
        # Check if this parent already exists (e.g., from cockpit data)
        existing_parent = self.parents.get(parent_number)
        
        # Find associated model data
        model_data = None
        for model in self.models.values():
            if (model.normal_model == str(parent_number) or
                model.fixed_model == str(parent_number) or
                model.destroyed_model == str(parent_number) or
                model.left_destroyed_model == str(parent_number) or
                model.right_destroyed_model == str(parent_number) or
                model.both_models_destroyed == str(parent_number) or
                model.damaged_model == str(parent_number)):
                model_data = model
                
                # Add BML version to model's versions set
                if not hasattr(model_data, 'bml_versions'):
                    model_data.bml_versions = set()
                model_data.bml_versions.add(bml_version)
                
                # Add textures to model's textures set
                if not hasattr(model_data, 'all_textures'):
                    model_data.all_textures = set()
                model_data.all_textures.update(textures)
                break
        
        # Handle parent data
        if existing_parent:
            # Update existing parent's textures and BML version
            existing_parent.textures = textures
            existing_parent.bml_version = bml_version
            parent_data = existing_parent
        elif model_data:
            # Create new parent data from model
            model_types = []
            
            # Check each model type
            if model_data.normal_model == str(parent_number):
                model_types.append("Normal")
            if model_data.fixed_model == str(parent_number):
                model_types.append("Repaired")
            if model_data.damaged_model == str(parent_number):
                model_types.append("Damaged")
            if model_data.destroyed_model == str(parent_number):
                model_types.append("Destroyed")
            if model_data.left_destroyed_model == str(parent_number):
                model_types.append("Left Destroyed")
            if model_data.right_destroyed_model == str(parent_number):
                model_types.append("Right Destroyed")
            if model_data.both_models_destroyed == str(parent_number):
                model_types.append("Both Destroyed")
            
            # Special case: if both Normal and Repaired are present, only show Normal
            if "Normal" in model_types and "Repaired" in model_types:
                model_types = [t for t in model_types if t != "Repaired"]
            
            # Join all model types with commas
            model_type = ", ".join(model_types)
            
            parent_data = ParentData(
                parent_number=parent_number,
                bml_version=bml_version,
                textures=textures,
                model_name=model_data.name,
                model_type=model_type,
                type=model_data.type,
                ct_number=model_data.ct_number,
                entity_idx=model_data.type_number,
                outsourced=is_outsourced
            )
            self.parents[parent_number] = parent_data
        else:
            # Create new parent data without model info
            parent_data = ParentData(
                parent_number=parent_number,
                bml_version=bml_version,
                textures=textures,
                model_name="",  # Empty for unknown models
                model_type="",
                type="",
                ct_number=0,  # No CT number
                entity_idx=0,  # No entity index
                outsourced=is_outsourced
            )
            self.parents[parent_number] = parent_data
        
        # Process textures for all parents (with or without CT numbers)
        if not is_outsourced and textures:  # Only process if not outsourced and has textures
            for texture_id in textures:
                if texture_id not in self.textures:
                    # Check texture availability and create TextureData
                    texture_data, exists = self.check_texture_files(texture_id)
                    texture_data.availability = exists
                    self.textures[texture_id] = texture_data
                
                # Add parent to texture's parent_models if not already there
                if parent_data not in self.textures[texture_id].parent_models:
                    self.textures[texture_id].parent_models.append(parent_data)

    def get_texture_data(self, texture_id: str) -> List[ParentData]:
        """Get all parent models associated with a texture."""
        if texture_id in self.textures:
            return self.textures[texture_id].parent_models
        return []

    def get_model_by_parent(self, parent_number: str) -> Optional[ModelData]:
        """Get model data associated with a parent number."""
        if parent_number in self.parents:
            parent_data = self.parents[parent_number]
            return self.models.get(parent_data.ct_number)
        return None

    def get_textures(self) -> List[str]:
        """Get list of all texture IDs."""
        return sorted(self.textures.keys(), key=int)
    
    def get_model_types(self) -> List[str]:
        return sorted(list(set(model.type for model in self.models.values())))
    
    def get_models_by_type(self, model_type: str = None) -> List[ModelData]:
        if model_type is None or model_type == "All":
            return list(self.models.values())
        return [model for model in self.models.values() if model.type == model_type]
    
    def get_model_by_ct(self, ct: int) -> Optional[ModelData]:
        return self.models.get(ct)
    
    def load_unused_textures(self, file_path: str) -> bool:
        try:
            self.unused_textures.clear()
            unused_data = []  # Store tuples of (texture_id, exists, texture_data)
            seen_textures = set()  # Track seen texture IDs
            
            # Set texture paths based on the location of the unused textures report
            base_path = os.path.dirname(file_path)
            self.set_texture_paths(base_path)
            
            with open(file_path, 'r') as f:
                # Skip the header line
                next(f)
                for line in f:
                    try:
                        texture_id = int(line.strip())
                        # Skip if we've already seen this texture ID
                        if texture_id in seen_textures:
                            logger.debug(f"Skipping duplicate texture ID: {texture_id}")
                            continue
                            
                        if 0 < texture_id < 10000:  # Validate texture ID range
                            seen_textures.add(texture_id)  # Add to seen set
                            texture_data, exists = self.check_texture_files(str(texture_id))
                            unused_data.append((texture_id, exists, texture_data))
                            logger.debug(f"Processed unused texture {texture_id}: exists={exists}, high_res={texture_data.high_res}")
                    except ValueError:
                        continue
            
            # Sort and store the valid texture IDs
            self.unused_textures = [data[0] for data in unused_data]
            self.unused_textures.sort()
            
            # Store the existence and texture data information
            self.unused_texture_data = {
                str(data[0]): {
                    "exists": data[1],
                    "texture_data": data[2]
                }
                for data in unused_data
            }
            
            total_lines = sum(1 for line in open(file_path)) - 1  # Subtract header line
            return True
            
        except Exception as e:
            logger.error(f"Error loading unused textures file: {str(e)}")
            return False
    
    def get_unused_texture_data(self, texture_id: str) -> Optional[dict]:
        """Get the existence and texture data for an unused texture."""
        return self.unused_texture_data.get(texture_id)
    
    def get_model_bml_versions(self, model: ModelData) -> str:
        """Get formatted BML versions string for a model."""
        if not hasattr(model, 'bml_versions'):
            return str(model.bml_version)  # Return default version
            
        versions = sorted(list(model.bml_versions))
        if len(versions) == 1:
            return str(versions[0])
        elif all(v == 1 for v in versions):
            return "1"
        elif all(v == 2 for v in versions):
            return "2"
        elif set(versions) == {1, 2}:
            return "1, 2"
        elif all(v == -1 for v in versions):
            return "-1"
        else:
            return ", ".join(str(v) for v in sorted(versions))
    
    def get_model_textures(self, model: ModelData) -> List[str]:
        """Get all textures associated with a model's parents."""
        if hasattr(model, 'all_textures'):
            return sorted(list(model.all_textures))
        return model.textures_used  # Return default textures if not updated print

    def get_unused_textures(self) -> List[int]:
        """Get list of all unused texture IDs."""
        return self.unused_textures

    def set_base_folder(self, ct_file_path: str):
        """Set base folder from CT file path."""
        # Get the base folder (up to Terrdata/objects)
        # Example: if ct_file_path is "C:/BMS/Data/Terrdata/objects/Falcon4_CT.xml"
        # base_folder should be "C:/BMS/Data/Terrdata/objects"
        self.base_folder = os.path.dirname(ct_file_path)
        logger.info(f"Set base folder: {self.base_folder}")

    def find_bms_main_folder(self) -> Optional[str]:
        """Find the main Falcon BMS folder by looking for launcher.exe."""
        if not self.base_folder:
            return None
            
        current_path = self.base_folder
        max_depth = 10  # Prevent infinite loops
        depth = 0
        
        while depth < max_depth:
            # Check if launcher.exe exists in current directory
            launcher_path = os.path.join(current_path, "launcher.exe")
            if os.path.exists(launcher_path):
                logger.info(f"Found BMS main folder: {current_path}")
                return current_path
            
            # Go up one directory
            parent_path = os.path.dirname(current_path)
            if parent_path == current_path:  # Reached root
                break
            current_path = parent_path
            depth += 1
        
        logger.warning("Could not find main BMS folder with launcher.exe")
        return None

    def get_path_relative_to_bms_main(self, path: str) -> str:
        """Convert a path to be relative to the main BMS folder instead of base_folder."""
        if not path:
            return path
            
        bms_main = self.find_bms_main_folder()
        if not bms_main or not self.base_folder:
            return path  # Fallback to original path
            
        try:
            # Calculate the relative path from BMS main to the CT file's directory (base_folder)
            base_relative_to_main = os.path.relpath(self.base_folder, bms_main)
            
            # If path is just a folder name like "KoreaObj", combine with the calculated base path
            if path in ["KoreaObj", "KoreaObj_HiRes"]:
                return os.path.join(base_relative_to_main, path)
            
            # If path starts with "Models", combine with the calculated base path  
            if path.startswith("Models"):
                return os.path.join(base_relative_to_main, path)
                
            # For absolute paths, try to make them relative to BMS main
            if os.path.isabs(path):
                try:
                    return os.path.relpath(path, bms_main)
                except ValueError:
                    return path  # Different drives, can't make relative
            
            # For other relative paths, combine with the calculated base path
            return os.path.join(base_relative_to_main, path)
            
        except ValueError:
            # If we can't calculate relative paths, return original
            return path

    def get_bml2_textures(self, parent_number: int) -> List[Dict[str, str]]:
        """Get PBR textures from materials.mtl file for a given parent number."""
        # Check cache first
        if hasattr(self, '_bml2_texture_cache') and parent_number in self._bml2_texture_cache:
            return self._bml2_texture_cache[parent_number]

        textures = []
        
        # Get parent data
        parent_data = self.parents.get(parent_number)
        if not parent_data or parent_data.bml_version != 2:
            return textures
            
        # Construct path for materials.mtl
        mtl_suggested_path = os.path.join(self.base_folder, "Models", str(parent_number), "materials.mtl")
        mtl_path = None
        if os.path.exists(mtl_suggested_path):
            mtl_path = mtl_suggested_path      
        else:
            return textures
        
        # Parse materials.mtl file
        try:
            with open(mtl_path, 'r') as f:
                data = json.load(f)
            
            # Track unique textures to avoid duplicates
            unique_textures = {}
            
            # Process each material
            for material in data.get("Materials", []):
                for texture in material.get("Textures", []):
                    file_name = texture.get("File", "")
                    if not file_name:
                        continue
                    
                    slot = texture.get("Slot", -1)
                    
                    # Determine texture type based on slot
                    texture_type = {
                        0: "Albedo",
                        1: "ARMW",
                        2: "Normal",
                        3: "Emission"
                    }.get(slot, "Unknown")
                    
                    # Process the texture name and path
                    # Remove .dds extension if present
                    base_name = file_name[:-4] if file_name.lower().endswith('.dds') else file_name
                    
                    # Normalize path separators (handle /, //, \, \\)
                    normalized_path = base_name.replace('\\\\', '/').replace('\\', '/').replace('//', '/')
                    
                    # Split path and filename
                    path_parts = normalized_path.split('/')
                    if len(path_parts) > 1:
                        texture_name = path_parts[-1]
                        texture_path = os.path.join("Models", *path_parts[:-1])
                    else:
                        texture_name = base_name
                        texture_path = os.path.join("Models", str(parent_number))
                    
                    # Add to unique textures if not already present
                    key = (texture_name, texture_type)
                    if key not in unique_textures:
                        unique_textures[key] = {
                            "name": texture_name,
                            "type": texture_type,
                            "path": texture_path
                        }
            
            # Convert unique textures to list
            textures = list(unique_textures.values())
            
            # Initialize cache if not exists
            if not hasattr(self, '_bml2_texture_cache'):
                self._bml2_texture_cache = {}
            
            # Cache the results
            self._bml2_texture_cache[parent_number] = textures
            
        except Exception as e:
            logger.error(f"Error parsing materials.mtl for parent {parent_number}: {str(e)}")
            return []
            
        return textures

    def _process_cockpit_data(self, ckpit_file: str, cockpit_name: str, cockpit_wings: int = None) -> int:
        """Helper function to process 3dCkpit.dat file and create parent data objects.
        Returns the number of cockpits processed."""
        try:
            if not os.path.exists(ckpit_file):
                logger.debug(f"Missing 3dCkpit.dat for {cockpit_name}")
                return 0
                
            # Parse 3dCkpit.dat
            with open(ckpit_file, 'r') as f:
                ckpit_content = f.read()
                
            # Extract parent numbers
            parent_info = []
            for line in ckpit_content.split('\n'):
                line = line.strip()
                if line.startswith('cockpitmodel '):
                    try:
                        parent_num = int(line.split()[1].rstrip(';'))
                        parent_info.append((parent_num, "Cockpit", "Cockpit"))
                    except (ValueError, IndexError) as e:
                        logger.debug(f"Invalid cockpit parent number in {cockpit_name}: {str(e)}")
                        continue
                elif line.startswith('cockpitmodel2 '):
                    try:
                        parent_num = int(line.split()[1].rstrip(';'))
                        parent_info.append((parent_num, "Cockpit", "Switches and Knobs"))
                    except (ValueError, IndexError) as e:
                        logger.debug(f"Invalid cockpit parent number in {cockpit_name}: {str(e)}")
                        continue
                elif line.startswith('cockpithudmodel '):
                    try:
                        parent_num = int(line.split()[1].rstrip(';'))
                        parent_info.append((parent_num, "Cockpit", "HUD and Glass"))
                    except (ValueError, IndexError) as e:
                        logger.debug(f"Invalid cockpit parent number in {cockpit_name}: {str(e)}")
                        continue
                elif line.startswith('cockpitrttcanopymodel '):
                    try:
                        parent_num = int(line.split()[1].rstrip(';'))
                        parent_info.append((parent_num, "Cockpit", "Additional Canopy"))
                    except (ValueError, IndexError) as e:
                        logger.debug(f"Invalid cockpit parent number in {cockpit_name}: {str(e)}")
                        continue
                elif line.startswith('cockpitcanopymodel '):
                    try:
                        parent_num = int(line.split()[1].rstrip(';'))
                        parent_info.append((parent_num, "Cockpit", "Canopy"))
                    except (ValueError, IndexError) as e:
                        logger.debug(f"Invalid cockpit parent number in {cockpit_name}: {str(e)}")
                        continue
                elif line.startswith('cockpitwingsmodel '):
                    try:
                        parent_num = int(line.split()[1].rstrip(';'))
                        parent_info.append((parent_num, "Cockpit", "Cockpit Wings"))
                    except (ValueError, IndexError) as e:
                        logger.debug(f"Invalid cockpit parent number in {cockpit_name}: {str(e)}")
                        continue
                elif line.startswith('cockpitmodel_empty '):
                    try:
                        parent_num = int(line.split()[1].rstrip(';'))
                        parent_info.append((parent_num, "Cockpit", "Empty Cockpit"))
                    except (ValueError, IndexError) as e:
                        logger.debug(f"Invalid cockpit parent number in {cockpit_name}: {str(e)}")
                        continue
                elif line.startswith('cockpitcanopymodel_empty '):
                    try:
                        parent_num = int(line.split()[1].rstrip(';'))
                        parent_info.append((parent_num, "Cockpit", "Empty Canopy"))
                    except (ValueError, IndexError) as e:
                        logger.debug(f"Invalid cockpit parent number in {cockpit_name}: {str(e)}")
                        continue
                elif line.startswith('cockpitlegsmodel '):
                    try:
                        parent_num = int(line.split()[1].rstrip(';'))
                        parent_info.append((parent_num, "Cockpit", "Legs"))
                    except (ValueError, IndexError) as e:
                        logger.debug(f"Invalid cockpit parent number in {cockpit_name}: {str(e)}")
                        continue
                elif line.startswith('cockpitmixedrealitycovermodel '):
                    try:
                        parent_num = int(line.split()[1].rstrip(';'))
                        parent_info.append((parent_num, "Cockpit", "AR Mask"))
                    except (ValueError, IndexError) as e:
                        logger.debug(f"Invalid cockpit parent number in {cockpit_name}: {str(e)}")
                        continue
            
            # Add cockpit wings parent if found and not -1
            if cockpit_wings and cockpit_wings != -1:
                parent_info.append((cockpit_wings, "Cockpit", "Cockpit Wings"))
            
            # Create ParentData objects for each parent
            cockpits_processed = 0
            for parent_num, type_, model_type in parent_info:
                # Skip invalid parent numbers
                if parent_num <= 0:
                    continue

                # Check if parent already exists and handle multiple aircraft variants
                if parent_num in self.parents:
                    existing_parent = self.parents[parent_num]
                    
                    # If this is already a cockpit parent, add as aircraft variant
                    if existing_parent.type == "Cockpit":
                        # Initialize aircraft_variants if it doesn't exist
                        if not hasattr(existing_parent, 'aircraft_variants'):
                            existing_parent.aircraft_variants = {}
                        
                        # Add this aircraft variant
                        existing_parent.aircraft_variants[cockpit_name] = model_type
                        logger.debug(f"Added aircraft variant {cockpit_name} to existing cockpit parent {parent_num}")
                    else:
                        # Update existing parent to be cockpit type
                        existing_parent.type = type_
                        existing_parent.model_name = f"{cockpit_name} {model_type}"
                        existing_parent.model_type = model_type
                        # Initialize aircraft_variants
                        existing_parent.aircraft_variants = {cockpit_name: model_type}
                else:
                    # Create new parent data
                    parent_data = ParentData(
                        parent_number=parent_num,
                        bml_version=1,  # Default to 1 for cockpit models
                        textures=[],  # Empty list as textures should come from PDR file
                        model_name=f"{cockpit_name} {model_type}",
                        model_type=model_type,
                        type=type_,  # This should be "Cockpit"
                        ct_number=0,  # No CT number for cockpit models
                        entity_idx=0,  # No entity index for cockpit models
                        outsourced=False
                    )
                    # Initialize aircraft_variants for new cockpit parents
                    parent_data.aircraft_variants = {cockpit_name: model_type}
                    self.parents[parent_num] = parent_data
                    cockpits_processed += 1
                    logger.debug(f"Created new cockpit parent {parent_num} for {cockpit_name}")
            
            return cockpits_processed
            
        except Exception as e:
            logger.error(f"Error processing 3dCkpit.dat for {cockpit_name}: {str(e)}")
            return 0

    def load_cockpit_parents(self, base_path: str) -> bool:
        """Load cockpit parent data from Acdata and CkptArt folders."""
        try:
            # Get root path (up to Terrdata/Objects) - this should be the base BMS folder
            root_path = os.path.dirname(os.path.dirname(os.path.dirname(base_path)))
            
            # Define possible paths for Acdata and CkptArt
            # Try both the calculated root path and the base_folder path
            base_folder_root = os.path.dirname(self.base_folder) if self.base_folder else os.path.dirname(base_path)
            
            acdata_paths = [
                os.path.join(root_path, "Sim", "Acdata"),
                os.path.join(os.path.dirname(base_path), "Sim", "Acdata"),
                os.path.join(base_folder_root, "Sim", "Acdata")
            ]
            
            ckptart_paths = [
                os.path.join(root_path, "art", "ckptart"),  # lowercase as mentioned by user
                os.path.join(root_path, "Art", "CkptArt"),  # uppercase variant
                os.path.join(os.path.dirname(base_path), "art", "ckptart"),
                os.path.join(os.path.dirname(base_path), "Art", "CkptArt"),
                os.path.join(base_folder_root, "art", "ckptart"),
                os.path.join(base_folder_root, "Art", "CkptArt")
            ]
            
            # Find valid Acdata path
            acdata_path = None
            for path in acdata_paths:
                try:
                    if os.path.exists(path):
                        acdata_path = path
                        break
                except Exception as e:
                    logger.error(f"Error checking Acdata path {path}: {str(e)}")
                    continue
                
            if not acdata_path:
                logger.warning("Could not find Acdata folder")
                return False
            
            # Find valid CkptArt path
            ckptart_path = None
            for path in ckptart_paths:
                try:
                    if os.path.exists(path):
                        ckptart_path = path
                        break
                except Exception as e:
                    logger.error(f"Error checking CkptArt path {path}: {str(e)}")
                    continue
                
            if not ckptart_path:
                logger.warning("Could not find CkptArt folder")
                logger.info(f"Tried CkptArt paths: {ckptart_paths}")
                return False

            logger.info(f"Using Acdata path: {acdata_path}")
            logger.info(f"Using CkptArt path: {ckptart_path}")

            # Create array to remember visited folders in CkptArt
            visited_folders = set()
            cockpits_found = 0
            
            # Process all .txtpb files in Acdata
            for txtpb_file in glob.glob(os.path.join(acdata_path, "*.txtpb")):
                try:
                    with open(txtpb_file, 'r') as f:
                        content = f.read()
                        
                    # Extract cockpit_name, cockpit_wings_parent, and type_ac
                    cockpit_name = None
                    cockpit_wings = None
                    type_ac = "NONE"
                    
                    for line in content.split('\n'):
                        if "cockpit_name" in line:
                            cockpit_name = line.split('"')[1] if '"' in line else None
                        elif "cockpit_wings_parent" in line:
                            try:
                                cockpit_wings = int(line.split()[-1])
                            except ValueError:
                                continue
                        elif "type_ac:" in line:
                            type_ac = line.split(':')[1].strip()
                    
                    # If no cockpit_name but type_ac is not NONE, use the txtpb filename
                    if (not cockpit_name or not cockpit_name.strip()) and type_ac != "NONE":
                        txtpb_basename = os.path.splitext(os.path.basename(txtpb_file))[0]
                        ckpit_folder = os.path.join(ckptart_path, txtpb_basename)
                        ckpit_file = os.path.join(ckpit_folder, "3dCkpit.dat")
                        
                        if os.path.exists(ckpit_file):
                            logger.info(f"Found cockpit for {txtpb_basename} using type_ac: {type_ac}")
                            cockpit_name = txtpb_basename
                    
                    if not cockpit_name:
                        continue
                        
                    # Process cockpit data using helper function
                    ckpit_file = os.path.join(ckptart_path, cockpit_name, "3dCkpit.dat")
                    processed_count = self._process_cockpit_data(ckpit_file, cockpit_name, cockpit_wings)
                    cockpits_found += processed_count
                    
                    # Add folder name to visited folders array
                    if processed_count > 0:
                        visited_folders.add(cockpit_name)
                
                except Exception as e:
                    logger.error(f"Error processing {txtpb_file}: {str(e)}")
                    continue
            
            # Process unvisited folders in CkptArt
            try:
                logger.info("Processing unvisited CkptArt folders...")
                unvisited_cockpits = 0
                
                for folder_name in os.listdir(ckptart_path):
                    folder_path = os.path.join(ckptart_path, folder_name)
                    
                    # Skip if not a directory or already visited
                    if not os.path.isdir(folder_path) or folder_name in visited_folders:
                        continue
                    
                    # Use folder name as cockpit name
                    ckpit_file = os.path.join(folder_path, "3dCkpit.dat")
                    processed_count = self._process_cockpit_data(ckpit_file, folder_name)
                    
                    if processed_count > 0:
                        unvisited_cockpits += processed_count
                        logger.info(f"Processed unvisited cockpit folder: {folder_name}")
                
                logger.info(f"Successfully loaded {unvisited_cockpits} cockpit parents from unvisited folders")
                cockpits_found += unvisited_cockpits
                
            except Exception as e:
                logger.error(f"Error processing unvisited CkptArt folders: {str(e)}")
            
            logger.info(f"Successfully loaded {cockpits_found} total cockpit parents")
            return True
            
        except Exception as e:
            logger.error(f"Error loading cockpit parents: {str(e)}")
            return False

    def load_parents_from_models_folder(self) -> bool:
        """Load parent data from Models folder when PDR is not available."""
        try:
            if not self.base_folder:
                logger.error("Base folder not set")
                return False

            models_path = os.path.join(self.base_folder, "Models")
            if not os.path.exists(models_path):
                logger.error(f"Models folder not found at: {models_path}")
                return False

            # Track all parent numbers to identify missing ones later
            found_parents = set()
            bml2_parents = set()  # Track BML2 parents for later texture processing

            # First pass: identify all existing parents and BML2 parents
            for folder_name in os.listdir(models_path):
                try:
                    if not folder_name.isdigit():
                        continue

                    parent_number = int(folder_name)
                    found_parents.add(parent_number)
                    folder_path = os.path.join(models_path, folder_name)
                    
                    # Check if materials.mtl exists to determine BML version
                    materials_file = os.path.join(folder_path, "materials.mtl")
                    if os.path.exists(materials_file):
                        bml2_parents.add(parent_number)

                except Exception as e:
                    logger.error(f"Error checking parent folder {folder_name}: {str(e)}")
                    continue

            # Second pass: process all models and update their BML versions
            for model in self.models.values():
                # Initialize BML versions set for the model
                if not hasattr(model, 'bml_versions'):
                    model.bml_versions = set()

                # Check each parent reference in the model
                for parent_attr in ['normal_model', 'fixed_model', 'damaged_model', 'destroyed_model', 
                                  'left_destroyed_model', 'right_destroyed_model', 'both_models_destroyed']:
                    parent_num = getattr(model, parent_attr)
                    if parent_num and parent_num.isdigit():
                        parent_number = int(parent_num)
                        if parent_number in bml2_parents:
                            model.bml_versions.add(2)  # BML2 if materials.mtl exists
                        elif parent_number in found_parents:
                            model.bml_versions.add(1)  # BML1 if folder exists but no materials.mtl
                        else:
                            model.bml_versions.add(-1)  # BML-1 if parent doesn't exist

            # Third pass: create parent data objects and process BML2 textures
            for folder_name in os.listdir(models_path):
                try:
                    if not folder_name.isdigit():
                        continue

                    parent_number = int(folder_name)
                    folder_path = os.path.join(models_path, folder_name)
                    
                    # Determine BML version
                    materials_file = os.path.join(folder_path, "materials.mtl")
                    bml_version = 2 if os.path.exists(materials_file) else 1

                    # Find associated model
                    model_data = None
                    for model in self.models.values():
                        if (model.normal_model == str(parent_number) or
                            model.fixed_model == str(parent_number) or
                            model.destroyed_model == str(parent_number) or
                            model.left_destroyed_model == str(parent_number) or
                            model.right_destroyed_model == str(parent_number) or
                            model.both_models_destroyed == str(parent_number) or
                            model.damaged_model == str(parent_number)):
                            model_data = model
                            break

                    # Create parent data
                    if model_data:
                        model_types = []
                        if model_data.normal_model == str(parent_number):
                            model_types.append("Normal")
                        if model_data.fixed_model == str(parent_number):
                            model_types.append("Repaired")
                        if model_data.damaged_model == str(parent_number):
                            model_types.append("Damaged")
                        if model_data.destroyed_model == str(parent_number):
                            model_types.append("Destroyed")
                        if model_data.left_destroyed_model == str(parent_number):
                            model_types.append("Left Destroyed")
                        if model_data.right_destroyed_model == str(parent_number):
                            model_types.append("Right Destroyed")
                        if model_data.both_models_destroyed == str(parent_number):
                            model_types.append("Both Destroyed")

                        # Special case: if both Normal and Repaired are present, only show Normal
                        if "Normal" in model_types and "Repaired" in model_types:
                            model_types = [t for t in model_types if t != "Repaired"]

                        model_type = ", ".join(model_types)

                        parent_data = ParentData(
                            parent_number=parent_number,
                            bml_version=bml_version,
                            textures=[],  # Will be populated later for BML2
                            model_name=model_data.name,
                            model_type=model_type,
                            type=model_data.type,
                            ct_number=model_data.ct_number,
                            entity_idx=model_data.type_number,
                            outsourced=False
                        )
                    else:
                        # Parent exists but no associated model
                        parent_data = ParentData(
                            parent_number=parent_number,
                            bml_version=bml_version,
                            textures=[],
                            model_name="",
                            model_type="",
                            type="",
                            ct_number=0,
                            entity_idx=0,
                            outsourced=False
                        )

                    self.parents[parent_number] = parent_data

                    # Process BML2 textures
                    if bml_version == 2:
                        if os.path.exists(materials_file):
                            try:
                                textures = self.get_bml2_textures(parent_number)
                                for texture in textures:
                                    texture_id = texture['name']
                                    texture_type = texture['type']
                                    texture_path = texture['path']

                                    # Create or update texture data
                                    if texture_id not in self.textures:
                                        texture_data = TextureData(
                                            texture_id=texture_id,
                                            parent_models=[],
                                            high_res=False,
                                            pbr=[],
                                            pbr_type=[],
                                            availability=True
                                        )
                                        self.textures[texture_id] = texture_data

                                    # Add parent to texture's parent_models if not already there
                                    if parent_data not in self.textures[texture_id].parent_models:
                                        self.textures[texture_id].parent_models.append(parent_data)

                                    # Check if texture files exist
                                    base_path = os.path.join(self.base_folder, texture_path)
                                    texture_file = os.path.join(base_path, f"{texture_id}.dds")
                                    
                                    # Update texture data based on file existence
                                    self.textures[texture_id].availability = os.path.exists(texture_file)

                                    # For PBR textures, check and add variants
                                    if texture_type in ["Normal", "ARMW"]:
                                        if texture_type == "Normal" and texture_id not in self.textures[texture_id].pbr:
                                            self.textures[texture_id].pbr.append(texture_id)
                                            self.textures[texture_id].pbr_type.append("normal")
                                        elif texture_type == "ARMW" and texture_id not in self.textures[texture_id].pbr:
                                            self.textures[texture_id].pbr.append(texture_id)
                                            self.textures[texture_id].pbr_type.append("armw")

                            except Exception as e:
                                logger.error(f"Error processing materials.mtl for parent {parent_number}: {str(e)}")
                        else:
                            logger.warning(f"No materials.mtl found for parent {parent_number}")

                except Exception as e:
                    logger.error(f"Error processing parent folder {folder_name}: {str(e)}")
                    continue

            # Add missing parents as BML version -1
            for model in self.models.values():
                for parent_attr in ['normal_model', 'fixed_model', 'damaged_model', 'destroyed_model', 
                                  'left_destroyed_model', 'right_destroyed_model', 'both_models_destroyed']:
                    parent_num = getattr(model, parent_attr)
                    if parent_num and parent_num.isdigit():
                        parent_number = int(parent_num)
                        if parent_number not in found_parents and parent_number not in self.parents:
                            parent_data = ParentData(
                                parent_number=parent_number,
                                bml_version=-1,
                                textures=[],
                                model_name=model.name,
                                model_type="Missing",
                                type=model.type,
                                ct_number=model.ct_number,
                                entity_idx=model.type_number,
                                outsourced=True
                            )
                            self.parents[parent_number] = parent_data

            logger.info(f"Completed loading from Models folder. Found {len(bml2_parents)} BML2 parents and {len(self.textures)} textures")
            return True

        except Exception as e:
            logger.error(f"Error loading parents from Models folder: {str(e)}")
            return False

    def get_models_using_parent(self, parent_number: int) -> List[ModelData]:
        """Get all models that use a specific parent number."""
        models_using_parent = []
        parent_str = str(parent_number)
        
        for model in self.models.values():
            # Check if this model uses the parent number in any of its model states
            if (model.normal_model == parent_str or
                model.fixed_model == parent_str or
                model.damaged_model == parent_str or
                model.destroyed_model == parent_str or
                model.left_destroyed_model == parent_str or
                model.right_destroyed_model == parent_str or
                model.both_models_destroyed == parent_str):
                models_using_parent.append(model)
        
        return models_using_parent

    def consolidate_parent_data(self):
        """Consolidate and deduplicate parent data, ensuring each parent shows all associated models."""
        try:
            logger.info("Starting parent data consolidation...")
            
            # Track parents that need consolidation
            consolidated_parents = {}
            
            for parent_number, parent_data in self.parents.items():
                # Get all models that use this parent
                models_using_parent = self.get_models_using_parent(parent_number)
                
                if models_using_parent:
                    # If we have models using this parent, update the parent data
                    consolidated_parent = ParentData(
                        parent_number=parent_number,
                        bml_version=parent_data.bml_version,
                        textures=parent_data.textures,
                        model_name=parent_data.model_name,
                        model_type=parent_data.model_type,
                        type=parent_data.type,
                        ct_number=parent_data.ct_number,
                        entity_idx=parent_data.entity_idx,
                        outsourced=parent_data.outsourced
                    )
                    
                    # Copy aircraft_variants if they exist
                    if hasattr(parent_data, 'aircraft_variants'):
                        consolidated_parent.aircraft_variants = parent_data.aircraft_variants
                    
                    consolidated_parents[parent_number] = consolidated_parent
                else:
                    # Keep the parent as is if no models are using it (e.g., cockpit-only parents)
                    consolidated_parents[parent_number] = parent_data
            
            # Update the parents dictionary
            self.parents = consolidated_parents
            
            logger.info(f"Consolidated {len(consolidated_parents)} parent entries")
            return True
            
        except Exception as e:
            logger.error(f"Error consolidating parent data: {str(e)}")
            return False

    def debug_cockpit_paths(self, base_path: str):
        """Debug utility to show all potential cockpit art paths."""
        logger.info("=== Cockpit Path Debug ===")
        logger.info(f"Base path: {base_path}")
        logger.info(f"Base folder: {self.base_folder}")
        
        # Get root path (up to Terrdata/Objects) - this should be the base BMS folder
        root_path = os.path.dirname(os.path.dirname(os.path.dirname(base_path)))
        base_folder_root = os.path.dirname(self.base_folder) if self.base_folder else os.path.dirname(base_path)
        
        logger.info(f"Root path: {root_path}")
        logger.info(f"Base folder root: {base_folder_root}")
        
        # List all potential paths and their existence
        ckptart_paths = [
            os.path.join(root_path, "art", "ckptart"),
            os.path.join(root_path, "Art", "CkptArt"),
            os.path.join(os.path.dirname(base_path), "art", "ckptart"),
            os.path.join(os.path.dirname(base_path), "Art", "CkptArt"),
            os.path.join(base_folder_root, "art", "ckptart"),
            os.path.join(base_folder_root, "Art", "CkptArt")
        ]
        
        for i, path in enumerate(ckptart_paths):
            exists = os.path.exists(path)
            logger.info(f"CkptArt path {i+1}: {path} - Exists: {exists}")
            if exists:
                try:
                    contents = os.listdir(path)
                    logger.info(f"  Contents count: {len(contents)}")
                    # Show first few folders as examples
                    folders = [item for item in contents[:5] if os.path.isdir(os.path.join(path, item))]
                    logger.info(f"  Sample folders: {folders}")
                except Exception as e:
                    logger.error(f"  Error reading directory: {str(e)}")
        
        logger.info("=== End Cockpit Path Debug ===")
