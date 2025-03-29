import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from download import download


class VideoSnifferApp:
    def __init__(self, root):
        self.root = root
        self.root.title("VideoSniffer")
        self.root.geometry("400x300")
        self.selected_folder: Path = Path()

        self.create_widgets()

    def create_widgets(self):
        tk.Label(self.root, text="VideoSniffer", font=("Arial", 18)).pack(pady=10)

        self.folder_label = tk.Label(self.root, text="No folder selected", font=("Arial", 10), fg="grey")
        self.folder_label.pack(pady=5)

        select_button = tk.Button(self.root, text="Select Folder", command=self.select_folder)
        select_button.pack(pady=5)

        tk.Label(self.root, text="Filename:", font=("Arial", 10)).pack(pady=(10, 0))
        self.filename_entry = tk.Entry(self.root, font=("Arial", 12), width=30)
        self.filename_entry.pack(pady=5)

        download_button = tk.Button(
            self.root, text="SEARCH MOVIES", font=("Arial", 14), width=20, height=2,
            command=self.initiate_download
        )
        download_button.pack(pady=20)

    def select_folder(self):
        save_dir: str = filedialog.askdirectory()
        if save_dir:
            self.selected_folder = Path(save_dir)
            self.folder_label.config(text=f"Folder: {save_dir}")

    def initiate_download(self):
        filename = self.filename_entry.get().strip()
        if not self.selected_folder:
            messagebox.showerror("Error", "Please select a folder first.")
            return
        if not filename:
            messagebox.showerror("Error", "Please enter a filename.")
            return

        output_filename = f"{filename}.ts"
        download(save_dir=self.selected_folder, output_filename=output_filename)
        messagebox.showinfo("Success", f"Download initiated for {output_filename}")


if __name__ == "__main__":
    root = tk.Tk()
    app = VideoSnifferApp(root)
    root.mainloop()
