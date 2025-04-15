import os
import sys
import customtkinter as ctk
from tkinter import ttk
from PIL import Image
from loguru import logger
from frames import HomeFrame, ModelsFrame, TexturesFrame, UnusedTexturesFrame, ParentsFrame, ProcessingWindow, PBRTexturesFrame
from data_manager import DataManager
import ctypes
import logging
import threading

# Configure logger
logger.remove()  # Remove any existing handlers
logger.add(
    "logs/bms_manager.log",
    rotation="10 MB",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {function}:{line} | {message}",
    level="DEBUG",  # Set to DEBUG to capture all log levels
    enqueue=True,  # Enable thread-safe logging
    backtrace=True,  # Include backtrace for errors
    diagnose=True,  # Include diagnostic information
    catch=True  # Catch any errors during logging
)

# Configure PIL logging
logging.getLogger('PIL').setLevel(logging.WARNING)  # Further reduce PIL logging
logging.getLogger('frames').setLevel(logging.INFO)  # Set frames logging to INFO only

# Configure CustomTkinter
ctk.set_appearance_mode("System")  # Use system theme
ctk.set_default_color_theme("blue")
ctk.deactivate_automatic_dpi_awareness()  # Disable automatic DPI scaling

def configure_table_styles():
    """Configure Treeview styles for consistent table appearance across the application."""
    style = ttk.Style()
    
    # Configure basic Treeview style
    style.configure(
        "Treeview",
        background="#FFFFFF",
        foreground="#2D3B45",
        fieldbackground="#FFFFFF",
        borderwidth=1,
        relief="solid"
    )
    
    # Configure Treeview headers
    style.configure(
        "Treeview.Heading",
        background="#B8CFE5",
        foreground="#2D3B45",
        relief="flat"
    )
    
    # Configure header hover and pressed states
    style.map(
        "Treeview.Heading",
        background=[("pressed", "#A1B9D0"), ("active", "#A1B9D0")],
        foreground=[("pressed", "#2D3B45"), ("active", "#2D3B45")]
    )
    
    # Configure row selection colors
    style.map(
        "Treeview",
        background=[("selected", "#7A92A9")],
        foreground=[("selected", "#FFFFFF")]
    )

def configure_treeview_tags(treeview):
    """Configure tags for a specific Treeview widget."""
    # Configure tags for different states
    treeview.tag_configure("missing", background="#B71C1C", foreground="#FFFFFF")
    treeview.tag_configure("partial", background="#FFA500", foreground="#000000")
    treeview.tag_configure("bml2", background="#2E7D32", foreground="#FFFFFF")
    treeview.tag_configure("bml1_2", background="#81C784", foreground="#000000")
    treeview.tag_configure("bml_1", background="#1565C0", foreground="#FFFFFF")
    treeview.tag_configure("bml_1_1", background="#90CAF9", foreground="#000000")
    treeview.tag_configure("pbr", background="#A5D6A7", foreground="#000000")
    treeview.tag_configure("highres", background="#90CAF9", foreground="#000000")
    treeview.tag_configure("both", background="#2E7D32", foreground="#FFFFFF")

