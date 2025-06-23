import tkinter as tk
from gui import BinCreatorGUI
from main import BinCreatorApp

def main():
    root = tk.Tk()
    app = BinCreatorApp()
    
    # Create GUI with callback to app's method
    gui = BinCreatorGUI(root, app.create_media_bins)
    
    root.mainloop()

if __name__ == "__main__":
    main()