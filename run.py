import tkinter as tk
from gui import BinCreatorGUI
from main import BinCreatorApp

def main():
    root = tk.Tk()
    
    # Create the app first, then pass it to the GUI
    app = BinCreatorApp()  # We'll set the GUI reference later
    gui = BinCreatorGUI(root, app)
    app.gui = gui  # Complete the circular reference
    
    root.mainloop()

if __name__ == "__main__":
    main()