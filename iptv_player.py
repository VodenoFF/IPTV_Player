import customtkinter as ctk
import requests
import json
from tkinter import messagebox
import logging
from typing import Dict, List
import os
from PIL import Image
from io import BytesIO
import threading
import sys
from concurrent.futures import ThreadPoolExecutor
from queue import Queue, Empty
import time
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Set MPV library path before importing mpv
MPV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib')
if sys.platform == 'win32':
    os.environ["PATH"] = MPV_PATH + os.pathsep + os.environ["PATH"]
    try:
        os.add_dll_directory(MPV_PATH)
    except Exception as e:
        logging.error(f"Error adding DLL directory: {str(e)}")

# Now import mpv after PATH is set
try:
    import mpv
except Exception as e:
    logging.error(f"Error importing MPV: {str(e)}")
    mpv = None

# Set up logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(levelname)s - %(message)s',
                   handlers=[
                       logging.StreamHandler()  # Only log to console
                   ])

class ImageCache:
    def __init__(self, max_size=100):
        self.cache = {}
        self.max_size = max_size
        self.access_times = {}
        self.lock = threading.Lock()
        
    def get(self, key):
        with self.lock:
            if key in self.cache:
                self.access_times[key] = time.time()
                return self.cache[key]
            return None
            
    def put(self, key, value):
        with self.lock:
            if len(self.cache) >= self.max_size:
                # Remove least recently used items
                oldest = sorted(self.access_times.items(), key=lambda x: x[1])[0][0]
                del self.cache[oldest]
                del self.access_times[oldest]
            
            self.cache[key] = value
            self.access_times[key] = time.time()
            
    def clear(self):
        with self.lock:
            self.cache.clear()
            self.access_times.clear()

class BatchedUIUpdater:
    def __init__(self, window, batch_size=10, update_interval=50):
        self.window = window
        self.batch_size = batch_size
        self.update_interval = update_interval
        self.update_queue = Queue()
        self.is_running = True
        self.update_thread = threading.Thread(target=self._process_updates, daemon=True)
        self.update_thread.start()
        
    def queue_update(self, update_func):
        self.update_queue.put(update_func)
        
    def _process_updates(self):
        while self.is_running:
            updates = []
            try:
                # Get first update
                updates.append(self.update_queue.get(timeout=0.1))
                
                # Try to get more updates up to batch size
                for _ in range(self.batch_size - 1):
                    try:
                        updates.append(self.update_queue.get_nowait())
                    except Empty:
                        break
                        
                if updates:
                    # Combine updates into a single operation
                    def batch_update():
                        for update in updates:
                            try:
                                update()
                            except Exception as e:
                                logging.error(f"Error in batched update: {str(e)}")
                    
                    self.window.after(0, batch_update)
                    time.sleep(self.update_interval / 1000)  # Convert to seconds
                    
            except Empty:
                time.sleep(0.1)  # Prevent busy waiting
            except Exception as e:
                logging.error(f"Error processing batched updates: {str(e)}")
                
    def shutdown(self):
        self.is_running = False
        if self.update_thread.is_alive():
            self.update_thread.join(timeout=1.0)

