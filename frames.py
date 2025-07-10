import customtkinter as ctk
from PIL import Image, ImageTk
from typing import List, Callable, Optional
from data_manager import ModelData, TextureData
from loguru import logger
from tkinter import ttk, messagebox
import ctypes
import threading
import os
import datetime
import math

# Configure logger
logger.remove()  # Remove any existing handlers
logger.add(
    "logs/data_manager.log",
    rotation="10 MB",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {function}:{line} | {message}",
    level="DEBUG",  # Set to DEBUG to capture all log levels
    enqueue=True,  # Enable thread-safe logging
    backtrace=True,  # Include backtrace for errors
    diagnose=True,  # Include diagnostic information
    catch=True  # Catch any errors during logging
)

class HomeFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, corner_radius=0)
        
        # Get DPI scaling
        try:
            awareness = ctypes.c_int()
            ctypes.windll.shcore.GetProcessDpiAwareness(0, ctypes.byref(awareness))
            dpi = ctypes.windll.user32.GetDpiForWindow(self.winfo_id()) / 96.0
        except Exception:
            dpi = self.winfo_fpixels('1i') / 72.0  # Fallback method
        
        # Calculate scaled sizes
        self.title_font_size = int(32 * dpi)
        self.subtitle_font_size = int(20 * dpi)
        self.base_font_size = int(14 * dpi)
        
        # Configure grid and frame color
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)  # Row 0 for logo, Row 1 for content
        self.configure(fg_color="#E3F4FF")  # Light blue background
        
        # Create main content frame that will expand horizontally
        self.content_frame = ctk.CTkFrame(self)
        self.content_frame.grid(row=1, column=0, padx=40, pady=(20, 40), sticky="nsew")
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.configure(fg_color="#F5F6F7")  # Very light gray background
        
        # Load and display F-16 logo in center
        try:
            logo_path = os.path.join("assets", "f16_logo.png")  # Update with your actual logo file
            logo_image = Image.open(logo_path)
            
            # Calculate logo size (30% of frame width)
            frame_width = self.winfo_width()
            if frame_width == 1:  # Not yet rendered
                frame_width = 800  # Default width
            
            logo_width = int(frame_width * 0.3)
            logo_height = int(logo_width * (logo_image.height / logo_image.width))
            
            logo = ctk.CTkImage(
                light_image=logo_image,
                dark_image=logo_image,
                size=(logo_width, logo_height)
            )
            
            self.logo_label = ctk.CTkLabel(
                self.content_frame,
                text="",
                image=logo
            )
            self.logo_label.grid(row=0, column=0, padx=20, pady=(40, 40))
            
        except Exception as e:
            logger.error(f"Error loading logo: {str(e)}")
        
        # Welcome text
        welcome_text = (
            "Welcome to the 3D Assets Manager for Falcon BMS"
        )
        
        self.welcome_label = ctk.CTkLabel(
            self.content_frame,
            text=welcome_text,
            font=ctk.CTkFont(size=self.subtitle_font_size, weight="bold"),
            text_color="#2D3B45",
            justify="center"
        )
        self.welcome_label.grid(row=1, column=0, padx=40, pady=(20, 30), sticky="ew")
        
        # Features section - very simplified
        features_text = (
            "• Browse and analyze 3D models\n"
            "• Track textures and materials\n"
            "• Manage PBR assets\n"
            "• Monitor unused resources"
        )
        
        self.features_label = ctk.CTkLabel(
            self.content_frame,
            text=features_text,
            font=ctk.CTkFont(size=self.base_font_size),
            text_color="#2D3B45",
            justify="center"
        )
        self.features_label.grid(row=2, column=0, padx=40, pady=(0, 30), sticky="ew")
        
        # Quick start - minimal
        workflow_text = (
            "Select Falcon4_CT.xml file to begin"
        )
        
        self.workflow_label = ctk.CTkLabel(
            self.content_frame,
            text=workflow_text,
            font=ctk.CTkFont(size=self.base_font_size, weight="bold"),
            text_color="#2D3B45",
            justify="center"
        )
        self.workflow_label.grid(row=3, column=0, padx=40, pady=(0, 20), sticky="ew")
        
        # Bind resize event
        self.bind("<Configure>", self._on_resize)
    
    def _on_resize(self, event=None):
        """Handle window resize event to adjust text wrapping and images."""
        if event and event.widget == self:
            # Update logo size if exists and is an image
            if hasattr(self, 'logo_label') and isinstance(self.logo_label._image, ctk.CTkImage):
                logo_width = int(event.width * 0.3)  # 30% of window width
                logo_height = int(logo_width * (self.logo_label._image._size[1] / self.logo_label._image._size[0]))
                self.logo_label._image.configure(size=(logo_width, logo_height))
            
            # Force update
            self.update_idletasks()

class ModelsFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, corner_radius=0)
        
        # Set frame background color
        self.configure(fg_color="#E3F4FF")
        
        # Initialize legend button color and details widgets dictionary
        self.legend_button_color = None
        self.detail_widgets = {}
        
        # Get DPI scaling
        try:
            awareness = ctypes.c_int()
            ctypes.windll.shcore.GetProcessDpiAwareness(0, ctypes.byref(awareness))
            dpi = ctypes.windll.user32.GetDpiForWindow(self.winfo_id()) / 96.0
        except Exception:
            dpi = self.winfo_fpixels('1i') / 72.0  # Fallback method
        
        # Calculate scaled sizes
        self.base_font_size = int(12 * dpi)  # Base font size
        self.table_font_size = int(11 * dpi)  # Table content font size
        self.table_header_size = int(12 * dpi)  # Table header font size
        self.row_height = int(25 * dpi)  # Row height

        # Configure style for row height only
        style = ttk.Style()
        style.configure("Treeview", rowheight=self.row_height)
        
        # Configure grid - make both columns expandable
        self.grid_columnconfigure(0, weight=1)  # Table column
        self.grid_columnconfigure(1, weight=1)  # Details column
        self.grid_rowconfigure(1, weight=1)     # Main content row
        
        # Search frame with new color
        self.search_frame = ctk.CTkFrame(self)
        self.search_frame.grid(row=0, column=0, columnspan=2, padx=20, pady=10, sticky="ew")
        self.search_frame.grid_columnconfigure(3, weight=1)  # Make search entry expandable
        self.search_frame.grid_columnconfigure(0, weight=0)  # Legend button fixed
        self.search_frame.grid_columnconfigure(1, weight=0)  # Version filter fixed
        self.search_frame.grid_columnconfigure(2, weight=0)  # Type filter fixed
        self.search_frame.grid_columnconfigure(4, weight=0)  # Search button fixed
        self.search_frame.configure(fg_color="#D4E5F2")  # Lighter shade for search frame
        
        # Add legend button with new colors
        self.legend_button = ctk.CTkButton(
            self.search_frame,
            text="Legend",
            width=80,
            command=self.show_legend,
            fg_color="#7A92A9",
            hover_color="#6E8499",
            text_color="#FFFFFF"
        )
        self.legend_button.grid(row=0, column=0, padx=5, pady=5)
        
        # Version filter with new colors
        self.color_var = ctk.StringVar(value="All BMLs")
        self.color_menu = ctk.CTkOptionMenu(
            self.search_frame,
            variable=self.color_var,
            values=["All BMLs", "Version 2", "Versions -1/1 & 2", "Version -1", "Version -1 & 1"],
            command=self.filter_models,
            font=ctk.CTkFont(size=self.base_font_size),
            fg_color="#7A92A9",
            button_color="#6E8499",
            button_hover_color="#5D7388",
            text_color="#FFFFFF",
            dropdown_fg_color="#7A92A9",
            dropdown_hover_color="#6E8499",
            dropdown_text_color="#FFFFFF"
        )
        self.color_menu.grid(row=0, column=1, padx=5, pady=5)
        
        # Type filter with new colors
        self.type_var = ctk.StringVar(value="All")
        self.type_menu = ctk.CTkOptionMenu(
            self.search_frame,
            variable=self.type_var,
            values=["All", "Feature", "Vehicle", "Weapon"],
            command=self.filter_models,
            font=ctk.CTkFont(size=self.base_font_size),
            fg_color="#7A92A9",
            button_color="#6E8499",
            button_hover_color="#5D7388",
            text_color="#FFFFFF",
            dropdown_fg_color="#7A92A9",
            dropdown_hover_color="#6E8499",
            dropdown_text_color="#FFFFFF"
        )
        self.type_menu.grid(row=0, column=2, padx=5, pady=5)
        
        # Search entry with new colors
        self.search_entry = ctk.CTkEntry(
            self.search_frame,
            placeholder_text="Search by name or CT number...",
            font=ctk.CTkFont(size=self.base_font_size),
            fg_color="#FFFFFF",
            border_color="#7A92A9",
            text_color="#2D3B45"
        )
        self.search_entry.grid(row=0, column=3, padx=5, pady=5, sticky="ew")
        self.search_entry.bind("<Return>", self.filter_models)
        
        # Search button with new colors
        self.search_button = ctk.CTkButton(
            self.search_frame,
            text="Search",
            command=self.filter_models,
            font=ctk.CTkFont(size=self.base_font_size),
            fg_color="#7A92A9",
            hover_color="#6E8499",
            text_color="#FFFFFF"
        )
        self.search_button.grid(row=0, column=4, padx=5, pady=5)
        
        # Status label with new colors
        self.status_label = ctk.CTkLabel(
            self.search_frame,
            text="",
            font=ctk.CTkFont(size=self.base_font_size),
            text_color="#2D3B45"
        )
        self.status_label.grid(row=1, column=0, columnspan=5, padx=5, pady=(0, 5), sticky="ew")
        
        # Create table frame with new color
        self.table_frame = ctk.CTkFrame(self)
        self.table_frame.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="nsew")
        self.table_frame.grid_columnconfigure(0, weight=1)
        self.table_frame.grid_rowconfigure(0, weight=1)
        self.table_frame.configure(fg_color="#D4E5F2")  # Lighter shade for table frame
        
        # Create and configure Treeview style
        style = ttk.Style()
        style.configure(
            "Treeview",
            rowheight=self.row_height,
            font=('Segoe UI', self.table_font_size),
            background="#FFFFFF",
            fieldbackground="#FFFFFF",
            foreground="#2D3B45"
        )
        style.configure(
            "Treeview.Heading",
            font=('Segoe UI', self.table_header_size, 'bold'),
            background="#B8CFE5",  # Lighter background for headers
            foreground="#2D3B45"   # Dark text for better visibility
        )
        style.map(
            "Treeview.Heading",
            background=[("pressed", "#A1B9D0"), ("active", "#A1B9D0")],  # Darker when pressed/hovered
            foreground=[("pressed", "#2D3B45"), ("active", "#2D3B45")]   # Keep text dark
        )
        
        # Create Treeview with adjusted column widths
        self.tree = ttk.Treeview(
            self.table_frame,
            columns=("ct", "type", "name"),
            show="headings",
            style="Treeview"
        )
        
        # Configure tags using the master's method
        self.master.master.configure_treeview_tags(self.tree)
        
        # Configure BML version tags
        self.tree.tag_configure("bml2", background="#2E7D32", foreground="white")  # Dark green
        self.tree.tag_configure("bml1_2", background="#81C784")  # Light green
        self.tree.tag_configure("bml_1", background="#1565C0", foreground="white")  # Dark blue
        self.tree.tag_configure("bml_1_1", background="#90CAF9")  # Light blue
        self.tree.tag_configure("bml_1_1_2", background="#81C784")  # Light green, same as bml1_2
        
        # Configure columns with scaled widths
        self.tree.heading("ct", text="CT", command=lambda: self.sort_table("ct"))
        self.tree.heading("type", text="Type", command=lambda: self.sort_table("type"))
        self.tree.heading("name", text="Name", command=lambda: self.sort_table("name"))
        
        self.tree.column("ct", width=int(80 * dpi), anchor="w")
        self.tree.column("type", width=int(100 * dpi), anchor="w")
        self.tree.column("name", width=int(300 * dpi), anchor="w")
        
        # Add scrollbars
        vsb = ttk.Scrollbar(self.table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(self.table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # Grid layout for table and scrollbars
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        # Bind selection event
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        
        # Store references
        self.models = []
        self.filtered_models = []
        self.current_sort = None
        self.sort_ascending = True
        
        # Setup details frame
        self.setup_details()
    
    def setup_details(self):
        # Model details frame with new color
        self.details_frame = ctk.CTkFrame(self)
        self.details_frame.grid(row=1, column=1, padx=20, pady=10, sticky="nsew")
        self.details_frame.grid_columnconfigure(0, weight=1)
        self.details_frame.grid_rowconfigure(0, weight=1)
        self.details_frame.configure(fg_color="#B8CFE5")  # Slightly darker shade for details frame
        
        # Create a scrollable frame for details with new colors
        self.details_scroll = ctk.CTkScrollableFrame(
            self.details_frame,
            fg_color="#D4E5F2"  # Lighter shade for content area
        )
        self.details_scroll.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # Create a frame for the details content
        self.details_content = ctk.CTkFrame(
            self.details_scroll,
            fg_color="transparent"
        )
        self.details_content.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.details_content.grid_columnconfigure(1, weight=1)
        
        # Setup details with new colors
        fields = [
            "Name", "Type", "CT Number", "Entity Index",
            "Normal Model", "Repaired Model", "Damaged Model",
            "Destroyed Model", "Left Destroyed Model",
            "Right Destroyed Model", "Both Destroyed Model",
            "BML Version", "Textures Used"
        ]
        
        for i, field in enumerate(fields):
            # Create label frame
            label_frame = ctk.CTkFrame(
                self.details_content,
                fg_color="transparent"
            )
            label_frame.grid(row=i, column=0, padx=(5,10), pady=2, sticky="nw")
            
            # Create label
            label = ctk.CTkLabel(
                label_frame,
                text=f"{field}:",
                anchor="w",
                font=ctk.CTkFont(size=self.base_font_size, weight="bold"),
                text_color="#2D3B45"
            )
            label.grid(row=0, column=0, padx=5, pady=2, sticky="w")
            
            # Create value widget
            if field == "Textures Used":
                value = ctk.CTkTextbox(
                    self.details_content,
                    font=ctk.CTkFont(size=self.base_font_size),
                    fg_color="#FFFFFF",
                    border_color="#7A92A9",
                    text_color="#2D3B45",
                    state="disabled",
                    wrap="word",
                    height=int(100 * (self.base_font_size/12))
                )
                value.grid(row=i, column=1, padx=(0,20), pady=(2,5), sticky="ew")
            else:
                value = ctk.CTkEntry(
                    self.details_content,
                    font=ctk.CTkFont(size=self.base_font_size),
                    fg_color="#FFFFFF",
                    border_color="#7A92A9",
                    text_color="#2D3B45",
                    state="readonly"
                )
                value.grid(row=i, column=1, padx=(0,20), pady=2, sticky="ew")
            
            # Store reference
            self.detail_widgets[field] = value
    
    def _on_select(self, event):
        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            ct_number = int(item['values'][0])
            for model in self.filtered_models:
                if model.ct_number == ct_number:
                    self.show_model_details(model)
                    break
    
    def update_table(self, models: List[ModelData]):
        self.models = models
        self.status_label.configure(text=f"Loading {len(models)} models...")
        self.update()
        self.filter_models()
    
    def _get_model_color_tag(self, model):
        """Get the color tag for a model based on its BML versions."""
        bml_versions = self.master.master.data_manager.get_model_bml_versions(model)
        
        if bml_versions == "2":
            return "bml2"
        elif bml_versions == "1, 2":
            return "bml1_2"
        elif bml_versions == "-1":
            return "bml_1"
        elif bml_versions == "-1, 1":
            return "bml_1_1"
        elif bml_versions == "-1, 2" or bml_versions == "-1, 1, 2":
            return "bml1_2"  # Use the same light green color for -1 + 2
        return ""
    
    def _color_name_to_tag(self, color_name):
        """Map version filter names to tag names."""
        color_map = {
            "Version 2": "bml2",
            "Versions -1/1 & 2": "bml1_2", 
            "Version -1": "bml_1",
            "Version -1 & 1": "bml_1_1"
        }
        return color_map.get(color_name, "")
    
    def filter_models(self, *args):
        # Update status
        self.status_label.configure(text="Filtering models...")
        self.update()
        
        # Get filter values
        type_filter = self.type_var.get()
        color_filter = self.color_var.get()
        search_text = self.search_entry.get().lower()
        
        # Filter models
        self.filtered_models = []
        for model in self.models:
            # Type filter
            if type_filter != "All" and model.type != type_filter:
                continue
            
            # Version filter
            if color_filter != "All BMLs":
                model_tag = self._get_model_color_tag(model)
                expected_tag = self._color_name_to_tag(color_filter)
                if model_tag != expected_tag:
                    continue
            
            # Search text filter
            if search_text and search_text not in model.name.lower() and search_text not in str(model.ct_number):
                continue
            
            self.filtered_models.append(model)
        
        # Sort if needed
        if self.current_sort:
            # Re-sort the filtered models using the current sort column
            if self.current_sort == "ct":
                self.filtered_models.sort(key=lambda x: x.ct_number, reverse=not self.sort_ascending)
            elif self.current_sort == "type":
                self.filtered_models.sort(key=lambda x: x.type, reverse=not self.sort_ascending)
            elif self.current_sort == "name":
                self.filtered_models.sort(key=lambda x: x.name.lower(), reverse=not self.sort_ascending)
        
        # Update display
        self._update_display()
        
        # Update status
        self.status_label.configure(text=f"Showing {len(self.filtered_models)} of {len(self.models)} models")
    
    def _update_display(self):
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Add models to tree
        for model in self.filtered_models:
            # Get color tag for this model
            tag = self._get_model_color_tag(model)
            
            # Insert item with appropriate tag
            self.tree.insert("", "end", values=(model.ct_number, model.type, model.name), tags=(tag,))
    
    def sort_table(self, column):
        # Update sort order
        if self.current_sort == column:
            self.sort_ascending = not self.sort_ascending
        else:
            self.current_sort = column
            self.sort_ascending = True
        
        # Sort models
        if column == "ct":
            self.filtered_models.sort(key=lambda x: x.ct_number, reverse=not self.sort_ascending)
        elif column == "type":
            self.filtered_models.sort(key=lambda x: x.type, reverse=not self.sort_ascending)
        elif column == "name":
            self.filtered_models.sort(key=lambda x: x.name.lower(), reverse=not self.sort_ascending)
        
        # Update display
        self._update_display()
        
        # Update column headers
        for col in ("ct", "type", "name"):
            self.tree.heading(col, text=f"{col.upper()}{' ▼' if col == column and self.sort_ascending else ' ▲' if col == column else ''}")
    
    def show_model_details(self, model: ModelData):
        # Update each field in the details frame
        for field, widget in self.detail_widgets.items():
            if isinstance(widget, ctk.CTkTextbox):
                widget.configure(state="normal")
                widget.delete("1.0", "end")
                
                textures = set()  # Use set to avoid duplicates
                
                # Check if any parent has BML Version 2
                bml_versions = self.master.master.data_manager.get_model_bml_versions(model)
                if "2" in bml_versions:
                    # Get all parent numbers for this model
                    parent_numbers = []
                    for parent in self.master.master.data_manager.parents.values():
                        if parent.ct_number == model.ct_number:
                            parent_numbers.append(parent.parent_number)
                    
                    # Get BML2 textures for each parent
                    for parent_number in parent_numbers:
                        bml2_textures = self.master.master.data_manager.get_bml2_textures(parent_number)
                        for tex in bml2_textures:
                            textures.add(tex["name"])
                else:
                    # Get regular textures
                    base_textures = self.master.master.data_manager.get_model_textures(model)
                    for texture_id in base_textures:
                        textures.add(texture_id)
                        # Get texture data to check for PBR variants
                        texture_data = self.master.master.data_manager.textures.get(texture_id)
                        if texture_data and texture_data.pbr:
                            # Add PBR variants
                            textures.update(texture_data.pbr)
                
                if textures:
                    widget.insert("1.0", ", ".join(sorted(textures, key=lambda x: (len(x), x))))
                widget.configure(state="disabled")
            else:
                if field == "Name":
                    widget.configure(state="normal")
                    widget.delete(0, "end")
                    widget.insert(0, model.name)
                    widget.configure(state="readonly")
                elif field == "Type":
                    widget.configure(state="normal")
                    widget.delete(0, "end")
                    widget.insert(0, model.type)
                    widget.configure(state="readonly")
                elif field == "CT Number":
                    widget.configure(state="normal")
                    widget.delete(0, "end")
                    widget.insert(0, str(model.ct_number))
                    widget.configure(state="readonly")
                elif field == "Entity Index":
                    widget.configure(state="normal")
                    widget.delete(0, "end")
                    widget.insert(0, str(model.type_number))
                    widget.configure(state="readonly")
                elif field == "Normal Model":
                    widget.configure(state="normal")
                    widget.delete(0, "end")
                    widget.insert(0, model.normal_model or "")
                    widget.configure(state="readonly")
                elif field == "Repaired Model":
                    widget.configure(state="normal")
                    widget.delete(0, "end")
                    widget.insert(0, model.fixed_model or "")
                    widget.configure(state="readonly")
                elif field == "Damaged Model":
                    widget.configure(state="normal")
                    widget.delete(0, "end")
                    widget.insert(0, model.damaged_model or "")
                    widget.configure(state="readonly")
                elif field == "Destroyed Model":
                    widget.configure(state="normal")
                    widget.delete(0, "end")
                    widget.insert(0, model.destroyed_model or "")
                    widget.configure(state="readonly")
                elif field == "Left Destroyed Model":
                    widget.configure(state="normal")
                    widget.delete(0, "end")
                    widget.insert(0, model.left_destroyed_model or "")
                    widget.configure(state="readonly")
                elif field == "Right Destroyed Model":
                    widget.configure(state="normal")
                    widget.delete(0, "end")
                    widget.insert(0, model.right_destroyed_model or "")
                    widget.configure(state="readonly")
                elif field == "Both Destroyed Model":
                    widget.configure(state="normal")
                    widget.delete(0, "end")
                    widget.insert(0, model.both_models_destroyed or "")
                    widget.configure(state="readonly")
                elif field == "BML Version":
                    widget.configure(state="normal")
                    widget.delete(0, "end")
                    # Get combined BML versions string
                    bml_versions = self.master.master.data_manager.get_model_bml_versions(model)
                    widget.insert(0, bml_versions)
                    widget.configure(state="readonly")

    def show_legend(self):
        # Store original color if not stored
        if self.legend_button_color is None:
            self.legend_button_color = self.legend_button.cget("fg_color")
        
        # Disable button and change color
        self.legend_button.configure(state="disabled", fg_color="gray")
        
        legend_items = [
            ("#2E7D32", "BML Version 2"),
            ("#81C784", "BML Version 1 and 2 or -1 and 2"),
            ("#1565C0", "BML Version -1"),
            ("#90CAF9", "BML Version -1 and 1")
        ]
        
        # Create legend window with callback
        LegendWindow(self, "3D Assets Color Legend", legend_items, 
                    on_close=lambda: self.legend_button.configure(
                        state="normal",
                        fg_color=self.legend_button_color
                    ))

class TexturesFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, corner_radius=0)
        
        # Set frame background color
        self.configure(fg_color="#E3F4FF")
        
        # Initialize legend button color
        self.legend_button_color = None
        
        # Get DPI scaling
        try:
            awareness = ctypes.c_int()
            ctypes.windll.shcore.GetProcessDpiAwareness(0, ctypes.byref(awareness))
            self.dpi = ctypes.windll.user32.GetDpiForWindow(self.winfo_id()) / 96.0
        except Exception:
            self.dpi = self.winfo_fpixels('1i') / 72.0  # Fallback method
        
        # Calculate scaled sizes
        self.base_font_size = int(12 * self.dpi)  # Base font size
        self.table_font_size = int(11 * self.dpi)  # Table content font size
        self.table_header_size = int(12 * self.dpi)  # Table header font size
        self.row_height = int(25 * self.dpi)  # Row height

        # Configure style for row height only
        style = ttk.Style()
        style.configure("Treeview", rowheight=self.row_height)
        
        # Configure grid layout - make both columns expandable with proper ratio
        self.grid_columnconfigure(0, weight=1)  # Left table gets 1 part
        self.grid_columnconfigure(1, weight=3)  # Right section gets 3 parts
        self.grid_rowconfigure(1, weight=1)     # Main content row
        
        # Search frame with new color
        self.search_frame = ctk.CTkFrame(self)
        self.search_frame.grid(row=0, column=0, columnspan=2, padx=20, pady=10, sticky="ew")
        self.search_frame.grid_columnconfigure(2, weight=1)  # Make search entry expandable
        self.search_frame.grid_columnconfigure(0, weight=0)  # Legend button fixed
        self.search_frame.grid_columnconfigure(1, weight=0)  # Color filter fixed
        self.search_frame.grid_columnconfigure(3, weight=0)  # Search button fixed
        self.search_frame.configure(fg_color="#D4E5F2")  # Lighter shade for search frame
        
        # Add legend button with new colors
        self.legend_button = ctk.CTkButton(
            self.search_frame,
            text="Legend",
            width=80,
            command=self.show_legend,
            fg_color="#7A92A9",
            hover_color="#6E8499",
            text_color="#FFFFFF"
        )
        self.legend_button.grid(row=0, column=0, padx=5, pady=5)
        
        # Color filter with new colors
        self.color_var = ctk.StringVar(value="All Types")
        self.color_menu = ctk.CTkOptionMenu(
            self.search_frame,
            variable=self.color_var,
            values=["All Types", "High & PBR", "PBR", "High", "No Texture"],
            command=self.search_textures,
            font=ctk.CTkFont(size=self.base_font_size),
            fg_color="#7A92A9",
            button_color="#6E8499",
            button_hover_color="#5D7388",
            text_color="#FFFFFF",
            dropdown_fg_color="#7A92A9",
            dropdown_hover_color="#6E8499",
            dropdown_text_color="#FFFFFF"
        )
        self.color_menu.grid(row=0, column=1, padx=5, pady=5)
        
        # Search entry with new colors
        self.search_entry = ctk.CTkEntry(
            self.search_frame,
            placeholder_text="Search textures...",
            font=ctk.CTkFont(size=self.base_font_size),
            fg_color="#FFFFFF",
            border_color="#7A92A9",
            text_color="#2D3B45"
        )
        self.search_entry.grid(row=0, column=2, padx=5, pady=5, sticky="ew")
        self.search_entry.bind("<Return>", self.search_textures)
        
        # Search button with new colors
        self.search_button = ctk.CTkButton(
            self.search_frame,
            text="Search",
            command=self.search_textures,
            font=ctk.CTkFont(size=self.base_font_size),
            fg_color="#7A92A9",
            hover_color="#6E8499",
            text_color="#FFFFFF"
        )
        self.search_button.grid(row=0, column=3, padx=5, pady=5)
        
        # Status label with new colors
        self.status_label = ctk.CTkLabel(
            self.search_frame,
            text="",
            font=ctk.CTkFont(size=self.base_font_size),
            text_color="#2D3B45"
        )
        self.status_label.grid(row=1, column=0, columnspan=4, padx=5, pady=(0, 5), sticky="ew")
        
        # Left side - Textures list frame with new color
        self.textures_frame = ctk.CTkFrame(self)
        self.textures_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        self.textures_frame.grid_columnconfigure(0, weight=1)
        self.textures_frame.grid_rowconfigure(0, weight=1)
        self.textures_frame.configure(fg_color="#B8CFE5")  # Slightly darker shade for frame
        
        # Create Treeview style
        style = ttk.Style()
        style.configure(
            "Treeview",
            rowheight=self.row_height,
            font=('Segoe UI', self.table_font_size),
            background="#FFFFFF",
            fieldbackground="#FFFFFF",
            foreground="#2D3B45"
        )
        style.configure(
            "Treeview.Heading",
            font=('Segoe UI', self.table_header_size, 'bold'),
            background="#B8CFE5",  # Lighter background for headers
            foreground="#2D3B45"   # Dark text for better visibility
        )
        style.map(
            "Treeview.Heading",
            background=[("pressed", "#A1B9D0"), ("active", "#A1B9D0")],  # Darker when pressed/hovered
            foreground=[("pressed", "#2D3B45"), ("active", "#2D3B45")]   # Keep text dark
        )
        
        # Create Treeview for textures list
        self.textures_tree = ttk.Treeview(
            self.textures_frame,
            columns=("texture",),
            show="headings",
            style="Treeview"
        )
        
        # Configure tags using the master's method
        self.master.master.configure_treeview_tags(self.textures_tree)
        
        # Configure tags for different states
        self.textures_tree.tag_configure("missing", background="#B71C1C", foreground="white")  # Red for missing
        self.textures_tree.tag_configure("pbr", background="#A5D6A7")  # Light green for PBR
        self.textures_tree.tag_configure("highres", background="#90CAF9")  # Light blue for high res
        self.textures_tree.tag_configure("both", background="#2E7D32", foreground="white")  # Dark green for both
        
        # Configure column with stretching
        self.textures_tree.heading("texture", text="Textures List", command=lambda: self.sort_textures("texture"))
        self.textures_tree.column("texture", width=int(150 * self.dpi), minwidth=int(100 * self.dpi), stretch=True)
        
        # Add scrollbars
        vsb = ttk.Scrollbar(self.textures_frame, orient="vertical", command=self.textures_tree.yview)
        hsb = ttk.Scrollbar(self.textures_frame, orient="horizontal", command=self.textures_tree.xview)
        self.textures_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # Grid layout for textures list
        self.textures_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        # Right side frame with new colors
        self.right_frame = ctk.CTkFrame(self)
        self.right_frame.grid(row=1, column=1, padx=20, pady=10, sticky="nsew")
        self.right_frame.grid_columnconfigure(0, weight=1)
        self.right_frame.configure(fg_color="#B8CFE5")  # Slightly darker shade for frame
        
        # Configure right frame row weights
        self.right_frame.grid_rowconfigure(0, weight=3)  # Details table gets 3 parts
        self.right_frame.grid_rowconfigure(1, weight=1)  # PBR table gets 1 part
        
        # Details table frame (top part)
        self.details_frame = ctk.CTkFrame(self.right_frame)
        self.details_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=(0, 5))
        self.details_frame.grid_columnconfigure(0, weight=1)
        self.details_frame.grid_rowconfigure(0, weight=1)
        self.details_frame.configure(fg_color="#D4E5F2")  # Lighter shade for inner frame
        
        # Create Treeview for details
        self.details_tree = ttk.Treeview(
            self.details_frame,
            columns=("parent", "model_name", "model_type", "type", "ct_number", "entity_idx", "times_used"),
            show="headings",
            style="Treeview"
        )
        
        # Configure columns with proportional widths
        self.details_tree.heading("parent", text="Parent Num", command=lambda: self.sort_details("parent"))
        self.details_tree.heading("model_name", text="Model Name", command=lambda: self.sort_details("model_name"))
        self.details_tree.heading("model_type", text="Model Type", command=lambda: self.sort_details("model_type"))
        self.details_tree.heading("type", text="Type", command=lambda: self.sort_details("type"))
        self.details_tree.heading("ct_number", text="CT Num", command=lambda: self.sort_details("ct_number"))
        self.details_tree.heading("entity_idx", text="Entity Idx", command=lambda: self.sort_details("entity_idx"))
        self.details_tree.heading("times_used", text="Times Used", command=lambda: self.sort_details("times_used"))
        
        # Set proportional column widths
        self.details_tree.column("parent", width=int(70 * self.dpi), minwidth=int(70 * self.dpi))
        self.details_tree.column("model_name", width=int(200 * self.dpi), minwidth=int(150 * self.dpi), stretch=True)
        self.details_tree.column("model_type", width=int(150 * self.dpi), minwidth=int(100 * self.dpi))
        self.details_tree.column("type", width=int(70 * self.dpi), minwidth=int(70 * self.dpi))
        self.details_tree.column("ct_number", width=int(70 * self.dpi), minwidth=int(70 * self.dpi))
        self.details_tree.column("entity_idx", width=int(60 * self.dpi), minwidth=int(60 * self.dpi))
        self.details_tree.column("times_used", width=int(80 * self.dpi), minwidth=int(80 * self.dpi))
        
        # Add scrollbars for details tree
        vsb_details = ttk.Scrollbar(self.details_frame, orient="vertical", command=self.details_tree.yview)
        hsb_details = ttk.Scrollbar(self.details_frame, orient="horizontal", command=self.details_tree.xview)
        self.details_tree.configure(yscrollcommand=vsb_details.set, xscrollcommand=hsb_details.set)
        
        # Grid layout for details table
        self.details_tree.grid(row=0, column=0, sticky="nsew")
        vsb_details.grid(row=0, column=1, sticky="ns")
        hsb_details.grid(row=1, column=0, sticky="ew")
        
        # PBR table frame (bottom part)
        self.pbr_frame = ctk.CTkFrame(self.right_frame)
        self.pbr_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=(5, 0))
        self.pbr_frame.grid_columnconfigure(0, weight=1)
        self.pbr_frame.grid_rowconfigure(0, weight=1)
        self.pbr_frame.configure(fg_color="#D4E5F2")  # Lighter shade for inner frame
        
        # Create PBR information table
        self.pbr_tree = ttk.Treeview(
            self.pbr_frame,
            columns=("texture_name", "texture_type", "texture_path"),
            show="headings",
            style="Treeview",
            height=4  # Fixed height of 4 rows
        )
        
        # Configure PBR columns
        self.pbr_tree.heading("texture_name", text="Texture Name")
        self.pbr_tree.heading("texture_type", text="Texture Type")
        self.pbr_tree.heading("texture_path", text="Texture Path")
        
        # Set column widths
        self.pbr_tree.column("texture_name", width=int(200 * self.dpi), minwidth=int(150 * self.dpi))
        self.pbr_tree.column("texture_type", width=int(150 * self.dpi), minwidth=int(100 * self.dpi))
        self.pbr_tree.column("texture_path", width=int(200 * self.dpi), minwidth=int(150 * self.dpi))
        
        # Add scrollbars for PBR tree
        vsb_pbr = ttk.Scrollbar(self.pbr_frame, orient="vertical", command=self.pbr_tree.yview)
        hsb_pbr = ttk.Scrollbar(self.pbr_frame, orient="horizontal", command=self.pbr_tree.xview)
        self.pbr_tree.configure(yscrollcommand=vsb_pbr.set, xscrollcommand=hsb_pbr.set)
        
        # Grid layout for PBR table
        self.pbr_tree.grid(row=0, column=0, sticky="nsew")
        vsb_pbr.grid(row=0, column=1, sticky="ns")
        hsb_pbr.grid(row=1, column=0, sticky="ew")
        
        # Bind selection event
        self.textures_tree.bind("<<TreeviewSelect>>", self._on_texture_select)
        
        # Store references
        self.textures = []
        self.filtered_textures = []
        self.current_sort = None
        self.sort_ascending = True
    
    def _get_texture_color_tag(self, texture_id):
        """Get the color tag for a texture based on its properties."""
        texture_data = self.master.master.data_manager.textures.get(str(texture_id))
        
        if not texture_data:
            return "missing"  # No texture data means missing texture
        
        if not texture_data.availability:
            return "missing"  # Red for missing textures
        elif texture_data.high_res and texture_data.pbr:
            return "both"  # Dark green for both high res and PBR
        elif texture_data.pbr:
            return "pbr"  # Light green for PBR only
        elif texture_data.high_res:
            return "highres"  # Light blue for high res only
        else:
            return ""  # Default case (no special properties)
    
    def _color_name_to_tag(self, color_name):
        """Map color filter names to tag names."""
        color_map = {
            "High & PBR": "both",
            "PBR": "pbr",
            "High": "highres",
            "No Texture": "missing"
        }
        return color_map.get(color_name, "")
    
    def update_list(self, textures: List[str] = None):
        """Update the textures list with new data."""
        if textures is None:
            textures = []
            self.status_label.configure(text="No texture data available - PDR file required")
            self.textures = []
            self.filtered_textures = []
            self._update_textures_display()
            return

        # Separate numeric and non-numeric textures for proper sorting
        numeric_textures = []
        non_numeric_textures = []
        
        for texture in textures:
            if str(texture).isdigit():
                numeric_textures.append(int(texture))
            else:
                non_numeric_textures.append(texture)
        
        # Sort both lists
        numeric_textures.sort()
        non_numeric_textures.sort()
        
        # Combine lists with numeric textures first
        self.textures = [str(t) for t in numeric_textures] + non_numeric_textures
        self.filtered_textures = self.textures.copy()
        
        self._update_textures_display()
        self.status_label.configure(text=f"Showing {len(self.filtered_textures)} of {len(self.textures)} textures")
    
    def _update_textures_display(self):
        # Clear existing items
        for item in self.textures_tree.get_children():
            self.textures_tree.delete(item)
        
        # Add textures to tree
        for texture in self.filtered_textures:
            # Get color tag for this texture
            tag = self._get_texture_color_tag(texture)
            
            # Insert item with appropriate tag
            self.textures_tree.insert("", "end", values=(str(texture),), tags=(tag,) if tag else ())
    
    def sort_textures(self, column):
        """Sort textures list."""
        if not self.textures:  # Don't sort if no data
            return
            
        if self.current_sort == column:
            self.sort_ascending = not self.sort_ascending
        else:
            self.current_sort = column
            self.sort_ascending = True
        
        # Separate numeric and non-numeric textures for proper sorting
        numeric_textures = []
        non_numeric_textures = []
        
        for texture in self.filtered_textures:
            if str(texture).isdigit():
                numeric_textures.append(int(texture))
            else:
                non_numeric_textures.append(texture)
        
        # Sort both lists
        numeric_textures.sort(reverse=not self.sort_ascending)
        non_numeric_textures.sort(reverse=not self.sort_ascending)
        
        # Combine lists with numeric textures first
        self.filtered_textures = [str(t) for t in numeric_textures] + non_numeric_textures
        
        self._update_textures_display()
        self.textures_tree.heading("texture", text=f"Textures List{' ▼' if self.sort_ascending else ' ▲'}")
    
    def search_textures(self, *args):
        """Search and filter textures by name and color type."""
        if not self.textures:  # Don't search if no data
            return
            
        search_text = self.search_entry.get().lower()
        color_filter = self.color_var.get()
        
        # Filter textures
        self.filtered_textures = []
        for texture in self.textures:
            # Check search text filter
            if search_text and search_text not in str(texture).lower():
                continue
            
            # Check color filter
            if color_filter != "All Types":
                texture_tag = self._get_texture_color_tag(texture)
                expected_tag = self._color_name_to_tag(color_filter)
                if texture_tag != expected_tag:
                    continue
            
            # If we get here, the texture passed all filters
            self.filtered_textures.append(texture)
        
        self._update_textures_display()
        self.status_label.configure(text=f"Showing {len(self.filtered_textures)} of {len(self.textures)} textures")
    
    def sort_details(self, column):
        # Get all items
        items = [(self.details_tree.set(item, column), item) for item in self.details_tree.get_children("")]
        
        # Convert to proper type for sorting
        if column in ["parent", "ct_number", "entity_idx"]:
            items = [(int(val) if val else 0, item) for val, item in items]
        elif column == "bms_version":
            items = [(int(val) if val else -1, item) for val, item in items]
        else:
            items = [(val.lower(), item) for val, item in items]
        
        # Sort items
        items.sort(reverse=not self.sort_ascending)
        
        # Update sort order
        if self.current_sort == column:
            self.sort_ascending = not self.sort_ascending
        else:
            self.current_sort = column
            self.sort_ascending = True
        
        # Reorder items
        for index, (_, item) in enumerate(items):
            self.details_tree.move(item, "", index)
        
        # Update column header
        self.details_tree.heading(
            column,
            text=f"{column.replace('_', ' ').title()}{' ▼' if self.sort_ascending else ' ▲'}"
        )
    
    def _on_texture_select(self, event):
        """Handle texture selection event."""
        selection = self.textures_tree.selection()
        if selection:
            texture_id = self.textures_tree.item(selection[0])['values'][0]
            self.show_texture_details(texture_id)
    
    def show_texture_details(self, texture_id: str):
        """Show details for selected texture."""
        # Clear existing items
        for item in self.details_tree.get_children():
            self.details_tree.delete(item)
        for item in self.pbr_tree.get_children():
            self.pbr_tree.delete(item)
        
        # Get texture data from data manager
        parent_models = self.master.master.data_manager.get_texture_data(str(texture_id))
        
        # Create a dictionary to track unique parent numbers and their texture usage count
        parent_usage = {}
        
        # Count texture usage for each parent
        for parent_model in parent_models:
            parent_num = parent_model.parent_number
            if parent_num not in parent_usage:
                parent_usage[parent_num] = {
                    'model': parent_model,
                    'count': parent_model.textures.count(str(texture_id))
                }
        
        # Add each unique parent model to the table with its usage count
        for parent_data in parent_usage.values():
            parent_model = parent_data['model']
            usage_count = parent_data['count']
            
            row_values = (
                str(parent_model.parent_number),
                parent_model.model_name,
                parent_model.model_type,
                parent_model.type,
                str(parent_model.ct_number),
                str(parent_model.entity_idx),
                str(usage_count)
            )
            self.details_tree.insert("", "end", values=row_values)
        
        # Process texture variants according to the search hierarchy
        base_path = self.master.master.data_manager.base_folder
        search_paths = [
            (os.path.join(base_path, "KoreaObj_HiRes"), True),  # True for high-res
            (os.path.join(base_path, "KoreaObj"), False)        # False for standard
        ]
        
        # Add base texture first
        base_found = False
        for search_dir, is_hires in search_paths:
            base_path = os.path.join(search_dir, f"{texture_id}.dds")
            if os.path.exists(base_path):
                base_found = True
                texture_type = "High Resolution Base" if is_hires else "Base Texture"
                # Convert path to be relative to main BMS folder
                folder_name = "KoreaObj_HiRes" if is_hires else "KoreaObj"
                display_path = self.master.master.data_manager.get_path_relative_to_bms_main(folder_name)
                self.pbr_tree.insert("", "end", values=(
                    texture_id,
                    texture_type,
                    display_path
                ))
                break
        
        if not base_found:
            # Add base texture entry even if not found
            # Convert path to be relative to main BMS folder
            display_path = self.master.master.data_manager.get_path_relative_to_bms_main("KoreaObj")
            self.pbr_tree.insert("", "end", values=(
                texture_id,
                "Base Texture",
                display_path
            ))
        
        # Process PBR variants
        variants = [
            ("_normal", "Normal"),
            ("_armw", "ARMW")
        ]
        
        # Track found variants to avoid duplicates
        found_variants = set()
        
        # Search for variants in each directory
        for search_dir, is_hires in search_paths:
            for suffix, variant_type in variants:
                variant_name = f"{texture_id}{suffix}"
                variant_path = os.path.join(search_dir, f"{variant_name}.dds")
                
                if os.path.exists(variant_path) and variant_name not in found_variants:
                    found_variants.add(variant_name)
                    texture_type = f"High Resolution {variant_type}" if is_hires else variant_type
                    # Convert path to be relative to main BMS folder
                    folder_name = "KoreaObj_HiRes" if is_hires else "KoreaObj"
                    display_path = self.master.master.data_manager.get_path_relative_to_bms_main(folder_name)
                    self.pbr_tree.insert("", "end", values=(
                        variant_name,
                        texture_type,
                        display_path
                    ))

    def show_legend(self):
        # Store original color if not stored
        if self.legend_button_color is None:
            self.legend_button_color = self.legend_button.cget("fg_color")
        
        # Disable button and change color
        self.legend_button.configure(state="disabled", fg_color="gray")
        
        legend_items = [
            ("#2E7D32", "Both PBR and High Resolution Available"),
            ("#A5D6A7", "PBR Textures Available"),
            ("#90CAF9", "High Resolution Available"),
            ("#B71C1C", "Missing Texture")
        ]
        
        # Create legend window with callback
        LegendWindow(self, "Textures Color Legend", legend_items,
                    on_close=lambda: self.legend_button.configure(
                        state="normal",
                        fg_color=self.legend_button_color
                    ))

    def set_texture_paths(self, base_path: str):
        """Set paths to KoreaObj folders."""
        # Set base folder first
        self.base_folder = os.path.dirname(base_path)
        # Set KoreaObj paths relative to base folder
        self.korea_obj_path = os.path.join(self.base_folder, "KoreaObj")
        self.korea_obj_hires_path = os.path.join(self.base_folder, "KoreaObj_HiRes")

class UnusedTexturesFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, corner_radius=0)
        
        # Set frame background color
        self.configure(fg_color="#E3F4FF")
        
        # Get DPI scaling
        try:
            awareness = ctypes.c_int()
            ctypes.windll.shcore.GetProcessDpiAwareness(0, ctypes.byref(awareness))
            dpi = ctypes.windll.user32.GetDpiForWindow(self.winfo_id()) / 96.0
        except Exception:
            dpi = self.winfo_fpixels('1i') / 72.0  # Fallback method
        
        # Calculate scaled sizes
        self.base_font_size = int(12 * dpi)  # Base font size
        self.table_font_size = int(11 * dpi)  # Table content font size
        self.table_header_size = int(12 * dpi)  # Table header font size
        self.row_height = int(25 * dpi)  # Row height

        # Configure style for row height only
        style = ttk.Style()
        style.configure("Treeview", rowheight=self.row_height)
        
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)  # Main content expands
        self.grid_rowconfigure(2, weight=0)  # Button frame doesn't expand
        
        # Header frame with new color
        self.header_frame = ctk.CTkFrame(self)
        self.header_frame.grid(row=0, column=0, padx=20, pady=(10,0), sticky="ew")
        self.header_frame.grid_columnconfigure(1, weight=1)  # Make legend frame expand
        self.header_frame.configure(fg_color="#D4E5F2")  # Lighter shade for header
        
        # Status label with new colors
        self.status_label = ctk.CTkLabel(
            self.header_frame,
            text="",
            font=ctk.CTkFont(size=self.base_font_size),
            text_color="#2D3B45"
        )
        self.status_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        # Create legend frame in header with border and new colors
        self.legend_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.legend_frame.grid(row=0, column=1, padx=10, pady=10, sticky="e")
        
        # Add legend items
        legend_items = [
            ("#B71C1C", "Missing Texture")
        ]
        
        for i, (color, text) in enumerate(legend_items):
            # Create color box with rounded corners
            color_box = ctk.CTkFrame(
                self.legend_frame,
                width=20,
                height=20,
                fg_color=color,
                corner_radius=5
            )
            color_box.grid(row=0, column=i*2, padx=(10, 5), pady=5)
            color_box.grid_propagate(False)  # Keep fixed size
            
            # Add text label with new colors
            label = ctk.CTkLabel(
                self.legend_frame,
                text=text,
                font=ctk.CTkFont(size=12),
                text_color="#2D3B45"
            )
            label.grid(row=0, column=i*2+1, padx=(0, 10), pady=5)
        
        # Table frame with new color
        self.table_frame = ctk.CTkFrame(self)
        self.table_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        self.table_frame.grid_columnconfigure(0, weight=1)
        self.table_frame.grid_rowconfigure(0, weight=1)
        self.table_frame.configure(fg_color="#B8CFE5")  # Slightly darker shade for frame
        
        # Create and configure Treeview style
        style = ttk.Style()
        style.configure(
            "Treeview",
            rowheight=self.row_height,
            font=('Segoe UI', self.table_font_size),
            background="#FFFFFF",
            fieldbackground="#FFFFFF",
            foreground="#2D3B45"
        )
        style.configure(
            "Treeview.Heading",
            font=('Segoe UI', self.table_header_size, 'bold'),
            background="#B8CFE5",  # Lighter background for headers
            foreground="#2D3B45"   # Dark text for better visibility
        )
        style.map(
            "Treeview.Heading",
            background=[("pressed", "#A1B9D0"), ("active", "#A1B9D0")],  # Darker when pressed/hovered
            foreground=[("pressed", "#2D3B45"), ("active", "#2D3B45")]   # Keep text dark
        )
        
        # Create Treeview for unused textures
        self.tree = ttk.Treeview(
            self.table_frame,
            columns=("texture_id", "armw", "normal", "highres", "highres_pbr"),
            show="headings",
            style="Treeview"
        )
        
        # Configure tags using the master's method
        self.master.master.configure_treeview_tags(self.tree)
        
        # Configure missing texture tag
        self.tree.tag_configure("missing", background="#B71C1C", foreground="white")
        
        # Configure columns
        self.tree.heading("texture_id", text="Texture ID", command=lambda: self.sort_column("texture_id"))
        self.tree.heading("armw", text="ARMW", command=lambda: self.sort_column("armw"))
        self.tree.heading("normal", text="Normal", command=lambda: self.sort_column("normal"))
        self.tree.heading("highres", text="HighRes", command=lambda: self.sort_column("highres"))
        self.tree.heading("highres_pbr", text="HighRes PBR", command=lambda: self.sort_column("highres_pbr"))
        
        # Set column widths
        self.tree.column("texture_id", width=int(100 * dpi), minwidth=int(80 * dpi))
        self.tree.column("armw", width=int(200 * dpi), minwidth=int(150 * dpi))
        self.tree.column("normal", width=int(200 * dpi), minwidth=int(150 * dpi))
        self.tree.column("highres", width=int(100 * dpi), minwidth=int(80 * dpi), anchor="center")
        self.tree.column("highres_pbr", width=int(100 * dpi), minwidth=int(80 * dpi), anchor="center")
        
        # Add scrollbars
        vsb = ttk.Scrollbar(self.table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(self.table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # Grid layout for table and scrollbars
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        # Bind selection event for texture removal
        self.tree.bind("<<TreeviewSelect>>", self._on_texture_select)
        
        # Store references
        self.textures = []
        self.current_sort = None
        self.sort_ascending = True
        
        # Button frame for deletion controls - positioned at bottom
        self.button_frame = ctk.CTkFrame(self)
        self.button_frame.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="ew")
        self.button_frame.grid_columnconfigure(0, weight=1)
        self.button_frame.grid_columnconfigure(1, weight=1)
        self.button_frame.configure(fg_color="#B8CFE5")  # Same shade as table frame
        
        # Remove Single Unused Texture button (red) - initially disabled
        self.remove_single_button = ctk.CTkButton(
            self.button_frame,
            text="Remove Single Unused Texture",
            command=self.remove_single_texture,
            fg_color="#B71C1C",  # Red color
            hover_color="#8E0000",  # Darker red for hover
            text_color="#FFFFFF",
            font=ctk.CTkFont(size=self.base_font_size, weight="bold"),
            height=int(40 * dpi),
            state="disabled"  # Initially disabled until a texture is selected
        )
        self.remove_single_button.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        
        # Remove All Unused Textures button (red)
        self.remove_all_button = ctk.CTkButton(
            self.button_frame,
            text="Remove All Unused Textures",
            command=self.remove_all_textures,
            fg_color="#B71C1C",  # Red color
            hover_color="#8E0000",  # Darker red for hover
            text_color="#FFFFFF",
            font=ctk.CTkFont(size=self.base_font_size, weight="bold"),
            height=int(40 * dpi)
        )
        self.remove_all_button.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
    
    def update_list(self, textures: List[int]) -> None:
        """Update the unused textures list with new data."""
        # Convert to set to remove duplicates, then sort
        unique_textures = sorted(list(set(textures)))
        self.textures = unique_textures
        
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Add textures to table
        for texture_id in self.textures:
            texture_data = self.master.master.data_manager.get_unused_texture_data(str(texture_id))
            
            if texture_data:
                # Get texture information
                exists = texture_data["exists"]
                tex_data = texture_data["texture_data"]
                
                # Find ARMW and Normal files
                armw_file = next((pbr for pbr, type_ in zip(tex_data.pbr, tex_data.pbr_type) if type_ == "armw"), "")
                normal_file = next((pbr for pbr, type_ in zip(tex_data.pbr, tex_data.pbr_type) if type_ == "normal"), "")
                
                # Insert with appropriate tag if texture doesn't exist
                values = (
                    str(texture_id),
                    armw_file,
                    normal_file,
                    "Yes" if tex_data.high_res else "No",
                    "Yes" if tex_data.pbr else "No"
                )
                
                # Apply missing tag if texture doesn't exist
                tags = ("missing",) if not exists else ()
                
                self.tree.insert("", "end", values=values, tags=tags)
        
        # Update status with both total counts
        total_with_duplicates = len(textures)
        total_unique = len(self.textures)
        if total_with_duplicates != total_unique:
            self.status_label.configure(text=f"Total: {total_unique} unique unused textures (removed {total_with_duplicates - total_unique} duplicates)")
        else:
            self.status_label.configure(text=f"Total: {total_unique} unused textures")
    
    def sort_column(self, column):
        """Sort table by column."""
        items = [(self.tree.set(item, column), item) for item in self.tree.get_children("")]
        
        # Convert to proper type for sorting
        if column == "texture_id":
            items = [(int(val) if val.isdigit() else val, item) for val, item in items]
        else:
            items = [(val.lower(), item) for val, item in items]
        
        # Update sort order
        if self.current_sort == column:
            self.sort_ascending = not self.sort_ascending
            items.reverse()
        else:
            self.current_sort = column
            self.sort_ascending = True
        
        # Rearrange items
        for idx, (_, item) in enumerate(items):
            self.tree.move(item, "", idx)
        
        # Update column header
        self.tree.heading(
            column,
            text=f"{column.replace('_', ' ').title()}{' ▼' if self.sort_ascending else ' ▲'}"
        )
    
    def remove_single_texture(self):
        """Remove a single selected unused texture."""
        # Get selected texture
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a texture to remove.")
            return
        
        # Get texture ID from selection
        item = self.tree.item(selection[0])
        texture_id = item['values'][0]
        
        # Confirmation dialog
        result = messagebox.askyesno(
            "Confirm Deletion",
            f"Are you sure you want to delete texture {texture_id} and all its associated files?\n\n"
            "This action cannot be undone and will permanently remove:\n"
            "• Base texture file (.dds)\n"
            "• ARMW texture file (if exists)\n"
            "• Normal texture file (if exists)\n"
            "• High-resolution versions (if exist)\n\n"
            "Continue with deletion?",
            icon="warning"
        )
        
        if result:
            deleted_files = self._delete_texture_files(texture_id)
            if deleted_files:
                # Format as dictionary for logging
                deleted_files_dict = {texture_id: deleted_files}
                self._log_deleted_files([int(texture_id)], deleted_files_dict)
                # Remove from list and refresh display
                if int(texture_id) in self.textures:
                    self.textures.remove(int(texture_id))
                self.update_list(self.textures)
                messagebox.showinfo("Success", f"Texture {texture_id} has been deleted successfully.")
            else:
                messagebox.showwarning("No Files Found", f"No files were found for texture {texture_id}.")

    def remove_all_textures(self):
        """Remove all unused textures."""
        if not self.textures:
            messagebox.showwarning("No Textures", "No unused textures to remove.")
            return
        
        # Confirmation dialog
        result = messagebox.askyesno(
            "Confirm Mass Deletion",
            f"Are you sure you want to delete ALL {len(self.textures)} unused textures?\n\n"
            "This action cannot be undone and will permanently remove all texture files including:\n"
            "• Base texture files (.dds)\n"
            "• ARMW texture files (if exist)\n"
            "• Normal texture files (if exist)\n"
            "• High-resolution versions (if exist)\n\n"
            "This is a destructive operation that cannot be reversed.\n"
            "Continue with mass deletion?",
            icon="warning"
        )
        
        if result:
            all_deleted_files = {}
            deleted_texture_ids = []
            
            for texture_id in self.textures[:]:  # Use slice to avoid modification during iteration
                deleted_files = self._delete_texture_files(str(texture_id))
                if deleted_files:
                    all_deleted_files[str(texture_id)] = deleted_files
                    deleted_texture_ids.append(texture_id)
            
            if all_deleted_files:
                self._log_deleted_files(deleted_texture_ids, all_deleted_files)
                # Clear the list and refresh display
                self.textures.clear()
                self.update_list([])
                messagebox.showinfo("Success", f"Successfully deleted {len(deleted_texture_ids)} textures and their associated files.")
            else:
                messagebox.showwarning("No Files Found", "No texture files were found to delete.")

    def _delete_texture_files(self, texture_id: str) -> List[str]:
        """Delete all files associated with a texture ID and return list of deleted files."""
        deleted_files = []
        
        # Get data manager for paths
        data_manager = self.master.master.data_manager
        
        if not data_manager.korea_obj_path or not data_manager.korea_obj_hires_path:
            logger.error("Texture paths not set in data manager")
            return deleted_files
        
        # Define all possible file patterns to check
        file_patterns = [
            # Standard KoreaObj files
            (os.path.join(data_manager.korea_obj_path, f"{texture_id}.dds"), "Base texture"),
            (os.path.join(data_manager.korea_obj_path, f"{texture_id}_armw.dds"), "ARMW texture"),
            (os.path.join(data_manager.korea_obj_path, f"{texture_id}_normal.dds"), "Normal texture"),
            # High-resolution KoreaObj_HiRes files
            (os.path.join(data_manager.korea_obj_hires_path, f"{texture_id}.dds"), "High-res base texture"),
            (os.path.join(data_manager.korea_obj_hires_path, f"{texture_id}_armw.dds"), "High-res ARMW texture"),
            (os.path.join(data_manager.korea_obj_hires_path, f"{texture_id}_normal.dds"), "High-res Normal texture"),
        ]
        
        # Try to delete each file
        for file_path, file_type in file_patterns:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    deleted_files.append(f"{file_type}: {file_path}")
                    logger.info(f"Deleted {file_type} file: {file_path}")
                except OSError as e:
                    logger.error(f"Failed to delete {file_type} file {file_path}: {str(e)}")
                    # Continue with other files even if one fails
        
        return deleted_files

    def _log_deleted_files(self, texture_ids: List[int], deleted_files_dict: dict):
        """Create a detailed log of deleted texture files."""
        # Create logs directory if it doesn't exist
        os.makedirs("logs", exist_ok=True)
        
        # Generate log filename with timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"logs/deleted_textures_{timestamp}.log"
        
        try:
            with open(log_filename, 'w', encoding='utf-8') as log_file:
                log_file.write("=" * 80 + "\n")
                log_file.write("DELETED UNUSED TEXTURES LOG\n")
                log_file.write("=" * 80 + "\n")
                log_file.write(f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                log_file.write(f"Total textures processed: {len(texture_ids)}\n")
                log_file.write(f"Total files deleted: {sum(len(files) for files in deleted_files_dict.values())}\n")
                log_file.write("\n")
                
                # Log each texture and its deleted files
                for texture_id in texture_ids:
                    texture_id_str = str(texture_id)
                    if texture_id_str in deleted_files_dict:
                        files = deleted_files_dict[texture_id_str]
                        log_file.write(f"TEXTURE ID: {texture_id}\n")
                        log_file.write("-" * 40 + "\n")
                        
                        if files:
                            for file_info in files:
                                log_file.write(f"  ✓ {file_info}\n")
                        else:
                            log_file.write("  ⚠ No files found for this texture\n")
                        
                        log_file.write("\n")
                
                log_file.write("=" * 80 + "\n")
                log_file.write("END OF LOG\n")
                log_file.write("=" * 80 + "\n")
            
            logger.info(f"Deletion log created: {log_filename}")
            
        except Exception as e:
            logger.error(f"Failed to create deletion log: {str(e)}")
            # Show error to user but don't fail the deletion process
            messagebox.showwarning("Log Error", f"Failed to create deletion log: {str(e)}")

    def _delete_all_textures(self) -> None:
        """Legacy method - redirects to remove_all_textures for compatibility."""
        self.remove_all_textures()

    def _on_texture_select(self, event):
        """Handle texture selection event."""
        selection = self.tree.selection()
        if selection:
            # Enable single texture removal button when a texture is selected
            self.remove_single_button.configure(state="normal")
        else:
            # Disable single texture removal button when no texture is selected
            self.remove_single_button.configure(state="disabled")

    def show_legend(self):
        legend_items = [
            ("#B71C1C", "Missing Texture")
        ]
        LegendWindow(self, "Unused Textures Color Legend", legend_items)

class ParentsFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, corner_radius=0)
        
        # Set frame background color
        self.configure(fg_color="#E3F4FF")
        
        # Initialize legend button color
        self.legend_button_color = None
        
        # Get DPI scaling
        try:
            awareness = ctypes.c_int()
            ctypes.windll.shcore.GetProcessDpiAwareness(0, ctypes.byref(awareness))
            dpi = ctypes.windll.user32.GetDpiForWindow(self.winfo_id()) / 96.0
        except Exception:
            dpi = self.winfo_fpixels('1i') / 72.0  # Fallback method
        
        # Calculate scaled sizes
        self.base_font_size = int(12 * dpi)  # Base font size
        self.table_font_size = int(11 * dpi)  # Table content font size
        self.table_header_size = int(12 * dpi)  # Table header font size
        self.row_height = int(25 * dpi)  # Row height

        # Configure style for row height only
        style = ttk.Style()
        style.configure("Treeview", rowheight=self.row_height)
        
        # Configure grid layout - make both columns expandable with proper ratio
        self.grid_columnconfigure(0, weight=1)  # Left table gets 1 part
        self.grid_columnconfigure(1, weight=3)  # Right section gets 3 parts
        self.grid_rowconfigure(1, weight=1)     # Main content row
        
        # Search frame with new color
        self.search_frame = ctk.CTkFrame(self)
        self.search_frame.grid(row=0, column=0, columnspan=2, padx=20, pady=10, sticky="ew")
        self.search_frame.grid_columnconfigure(3, weight=1)  # Make search entry expandable
        self.search_frame.grid_columnconfigure(0, weight=0)  # Legend button fixed
        self.search_frame.grid_columnconfigure(1, weight=0)  # Color filter fixed
        self.search_frame.grid_columnconfigure(2, weight=0)  # Type filter fixed
        self.search_frame.grid_columnconfigure(4, weight=0)  # Search button fixed
        self.search_frame.configure(fg_color="#D4E5F2")  # Lighter shade for search frame
        
        # Add legend button with new colors
        self.legend_button = ctk.CTkButton(
            self.search_frame,
            text="Legend",
            width=80,
            command=self.show_legend,
            fg_color="#7A92A9",
            hover_color="#6E8499",
            text_color="#FFFFFF"
        )
        self.legend_button.grid(row=0, column=0, padx=5, pady=5)
        
        # Add color filter with new colors
        self.color_var = ctk.StringVar(value="All Colors")
        self.color_menu = ctk.CTkOptionMenu(
            self.search_frame,
            variable=self.color_var,
            values=["All Colors", "PBR", "Semi-PBR", "Outsourced", "No Texture"],
            command=self.filter_parents,
            font=ctk.CTkFont(size=self.base_font_size),
            fg_color="#7A92A9",
            button_color="#6E8499",
            button_hover_color="#5D7388",
            text_color="#FFFFFF",
            dropdown_fg_color="#7A92A9",
            dropdown_hover_color="#6E8499",
            dropdown_text_color="#FFFFFF"
        )
        self.color_menu.grid(row=0, column=1, padx=5, pady=5)
        
        # Add type filter with new colors
        self.type_var = ctk.StringVar(value="All")
        self.type_menu = ctk.CTkOptionMenu(
            self.search_frame,
            variable=self.type_var,
            values=["All", "Feature", "Vehicle", "Weapon", "Cockpit"],
            command=self.filter_parents,
            font=ctk.CTkFont(size=self.base_font_size),
            fg_color="#7A92A9",
            button_color="#6E8499",
            button_hover_color="#5D7388",
            text_color="#FFFFFF",
            dropdown_fg_color="#7A92A9",
            dropdown_hover_color="#6E8499",
            dropdown_text_color="#FFFFFF"
        )
        self.type_menu.grid(row=0, column=2, padx=5, pady=5)
        
        # Search entry with new colors
        self.search_entry = ctk.CTkEntry(
            self.search_frame,
            placeholder_text="Search parents...",
            font=ctk.CTkFont(size=self.base_font_size),
            fg_color="#FFFFFF",
            border_color="#7A92A9",
            text_color="#2D3B45"
        )
        self.search_entry.grid(row=0, column=3, padx=5, pady=5, sticky="ew")
        self.search_entry.bind("<Return>", self.search_parents)
        
        # Search button with new colors
        self.search_button = ctk.CTkButton(
            self.search_frame,
            text="Search",
            command=self.search_parents,
            font=ctk.CTkFont(size=self.base_font_size),
            fg_color="#7A92A9",
            hover_color="#6E8499",
            text_color="#FFFFFF"
        )
        self.search_button.grid(row=0, column=4, padx=5, pady=5)
        
        # Status label with new colors
        self.status_label = ctk.CTkLabel(
            self.search_frame,
            text="",
            font=ctk.CTkFont(size=self.base_font_size),
            text_color="#2D3B45"
        )
        self.status_label.grid(row=1, column=0, columnspan=5, padx=5, pady=(0, 5), sticky="ew")
        
        # Left side - Parents list frame with new color
        self.parents_frame = ctk.CTkFrame(self)
        self.parents_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        self.parents_frame.grid_columnconfigure(0, weight=1)
        self.parents_frame.grid_rowconfigure(0, weight=1)
        self.parents_frame.configure(fg_color="#B8CFE5")  # Slightly darker shade for frame
        
        # Create Treeview style
        style = ttk.Style()
        style.configure(
            "Treeview",
            rowheight=self.row_height,
            font=('Segoe UI', self.table_font_size),
            background="#FFFFFF",
            fieldbackground="#FFFFFF",
            foreground="#2D3B45"
        )
        style.configure(
            "Treeview.Heading",
            font=('Segoe UI', self.table_header_size, 'bold'),
            background="#B8CFE5",  # Lighter background for headers
            foreground="#2D3B45"   # Dark text for better visibility
        )
        style.map(
            "Treeview.Heading",
            background=[("pressed", "#A1B9D0"), ("active", "#A1B9D0")],  # Darker when pressed/hovered
            foreground=[("pressed", "#2D3B45"), ("active", "#2D3B45")]   # Keep text dark
        )
        
        # Create Treeview for parents list
        self.parents_tree = ttk.Treeview(
            self.parents_frame,
            columns=("parent",),
            show="headings",
            style="Treeview"
        )
        
        # Configure tags using the master's method
        self.master.master.configure_treeview_tags(self.parents_tree)
        
        # Configure BML version and PBR tags
        self.parents_tree.tag_configure("bml2", background="#2E7D32", foreground="white")  # Dark green
        self.parents_tree.tag_configure("bml1_pbr", background="#81C784")  # Light green
        self.parents_tree.tag_configure("bml_1", background="#1565C0", foreground="white")  # Dark blue
        self.parents_tree.tag_configure("missing", background="#B71C1C", foreground="white")  # Red for missing/no texture
        
        # Configure column with stretching
        self.parents_tree.heading("parent", text="Parents List", command=lambda: self.sort_parents("parent"))
        self.parents_tree.column("parent", width=int(150 * dpi), minwidth=int(100 * dpi), stretch=True)
        
        # Add scrollbars
        vsb = ttk.Scrollbar(self.parents_frame, orient="vertical", command=self.parents_tree.yview)
        hsb = ttk.Scrollbar(self.parents_frame, orient="horizontal", command=self.parents_tree.xview)
        self.parents_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # Grid layout for parents list
        self.parents_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        # Right side frame with new colors
        self.right_frame = ctk.CTkFrame(self)
        self.right_frame.grid(row=1, column=1, padx=20, pady=10, sticky="nsew")
        self.right_frame.grid_columnconfigure(0, weight=1)
        self.right_frame.configure(fg_color="#B8CFE5")  # Slightly darker shade for frame
        
        # Configure right frame row weights
        self.right_frame.grid_rowconfigure(0, weight=3)  # Details table gets 3 parts
        self.right_frame.grid_rowconfigure(1, weight=1)  # PBR table gets 1 part
        
        # Parent Information Table Frame (top part)
        self.info_frame = ctk.CTkFrame(self.right_frame)
        self.info_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=(0, 5))
        self.info_frame.grid_columnconfigure(0, weight=1)
        self.info_frame.grid_rowconfigure(0, weight=1)
        self.info_frame.configure(fg_color="#D4E5F2")  # Lighter shade for inner frame
        
        # Create Treeview for parent information
        self.info_tree = ttk.Treeview(
            self.info_frame,
            columns=("bms_version", "model_name", "model_type", "type", "ct_number", "entity_idx"),
            show="headings",
            style="Treeview"
        )
        
        # Configure columns
        self.info_tree.heading("bms_version", text="BMS Ver", command=lambda: self.sort_info("bms_version"))
        self.info_tree.heading("model_name", text="Model Name", command=lambda: self.sort_info("model_name"))
        self.info_tree.heading("model_type", text="Model Type", command=lambda: self.sort_info("model_type"))
        self.info_tree.heading("type", text="Type", command=lambda: self.sort_info("type"))
        self.info_tree.heading("ct_number", text="CT Num", command=lambda: self.sort_info("ct_number"))
        self.info_tree.heading("entity_idx", text="Entity Idx", command=lambda: self.sort_info("entity_idx"))
        
        # Set column widths
        self.info_tree.column("bms_version", width=int(60 * dpi), minwidth=int(60 * dpi))
        self.info_tree.column("model_name", width=int(200 * dpi), minwidth=int(150 * dpi), stretch=True)
        self.info_tree.column("model_type", width=int(150 * dpi), minwidth=int(100 * dpi))
        self.info_tree.column("type", width=int(70 * dpi), minwidth=int(70 * dpi))
        self.info_tree.column("ct_number", width=int(70 * dpi), minwidth=int(70 * dpi))
        self.info_tree.column("entity_idx", width=int(60 * dpi), minwidth=int(60 * dpi))
        
        # Add scrollbars for info tree
        vsb_info = ttk.Scrollbar(self.info_frame, orient="vertical", command=self.info_tree.yview)
        hsb_info = ttk.Scrollbar(self.info_frame, orient="horizontal", command=self.info_tree.xview)
        self.info_tree.configure(yscrollcommand=vsb_info.set, xscrollcommand=hsb_info.set)
        
        # Grid layout for info table
        self.info_tree.grid(row=0, column=0, sticky="nsew")
        vsb_info.grid(row=0, column=1, sticky="ns")
        hsb_info.grid(row=1, column=0, sticky="ew")
        
        # Textures Information Table Frame (bottom part)
        self.texture_frame = ctk.CTkFrame(self.right_frame)
        self.texture_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=(5, 0))
        self.texture_frame.grid_columnconfigure(0, weight=1)
        self.texture_frame.grid_rowconfigure(0, weight=1)
        self.texture_frame.configure(fg_color="#D4E5F2")  # Lighter shade for inner frame
        
        # Create Treeview for texture information
        self.texture_tree = ttk.Treeview(
            self.texture_frame,
            columns=("texture_name", "texture_type", "texture_path"),
            show="headings",
            style="Treeview"
        )
        
        # Configure columns
        self.texture_tree.heading("texture_name", text="Texture Name")
        self.texture_tree.heading("texture_type", text="Texture Type")
        self.texture_tree.heading("texture_path", text="Texture Path")
        
        # Set column widths
        self.texture_tree.column("texture_name", width=int(200 * dpi), minwidth=int(150 * dpi))
        self.texture_tree.column("texture_type", width=int(150 * dpi), minwidth=int(100 * dpi))
        self.texture_tree.column("texture_path", width=int(200 * dpi), minwidth=int(150 * dpi))
        
        # Configure missing texture tag
        self.texture_tree.tag_configure("missing", background="#B71C1C", foreground="white")  # Red for missing textures
        
        # Add scrollbars for texture tree
        vsb_texture = ttk.Scrollbar(self.texture_frame, orient="vertical", command=self.texture_tree.yview)
        hsb_texture = ttk.Scrollbar(self.texture_frame, orient="horizontal", command=self.texture_tree.xview)
        self.texture_tree.configure(yscrollcommand=vsb_texture.set, xscrollcommand=hsb_texture.set)
        
        # Grid layout for texture table
        self.texture_tree.grid(row=0, column=0, sticky="nsew")
        vsb_texture.grid(row=0, column=1, sticky="ns")
        hsb_texture.grid(row=1, column=0, sticky="ew")
        
        # Bind selection event
        self.parents_tree.bind("<<TreeviewSelect>>", self._on_parent_select)
        
        # Store references
        self.parents = []
        self.filtered_parents = []
        self.current_sort = None
        self.sort_ascending = True
    
    def _get_parent_color_tag(self, parent_data):
        """Get the color tag for a parent based on its properties."""
        if not parent_data:
            return "missing"  # No parent data means missing/no texture
        
        # Check if ParentDetailsReport file is loaded
        pdr_loaded = bool(self.master.master.data_manager.pdr_file)
        
        if parent_data.bml_version == 2:
            return "bml2"  # PBR (Dark Green)
        elif parent_data.bml_version == 1 and pdr_loaded and any(texture_id in self.master.master.data_manager.textures and self.master.master.data_manager.textures[texture_id].pbr for texture_id in parent_data.textures if parent_data.textures):
            return "bml1_pbr"  # Semi-PBR (Light Green)
        elif parent_data.bml_version == 1 and not pdr_loaded:
            return ""  # Default case when PDR not loaded - don't assume missing textures
        elif parent_data.bml_version == -1:
            return "bml_1"  # Outsourced (Blue)
        elif pdr_loaded and (not parent_data.textures or len(parent_data.textures) == 0):
            return "missing"  # No Texture (Red) - only when PDR is loaded
        else:
            return ""  # Default case
    
    def _color_name_to_tag(self, color_name):
        """Map color filter names to tag names."""
        color_map = {
            "PBR": "bml2",
            "Semi-PBR": "bml1_pbr",
            "Outsourced": "bml_1",
            "No Texture": "missing"
        }
        return color_map.get(color_name, "")
    
    def update_list(self, parents: List[int]):
        """Update the parents list with new data."""
        self.parents = sorted(parents)
        self.filtered_parents = self.parents.copy()
        self._update_parents_display()
        self.status_label.configure(text=f"Showing {len(self.filtered_parents)} of {len(self.parents)} parents")
    
    def _update_parents_display(self):
        """Update the parents list display."""
        for item in self.parents_tree.get_children():
            self.parents_tree.delete(item)
        
        for parent in self.filtered_parents:
            # Skip -1 parent numbers as they are generic/empty values
            if parent == -1:
                continue
                
            # Get parent data
            parent_data = self.master.master.data_manager.parents.get(parent)
            
            # Get color tag for this parent
            tag = self._get_parent_color_tag(parent_data)
            
            # Insert item with appropriate tag
            self.parents_tree.insert("", "end", values=(str(parent),), tags=(tag,) if tag else ())
    
    def filter_parents(self, *args):
        """Filter parents based on type, color, and search text."""
        type_filter = self.type_var.get()
        color_filter = self.color_var.get()
        search_text = self.search_entry.get().lower()
        
        # Clear filtered parents list
        self.filtered_parents = []
        
        # Count for status
        total_parents = 0
        filtered_count = 0
        
        for parent in self.parents:
            total_parents += 1
            
            # Get parent data
            parent_data = self.master.master.data_manager.parents.get(parent)
            
            # Check type filter
            passes_type = False
            if type_filter == "All":
                passes_type = True
            elif type_filter == "Cockpit":
                passes_type = parent_data and parent_data.type == "Cockpit"
            else:
                passes_type = parent_data and parent_data.type == type_filter and parent_data.type != "Cockpit"
            
            if not passes_type:
                continue
            
            # Check color filter
            if color_filter != "All Colors":
                parent_tag = self._get_parent_color_tag(parent_data)
                expected_tag = self._color_name_to_tag(color_filter)
                if parent_tag != expected_tag:
                    continue
            
            # Check search filter
            if search_text:
                parent_name = parent_data.model_name if parent_data else ""
                if str(parent).lower().find(search_text) == -1 and parent_name.lower().find(search_text) == -1:
                    continue
            
            # If we get here, the parent passed all filters
            self.filtered_parents.append(parent)
            filtered_count += 1
        
        # Update display
        self._update_parents_display()
        
        # Update status label with counts
        if type_filter != "All":
            type_count = sum(1 for p in self.parents if self.master.master.data_manager.parents.get(p) and 
                           self.master.master.data_manager.parents.get(p).type == type_filter)
            self.status_label.configure(text=f"Showing {filtered_count} of {type_count} {type_filter} parents")
        else:
            self.status_label.configure(text=f"Showing {filtered_count} of {total_parents} parents")
    
    def search_parents(self, *args):
        """Search parents based on input text."""
        self.filter_parents()
    
    def sort_parents(self, column):
        """Sort parents list."""
        if self.current_sort == column:
            self.sort_ascending = not self.sort_ascending
        else:
            self.current_sort = column
            self.sort_ascending = True
        
        self.filtered_parents.sort(reverse=not self.sort_ascending)
        self._update_parents_display()
        self.parents_tree.heading("parent", text=f"Parents List{' ▼' if self.sort_ascending else ' ▲'}")
    
    def sort_info(self, column):
        """Sort parent information table."""
        items = [(self.info_tree.set(item, column), item) for item in self.info_tree.get_children("")]
        
        if column in ["ct_number", "entity_idx"]:
            items = [(int(val) if val else 0, item) for val, item in items]
        elif column == "bms_version":
            items = [(int(val) if val else -1, item) for val, item in items]
        else:
            items = [(val.lower(), item) for val, item in items]
        
        items.sort(reverse=not self.sort_ascending)
        
        if self.current_sort == column:
            self.sort_ascending = not self.sort_ascending
        else:
            self.current_sort = column
            self.sort_ascending = True
        
        for index, (_, item) in enumerate(items):
            self.info_tree.move(item, "", index)
        
        self.info_tree.heading(column, text=f"{column.replace('_', ' ').title()}{' ▼' if self.sort_ascending else ' ▲'}"
        )
    
    def _on_parent_select(self, event):
        """Handle parent selection event."""
        selection = self.parents_tree.selection()
        if selection:
            parent_number = self.parents_tree.item(selection[0])['values'][0]
            self.show_parent_details(parent_number)
    
    def show_parent_details(self, parent_number: str):
        """Show details for selected parent number."""
        # Clear existing items
        for item in self.info_tree.get_children():
            self.info_tree.delete(item)
        for item in self.texture_tree.get_children():
            self.texture_tree.delete(item)
        
        # Get all models that use this parent number
        models_using_parent = self.master.master.data_manager.get_models_using_parent(int(parent_number))
        
        # Get parent data from data manager for texture information
        parent_data = self.master.master.data_manager.parents.get(int(parent_number))
        
        # Display all models that use this parent
        if models_using_parent:
            for model in models_using_parent:
                # Get BML versions for this model
                bml_versions = self.master.master.data_manager.get_model_bml_versions(model)
                
                # Determine which model states use this parent
                model_states = []
                parent_str = str(parent_number)
                if model.normal_model == parent_str:
                    model_states.append("Normal")
                if model.fixed_model == parent_str:
                    model_states.append("Repaired")
                if model.damaged_model == parent_str:
                    model_states.append("Damaged")
                if model.destroyed_model == parent_str:
                    model_states.append("Destroyed")
                if model.left_destroyed_model == parent_str:
                    model_states.append("Left Destroyed")
                if model.right_destroyed_model == parent_str:
                    model_states.append("Right Destroyed")
                if model.both_models_destroyed == parent_str:
                    model_states.append("Both Destroyed")
                
                # Join model states for display
                model_type_display = ", ".join(model_states) if model_states else "Unknown"
                
                self.info_tree.insert("", "end", values=(
                    bml_versions,
                    model.name,
                    model_type_display,
                    model.type,
                    str(model.ct_number),
                    str(model.type_number)  # This is the Entity Index
                ))
        elif parent_data:
            # If no models found but parent data exists (e.g., cockpit parents)
            # If this is a cockpit parent with multiple aircraft variants
            if hasattr(parent_data, 'aircraft_variants') and parent_data.aircraft_variants:
                # Add an entry for each aircraft variant
                for aircraft_name, model_type in parent_data.aircraft_variants.items():
                    self.info_tree.insert("", "end", values=(
                        str(parent_data.bml_version),
                        aircraft_name,
                        model_type,
                        parent_data.type,
                        str(parent_data.ct_number),
                        str(parent_data.entity_idx)
                    ))
            else:
                # Add single entry for non-cockpit or single-aircraft parent
                self.info_tree.insert("", "end", values=(
                    str(parent_data.bml_version),
                    parent_data.model_name,
                    parent_data.model_type,
                    parent_data.type,
                    str(parent_data.ct_number),
                    str(parent_data.entity_idx)
                ))
        
        # Add texture information based on parent data if available
        if parent_data:
            # Add texture information based on BML version only
            if parent_data.bml_version == 2:
                # Get BML2 textures from materials.mtl
                bml2_textures = self.master.master.data_manager.get_bml2_textures(parent_data.parent_number)
                for tex in bml2_textures:
                    # Check if texture exists
                    full_path = os.path.join(self.master.master.data_manager.base_folder, tex["path"], tex["name"])
                    exists = os.path.exists(full_path)
                    
                    # Convert path to be relative to main BMS folder
                    display_path = self.master.master.data_manager.get_path_relative_to_bms_main(tex["path"])
                    
                    self.texture_tree.insert("", "end", values=(
                        tex["name"],
                        tex["type"],
                        display_path  # Show path relative to main BMS folder
                    ))  # Removed tags
            elif parent_data.bml_version == 1:
                # Add regular texture information
                if parent_data.textures:
                    for texture_id in parent_data.textures:
                        texture_data = self.master.master.data_manager.textures.get(texture_id)
                        if texture_data:
                            # Convert KoreaObj path to be relative to main BMS folder
                            display_path = self.master.master.data_manager.get_path_relative_to_bms_main("KoreaObj")
                            
                            # Add base texture
                            self.texture_tree.insert("", "end", values=(
                                texture_id,
                                "Texture",
                                display_path  # Show path relative to main BMS folder
                            ))
                            
                            # Add PBR textures if available
                            if texture_data.pbr:
                                for pbr_name, pbr_type in zip(texture_data.pbr, texture_data.pbr_type):
                                    self.texture_tree.insert("", "end", values=(
                                        pbr_name,
                                        pbr_type.upper(),
                                        display_path  # Show path relative to main BMS folder
                                    ))

    def show_legend(self):
        # Store original color if not stored
        if self.legend_button_color is None:
            self.legend_button_color = self.legend_button.cget("fg_color")
        
        # Disable button and change color
        self.legend_button.configure(state="disabled", fg_color="gray")
        
        # Check if PDR is loaded to customize legend
        pdr_loaded = bool(self.master.master.data_manager.pdr_file)
        missing_texture_text = "Missing Texture (when PDR loaded)" if not pdr_loaded else "Missing Texture"
        
        legend_items = [
            ("#2E7D32", "BML Version 2"),
            ("#81C784", "BML Version 1 with PBR"),
            ("#1565C0", "BML Version -1"),
            ("#B71C1C", missing_texture_text)
        ]
        
        # Create legend window with callback
        LegendWindow(self, "Parents Color Legend", legend_items,
                    on_close=lambda: self.legend_button.configure(
                        state="normal",
                        fg_color=self.legend_button_color
                    ))

class ProcessingWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        
        # Initialize animation state
        self._is_running = True
        self._animation_step = 0
        
        # Configure window
        self.title("Processing Data")
        window_width = 400
        window_height = 200
        self.geometry(f"{window_width}x{window_height}")
        self.resizable(False, False)
        
        # Set modern background color matching the app theme
        self.configure(fg_color="#E3F4FF")
        
        # Center window on parent
        self.update_idletasks()  # Ensure parent geometry is updated
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (window_width // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (window_height // 2)
        self.geometry(f"+{x}+{y}")
        
        # Make window modal and topmost
        self.transient(parent)
        self.grab_set()
        self.lift()
        self.attributes('-topmost', True)
        
        # Configure grid layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Create main content frame with modern styling
        self.content_frame = ctk.CTkFrame(
            self,
            fg_color="#D4E5F2",
            corner_radius=15,
            border_width=1,
            border_color="#7A92A9"
        )
        self.content_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.content_frame.grid_columnconfigure(0, weight=1)
        
        # Title label with modern styling
        self.title_label = ctk.CTkLabel(
            self.content_frame,
            text="Processing Files",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#2D3B45"
        )
        self.title_label.grid(row=0, column=0, padx=30, pady=(25, 10))
        
        # Status label for dynamic updates
        self.status_label = ctk.CTkLabel(
            self.content_frame,
            text="Loading and analyzing data...",
            font=ctk.CTkFont(size=12),
            text_color="#5A6B77"
        )
        self.status_label.grid(row=1, column=0, padx=30, pady=(0, 15))
        
        # Modern animated progress bar
        self.progress_bar = ctk.CTkProgressBar(
            self.content_frame,
            width=300,
            height=8,
            corner_radius=4,
            fg_color="#B8CFE5",
            progress_color="#7A92A9",
            border_width=0
        )
        self.progress_bar.grid(row=2, column=0, padx=30, pady=(0, 15), sticky="ew")
        
        # Set initial progress value
        self.progress_bar.set(0)
        
        # Create animated dots for additional visual feedback
        self.dots_label = ctk.CTkLabel(
            self.content_frame,
            text="•",
            font=ctk.CTkFont(size=20),
            text_color="#7A92A9"
        )
        self.dots_label.grid(row=3, column=0, padx=30, pady=(0, 25))
        
        # Start animations
        self._animate_progress()
        self._animate_dots()
        
        # Ensure window stays on top during processing
        self.after(100, self._maintain_focus)
    
    def _animate_progress(self):
        """Animate the progress bar with a smooth wave effect"""
        if not self._is_running:
            return
            
        # Create a smooth sine wave animation
        import math
        progress_value = (math.sin(self._animation_step * 0.1) + 1) / 2
        self.progress_bar.set(progress_value)
        
        self._animation_step += 1
        
        # Schedule next animation frame (60 FPS for smooth animation)
        self.after(16, self._animate_progress)
    
    def _animate_dots(self):
        """Animate the loading dots"""
        if not self._is_running:
            return
            
        dot_patterns = ["•", "••", "•••", "••", "•"]
        pattern_index = (self._animation_step // 30) % len(dot_patterns)
        self.dots_label.configure(text=dot_patterns[pattern_index])
        
        # Schedule next dot animation (slower than progress bar)
        self.after(100, self._animate_dots)
    
    def _maintain_focus(self):
        """Ensure window stays focused and topmost during processing"""
        if not self._is_running:
            return
            
        try:
            self.lift()
            self.focus_force()
            # Schedule next focus check
            self.after(500, self._maintain_focus)
        except:
            # Window might be destroyed, ignore errors
            pass
    
    def update_status(self, status_text):
        """Thread-safe method to update status text"""
        if self._is_running:
            self.after(0, lambda: self.status_label.configure(text=status_text))
    
    def close(self):
        """Close the processing window and stop all animations"""
        self._is_running = False
        try:
            self.grab_release()
            self.destroy()
        except:
            # Window might already be destroyed, ignore errors
            pass

class LegendWindow(ctk.CTkToplevel):
    def __init__(self, parent, title, legend_items, on_close=None):
        super().__init__(parent)
        
        self.title(title)
        self.geometry("300x200")
        self.resizable(False, False)
        
        # Configure window appearance
        self.configure(fg_color="#E3F4FF")
        
        # Create frame for legend items
        legend_frame = ctk.CTkFrame(self, fg_color="#D4E5F2")
        legend_frame.pack(padx=10, pady=10, fill="both", expand=True)
        
        # Add legend items
        for color, text in legend_items:
            item_frame = ctk.CTkFrame(legend_frame, fg_color="transparent")
            item_frame.pack(padx=5, pady=5, fill="x")
            
            color_box = ctk.CTkLabel(
                item_frame,
                text="",
                width=20,
                height=20,
                fg_color=color
            )
            color_box.pack(side="left", padx=(5, 10))
            
            text_label = ctk.CTkLabel(
                item_frame,
                text=text,
                anchor="w",
                fg_color="transparent"
            )
            text_label.pack(side="left", fill="x", expand=True)
        
        # Store callback
        self.on_close = on_close
        
        # Bind close event
        self.protocol("WM_DELETE_WINDOW", self.on_window_close)
        
        # Make window modal
        self.transient(parent)
        self.grab_set()
        
    def on_window_close(self):
        if self.on_close:
            self.on_close()
        self.destroy()

class PBRTexturesFrame(ctk.CTkFrame):
    def __init__(self, master, data_manager, dpi=1.0):
        super().__init__(master)
        logger.info("Initializing PBRTexturesFrame")
        
        self.data_manager = data_manager
        self.dpi = dpi
        
        # Set frame background color
        self.configure(fg_color="#E3F4FF")
        
        # Calculate scaled sizes
        self.base_font_size = int(12 * self.dpi)
        self.table_font_size = int(11 * self.dpi)
        self.table_header_size = int(12 * self.dpi)
        self.row_height = int(25 * self.dpi)

        # Configure style for row height only
        style = ttk.Style()
        style.configure("Treeview", rowheight=self.row_height)
        
        # Configure grid layout
        self.grid_columnconfigure(0, weight=1)  # Left side gets 1 part
        self.grid_columnconfigure(1, weight=3)  # Right side gets 3 parts
        self.grid_rowconfigure(2, weight=1)  # Main content row
        
        # Search frame with new color
        search_frame = ctk.CTkFrame(self)
        search_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=(10, 0))
        search_frame.grid_columnconfigure(1, weight=1)  # Make search entry expandable
        search_frame.grid_columnconfigure(0, weight=0)  # Color filter fixed
        search_frame.grid_columnconfigure(2, weight=0)  # Search button fixed
        search_frame.configure(fg_color="#D4E5F2")  # Lighter shade for search frame
        
        # Color filter with new colors
        self.color_var = ctk.StringVar(value="All Types")
        self.color_menu = ctk.CTkOptionMenu(
            search_frame,
            variable=self.color_var,
            values=["All Types", "Multiple-Paths", "Missing Texture"],
            command=self.search_textures,
            font=ctk.CTkFont(size=self.base_font_size),
            fg_color="#7A92A9",
            button_color="#6E8499",
            button_hover_color="#5D7388",
            text_color="#FFFFFF",
            dropdown_fg_color="#7A92A9",
            dropdown_hover_color="#6E8499",
            dropdown_text_color="#FFFFFF"
        )
        self.color_menu.grid(row=0, column=0, padx=5, pady=5)
        
        # Add search entry with scaled font and new colors
        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Search textures by name...",
            font=ctk.CTkFont(size=self.base_font_size),
            fg_color="#FFFFFF",
            border_color="#7A92A9",
            text_color="#2D3B45"
        )
        self.search_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.search_entry.bind("<Return>", self.search_textures)
        
        # Add search button with scaled font and new colors
        self.search_button = ctk.CTkButton(
            search_frame,
            text="Search",
            command=self.search_textures,
            font=ctk.CTkFont(size=self.base_font_size),
            fg_color="#7A92A9",
            hover_color="#6E8499",
            text_color="#FFFFFF"
        )
        self.search_button.grid(row=0, column=2, padx=5, pady=5)
        
        # Create header frame with legend and status
        header_frame = ctk.CTkFrame(self)
        header_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=20, pady=(10, 10))
        header_frame.grid_columnconfigure(1, weight=1)  # Make status expand
        header_frame.configure(fg_color="#D4E5F2")  # Lighter shade for header frame
        
        # Create legend frame
        legend_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        legend_frame.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        # Add legend items
        legend_items = [
            ("Missing Texture", "#B71C1C"),
            ("Multiple Paths", "#FDD835")  # Yellow for multiple paths
        ]
        
        for i, (text, color) in enumerate(legend_items):
            # Create color box with rounded corners
            color_box = ctk.CTkFrame(
                legend_frame,
                width=20,
                height=20,
                fg_color=color,
                corner_radius=5
            )
            color_box.grid(row=0, column=i*2, padx=(10, 5), pady=5)
            color_box.grid_propagate(False)  # Keep fixed size
            
            label = ctk.CTkLabel(
                legend_frame,
                text=text,
                font=ctk.CTkFont(size=12),
                text_color="#2D3B45"
            )
            label.grid(row=0, column=i*2+1, padx=(0, 10), pady=5)
        
        # Add status label with new colors
        self.status_label = ctk.CTkLabel(
            header_frame,
            text="",
            font=ctk.CTkFont(size=self.base_font_size),
            text_color="#2D3B45"
        )
        self.status_label.grid(row=0, column=1, padx=10, pady=5, sticky="e")
        
        # Create left frame for texture list with new color
        left_frame = ctk.CTkFrame(self)
        left_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=10)
        left_frame.grid_columnconfigure(0, weight=1)
        left_frame.grid_rowconfigure(0, weight=1)
        left_frame.configure(fg_color="#B8CFE5")  # Slightly darker shade for frame
        
        # Create texture list
        self.texture_list = ttk.Treeview(
            left_frame,
            columns=("texture",),
            show="headings",
            style="Treeview"
        )
        
        # Configure tags using the master's method
        self.master.master.configure_treeview_tags(self.texture_list)
        
        # Add scrollbar
        vsb = ttk.Scrollbar(left_frame, orient="vertical", command=self.texture_list.yview)
        hsb = ttk.Scrollbar(left_frame, orient="horizontal", command=self.texture_list.xview)
        self.texture_list.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # Grid layout for texture list
        self.texture_list.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        # Create right frame for details with new colors
        right_frame = ctk.CTkFrame(self)
        right_frame.grid(row=2, column=1, sticky="nsew", padx=20, pady=10)
        right_frame.grid_columnconfigure(0, weight=1)
        right_frame.grid_rowconfigure(0, weight=1)  # Parents table gets 1 part
        right_frame.grid_rowconfigure(1, weight=1)  # Info table gets 1 part
        right_frame.configure(fg_color="#B8CFE5")  # Slightly darker shade for frame
        
        # Create parents table frame (top) with new color
        parents_frame = ctk.CTkFrame(right_frame)
        parents_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=(0, 5))
        parents_frame.grid_columnconfigure(0, weight=1)
        parents_frame.grid_rowconfigure(0, weight=1)
        parents_frame.configure(fg_color="#D4E5F2")  # Lighter shade for inner frame
        
        # Create parents table
        self.parents_tree = ttk.Treeview(
            parents_frame,
            columns=("parent", "name", "model_type", "ct_number", "entity_idx"),
            show="headings",
            style="Treeview"
        )
        
        # Configure parents columns
        self.parents_tree.heading("parent", text="Parent Number")
        self.parents_tree.heading("name", text="Name")
        self.parents_tree.heading("model_type", text="Model Type")
        self.parents_tree.heading("ct_number", text="CT Number")
        self.parents_tree.heading("entity_idx", text="Entity Idx")
        
        # Set column widths
        self.parents_tree.column("parent", width=int(100 * self.dpi), minwidth=int(80 * self.dpi))
        self.parents_tree.column("name", width=int(200 * self.dpi), minwidth=int(150 * self.dpi))
        self.parents_tree.column("model_type", width=int(150 * self.dpi), minwidth=int(100 * self.dpi))
        self.parents_tree.column("ct_number", width=int(80 * self.dpi), minwidth=int(70 * self.dpi))
        self.parents_tree.column("entity_idx", width=int(80 * self.dpi), minwidth=int(70 * self.dpi))
        
        # Add scrollbars for parents table
        vsb_parents = ttk.Scrollbar(parents_frame, orient="vertical", command=self.parents_tree.yview)
        hsb_parents = ttk.Scrollbar(parents_frame, orient="horizontal", command=self.parents_tree.xview)
        self.parents_tree.configure(yscrollcommand=vsb_parents.set, xscrollcommand=hsb_parents.set)
        
        # Grid layout for parents table
        self.parents_tree.grid(row=0, column=0, sticky="nsew")
        vsb_parents.grid(row=0, column=1, sticky="ns")
        hsb_parents.grid(row=1, column=0, sticky="ew")
        
        # Create info table frame (bottom) with new color
        info_frame = ctk.CTkFrame(right_frame)
        info_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=(5, 0))
        info_frame.grid_columnconfigure(0, weight=1)
        info_frame.grid_rowconfigure(0, weight=1)
        info_frame.configure(fg_color="#D4E5F2")  # Lighter shade for inner frame
        
        # Create info table
        self.info_tree = ttk.Treeview(
            info_frame,
            columns=("type", "path"),
            show="headings",
            style="Treeview"  # Use the same style as the main table
        )
        
        # Configure info columns
        self.info_tree.heading("type", text="Texture Type")
        self.info_tree.heading("path", text="Texture Path")
        self.info_tree.column("type", width=int(150 * self.dpi), minwidth=int(100 * self.dpi))
        self.info_tree.column("path", width=int(300 * self.dpi), minwidth=int(200 * self.dpi))
        
        # Add scrollbars for info table
        vsb_info = ttk.Scrollbar(info_frame, orient="vertical", command=self.info_tree.yview)
        hsb_info = ttk.Scrollbar(info_frame, orient="horizontal", command=self.info_tree.xview)
        self.info_tree.configure(yscrollcommand=vsb_info.set, xscrollcommand=hsb_info.set)
        
        # Grid layout for info table
        self.info_tree.grid(row=0, column=0, sticky="nsew")
        vsb_info.grid(row=0, column=1, sticky="ns")
        hsb_info.grid(row=1, column=0, sticky="ew")
        
        # Bind selection event
        self.texture_list.bind("<<TreeviewSelect>>", self._on_texture_select)
        
        # Store all textures for search
        self.all_textures = {}
    
    def _get_texture_color_tag(self, texture_name, texture_data):
        """Get the color tag for a texture based on its properties."""
        # Count how many paths exist and don't exist
        paths_exist = sum(exists for exists in texture_data['paths'].values())
        total_paths = len(texture_data['paths'])
        
        # Count unique base paths
        unique_base_paths = len(texture_data['base_paths'])
        
        # Determine tag based on existence in paths
        if paths_exist == 0:
            return "missing"  # Red for missing textures
        elif paths_exist < total_paths:
            return "missing"  # Red for partially missing textures
        elif unique_base_paths > 1:
            return "partial"  # Yellow for multiple paths
        else:
            return ""  # Default case (no special properties)
    
    def _color_name_to_tag(self, color_name):
        """Map color filter names to tag names."""
        color_map = {
            "Multiple-Paths": "partial",
            "Missing Texture": "missing"
        }
        return color_map.get(color_name, "")
        
        # Configure tags for different states
        self.texture_list.tag_configure("missing", background="#B71C1C", foreground="white")  # Red background, white text
        self.texture_list.tag_configure("partial", background="#FDD835", foreground="black")  # Yellow background, black text for multiple paths
        self.info_tree.tag_configure("multiple_paths", background="#FDD835")  # Yellow background for multiple paths
        
        logger.info("PBRTexturesFrame initialization complete")

    def update_list(self):
        """Update the list of PBR textures."""
        try:
            logger.info("Starting PBR textures update")
            
            # Clear existing items
            for item in self.texture_list.get_children():
                self.texture_list.delete(item)
            
            # Track unique textures and their paths
            self.all_textures = {}
            
            # Get all parent numbers with BML version 2
            bml2_parents = [
                parent_number for parent_number, parent_data 
                in self.data_manager.parents.items() 
                if parent_data.bml_version == 2
            ]
            logger.info(f"Found {len(bml2_parents)} BML2 parents")
            
            if not bml2_parents:
                logger.warning("No BML2 parents found")
                return
            
            # Pre-cache existence checks for better performance
            existence_cache = {}
            
            # Process all BML2 parents in a batch
            for parent_number in bml2_parents:
                textures = self.data_manager.get_bml2_textures(parent_number)
                
                for texture in textures:
                    texture_name = texture['name']
                    texture_path = texture['path']
                    texture_type = texture['type']
                    
                    # Initialize texture data if not exists
                    if texture_name not in self.all_textures:
                        self.all_textures[texture_name] = {
                            'parents': set(),
                            'types': set(),
                            'paths': {},
                            'type': texture_type,
                            'base_paths': set()
                        }
                    
                    # Add parent and type information
                    self.all_textures[texture_name]['parents'].add(parent_number)
                    self.all_textures[texture_name]['types'].add(texture_type)
                    self.all_textures[texture_name]['base_paths'].add(texture_path)
                    
                    # Check if texture exists (use cache)
                    cache_key = (texture_path, texture_name)
                    if cache_key not in existence_cache:
                        full_path = os.path.join(self.data_manager.base_folder, texture_path, f"{texture_name}.dds")
                        existence_cache[cache_key] = os.path.exists(full_path)
                    
                    exists = existence_cache[cache_key]
                    self.all_textures[texture_name]['paths'][texture_path] = exists
            
            # Add textures to list (batch operation)
            items_to_add = []
            for texture_name, data in sorted(self.all_textures.items()):
                # Get color tag for this texture
                tag = self._get_texture_color_tag(texture_name, data)
                items_to_add.append((texture_name, tag))
            
            # Batch insert items
            for texture_name, tag in items_to_add:
                self.texture_list.insert("", "end", values=(texture_name,), tags=(tag,) if tag else ())
            
            # Update status
            total_textures = len(self.all_textures)
            missing_textures = sum(1 for data in self.all_textures.values() 
                                 if sum(exists for exists in data['paths'].values()) < len(data['paths']))
            multiple_paths = sum(1 for data in self.all_textures.values() 
                               if len(data['base_paths']) > 1)
            
            status_text = f"Total PBR Textures: {total_textures} "
            status_text += f"(Missing: {missing_textures}, Multiple Paths: {multiple_paths})"
            self.status_label.configure(text=status_text)
            
            logger.info(f"Completed PBR textures update: {status_text}")
            
        except Exception as e:
            logger.error(f"Error in update_list: {str(e)}")
            raise

    def show_texture_details(self, texture_name):
        """Show details for the selected texture."""
        try:
            logger.debug(f"Showing details for texture: {texture_name}")
            
            # Clear existing items
            for item in self.info_tree.get_children():
                self.info_tree.delete(item)
            for item in self.parents_tree.get_children():
                self.parents_tree.delete(item)
            
            # Get texture data
            texture_data = self.all_textures.get(texture_name)
            if not texture_data:
                logger.warning(f"No texture data found for {texture_name}")
                return
            
            logger.debug(f"Found texture data: {texture_data}")
            
            # Add paths to info table
            for path, exists in sorted(texture_data['paths'].items()):
                # Skip variant paths for display
                # Normalize path separators before checking
                normalized_display_path = path.replace('\\\\', '/').replace('\\', '/').replace('//', '/')
                if "/" in normalized_display_path and normalized_display_path.split("/")[-1] in ["Normal", "ARMW"]:
                    continue
                    
                # Get the texture type
                texture_type = texture_data['type']
                
                # Convert path to be relative to main BMS folder
                display_path = self.data_manager.get_path_relative_to_bms_main(path)
                
                logger.debug(f"Adding path info - Type: {texture_type}, Path: {display_path}, Exists: {exists}")
                self.info_tree.insert("", "end", values=(
                    texture_type,
                    display_path
                ))  # Removed tags
            
            # Update parents table
            for parent_number in texture_data['parents']:
                parent = self.data_manager.parents.get(parent_number)
                if parent:
                    logger.debug(f"Adding parent info - Number: {parent_number}, Name: {parent.model_name}")
                    self.parents_tree.insert("", "end", values=(
                        str(parent.parent_number),
                        parent.model_name,
                        parent.model_type,
                        str(parent.ct_number),
                        str(parent.entity_idx)
                    ))
                else:
                    logger.warning(f"Parent data not found for parent number {parent_number}")
                    
        except Exception as e:
            logger.exception(f"Error showing texture details for {texture_name}: {str(e)}")
            raise

    def show_legend(self):
        # Store original color if not stored
        if self.legend_button_color is None:
            self.legend_button_color = self.legend_button.cget("fg_color")
        
        # Disable button and change color
        self.legend_button.configure(state="disabled", fg_color="gray")
        
        legend_items = [
            ("#2E7D32", "Both PBR and High Resolution Available"),
            ("#A5D6A7", "PBR Textures Available"),
            ("#90CAF9", "High Resolution Available"),
            ("#B71C1C", "Missing Texture")
        ]
        
        # Create legend window with callback
        LegendWindow(self, "Textures Color Legend", legend_items,
                    on_close=lambda: self.legend_button.configure(
                        state="normal",
                        fg_color=self.legend_button_color
                    ))

    def set_texture_paths(self, base_path: str):
        """Set paths to KoreaObj folders."""
        # Set base folder first
        self.base_folder = os.path.dirname(base_path)
        # Set KoreaObj paths relative to base folder
        self.korea_obj_path = os.path.join(self.base_folder, "KoreaObj")
        self.korea_obj_hires_path = os.path.join(self.base_folder, "KoreaObj_HiRes")

    def normalize_texture_path(self, parent_number: int, texture_path: str) -> str:
        """Normalize texture path to a standard format."""
        # Remove .dds extension if present
        if texture_path.lower().endswith('.dds'):
            texture_path = texture_path[:-4]
            
        # Normalize path separators (handle /, //, \, \\)
        normalized_path = texture_path.replace('\\\\', '/').replace('\\', '/').replace('//', '/')
            
        # If path starts with a parent number or _MiscTex, use that
        if '/' in normalized_path:
            prefix = normalized_path.split('/')[0]
            if prefix.isdigit() or prefix == '_MiscTex':
                return f"Models/{normalized_path}"
        
        # Otherwise, use the parent's model folder
        return f"Models/{parent_number}"

    def search_textures(self, *args):
        """Search and filter textures by name and color type."""
        search_text = self.search_entry.get().lower().strip()
        color_filter = self.color_var.get()
        
        # Clear existing items
        for item in self.texture_list.get_children():
            self.texture_list.delete(item)
        
        # Filter textures
        matching_textures = {}
        for texture_name, data in self.all_textures.items():
            # Check search text filter
            if search_text and search_text not in texture_name.lower():
                continue
            
            # Check color filter
            if color_filter != "All Types":
                texture_tag = self._get_texture_color_tag(texture_name, data)
                expected_tag = self._color_name_to_tag(color_filter)
                if texture_tag != expected_tag:
                    continue
            
            # If we get here, the texture passed all filters
            matching_textures[texture_name] = data
        
        # Add filtered textures to list
        for texture_name, data in sorted(matching_textures.items()):
            # Get color tag for this texture
            tag = self._get_texture_color_tag(texture_name, data)
            
            # Add to list
            self.texture_list.insert("", "end", values=(texture_name,), tags=(tag,) if tag else ())
        
        # Update status with search results
        total_matching = len(matching_textures)
        missing_matching = sum(1 for data in matching_textures.values() 
                             if sum(exists for exists in data['paths'].values()) < len(data['paths']))
        multiple_matching = sum(1 for data in matching_textures.values() 
                              if len(data['base_paths']) > 1)
        
        if search_text or color_filter != "All Types":
            status_text = f"Found {total_matching} matching textures "
        else:
            status_text = f"Showing all {total_matching} textures "
        
        status_text += f"(Missing: {missing_matching}, Multiple Paths: {multiple_matching})"
        self.status_label.configure(text=status_text)

    def _on_texture_select(self, event):
        """Handle texture selection event."""
        selection = self.texture_list.selection()
        if not selection:
            return
        
        # Get selected texture name
        texture_name = self.texture_list.item(selection[0])['values'][0]
        self.show_texture_details(texture_name)
        
    def show_legend(self):
        # Store original color if not stored
        if self.legend_button_color is None:
            self.legend_button_color = self.legend_button.cget("fg_color")
        
        # Disable button and change color
        self.legend_button.configure(state="disabled", fg_color="gray")
        
        legend_items = [
            ("#2E7D32", "Both PBR and High Resolution Available"),
            ("#A5D6A7", "PBR Textures Available"),
            ("#90CAF9", "High Resolution Available"),
            ("#B71C1C", "Missing Texture")
        ]
        
        # Create legend window with callback
        LegendWindow(self, "Textures Color Legend", legend_items,
                    on_close=lambda: self.legend_button.configure(
                        state="normal",
                        fg_color=self.legend_button_color
                    ))