class BMSManager(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Configure table styles
        configure_table_styles()
        
        # Store the configure_treeview_tags function as an instance method
        self.configure_treeview_tags = configure_treeview_tags
        
        # Get DPI scaling
        try:
            awareness = ctypes.c_int()
            ctypes.windll.shcore.GetProcessDpiAwareness(0, ctypes.byref(awareness))
            self.dpi = ctypes.windll.user32.GetDpiForWindow(self.winfo_id()) / 96.0
        except Exception:
            self.dpi = self.winfo_fpixels('1i') / 72.0  # Fallback method
        
        # Calculate scaled sizes
        self.base_font_size = int(12 * self.dpi)  # Match frames base size
        self.title_font_size = int(14 * self.dpi)  # Keep title larger
        self.nav_font_size = int(14 * self.dpi)  # Slightly larger than base for navigation
        
        # Initialize data manager
        self.data_manager = DataManager()
        
        # Configure main window
        self.title("3D Assets Manager v0.95")
        self.geometry("1370x730")
        self.minsize(800, 600)  # Set minimum window size
        
        # Set window background color
        self.configure(fg_color="#E3F4FF")
        
        # Set window icon if available
        try:
            icon_path = os.path.join("assets", "icon.ico")
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
                logger.info("Window icon loaded successfully")
        except Exception as e:
            logger.warning(f"Could not load window icon: {str(e)}")
        
        # Bind window events with delay to prevent rapid updates
        self._configure_pending = False
        self.bind("<Configure>", self._on_window_configure)
        self.bind("<Map>", self._on_window_map)
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # Configure grid layout
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        # Load images for navigation
        self.nav_images = {}
        nav_image_files = {
            "home": "home.png",
            "models": "3D Assets.png",
            "textures": "textures.png",
            "parents": "models.png",
            "unused": "Notextures.png",
            "pbr": "PBRTexture.png"
        }
        
        for name, filename in nav_image_files.items():
            try:
                image = Image.open(os.path.join("assets", filename))
                if image.mode != 'RGBA':
                    image = image.convert('RGBA')
                self.nav_images[name] = ctk.CTkImage(
                    image,
                    size=(int(20 * self.dpi), int(20 * self.dpi))
                )
            except Exception as e:
                logger.error(f"Error loading {filename}: {str(e)}")
                self.nav_images[name] = ctk.CTkImage(
                    Image.new('RGBA', (20, 20), (0, 0, 0, 0)),
                    size=(int(20 * self.dpi), int(20 * self.dpi))
                )
        
        # Create navigation frame with new color
        self.navigation_frame = ctk.CTkFrame(self, corner_radius=0)
        self.navigation_frame.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self.navigation_frame.grid_rowconfigure(8, weight=1)  # Increased to accommodate image
        self.navigation_frame.configure(fg_color="#A1B9D0")
        
        # Navigation image
        try:
            nav_image = Image.open(os.path.join("assets", "navigation.png"))
            if nav_image.mode != 'RGBA':
                nav_image = nav_image.convert('RGBA')
            
            # Calculate image size (90% of navigation panel width)
            nav_width = int(200 * self.dpi * 0.9)  # 90% of typical nav panel width
            nav_height = int(nav_width * (nav_image.height / nav_image.width))
            
            nav_img = ctk.CTkImage(
                light_image=nav_image,
                dark_image=nav_image,
                size=(nav_width, nav_height)
            )
            
            self.nav_image_label = ctk.CTkLabel(
                self.navigation_frame,
                text="",
                image=nav_img
            )
            self.nav_image_label.grid(row=0, column=0, padx=10, pady=(20, 10))
            
        except Exception as e:
            logger.error(f"Error loading navigation image: {str(e)}")
        
        # Navigation label
        self.navigation_label = ctk.CTkLabel(
            self.navigation_frame, text="Navigation",
            compound="left",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#2D3B45"
        )
        self.navigation_label.grid(row=1, column=0, padx=20, pady=(0, 20))
        
        # Navigation buttons with new colors
        button_color = "#A1B9D0"  # Same as panel
        hover_color = "#92A8BD"   # Slightly darker for hover
        selected_color = "#7A92A9" # Even darker for selected
        
        self.home_button = ctk.CTkButton(
            self.navigation_frame, corner_radius=0, height=int(40 * self.dpi),
            border_spacing=10, text="Dashboard",
            fg_color=button_color, text_color="#2D3B45",
            hover_color=hover_color,
            font=ctk.CTkFont(size=self.nav_font_size),
            image=self.nav_images["home"], anchor="w",
            command=self.home_button_event
        )
        self.home_button.grid(row=2, column=0, sticky="ew")  # Moved down one row
        
        self.models_button = ctk.CTkButton(
            self.navigation_frame, corner_radius=0, height=int(40 * self.dpi),
            border_spacing=10, text="3D Assets",
            fg_color=button_color, text_color="#2D3B45",
            hover_color=hover_color,
            font=ctk.CTkFont(size=self.nav_font_size),
            image=self.nav_images["models"], anchor="w",
            command=self.models_button_event
        )
        self.models_button.grid(row=3, column=0, sticky="ew")  # Moved down one row
        
        self.parents_button = ctk.CTkButton(
            self.navigation_frame, corner_radius=0, height=int(40 * self.dpi),
            border_spacing=10, text="Parents",
            fg_color=button_color, text_color="#2D3B45",
            hover_color=hover_color,
            font=ctk.CTkFont(size=self.nav_font_size),
            image=self.nav_images["parents"], anchor="w",
            command=self.parents_button_event
        )
        self.parents_button.grid(row=4, column=0, sticky="ew")  # Moved down one row
        
        self.textures_button = ctk.CTkButton(
            self.navigation_frame, corner_radius=0, height=int(40 * self.dpi),
            border_spacing=10, text="Textures",
            fg_color=button_color, text_color="#2D3B45",
            hover_color=hover_color,
            font=ctk.CTkFont(size=self.nav_font_size),
            image=self.nav_images["textures"], anchor="w",
            command=self.textures_button_event
        )
        self.textures_button.grid(row=5, column=0, sticky="ew")  # Moved down one row
        
        self.pbr_button = ctk.CTkButton(
            self.navigation_frame, corner_radius=0, height=int(40 * self.dpi),
            border_spacing=10, text="PBR Textures",
            fg_color=button_color, text_color="#2D3B45",
            hover_color=hover_color,
            font=ctk.CTkFont(size=self.nav_font_size),
            image=self.nav_images["pbr"], anchor="w",
            command=self.pbr_button_event
        )
        self.pbr_button.grid(row=6, column=0, sticky="ew", padx=0, pady=0)  # Moved down one row
        
        self.unused_button = ctk.CTkButton(
            self.navigation_frame, corner_radius=0, height=int(40 * self.dpi),
            border_spacing=10, text="Unused Textures",
            fg_color=button_color, text_color="#2D3B45",
            hover_color=hover_color,
            font=ctk.CTkFont(size=self.nav_font_size),
            image=self.nav_images["unused"], anchor="w",
            command=self.unused_button_event
        )
        self.unused_button.grid(row=7, column=0, sticky="ew")  # Moved down one row
        
        # Create main frame with new color
        self.main_frame = ctk.CTkFrame(self, corner_radius=0)
        self.main_frame.grid(row=0, column=1, rowspan=2, sticky="nsew")
        self.main_frame.configure(fg_color="#E3F4FF")
        
        # Create panel frame for file selection area (dark background)
        self.file_selection_area = ctk.CTkFrame(self, corner_radius=0)
        self.file_selection_area.grid(row=2, column=0, columnspan=2, sticky="ew")
        self.file_selection_area.grid_columnconfigure(0, weight=1)
        self.file_selection_area.configure(fg_color="#8599AD")  # Using the previous outer frame's color
        
        # Create file selection frame with lighter color
        self.file_frame = ctk.CTkFrame(self.file_selection_area)
        self.file_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=15)
        self.file_frame.grid_columnconfigure(1, weight=1)
        self.file_frame.configure(fg_color="#B8CFE5")  # Lighter shade for inner frame
        
        # File selection widgets with new colors
        self.ct_label = ctk.CTkLabel(
            self.file_frame, text="Falcon4_CT.xml:",
            font=ctk.CTkFont(size=12),
            text_color="#2D3B45"
        )
        self.ct_label.grid(row=0, column=0, padx=5, pady=5)
        
        self.ct_entry = ctk.CTkEntry(
            self.file_frame, width=300, state="readonly",
            font=ctk.CTkFont(size=12),
            fg_color="#FFFFFF",  # White background for better contrast
            border_color="#7A92A9",
            text_color="#2D3B45"
        )
        self.ct_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        self.ct_button = ctk.CTkButton(
            self.file_frame, text="Browse",
            font=ctk.CTkFont(size=12),
            fg_color="#7A92A9",
            hover_color="#6E8499",
            text_color="#FFFFFF",
            command=self.browse_ct_file
        )
        self.ct_button.grid(row=0, column=2, padx=5, pady=5)
        
        self.pdr_label = ctk.CTkLabel(
            self.file_frame, text="ParentsDetailsReport.txt:",
            font=ctk.CTkFont(size=12),
            text_color="#2D3B45"
        )
        self.pdr_label.grid(row=1, column=0, padx=5, pady=5)
        
        self.pdr_entry = ctk.CTkEntry(
            self.file_frame, width=300, state="readonly",
            font=ctk.CTkFont(size=12),
            fg_color="#FFFFFF",  # White background for better contrast
            border_color="#7A92A9",
            text_color="#2D3B45"
        )
        self.pdr_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        
        self.pdr_status = ctk.CTkLabel(
            self.file_frame, text="Not loaded",
            font=ctk.CTkFont(size=12),
            text_color="#2D3B45"
        )
        self.pdr_status.grid(row=1, column=2, padx=5, pady=5)
        
        # Select default frame
        self.select_frame_by_name("home")
    
    def _on_window_configure(self, event=None):
        """Handle window configuration changes with delay"""
        if event and event.widget == self and not self._configure_pending:
            self._configure_pending = True
            self.after(250, self._update_window)  # Add 250ms delay
    
    def _update_window(self):
        """Update window after delay"""
        self._configure_pending = False
        self.update_idletasks()
        
        # Force redraw of current frame only
        current_frame = None
        for widget in self.main_frame.winfo_children():
            if isinstance(widget, (HomeFrame, ModelsFrame, TexturesFrame, UnusedTexturesFrame, ParentsFrame)):
                current_frame = widget
                break
        
        if current_frame:
            current_frame.update_idletasks()
    
    def _on_window_map(self, event=None):
        """Handle window mapping (showing) event"""
        self.update_idletasks()
    
    def _on_closing(self):
        """Handle window closing event"""
        try:
            self.quit()
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
            self.destroy()
    
    def select_frame_by_name(self, name):
        try:
            # Set button colors with new color scheme
            selected_color = "#7A92A9"
            normal_color = "#A1B9D0"
            
            self.home_button.configure(fg_color=selected_color if name == "home" else normal_color)
            self.models_button.configure(fg_color=selected_color if name == "models" else normal_color)
            self.textures_button.configure(fg_color=selected_color if name == "textures" else normal_color)
            self.parents_button.configure(fg_color=selected_color if name == "parents" else normal_color)
            self.unused_button.configure(fg_color=selected_color if name == "unused" else normal_color)
            self.pbr_button.configure(fg_color=selected_color if name == "pbr" else normal_color)
            
            # Remove any existing frame reference
            if hasattr(self, f"{name}_frame"):
                delattr(self, f"{name}_frame")
            
            # Destroy existing frames with proper cleanup
            for widget in self.main_frame.winfo_children():
                try:
                    widget.destroy()
                except Exception as e:
                    logger.error(f"Error cleaning up widget: {str(e)}")
                    continue
            
            # Update the display to ensure cleanup is complete
            self.main_frame.update_idletasks()
            
            # Show selected frame
            frame = None
            if name == "home":
                frame = HomeFrame(self.main_frame)
            elif name == "models":
                frame = ModelsFrame(self.main_frame)
                if self.data_manager.ct_file:
                    logger.info("Updating models frame with loaded data")
                    models = self.data_manager.get_models_by_type()
                    if models:
                        logger.info(f"Found {len(models)} models to display")
                        frame.update_table(models)
                    else:
                        logger.warning("No models found in data manager")
            elif name == "textures":
                frame = TexturesFrame(self.main_frame)
                if self.data_manager.pdr_file:
                    logger.info("Updating textures frame with loaded data")
                    textures = self.data_manager.get_textures()
                    if textures:
                        logger.info(f"Found {len(textures)} textures to display")
                        frame.update_list(textures)
                    else:
                        logger.warning("No textures found in data manager")
            elif name == "parents":
                frame = ParentsFrame(self.main_frame)
                if self.data_manager.ct_file:
                    logger.info("Updating parents frame with loaded data")
                    # Load cockpit parents if not already loaded
                    if not hasattr(self.data_manager, 'cockpit_parents_loaded'):
                        logger.info("Loading cockpit parents data")
                        self.data_manager.load_cockpit_parents(self.data_manager.ct_file)
                        self.data_manager.cockpit_parents_loaded = True
                    
                    # Get all parents including cockpit parents
                    parents = list(self.data_manager.parents.keys())
                    if parents:
                        logger.info(f"Found {len(parents)} parents to display")
                        frame.update_list(parents)
                    else:
                        logger.warning("No parents found in data manager")
            elif name == "unused":
                frame = UnusedTexturesFrame(self.main_frame)
                if self.data_manager.pdr_file:
                    unused_file = os.path.join(os.path.dirname(self.data_manager.pdr_file), "KoreaObjUnusedTexturesReport.txt")
                    if os.path.exists(unused_file):
                        logger.info(f"Loading unused textures from {unused_file}")
                        if self.data_manager.load_unused_textures(unused_file):
                            unused_textures = self.data_manager.get_unused_textures()
                            if unused_textures:
                                logger.info(f"Found {len(unused_textures)} unused textures")
                                frame.update_list(unused_textures)
                            else:
                                logger.warning("No unused textures found")
            elif name == "pbr":
                try:
                    frame = PBRTexturesFrame(self.main_frame, self.data_manager, self.dpi)
                    # Wait for frame to be ready
                    self.update_idletasks()
                    frame.update_idletasks()
                    
                    if self.data_manager.pdr_file:
                        logger.info("Updating PBR textures frame with PDR file")
                        frame.update_list()
                    else:
                        logger.info("Updating PBR textures frame without PDR file")
                        # Load parents from Models folder if PDR is not available
                        if not hasattr(self.data_manager, 'parents_loaded_from_models'):
                            logger.info("Loading parents from Models folder")
                            self.data_manager.load_parents_from_models_folder()
                            self.data_manager.parents_loaded_from_models = True
                        frame.update_list()
                except Exception as e:
                    logger.exception(f"Error initializing PBR frame: {str(e)}")
                    raise
            
            if frame:
                # Wait for frame to be ready
                self.update_idletasks()
                
                # Grid the new frame
                frame.grid(row=0, column=0, sticky="nsew")
                
                # Store reference to current frame with correct attribute name
                setattr(self, f"{name}_frame", frame)
                
                # Configure grid for the selected frame
                self.main_frame.grid_columnconfigure(0, weight=1)
                self.main_frame.grid_rowconfigure(0, weight=1)
                
                # Update the frame
                frame.update_idletasks()
                
        except Exception as e:
            logger.error(f"Error creating {name} frame: {str(e)}")
            logger.error("Stack trace:", exc_info=True)
    
    def home_button_event(self):
        self.select_frame_by_name("home")
    
    def models_button_event(self):
        self.select_frame_by_name("models")
    
    def textures_button_event(self):
        self.select_frame_by_name("textures")
    
    def parents_button_event(self):
        self.select_frame_by_name("parents")
    
    def unused_button_event(self):
        self.select_frame_by_name("unused")
    
    def pbr_button_event(self):
        self.select_frame_by_name("pbr")
    
    def _load_files_thread(self, filename, processing_window):
        """Thread function to load files"""
        try:
            # Set texture paths based on CT file location
            self.data_manager.set_texture_paths(filename)
            
            # Load CT file
            if self.data_manager.load_ct_file(filename):
                self.load_parent_details_report(filename)
                
                # Update current frame if needed
                self.after(0, self._update_current_frame)
        finally:
            # Close processing window
            self.after(0, processing_window.close)

    def _update_current_frame(self):
        """Update the current frame with loaded data"""
        try:
            current_frame = None
            if self.main_frame.winfo_children():
                current_frame = self.main_frame.winfo_children()[0]
            
            if isinstance(current_frame, ModelsFrame):
                models = self.data_manager.get_models_by_type()
                if hasattr(self, 'models_frame'):
                    self.models_frame.update_table(models)
            elif isinstance(current_frame, UnusedTexturesFrame):
                # Check for unused textures file
                if self.data_manager.pdr_file:
                    unused_file = os.path.join(os.path.dirname(self.data_manager.pdr_file), "KoreaObjUnusedTexturesReport.txt")
                    if os.path.exists(unused_file):
                        if self.data_manager.load_unused_textures(unused_file):
                            unused_textures = self.data_manager.get_unused_textures()
                            if unused_textures and hasattr(self, 'unused_frame'):
                                self.unused_frame.update_list(unused_textures)
            elif isinstance(current_frame, TexturesFrame):
                if hasattr(self, 'textures_frame'):
                    textures = self.data_manager.get_textures()
                    if textures:
                        self.textures_frame.update_list(textures)
            elif isinstance(current_frame, ParentsFrame):
                if hasattr(self, 'parents_frame'):
                    parents = list(self.data_manager.parents.keys())
                    if parents:
                        self.parents_frame.update_list(parents)
            elif isinstance(current_frame, PBRTexturesFrame):
                if hasattr(self, 'pbr_frame'):
                    self.pbr_frame.update_list()
        except Exception as e:
            logger.error(f"Error updating current frame: {str(e)}")
            logger.error("Stack trace:", exc_info=True)

    def browse_ct_file(self):
        filename = ctk.filedialog.askopenfilename(
            title="Select Falcon4_CT.xml",
            filetypes=[("XML files", "*.xml")]
        )
        if filename:
            self.ct_entry.configure(state="normal")
            self.ct_entry.delete(0, ctk.END)
            self.ct_entry.insert(0, filename)
            self.ct_entry.configure(state="readonly")
            
            # Set base folder for BML2 textures
            self.data_manager.set_base_folder(filename)
            
            # Show processing window
            processing_window = ProcessingWindow(self)
            
            # Start loading thread
            thread = threading.Thread(
                target=self._load_files_thread,
                args=(filename, processing_window)
            )
            thread.daemon = True
            thread.start()
    
    def load_parent_details_report(self, ct_file):
        try:
            # Clear the PDR entry first (always clear it when loading new CT file)
            self.pdr_entry.configure(state="normal")
            self.pdr_entry.delete(0, ctk.END)
            self.pdr_entry.configure(state="readonly")
            
            # Get the directory containing Falcon4_CT.xml
            ct_dir = os.path.dirname(ct_file)
            
            # Try the direct path first (same directory as CT file)
            pdr_path = os.path.normpath(os.path.join(ct_dir, "ParentStatistics", "ParentsDetailsReport.txt"))
            
            logger.info(f"Looking for ParentsDetailsReport.txt at: {pdr_path}")
            
            if os.path.exists(pdr_path):
                # PDR found, set the path
                self.pdr_entry.configure(state="normal")
                self.pdr_entry.insert(0, pdr_path)
                self.pdr_entry.configure(state="readonly")
                
                if self.data_manager.load_pdr_file(pdr_path):
                    self.pdr_status.configure(text="Loaded", text_color="green")
                    logger.info(f"Successfully loaded ParentsDetailsReport.txt from {pdr_path}")
                else:
                    self.pdr_status.configure(text="Error loading file", text_color="red")
            else:
                # PDR not found, use alternative loading method
                logger.warning("ParentsDetailsReport.txt not found, using alternative loading method")
                self.pdr_status.configure(text="Using Models folder", text_color="orange")
                
                if self.data_manager.load_parents_from_models_folder():
                    logger.info("Successfully loaded parent data from Models folder")
                else:
                    logger.error("Failed to load parent data from Models folder")
                    self.pdr_status.configure(text="Loading failed", text_color="red")
                    return
            
            # Load cockpit parents after either method
            self.data_manager.load_cockpit_parents(ct_file)
            
            # Update current frame if needed
            self._update_current_frame()
                
        except Exception as e:
            self.pdr_status.configure(text="Error loading file", text_color="red")
            logger.error(f"Error loading ParentsDetailsReport.txt: {str(e)}")
            logger.error("Stack trace:", exc_info=True)

    def set_texture_paths(self, base_directory):
        self.data_manager.set_texture_paths(base_directory)

if __name__ == "__main__":
    try:
        # Create logs directory if it doesn't exist
        os.makedirs("logs", exist_ok=True)
        
        # Create assets directory if it doesn't exist
        os.makedirs("assets", exist_ok=True)
        
        app = BMSManager()
        app.mainloop()
    except Exception as e:
        logger.critical(f"Application crashed: {str(e)}")
        sys.exit(1) 