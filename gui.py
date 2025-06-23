import tkinter as tk
from tkinter import ttk, filedialog
from functools import partial

class BinCreatorGUI:
    def __init__(self, root, on_create_bins_callback):
        self.root = root
        self.on_create_bins = on_create_bins_callback
        self.setup_ui()
    
    def setup_ui(self):
        """Configure all GUI elements"""
        self.root.title("DaVinci Resolve Media Bin Creator")
        self.root.geometry("800x600")
        
        # Configure styles
        self.style = ttk.Style()
        self.style.configure("TFrame", padding=10)
        self.style.configure("TButton", padding=5)
        self.style.configure("TLabel", padding=5)
        
        # Create main container
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Set up all UI components
        self._setup_folder_selection()
        self._setup_info_section()
        self._setup_results_display()
        self._setup_action_buttons()
        self._setup_status_bar()
    
    def _setup_folder_selection(self):
        """Set up folder selection widgets"""
        ttk.Label(self.main_frame, text="Root Folder:").pack(anchor=tk.W)
        
        self.folder_entry = ttk.Entry(self.main_frame)
        self.folder_entry.pack(fill=tk.X, pady=5)
        
        browse_btn = ttk.Button(
            self.main_frame, 
            text="Browse...", 
            command=self._browse_folder
        )
        browse_btn.pack(pady=5)
    
    def _setup_info_section(self):
            """Set up information labels"""
            info_text = [
                "Folder Structure Requirements:",
                "1. Root folder should contain date in name (e.g., '2024-11-22 Project')",
                "2. Subfolders should be named like: 'PAX - Location - Load'",
                "Example: 'Alexii - Russ - L2'"
            ]
            for text in info_text:
                ttk.Label(
                    self.main_frame, 
                    text=text, 
                    font=('Arial', 10, 'bold') if text.startswith("Folder") else None
                ).pack(anchor=tk.W)
        
    def _setup_results_display(self):
        """Set up the results text widget"""
        ttk.Label(self.main_frame, text="Processing Log:").pack(anchor=tk.W)
        
        self.result_text = tk.Text(
            self.main_frame, 
            wrap=tk.WORD, 
            bg='#f0f0f0', 
            padx=5, 
            pady=5
        )
        self.result_text.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(self.result_text)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.result_text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.result_text.yview)

    def _setup_action_buttons(self):
        """Set up action buttons"""
        btn_frame = ttk.Frame(self.main_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(
            btn_frame,
            text="Create Media Bins",
            command=self._on_create_bins
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            btn_frame,
            text="Clear Log",
            command=self.clear_log
        ).pack(side=tk.LEFT, padx=5)

    def _setup_status_bar(self):
        """Set up status bar"""
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        
        ttk.Label(
            self.main_frame, 
            textvariable=self.status_var,
            relief=tk.SUNKEN, 
            anchor=tk.W
        ).pack(fill=tk.X, pady=(10,0))

    def update_status(self, message):
        """Update status bar message"""
        self.status_var.set(message)    
    def get_folder_path(self):
        """Public method to get the current folder path"""
        return self.folder_entry.get()

    def add_log_message(self, message):
        """Public method to add messages to the log"""
        self.result_text.insert(tk.END, message)
        self.result_text.see(tk.END)
        self.result_text.update_idletasks()

    def clear_log(self):
        """Public method to clear the log"""
        self.result_text.delete(1.0, tk.END)

    def _browse_folder(self):
        """Handle folder browsing"""
        if folder_path := filedialog.askdirectory():
            self.folder_entry.delete(0, tk.END)
            self.folder_entry.insert(0, folder_path)

    def _on_create_bins(self):
        """Handle create bins button click"""
        self.on_create_bins(self.get_folder_path(), self.add_log_message)
        