class ChannelWidgetPool:
    def __init__(self, parent):
        self.parent = parent
        self.available_widgets = []
        self.active_widgets = {}
        self.pool_size = 20  # Initial pool size
        
    def get_widget(self):
        """Get a widget from the pool or create a new one"""
        if not self.available_widgets:
            self._create_widgets(max(5, self.pool_size // 2))
            
        widget = self.available_widgets.pop()
        self.active_widgets[id(widget)] = widget
        return widget
        
    def return_widget(self, widget):
        """Return a widget to the pool"""
        widget_id = id(widget)
        if widget_id in self.active_widgets:
            del self.active_widgets[widget_id]
            widget.grid_remove()  # Hide but keep the widget
            self.available_widgets.append(widget)
            
    def _create_widgets(self, count):
        """Create new widgets for the pool"""
        for _ in range(count):
            # Create main channel frame
            channel_frame = ctk.CTkFrame(
                self.parent,
                fg_color=("gray90", "gray20"),
                corner_radius=10,
                border_width=1,
                border_color=("gray80", "gray30")
            )
            channel_frame.grid_columnconfigure(1, weight=1)
            
            # Content frame
            content_frame = ctk.CTkFrame(
                channel_frame,
                fg_color="transparent"
            )
            content_frame.grid(row=0, column=0, sticky="ew", padx=8, pady=8)
            content_frame.grid_columnconfigure(1, weight=1)
            
            # Icon frame
            icon_frame = ctk.CTkFrame(
                content_frame,
                fg_color=("gray85", "gray25"),
                corner_radius=8,
                width=40,
                height=40
            )
            icon_frame.grid(row=0, column=0, padx=(0, 10))
            icon_frame.grid_propagate(False)
            
            # Placeholder icon
            placeholder = ctk.CTkLabel(
                icon_frame,
                text="📺",
                font=("Helvetica", 16),
                text_color=("gray60", "gray60")
            )
            placeholder.place(relx=0.5, rely=0.5, anchor="center")
            
            # Channel name label
            name_label = ctk.CTkLabel(
                content_frame,
                text="",
                font=("Helvetica", 12),
                anchor="w",
                text_color=("gray20", "gray90")
            )
            name_label.grid(row=0, column=1, sticky="w")
            
            # Store references
            channel_frame.content_frame = content_frame
            channel_frame.icon_frame = icon_frame
            channel_frame.placeholder = placeholder
            channel_frame.name_label = name_label
            
            self.available_widgets.append(channel_frame)

    def clear_all(self):
        """Hide all active widgets"""
        for widget in list(self.active_widgets.values()):
            self.return_widget(widget)

class ChannelList:
    def __init__(self, parent, width=240):
        self.parent = parent
        self.width = width
        self.channels = []
        self.item_height = 40
        self.hover_index = -1
        self.selected_index = -1
        self.scroll_offset = 0
        self.on_channel_click = None
        self.last_render_time = 0
        self.render_buffer = 10  # Number of items to render above/below viewport
        self.is_scrolling = False
        self.scroll_timer = None
        
        # Create main container
        self.container = ctk.CTkFrame(
            parent,
            fg_color=("gray95", "gray10"),
            corner_radius=0
        )
        self.container.grid(row=0, column=0, sticky="nsew")
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure(0, weight=1)
        
        # Create canvas for custom rendering
        self.canvas = ctk.CTkCanvas(
            self.container,
            bg="#1a1a1a",
            highlightthickness=0,
            borderwidth=0
        )
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        # Create scrollbar
        self.scrollbar = ctk.CTkScrollbar(
            self.container,
            command=self.canvas.yview,
            button_color=("#404040", "#404040"),
            button_hover_color=("#4a4a4a", "#4a4a4a"),
            width=8
        )
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Configure canvas scrolling
        self.canvas.configure(yscrollcommand=self.on_scroll)
        
        # Bind events
        self.canvas.bind("<Configure>", self._on_configure)
        self.canvas.bind("<Motion>", self._on_motion)
        self.canvas.bind("<Leave>", self._on_leave)
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        
        # Create image cache
        self.image_cache = {}
        self.rendered_items = set()
        
    def on_scroll(self, *args):
        """Handle scroll events with debouncing"""
        self.scrollbar.set(*args)
        self.is_scrolling = True
        
        # Cancel previous timer if exists
        if self.scroll_timer:
            self.parent.after_cancel(self.scroll_timer)
        
        # Schedule new render
        self.scroll_timer = self.parent.after(50, self.handle_scroll_end)
        
        # Render immediately with larger buffer during scrolling
        self.render(buffer_size=15)
        
    def handle_scroll_end(self):
        """Handle end of scrolling"""
        self.is_scrolling = False
        self.scroll_timer = None
        self.render(buffer_size=self.render_buffer)
        
    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling"""
        if self.canvas.winfo_height() < self.canvas.bbox("all")[3]:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            
    def render(self, buffer_size=None):
        """Render the channel list with buffering"""
        if not self.channels:
            return
            
        current_time = time.time()
        if current_time - self.last_render_time < 0.016:  # Limit to ~60fps
            return
            
        self.last_render_time = current_time
        buffer_size = buffer_size or self.render_buffer
        
        try:
            # Get visible range
            visible_top = max(0, int(self.canvas.yview()[0] * len(self.channels)))
            visible_bottom = min(len(self.channels), int(self.canvas.yview()[1] * len(self.channels)) + 1)
            
            # Calculate buffer range
            start_idx = max(0, visible_top - buffer_size)
            end_idx = min(len(self.channels), visible_bottom + buffer_size)
            
            # Get currently visible items
            visible_items = set(range(start_idx, end_idx))
            
            # Remove items that are no longer visible
            items_to_remove = self.rendered_items - visible_items
            if items_to_remove:
                self.canvas.delete(*[f"item_{idx}" for idx in items_to_remove])
                self.rendered_items -= items_to_remove
            
            # Render new visible items
            items_to_render = visible_items - self.rendered_items
            for idx in items_to_render:
                self._render_channel(idx)
                self.rendered_items.add(idx)
                
        except Exception as e:
            logging.error(f"Error in render: {str(e)}")
            
    def _render_channel(self, index):
        """Render a single channel item with tags"""
        if index >= len(self.channels):
            return
            
        channel = self.channels[index]
        y = index * self.item_height
        
        # Create tag for this item
        item_tag = f"item_{index}"
        
        # Background
        bg_color = "#2d7cd6" if index == self.selected_index else \
                  "#333333" if index == self.hover_index else "#1a1a1a"
        
        # Draw background
        self.canvas.create_rectangle(
            4, y + 2,
            self.width - 4, y + self.item_height - 2,
            fill=bg_color,
            outline="",
            tags=(item_tag, "bg")
        )
        
        # Channel name
        text_color = "#ffffff" if index in (self.hover_index, self.selected_index) else "#cccccc"
        self.canvas.create_text(
            45, y + self.item_height//2,
            text=channel['name'],
            fill=text_color,
            anchor="w",
            font=("Segoe UI", 11),
            tags=(item_tag, "text")
        )
        
        # Icon background
        icon_size = 28
        icon_x = 8
        icon_y = y + (self.item_height - icon_size) // 2
        
        self.canvas.create_rectangle(
            icon_x, icon_y,
            icon_x + icon_size, icon_y + icon_size,
            fill="#2b2b2b",
            outline="#333333",
            width=1,
            tags=(item_tag, "icon_bg")
        )
        
        # Load icon if available and not scrolling fast
        if channel.get('stream_icon') and not self.is_scrolling:
            if channel['stream_icon'] not in self.image_cache:
                self._load_icon(channel['stream_icon'], index, item_tag)
            elif self.image_cache[channel['stream_icon']]:
                self.canvas.create_image(
                    icon_x + icon_size//2,
                    icon_y + icon_size//2,
                    image=self.image_cache[channel['stream_icon']],
                    tags=(item_tag, "icon")
                )
                
    def _load_icon(self, url, index, item_tag):
        """Load channel icon with delayed rendering"""
        def on_icon_loaded(icon):
            if icon and not self.is_scrolling:
                self.image_cache[url] = icon
                if index in self.rendered_items:
                    self._render_channel(index)
        
        if hasattr(self.parent, 'icon_load_queue'):
            self.parent.icon_load_queue.put((url, on_icon_loaded))

    def set_channels(self, channels):
        """Set the list of channels to display"""
        self.channels = channels
        self.scroll_offset = 0
        self.hover_index = -1
        self.selected_index = -1
        self._update_scroll_region()
        self.render()
        
    def _update_scroll_region(self):
        """Update the canvas scroll region"""
        total_height = len(self.channels) * self.item_height
        self.canvas.configure(scrollregion=(0, 0, self.width, total_height))
        
    def _on_configure(self, event):
        """Handle canvas resize"""
        self.width = event.width
        self.render()
        
    def _on_motion(self, event):
        """Handle mouse motion for hover effects"""
        y = self.canvas.canvasy(event.y)  # Convert to canvas coordinates
        index = int(y // self.item_height)
        
        if 0 <= index < len(self.channels) and index != self.hover_index:
            self.hover_index = index
            self.render()
            
    def _on_leave(self, event):
        """Handle mouse leave"""
        if self.hover_index != -1:
            self.hover_index = -1
            self.render()
            
    def _on_click(self, event):
        """Handle channel selection"""
        y = self.canvas.canvasy(event.y)
        index = int(y // self.item_height)
        
        if 0 <= index < len(self.channels):
            self.selected_index = index
            if self.on_channel_click:
                self.on_channel_click(self.channels[index])
            self.render()

class IPTVPlayer:
    def __init__(self):
        # Initialize encryption key
        self.init_encryption()
        
        self.window = ctk.CTk()
        self.window.title("IPTV Player")
        self.window.geometry("300x350")  # Smaller window size
        self.window.resizable(False, False)
        
        # Configure the grid
        self.window.grid_columnconfigure(0, weight=1)
        self.window.grid_rowconfigure(0, weight=1)
        
        # Setup data directory in AppData
        self.app_data_dir = os.path.join(os.getenv('APPDATA') or os.path.expanduser('~'), 'IPTV_Player')
        os.makedirs(self.app_data_dir, exist_ok=True)
        
        # Load saved credentials and settings
        self.credentials_file = os.path.join(self.app_data_dir, 'credentials.json')
        self.settings_file = os.path.join(self.app_data_dir, 'settings.json')
        self.key_file = os.path.join(self.app_data_dir, '.key')
        
        self.load_credentials()
        self.load_settings()
        
        # Initialize volume state
        self.last_volume = self.saved_volume
        self.is_muted = False
        
        # Initialize data structures
        self.categories: Dict[str, Dict] = {}
        self.stream_icons: Dict[str, ctk.CTkImage] = {}
        
        # Initialize MPV player
        self.player = None
        
        # Controls visibility timer
        self.hide_controls_timer = None
        self.controls_visible = False
        
        # Fullscreen state
        self.is_fullscreen = False
        self.window.bind("<Escape>", self.exit_fullscreen)
        
        # Initialize thread pool and queues
        self.thread_pool = ThreadPoolExecutor(max_workers=8)  # Increased workers for parallel image loading
        self.ui_update_queue = Queue()
        self.icon_load_queue = Queue()
        
        # Cache for failed icon URLs to prevent repeated attempts
        self.failed_icons = set()
        
        # Start UI update thread
        self.ui_update_thread = threading.Thread(target=self.process_ui_updates, daemon=True)
        self.ui_update_thread.start()
        
        # Start multiple icon loading threads for parallel processing
        self.icon_load_threads = []
        for _ in range(4):  # Create 4 icon loading threads
            thread = threading.Thread(target=self.process_icon_loads, daemon=True)
            thread.start()
            self.icon_load_threads.append(thread)
        
        # Flag to track if loading is complete
        self.loading_complete = threading.Event()
        
        # Create login frame
        self.create_login_frame()
        
        # Add after other initializations
        self.channel_pool = None  # Will be initialized when channels frame is created
        
        # Add after other initializations
        self.image_cache = ImageCache(max_size=100)
        self.ui_updater = None  # Will be initialized after window creation
        
    def init_encryption(self):
        """Initialize encryption key"""
        try:
            self.key_file = os.path.join(os.getenv('APPDATA') or os.path.expanduser('~'), 'IPTV_Player', '.key')
            os.makedirs(os.path.dirname(self.key_file), exist_ok=True)
            
            if os.path.exists(self.key_file):
                with open(self.key_file, 'rb') as f:
                    self.key = f.read()
            else:
                # Generate a new key
                salt = os.urandom(16)
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=100000,
                )
                self.key = base64.urlsafe_b64encode(kdf.derive(os.urandom(32)))
                # Save the key
                with open(self.key_file, 'wb') as f:
                    f.write(self.key)
            
            self.cipher_suite = Fernet(self.key)
        except Exception as e:
            logging.error(f"Error initializing encryption: {str(e)}")
            self.cipher_suite = None

    def encrypt_password(self, password: str) -> str:
        """Encrypt password using Fernet"""
        try:
            if self.cipher_suite:
                return self.cipher_suite.encrypt(password.encode()).decode()
            return password
        except Exception as e:
            logging.error(f"Error encrypting password: {str(e)}")
            return password

    def decrypt_password(self, encrypted_password: str) -> str:
        """Decrypt password using Fernet"""
        try:
            if self.cipher_suite:
                return self.cipher_suite.decrypt(encrypted_password.encode()).decode()
            return encrypted_password
        except Exception as e:
            logging.error(f"Error decrypting password: {str(e)}")
            return encrypted_password

    def load_credentials(self):
        try:
            if os.path.exists(self.credentials_file):
                with open(self.credentials_file, 'r') as f:
                    creds = json.load(f)
                    self.saved_username = creds.get('username', '')
                    encrypted_password = creds.get('encrypted_password', '')
                    self.saved_password = self.decrypt_password(encrypted_password) if encrypted_password else ''
            else:
                self.saved_username = ''
                self.saved_password = ''
        except Exception as e:
            logging.error(f"Error loading credentials: {str(e)}")
            self.saved_username = ''
            self.saved_password = ''

    def save_credentials(self, username, password):
        """Save credentials with encrypted password"""
        try:
            encrypted_password = self.encrypt_password(password)
            with open(self.credentials_file, 'w') as f:
                json.dump({
                    'username': username,
                    'encrypted_password': encrypted_password
                }, f)
        except Exception as e:
            logging.error(f"Error saving credentials: {str(e)}")

    def load_settings(self):
        """Load saved settings"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                    self.saved_volume = float(settings.get('volume', 100))
            else:
                self.saved_volume = 100
        except Exception as e:
            logging.error(f"Error loading settings: {str(e)}")
            self.saved_volume = 100

    def save_settings(self):
        """Save current settings"""
        try:
            settings = {
                'volume': self.last_volume
            }
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f)
        except Exception as e:
            logging.error(f"Error saving settings: {str(e)}")

    def create_login_frame(self):
        # Center container frame
        center_frame = ctk.CTkFrame(self.window, fg_color="transparent")
        center_frame.place(relx=0.5, rely=0.5, anchor="center")
        
        # Login frame with shadow effect
        self.login_frame = ctk.CTkFrame(
            center_frame,
            corner_radius=15,
            fg_color=("gray95", "gray10"),
            border_width=1,
            border_color=("gray80", "gray20")
        )
        self.login_frame.grid(row=0, column=0, padx=20, pady=20)
        
        # Logo/Title container
        title_frame = ctk.CTkFrame(self.login_frame, fg_color="transparent")
        title_frame.grid(row=0, column=0, padx=30, pady=(30, 20), sticky="ew")
        
        # Title with icon
        title_label = ctk.CTkLabel(
            title_frame,
            text="IPTV Player",
            font=("Helvetica", 24, "bold"),
            text_color=("#1f538d", "#2d7cd6")
        )
        title_label.grid(row=0, column=0, sticky="ew")
        
        # Subtitle
        subtitle_label = ctk.CTkLabel(
            title_frame,
            text="Sign in to continue",
            font=("Helvetica", 12),
            text_color=("gray50", "gray70")
        )
        subtitle_label.grid(row=1, column=0, pady=(5, 0))
        
        # Username entry with icon
        username_frame = ctk.CTkFrame(self.login_frame, fg_color="transparent")
        username_frame.grid(row=1, column=0, padx=30, pady=(20, 10), sticky="ew")
        
        username_icon = ctk.CTkLabel(
            username_frame,
            text="👤",
            font=("Helvetica", 14),
            width=20
        )
        username_icon.grid(row=0, column=0, padx=(0, 10))
        
        self.username_entry = ctk.CTkEntry(
            username_frame,
            placeholder_text="Username",
            width=250,
            height=40,
            corner_radius=8,
            border_width=1,
            border_color=("gray70", "gray30")
        )
        self.username_entry.grid(row=0, column=1, sticky="ew")
        self.username_entry.insert(0, self.saved_username)
        
        # Password entry with icon
        password_frame = ctk.CTkFrame(self.login_frame, fg_color="transparent")
        password_frame.grid(row=2, column=0, padx=30, pady=(0, 10), sticky="ew")
        
        password_icon = ctk.CTkLabel(
            password_frame,
            text="🔒",
            font=("Helvetica", 14),
            width=20
        )
        password_icon.grid(row=0, column=0, padx=(0, 10))
        
        self.password_entry = ctk.CTkEntry(
            password_frame,
            placeholder_text="Password",
            show="●",
            width=250,
            height=40,
            corner_radius=8,
            border_width=1,
            border_color=("gray70", "gray30")
        )
        self.password_entry.grid(row=0, column=1, sticky="ew")
        self.password_entry.insert(0, self.saved_password)
        
        # Remember me checkbox
        self.remember_var = ctk.BooleanVar(value=bool(self.saved_username))
        self.remember_checkbox = ctk.CTkCheckBox(
            self.login_frame,
            text="Remember me",
            variable=self.remember_var,
            font=("Helvetica", 12),
            corner_radius=6,
            border_width=2,
            hover_color=("#1a4c7c", "#265d8d"),
            fg_color=("#1f538d", "#2d7cd6"),
            text_color=("gray60", "gray80")
        )
        self.remember_checkbox.grid(row=3, column=0, padx=30, pady=(5, 20), sticky="w")
        
        # Login button with gradient effect
        login_button = ctk.CTkButton(
            self.login_frame,
            text="Sign In",
            command=self.login,
            width=250,
            height=40,
            corner_radius=8,
            font=("Helvetica", 14, "bold"),
            fg_color=("#1f538d", "#2d7cd6"),
            hover_color=("#1a4c7c", "#265d8d"),
            border_width=0
        )
        login_button.grid(row=4, column=0, padx=30, pady=(0, 30))
        
        # Bind enter key to login
        self.window.bind("<Return>", lambda e: self.login())
        
        # Add hover effects
        for entry in [self.username_entry, self.password_entry]:
            entry.bind("<Enter>", lambda e, widget=entry: self.on_entry_hover(widget, True))
            entry.bind("<Leave>", lambda e, widget=entry: self.on_entry_hover(widget, False))
            
        # Add paste functionality
        def paste_to_entry(event):
            widget = event.widget
            try:
                widget.delete("sel.first", "sel.last")
            except:
                pass
            widget.insert("insert", self.window.clipboard_get())
            return "break"
            
        # Bind Ctrl+V to both entry fields
        self.username_entry.bind("<Control-v>", paste_to_entry)
        self.password_entry.bind("<Control-v>", paste_to_entry)

    def on_entry_hover(self, widget, entering):
        """Handle hover effect for entry widgets"""
        if entering:
            widget.configure(border_color=("#1f538d", "#2d7cd6"))
        else:
            widget.configure(border_color=("gray70", "gray30"))

    def create_loading_screen(self):
        # Remove login frame
        self.login_frame.destroy()
        
        # Create loading frame with modern style
        self.loading_frame = ctk.CTkFrame(
            self.window,
            corner_radius=15,
            fg_color=("gray95", "gray10"),
            border_width=1,
            border_color=("gray80", "gray20")
        )
        self.loading_frame.place(relx=0.5, rely=0.5, anchor="center")
        
        # Loading animation container
        animation_frame = ctk.CTkFrame(self.loading_frame, fg_color="transparent")
        animation_frame.grid(row=0, column=0, padx=40, pady=(40, 20))
        
        # Title with brand color
        title_label = ctk.CTkLabel(
            animation_frame,
            text="IPTV Player",
            font=("Helvetica", 24, "bold"),
            text_color=("#1f538d", "#2d7cd6")
        )
        title_label.grid(row=0, column=0, pady=(0, 20))
        
        # Modern progress bar
        self.progress = ctk.CTkProgressBar(
            animation_frame,
            mode="indeterminate",
            width=250,
            height=4,
            corner_radius=2,
            progress_color=("#1f538d", "#2d7cd6"),
            fg_color=("gray85", "gray25")
        )
        self.progress.grid(row=1, column=0, pady=(0, 15))
        self.progress.start()
        
        # Status label with modern font
        self.status_label = ctk.CTkLabel(
            animation_frame,
            text="Connecting to server...",
            font=("Helvetica", 12),
            text_color=("gray60", "gray70")
        )
        self.status_label.grid(row=2, column=0, pady=(0, 40))

    def update_loading_status(self, status):
        """Update the loading status text"""
        if hasattr(self, 'status_label'):
            self.status_label.configure(text=status)

    def process_ui_updates(self):
        """Process UI updates from background threads"""
        while True:
            try:
                # Get the next UI update task
                task = self.ui_update_queue.get()
                if task is None:  # Shutdown signal
                    break
                    
                # Execute the UI update on the main thread
                self.window.after(0, task)
                
                # Mark task as done
                self.ui_update_queue.task_done()
            except Exception as e:
                logging.error(f"Error processing UI update: {str(e)}")

    def process_icon_loads(self):
        """Process icon loading tasks with improved error handling"""
        while True:
            try:
                # Get the next icon loading task
                task = self.icon_load_queue.get()
                if task is None:  # Shutdown signal
                    break
                
                icon_url, callback = task
                
                # Skip if URL previously failed
                if icon_url in self.failed_icons:
                    self.icon_load_queue.task_done()
                    continue
                
                # Load icon
                icon = self.load_channel_icon(icon_url)
                
                # Schedule callback on main thread if icon loaded
                if icon and callback:
                    self.ui_update_queue.put(callback(icon))
                
                # Mark task as done
                self.icon_load_queue.task_done()
                
            except Exception as e:
                logging.error(f"Error in icon loading thread: {str(e)}")
                self.icon_load_queue.task_done()

    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        
        if not username or not password:
            messagebox.showerror("Error", "Please enter both username and password")
            return
            
        # Store password for API requests
        self.api_password = password
            
        # Show loading screen
        self.create_loading_screen()
        
        # Start login process in background thread
        self.thread_pool.submit(self.login_process, username, password)

    def login_process(self, username, password):
        """Handle login process in background thread"""
        try:
            self.ui_update_queue.put(lambda: self.update_loading_status("Authenticating..."))
            
            # API endpoint with original password
            api_url = f"http://152.53.86.6/player_api.php?username={username}&password={password}"
            response = requests.get(api_url)
            data = response.json()
            
            if data.get("user_info", {}).get("auth") == 1:
                # Store credentials
                self.username = username
                self.api_password = password  # Store password for API requests
                
                # Save credentials if remember me is checked
                if hasattr(self, 'remember_var') and self.remember_var.get():
                    self.save_credentials(username, password)
                elif os.path.exists(self.credentials_file):
                    os.remove(self.credentials_file)
                
                # Load categories and streams in parallel
                self.ui_update_queue.put(lambda: self.update_loading_status("Loading channels and categories..."))
                
                categories_future = self.thread_pool.submit(self.get_live_categories)
                streams_future = self.thread_pool.submit(self.get_live_streams)
                
                categories_data = categories_future.result()
                streams_data = streams_future.result()
                
                if categories_data and streams_data:
                    # Organize data
                    self.organize_streams_by_category(categories_data, streams_data)
                    
                    # Update UI on main thread
                    self.ui_update_queue.put(lambda: self.finish_login())
                else:
                    self.ui_update_queue.put(self.show_login_error)
            else:
                self.ui_update_queue.put(lambda: self.show_login_error("Invalid credentials"))
                
        except Exception as e:
            error_msg = str(e)
            logging.error(f"Login error: {error_msg}")
            self.ui_update_queue.put(lambda: self.show_login_error(error_msg))

    def finish_login(self):
        """Complete login process on main thread"""
        # Prepare main window
        self.window.geometry("1280x720")
        self.window.resizable(True, True)
        
        # Remove loading screen and create main interface
        self.loading_frame.destroy()
        self.create_main_interface()
        
        # Signal that loading is complete
        self.loading_complete.set()

    def show_login_error(self, message="Authentication failed"):
        """Show login error and return to login screen"""
        self.loading_frame.destroy()
        self.create_login_frame()
        messagebox.showerror("Error", message)

    def get_live_categories(self):
        try:
            api_url = f"http://152.53.86.6/player_api.php?username={self.username}&password={self.api_password}&action=get_live_categories"
            response = requests.get(api_url)
            categories_data = response.json()
            
            # Log the received data
            logging.info("Retrieved categories data:")
            logging.info(json.dumps(categories_data, indent=2))
            
            return categories_data
        except Exception as e:
            logging.error(f"Error fetching categories: {str(e)}")
            messagebox.showerror("Error", "Failed to fetch categories")
            return None
            
    def get_live_streams(self):
        try:
            api_url = f"http://152.53.86.6/player_api.php?username={self.username}&password={self.api_password}&action=get_live_streams"
            response = requests.get(api_url)
            streams_data = response.json()
            
            # Log the received data
            logging.info("Retrieved live streams data:")
            logging.info(json.dumps(streams_data, indent=2))
            
            return streams_data
        except Exception as e:
            logging.error(f"Error fetching live streams: {str(e)}")
            messagebox.showerror("Error", "Failed to fetch channels")
            return None
    
    def organize_streams_by_category(self, categories_data, streams_data):
        # Initialize categories dictionary with full category info
        self.categories = {}
        for cat in categories_data:
            self.categories[cat['category_name']] = {
                'category_id': cat['category_id'],
                'parent_id': cat.get('parent_id', '0'),
                'channels': []
            }
        
        # Create a mapping of category_id to category_name for easier lookup
        category_id_to_name = {
            cat['category_id']: cat['category_name'] 
            for cat in categories_data
        }
        
        # Sort streams by num
        streams_data.sort(key=lambda x: int(x.get('num', 0)))
        
        # Organize streams into categories
        for stream in streams_data:
            stream_info = {
                'name': stream.get('name', 'Unknown'),
                'stream_icon': stream.get('stream_icon', ''),
                'stream_id': stream.get('stream_id', ''),
                'epg_channel_id': stream.get('epg_channel_id', ''),
                'num': stream.get('num', 0)
            }
            
            # Check if channel has category_ids
            category_ids = stream.get('category_ids', [])
            if isinstance(category_ids, list) and category_ids:
                # Add channel to each category it belongs to
                for cat_id in category_ids:
                    cat_id_str = str(cat_id)
                    if cat_id_str in category_id_to_name:
                        cat_name = category_id_to_name[cat_id_str]
                        self.categories[cat_name]['channels'].append(stream_info)
            else:
                # Fallback to category_name if no category_ids
                category_name = stream.get('category_name', 'Uncategorized')
                if category_name in self.categories:
                    self.categories[category_name]['channels'].append(stream_info)
                else:
                    if 'Uncategorized' not in self.categories:
                        self.categories['Uncategorized'] = {
                            'category_id': '0',
                            'parent_id': '0',
                            'channels': []
                        }
                    self.categories['Uncategorized']['channels'].append(stream_info)
        
        logging.info("Organized streams by category with additional info:")
        logging.info(json.dumps(self.categories, indent=2))
            
    def open_player_window(self, user_data):
        self.login_frame.destroy()
        
        # Fetch categories and streams data
        categories_data = self.get_live_categories()
        streams_data = self.get_live_streams()
        
        if categories_data and streams_data:
            # Organize the data
            self.organize_streams_by_category(categories_data, streams_data)
            
            # Create the main interface
            self.create_main_interface()
    
    def create_main_interface(self):
        # Create main container with modern styling
        self.main_frame = ctk.CTkFrame(
            self.window,
            fg_color="transparent"
        )
        self.main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.main_frame.grid_columnconfigure(0, weight=0)  # Left panel column
        self.main_frame.grid_columnconfigure(1, weight=3)  # Player column
        self.main_frame.grid_rowconfigure(0, weight=1)
        
        # Left panel with modern design
        left_panel = ctk.CTkFrame(
            self.main_frame,
            corner_radius=15,
            fg_color=("gray95", "gray10"),
            border_width=1,
            border_color=("gray80", "gray20")
        )
        left_panel.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        left_panel.grid_rowconfigure(1, weight=0)
        left_panel.grid_rowconfigure(2, weight=1)
        
        # Create the channels frame first
        self.channels_frame = ctk.CTkScrollableFrame(
            left_panel,
            fg_color="transparent",
            corner_radius=0,
            width=240,
            scrollbar_button_color=("gray75", "gray30"),
            scrollbar_button_hover_color=("gray65", "gray35")
        )
        self.channels_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        
        # Initialize the channel pool
        self.channel_pool = ChannelWidgetPool(self.channels_frame)
        
        # Initialize UI updater
        self.ui_updater = BatchedUIUpdater(self.window)

        # Categories section with header
        categories_header = ctk.CTkLabel(
            left_panel,
            text="Categories",
            font=("Helvetica", 14, "bold"),
            text_color=("gray20", "gray90")
        )
        categories_header.grid(row=0, column=0, padx=15, pady=(10, 5), sticky="w")
        
        # Categories scrollable frame with reduced height
        categories_scroll = ctk.CTkScrollableFrame(
            left_panel,
            fg_color="transparent",
            corner_radius=0,
            height=120,
            width=240,  # Increased width to account for scrollbar
            scrollbar_button_color=("gray75", "gray30"),
            scrollbar_button_hover_color=("gray65", "gray35")
        )
        categories_scroll.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        
        # Style category buttons with smaller height and gray theme
        for i, (category_name, category_info) in enumerate(self.categories.items()):
            btn = ctk.CTkButton(
                categories_scroll,
                text=category_name,
                command=lambda cat=category_name: self.show_category_channels(cat),
                height=28,
                corner_radius=6,
                fg_color=("gray90", "gray20"),
                text_color=("gray20", "gray90"),
                hover_color=("gray80", "gray25"),
                border_width=1,
                border_color=("gray75", "gray30"),
                font=("Helvetica", 11)
            )
            btn.grid(row=i, column=0, padx=5, pady=2, sticky="ew")
        
        # Right panel (player) with modern design
        self.player_frame = ctk.CTkFrame(
            self.main_frame,
            corner_radius=15,
            fg_color=("gray95", "gray10"),
            border_width=1,
            border_color=("gray80", "gray20")
        )
        self.player_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self.player_frame.grid_columnconfigure(0, weight=1)
        self.player_frame.grid_rowconfigure(0, weight=1)
        
        # Video container with modern styling
        self.video_container = ctk.CTkFrame(
            self.player_frame,
            fg_color="black",
            corner_radius=12
        )
        self.video_container.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        
        # Video widget (full container)
        self.video_widget = ctk.CTkFrame(self.video_container, fg_color="black")
        self.video_widget.place(relx=0, rely=0, relwidth=1, relheight=1)
        
        # Create controls panel that overlays the video with modern design
        self.controls_panel = ctk.CTkFrame(
            self.video_container,
            fg_color=("gray95", "gray10"),
            corner_radius=0,
            border_width=1,
            border_color=("gray80", "gray20")
        )
        # Place it at the bottom with no gap
        self.controls_panel.place(relx=0, rely=1, anchor="sw", relwidth=1)
        
        # Left controls container
        left_controls = ctk.CTkFrame(self.controls_panel, fg_color="transparent")
        left_controls.grid(row=0, column=0, padx=8, pady=6, sticky="w")
        
        # Right controls container
        right_controls = ctk.CTkFrame(self.controls_panel, fg_color="transparent")
        right_controls.grid(row=0, column=1, padx=8, pady=6, sticky="e")
        
        # Configure grid
        self.controls_panel.grid_columnconfigure(1, weight=1)  # Give space between left and right controls

        # Control buttons with modern design matching the app theme
        button_color = ("gray90", "gray20")
        hover_color = ("gray80", "gray25")
        text_color = ("gray20", "gray90")
        button_height = 32

        # Previous channel button (left)
        self.prev_button = ctk.CTkButton(
            left_controls,
            text="⏮",
            width=40,
            height=button_height,
            fg_color=button_color,
            hover_color=hover_color,
            text_color=text_color,
            corner_radius=6,
            font=("Helvetica", 14),
            command=self.previous_channel
        )
        self.prev_button.grid(row=0, column=0, padx=4)

        # Play/Pause button (left)
        self.play_button = ctk.CTkButton(
            left_controls,
            text="⏸",
            width=40,
            height=button_height,
            fg_color=button_color,
            hover_color=hover_color,
            text_color=text_color,
            corner_radius=6,
            font=("Helvetica", 14),
            command=self.toggle_pause
        )
        self.play_button.grid(row=0, column=1, padx=4)

        # Next channel button (left)
        self.next_button = ctk.CTkButton(
            left_controls,
            text="⏭",
            width=40,
            height=button_height,
            fg_color=button_color,
            hover_color=hover_color,
            text_color=text_color,
            corner_radius=6,
            font=("Helvetica", 14),
            command=self.next_channel
        )
        self.next_button.grid(row=0, column=2, padx=4)

        # Volume control frame (right)
        volume_frame = ctk.CTkFrame(right_controls, fg_color="transparent")
        volume_frame.grid(row=0, column=0, padx=(0, 4))

        # Volume button
        self.volume_button = ctk.CTkButton(
            volume_frame,
            text="🔊",
            width=40,
            height=button_height,
            fg_color=button_color,
            hover_color=hover_color,
            text_color=text_color,
            corner_radius=6,
            font=("Helvetica", 14),
            command=self.toggle_mute
        )
        self.volume_button.grid(row=0, column=0, padx=(0, 4))

        # Volume slider with modern style matching theme and saved volume
        self.volume_slider = ctk.CTkSlider(
            volume_frame,
            from_=0,
            to=100,
            number_of_steps=100,
            command=self.set_volume,
            height=12,
            width=100,
            button_color=("gray85", "gray30"),
            button_hover_color=("gray75", "gray35"),
            progress_color=("#1f538d", "#2d7cd6"),
            fg_color=("gray90", "gray20")
        )
        self.volume_slider.grid(row=0, column=1, padx=4)
        self.volume_slider.set(self.saved_volume)  # Set saved volume

        # Fullscreen button (right)
        self.fullscreen_button = ctk.CTkButton(
            right_controls,
            text="⛶",
            width=40,
            height=button_height,
            fg_color=button_color,
            hover_color=hover_color,
            text_color=text_color,
            corner_radius=6,
            font=("Helvetica", 14),
            command=self.toggle_fullscreen
        )
        self.fullscreen_button.grid(row=0, column=1, padx=4)

        # Bind mouse events to both video widget and container
        for widget in [self.video_widget, self.video_container, self.controls_panel]:
            widget.bind("<Motion>", self.on_mouse_motion)
            widget.bind("<Enter>", self.on_mouse_motion)
            widget.bind("<Leave>", self.on_mouse_leave)
        
        # Also bind to all control panel children
        for child in self.controls_panel.winfo_children():
            child.bind("<Motion>", self.on_mouse_motion)
            child.bind("<Enter>", self.on_mouse_motion)
            
        # Show controls initially (will be hidden by timer)
        self.show_controls()
        
        try:
            if mpv is None:
                raise Exception("MPV library not available")

            # Initialize MPV with optimized quality settings
            self.player = mpv.MPV(
                # Basic settings
                wid=str(int(self.video_widget.winfo_id())),
                log_handler=print,
                input_default_bindings=True,
                input_vo_keyboard=True,
                osd_level=0,
                keep_open='always',
                
                # Video output settings
                vo='gpu',
                gpu_api='auto',
                hwdec='auto',
                profile='gpu-hq',
                
                # Video quality settings
                scale='ewa_lanczossharp',
                cscale='ewa_lanczossharp',
                dscale='mitchell',
                linear_downscaling=True,
                sigmoid_upscaling=True,
                
                # Performance settings
                video_sync='display-resample',
                interpolation=True,
                tscale='oversample',
                
                # Network and cache settings
                cache=True,
                cache_secs=30,
                demuxer_max_bytes='512M',
                demuxer_max_back_bytes='128M',
                network_timeout=30,
                stream_buffer_size='64M',
                
                # Error handling
                hr_seek='yes',
                force_seekable=True,
                
                # Stream options
                stream_lavf_o='fflags=+nobuffer+fastseek+flush_packets,analyzeduration=2000000,probesize=2000000,reconnect=1,reconnect_streamed=1,reconnect_delay_max=5'
            )
            
            # Set additional properties for quality
            self.player['vf'] = 'format=yuv420p'  # Ensure compatible color format
            self.player['video-sync-max-factor'] = 2
            self.player['video-timing-offset'] = 0
            
            # Register event callbacks
            @self.player.property_observer('core-idle')
            def handle_player_event(_name, value):
                if value:
                    logging.info("Player is idle")
                else:
                    logging.info("Player is active")
            
            @self.player.event_callback('start-file')
            def handle_start(_):
                logging.info("Starting playback")
                # Set optimal playback settings
                self.player['speed'] = 1.0
                self.player['video-sync'] = 'display-resample'
                self.player['interpolation'] = True
            
            @self.player.event_callback('end-file')
            def handle_end(event):
                try:
                    # Properly access event properties
                    if hasattr(event, 'reason') and event.reason == 'error':
                        self.ui_update_queue.put(
                            lambda: messagebox.showwarning("Playback Error", 
                            "Stream error occurred. Please try again.")
                        )
                    logging.info(f"Playback ended: {getattr(event, 'reason', 'unknown')}")
                except Exception as e:
                    logging.error(f"Error handling end-file event: {str(e)}")
            
            logging.info("MPV player initialized successfully with optimized settings")
            
            # Store current channel info
            self.current_category = None
            self.current_channel_index = -1
            
        except Exception as e:
            logging.error(f"Error initializing MPV player: {str(e)}")
            messagebox.showerror("Error", 
                "Failed to initialize video player. Please ensure MPV is properly installed.\n"
                f"Error: {str(e)}")
            self.player = None
        
        # Show first category's channels after everything is initialized
        if self.categories:
            first_category = next(iter(self.categories.keys()))
            self.show_category_channels(first_category)

    def on_mouse_motion(self, event=None):
        """Handle mouse motion to show/hide controls"""
        # Get mouse position relative to video container
        mouse_y = self.window.winfo_pointery() - self.video_container.winfo_rooty()
        container_height = self.video_container.winfo_height()
        
        # Check if mouse is over volume controls
        mouse_over_controls = False
        if self.controls_visible:
            control_x = self.window.winfo_pointerx() - self.window.winfo_rootx()
            control_y = self.window.winfo_pointery() - self.window.winfo_rooty()
            
            try:
                widget_under_mouse = self.window.winfo_containing(
                    self.window.winfo_pointerx(),
                    self.window.winfo_pointery()
                )
                # Check if mouse is over volume slider or volume button
                mouse_over_controls = (
                    widget_under_mouse in [self.volume_slider, self.volume_button] or
                    (hasattr(widget_under_mouse, 'winfo_parent') and 
                     widget_under_mouse.winfo_parent() and 
                     self.window.nametowidget(widget_under_mouse.winfo_parent()) in [self.volume_slider, self.volume_button])
                )
            except:
                pass
        
        # Show controls if mouse is near bottom or over volume controls
        if mouse_y > container_height - 40 or mouse_over_controls:
            if self.hide_controls_timer:
                self.window.after_cancel(self.hide_controls_timer)
                self.hide_controls_timer = None
            
            # Show controls if not visible
            if not self.controls_visible:
                self.show_controls()
        else:
            # Hide controls if mouse moves away and not over volume controls
            if self.controls_visible:
                if self.hide_controls_timer:
                    self.window.after_cancel(self.hide_controls_timer)
                self.hide_controls_timer = self.window.after(500, self.hide_controls)
        
        # Get mouse position relative to window for left panel
        mouse_x = self.window.winfo_pointerx() - self.window.winfo_rootx()
        
        # Show left panel in fullscreen when mouse is on the left edge
        if self.is_fullscreen and mouse_x < 10:
            for widget in self.main_frame.winfo_children():
                if widget != self.player_frame:
                    widget.grid()
        # Hide left panel in fullscreen when mouse moves away
        elif self.is_fullscreen and mouse_x > 250:
            for widget in self.main_frame.winfo_children():
                if widget != self.player_frame:
                    widget.grid_remove()

    def on_mouse_leave(self, event):
        """Handle mouse leaving the control area"""
        # Get the widget currently under the mouse
        widget_under_mouse = event.widget.winfo_containing(
            event.x_root, 
            event.y_root
        )
        
        # Check if mouse is over volume controls
        mouse_over_controls = (
            widget_under_mouse in [self.volume_slider, self.volume_button] or
            (hasattr(widget_under_mouse, 'winfo_parent') and 
             widget_under_mouse.winfo_parent() and 
             self.window.nametowidget(widget_under_mouse.winfo_parent()) in [self.volume_slider, self.volume_button])
        )
        
        # Don't hide if mouse is still over video container, controls, or volume controls
        if widget_under_mouse in [self.video_container, self.controls_panel] or \
           mouse_over_controls or \
           (hasattr(widget_under_mouse, 'winfo_parent') and 
            widget_under_mouse.winfo_parent() and 
            self.window.nametowidget(widget_under_mouse.winfo_parent()) == self.controls_panel):
            return
        
        # Hide controls after a short delay if not over volume controls
        if not mouse_over_controls:
            if self.hide_controls_timer:
                self.window.after_cancel(self.hide_controls_timer)
            self.hide_controls_timer = self.window.after(800, self.hide_controls)

    def show_controls(self):
        """Show the control panel with animation"""
        if not self.controls_visible:
            # Cancel any existing animation
            if hasattr(self, '_control_animation'):
                self.window.after_cancel(self._control_animation)

            # Initialize animation
            self._current_y = 1.1 if not hasattr(self, '_current_y') else self._current_y
            self._target_y = 1.0  # Move to bottom edge
            
            def animate():
                # Smooth animation
                self._current_y += (self._target_y - self._current_y) * 0.3
                
                # Update position
                self.controls_panel.place(
                    relx=0,
                    rely=self._current_y,
                    anchor="sw",
                    relwidth=1
                )
                
                # Continue animation if not close enough to target
                if abs(self._target_y - self._current_y) > 0.001:
                    self._control_animation = self.window.after(16, animate)
                else:
                    self._current_y = self._target_y
                    self.controls_panel.place(
                        relx=0,
                        rely=self._target_y,
                        anchor="sw",
                        relwidth=1
                    )

            # Start animation
            animate()
            self.controls_visible = True

    def hide_controls(self):
        """Hide the control panel with animation"""
        if self.controls_visible:
            # Cancel any existing animation
            if hasattr(self, '_control_animation'):
                self.window.after_cancel(self._control_animation)

            # Initialize animation
            self._current_y = 1.0 if not hasattr(self, '_current_y') else self._current_y
            self._target_y = 1.1
            
            def animate():
                # Smooth animation
                self._current_y += (self._target_y - self._current_y) * 0.3
                
                # Update position
                self.controls_panel.place(
                    relx=0,
                    rely=self._current_y,
                    anchor="sw",
                    relwidth=1
                )
                
                # Continue animation if not close enough to target
                if abs(self._target_y - self._current_y) > 0.001:
                    self._control_animation = self.window.after(16, animate)
                else:
                    self._current_y = self._target_y
                    self.controls_panel.place_forget()
                    self.controls_visible = False
                    self.hide_controls_timer = None

            # Start animation
            animate()

    def toggle_fullscreen(self):
        if not self.player:
            return
        
        self.is_fullscreen = not self.is_fullscreen
        
        # Store current volume and mute states
        current_volume = self.volume_slider.get()
        current_mute = self.is_muted
        
        if self.is_fullscreen:
            # Store current window position and size before going fullscreen
            self.before_fullscreen = {
                'geometry': self.window.geometry(),
                'x': self.window.winfo_x(),
                'y': self.window.winfo_y(),
                'width': self.window.winfo_width(),
                'height': self.window.winfo_height(),
                'volume': current_volume,
                'muted': current_mute
            }
            
            # Get current monitor
            x = self.window.winfo_x()
            y = self.window.winfo_y()
            width = self.window.winfo_width()
            height = self.window.winfo_height()
            
            # Calculate center point of the window
            center_x = x + width // 2
            center_y = y + height // 2
            
            # Get monitor info where the center of the window is
            monitor_info = self.window.winfo_containing(center_x, center_y).winfo_toplevel().winfo_geometry()
            mon_x, mon_y, mon_width, mon_height = map(int, monitor_info.replace('x', '+').split('+'))
            
            # Set window to fullscreen on the current monitor
            self.window.attributes('-fullscreen', True)
            self.window.geometry(f"{mon_width}x{mon_height}+{mon_x}+{mon_y}")
            self.fullscreen_button.configure(text="⛗")
            
            # Hide left panel
            for widget in self.main_frame.winfo_children():
                if widget != self.player_frame:
                    widget.grid_remove()
            
            # Remove all padding and margins
            self.main_frame.grid_configure(padx=0, pady=0)
            self.player_frame.grid_configure(padx=0, pady=0)
            self.video_container.grid_configure(padx=0, pady=0)
            
            # Ensure video container fills the entire space
            self.video_container.configure(corner_radius=0)
            self.player_frame.configure(corner_radius=0, border_width=0)
            
            # Adjust grid configuration for fullscreen
            self.main_frame.grid_columnconfigure(0, weight=0)  # Left panel column
            self.main_frame.grid_columnconfigure(1, weight=1)  # Player column
            
        else:
            # Exit fullscreen and restore previous position
            self.window.attributes('-fullscreen', False)
            if hasattr(self, 'before_fullscreen'):
                self.window.geometry(self.before_fullscreen['geometry'])
            
            self.fullscreen_button.configure(text="⛶")
            
            # Show left panel
            for widget in self.main_frame.winfo_children():
                widget.grid()
            
            # Restore padding and margins
            self.main_frame.grid_configure(padx=10, pady=10)
            self.player_frame.grid_configure(padx=5, pady=5)
            self.video_container.grid_configure(padx=8, pady=8)
            
            # Restore corner radius and border
            self.video_container.configure(corner_radius=12)
            self.player_frame.configure(corner_radius=15, border_width=1)
            
            # Restore grid configuration
            self.main_frame.grid_columnconfigure(0, weight=0)  # Left panel column
            self.main_frame.grid_columnconfigure(1, weight=3)  # Player column
            
            self.is_fullscreen = False
        
        # Restore volume and mute states
        if hasattr(self, 'before_fullscreen'):
            if current_mute:
                self.volume_slider.set(0)
                self.volume_button.configure(text="🔇")
            else:
                self.volume_slider.set(current_volume)
                if current_volume == 0:
                    self.volume_button.configure(text="🔇")
                elif current_volume < 50:
                    self.volume_button.configure(text="🔈")
                else:
                    self.volume_button.configure(text="🔊")
            
            # Ensure player state matches UI
            if self.player:
                self.player.mute = current_mute
                if not current_mute:
                    self.player.volume = current_volume

    def exit_fullscreen(self, event=None):
        if self.is_fullscreen:
            self.toggle_fullscreen()
        
    def toggle_pause(self):
        if not self.player:
            return
            
        self.player.cycle('pause')
        # Update button text
        self.play_button.configure(text="▶" if self.player.pause else "⏸")
        
    def toggle_mute(self):
        if not self.player:
            return
        
        if not self.is_muted:
            # Muting - store current volume
            self.last_volume = self.volume_slider.get()
            self.player.mute = True
            self.volume_slider.set(0)
            self.volume_button.configure(text="🔇")
            self.is_muted = True
        else:
            # Unmuting - restore last volume
            self.player.mute = False
            self.volume_slider.set(self.last_volume)
            self.set_volume(self.last_volume)
            self.volume_button.configure(text="🔊" if self.last_volume >= 50 else "🔈")
            self.is_muted = False

    def previous_channel(self):
        if not self.current_category or self.current_channel_index < 0:
            return
            
        channels = self.categories[self.current_category]['channels']
        self.current_channel_index = (self.current_channel_index - 1) % len(channels)
        self.play_channel(channels[self.current_channel_index])
        
    def next_channel(self):
        if not self.current_category or self.current_channel_index < 0:
            return
            
        channels = self.categories[self.current_category]['channels']
        self.current_channel_index = (self.current_channel_index + 1) % len(channels)
        self.play_channel(channels[self.current_channel_index])
        
    def play_channel(self, channel):
        try:
            if not self.player:
                messagebox.showerror("Error", 
                    "Video player is not initialized.\n"
                    "Please ensure MPV is properly installed and restart the application.")
                return
            
            # Update current channel info
            category_name = next((cat for cat, info in self.categories.items() 
                                if channel in info['channels']), None)
            if category_name:
                self.current_category = category_name
                self.current_channel_index = self.categories[category_name]['channels'].index(channel)
            
            # Construct stream URL with API password
            stream_url = f"http://152.53.86.6/live/{self.username}/{self.api_password}/{channel['stream_id']}.ts"
            
            try:
                # Stop current playback
                self.player.command('stop')
                self.player.command('playlist-clear')
                
                # Set stream options as a single string
                self.player.stream_lavf_o = 'fflags=+nobuffer+fastseek+flush_packets,analyzeduration=2000000,probesize=2000000,reconnect=1,reconnect_streamed=1,reconnect_delay_max=5'
                
                # Reset player state
                self.player.pause = False
                
                # Start playback
                self.player.play(stream_url)
                
                # Update window title
                self.window.title(f"IPTV Player - {channel['name']}")
                
                # Reset play/pause button
                self.play_button.configure(text="⏸")
                
                logging.info(f"Started playing channel: {channel['name']} (ID: {channel['stream_id']})")
                
            except Exception as e:
                logging.error(f"Error during playback start: {str(e)}")
                messagebox.showerror("Error", 
                    f"Failed to start playback: {str(e)}\n"
                    "Please try again or select a different channel.")
                
        except Exception as e:
            logging.error(f"Error in play_channel: {str(e)}")
            messagebox.showerror("Error", 
                f"An error occurred while trying to play the channel: {str(e)}")

    def load_channel_icon(self, icon_url):
        """Load channel icon with improved caching"""
        if not icon_url or not icon_url.startswith(('http://', 'https://')):
            return None
            
        # Check memory cache first
        cached_icon = self.image_cache.get(icon_url)
        if cached_icon:
            return cached_icon
            
        # Check if this URL previously failed
        if icon_url in self.failed_icons:
            return None
            
        try:
            # Download image with timeout and caching
            headers = {
                'User-Agent': 'Mozilla/5.0',
                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8'
            }
            
            # Use session for connection pooling
            with requests.Session() as session:
                response = session.get(
                    icon_url,
                    timeout=5,
                    headers=headers,
                    stream=True
                )
                response.raise_for_status()
                
                # Process image data
                img_data = BytesIO(response.content)
                with Image.open(img_data) as img:
                    # Convert and resize efficiently
                    if img.mode not in ('RGB', 'RGBA'):
                        img = img.convert('RGBA')
                    
                    # Keep aspect ratio with efficient resizing
                    width, height = img.size
                    aspect_ratio = width / height
                    if aspect_ratio > 1:
                        new_width, new_height = 40, int(40 / aspect_ratio)
                    else:
                        new_width, new_height = int(40 * aspect_ratio), 40
                    
                    # Use LANCZOS for better quality-performance trade-off
                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    
                    # Create and cache CTkImage
                    ctk_image = ctk.CTkImage(
                        light_image=img,
                        dark_image=img,
                        size=(new_width, new_height)
                    )
                    
                    self.image_cache.put(icon_url, ctk_image)
                    return ctk_image
                
        except Exception as e:
            logging.error(f"Error loading icon {icon_url}: {str(e)}")
            self.failed_icons.add(icon_url)
            return None

    def update_channel_icon(self, icon_frame, icon):
        """Update channel frame with loaded icon using batched updates"""
        if not icon_frame or not icon_frame.winfo_exists():
            return
        
        def update():
            try:
                if not icon_frame.winfo_exists():
                    return
                    
                # Remove old icon if exists
                if hasattr(icon_frame, 'icon_label'):
                    icon_frame.icon_label.destroy()
                    
                if icon:
                    # Create new icon label
                    icon_label = ctk.CTkLabel(
                        icon_frame,
                        text="",
                        image=icon
                    )
                    icon_label.place(relx=0.5, rely=0.5, anchor="center")
                    
                    # Store references
                    icon_frame.icon_label = icon_label
                    icon_frame.icon = icon
                    
                    # Hide placeholder
                    if hasattr(icon_frame, 'placeholder'):
                        icon_frame.placeholder.place_forget()
                    
            except Exception as e:
                logging.error(f"Error updating channel icon: {str(e)}")
        
        # Queue the update
        if hasattr(self, 'ui_updater') and self.ui_updater:
            self.ui_updater.queue_update(update)
        else:
            self.window.after(0, update)

    def show_category_channels(self, category_name):
        """Show channels for the selected category"""
        try:
            # Clear existing channels
            for widget in self.channels_frame.winfo_children():
                widget.destroy()
            
            category_info = self.categories[category_name]
            
            # Add category name header
            header = ctk.CTkLabel(
                self.channels_frame,
                text=category_name,
                font=("Helvetica", 14, "bold"),
                text_color=("gray20", "gray90")
            )
            header.grid(row=0, column=0, padx=5, pady=(5, 10), sticky="w")
            
            # Add channels for selected category
            for i, channel in enumerate(category_info['channels']):
                # Create channel frame with placeholder
                channel_frame = self.create_channel_frame(i+1, channel)
                if channel_frame and hasattr(channel_frame, 'icon_frame') and channel.get('stream_icon'):
                    icon_url = channel['stream_icon']
                    frame_ref = channel_frame.icon_frame
                    
                    def make_callback(frame):
                        def update_icon(icon):
                            try:
                                if frame and frame.winfo_exists():
                                    self.update_channel_icon(frame, icon)
                            except Exception as e:
                                logging.error(f"Error in icon callback: {str(e)}")
                        return update_icon
                    
                    self.icon_load_queue.put((
                        icon_url,
                        make_callback(frame_ref)
                    ))
                    
        except Exception as e:
            logging.error(f"Error showing category channels: {str(e)}")
            messagebox.showerror("Error", f"Failed to show channels: {str(e)}")

    def create_channel_frame(self, index, channel):
        """Create channel frame with modern design"""
        try:
            # Create main channel frame with modern styling
            channel_frame = ctk.CTkFrame(
                self.channels_frame,
                fg_color=("gray90", "gray20"),
                corner_radius=10,
                border_width=1,
                border_color=("gray80", "gray30")
            )
            channel_frame.grid(row=index, column=0, sticky="ew", padx=8, pady=4)
            channel_frame.grid_columnconfigure(0, weight=1)
            
            # Content frame
            content_frame = ctk.CTkFrame(
                channel_frame,
                fg_color="transparent"
            )
            content_frame.grid(row=0, column=0, sticky="ew", padx=8, pady=8)
            content_frame.grid_columnconfigure(1, weight=1)
            
            # Modern icon frame
            icon_frame = ctk.CTkFrame(
                content_frame,
                fg_color=("gray85", "gray25"),
                corner_radius=8,
                width=40,
                height=40
            )
            icon_frame.grid(row=0, column=0, padx=(0, 10))
            icon_frame.grid_propagate(False)
            
            # Placeholder
            placeholder = ctk.CTkLabel(
                icon_frame,
                text="📺",
                font=("Helvetica", 16),
                text_color=("gray60", "gray60")
            )
            placeholder.place(relx=0.5, rely=0.5, anchor="center")
            
            # Channel name
            name = ctk.CTkLabel(
                content_frame,
                text=channel['name'],
                font=("Helvetica", 12),
                anchor="w",
                text_color=("gray20", "gray90")
            )
            name.grid(row=0, column=1, sticky="w")
            
            # Store references
            channel_frame.channel_info = channel
            channel_frame.icon_frame = icon_frame
            channel_frame.placeholder = placeholder
            channel_frame.content_frame = content_frame
            channel_frame.name_label = name
            
            # Store references in icon frame
            icon_frame.channel_info = channel
            icon_frame.placeholder = placeholder
            icon_frame.channel_frame = channel_frame
            
            # Bind events
            def on_click(e, ch=channel):
                self.play_channel(ch)
                
            def on_hover(entering):
                if entering:
                    channel_frame.configure(
                        fg_color=("gray85", "gray25"),
                        border_color=("#1f538d", "#2d7cd6")
                    )
                else:
                    channel_frame.configure(
                        fg_color=("gray90", "gray20"),
                        border_color=("gray80", "gray30")
                    )
                
            for widget in [channel_frame, content_frame, name]:
                widget.bind("<Button-1>", on_click)
                widget.bind("<Enter>", lambda e: on_hover(True))
                widget.bind("<Leave>", lambda e: on_hover(False))
            
            return channel_frame
            
        except Exception as e:
            logging.error(f"Error creating channel frame: {str(e)}")
            return None

    def on_channel_hover(self, frame, entering):
        """Modern hover effect for channel frames"""
        if entering:
            frame.configure(
                fg_color=("gray85", "gray25"),
                border_color=("#1f538d", "#2d7cd6")
            )
        else:
            frame.configure(
                fg_color=("gray90", "gray20"),
                border_color=("gray80", "gray30")
            )
    
    def __del__(self):
        # Clean up threads
        if hasattr(self, 'ui_update_queue'):
            self.ui_update_queue.put(None)  # Signal thread to stop
        
        # Stop all icon loading threads
        if hasattr(self, 'icon_load_queue'):
            for _ in self.icon_load_threads:
                self.icon_load_queue.put(None)
        
        if hasattr(self, 'thread_pool'):
            self.thread_pool.shutdown(wait=False)
        
        # Clean up player
        if self.player:
            self.player.terminate()

        # Add cleanup for new components
        if hasattr(self, 'ui_updater'):
            self.ui_updater.shutdown()
        
        if hasattr(self, 'image_cache'):
            self.image_cache.clear()

    def run(self):
        self.window.mainloop()

    def set_volume(self, value):
        if not self.player:
            return
            
        value = float(value)
        self.player.volume = value
        
        # Update volume button icon based on volume level
        if value == 0:
            self.volume_button.configure(text="🔇")
            self.is_muted = True
        elif value < 50:
            self.volume_button.configure(text="🔈")
            self.is_muted = False
        else:
            self.volume_button.configure(text="🔊")
            self.is_muted = False
            
        # Store last volume if not muted and volume is greater than 0
        if not self.is_muted and value > 0:
            self.last_volume = value
            self.save_settings()
            
        # Ensure player mute state matches UI
        self.player.mute = self.is_muted

if __name__ == "__main__":
    # Set the default theme
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    
    app = IPTVPlayer()
    app.run() 