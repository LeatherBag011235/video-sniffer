import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk, filedialog, messagebox

from sniffer_class.downloader import download_ui


class VideoSnifferApp:
    def __init__(self, root: tk.Tk):
        self.root: tk.Tk = root
        self.root.iconbitmap("movie.ico")
        self.root.title("VideoSniffer")
        self.root.geometry("400x350")
        self.selected_folder = Path()
        self.create_widgets()

    def create_widgets(self):
        """Add all widgets to the main window."""
        tk.Label(self.root, text="VideoSniffer", font=("Arial", 18)).pack(pady=10)

        self.folder_label: tk.Label = tk.Label(self.root, text="No folder selected", font=("Arial", 10), fg="grey")
        self.folder_label.pack(pady=5)

        select_button: tk.Button = tk.Button(self.root, text="Select Folder", command=self.select_folder)
        select_button.pack(pady=5)

        tk.Label(self.root, text="Filename:", font=("Arial", 10)).pack(pady=(10, 0))
        self.filename_entry: tk.Entry = tk.Entry(self.root, font=("Arial", 12), width=30)
        self.filename_entry.pack(pady=5)

        download_button: tk.Button = tk.Button(
            self.root, text="SEARCH MOVIES", font=("Arial", 14), width=20, height=2,
            command=self.initiate_download
        )
        download_button.pack(pady=20)

        self.progress: ttk.Progressbar = ttk.Progressbar(self.root, length=300, mode='determinate')
        self.progress.pack(pady=10)

    def select_folder(self) -> None:
        """Opens prompt to select folder"""
        save_dir: str = filedialog.askdirectory()
        if save_dir:
            self.selected_folder = Path(save_dir)
            self.folder_label.config(text=f"Folder: {save_dir}")

    def initiate_download(self) -> None:
        filename = self.filename_entry.get().strip()

        if not self.selected_folder:
            messagebox.showerror("Error", "Please select a folder first.")
            return
        if not filename:
            messagebox.showerror("Error", "Please enter a filename.")
            return

        # Run run_download in its own thread not to block main UI
        threading.Thread(
            target=self.run_download,
            args=(self.selected_folder, f"{filename}.ts"),
            daemon=True
        ).start()

    def run_download(self, save_dir: Path, output_filename: str) -> None:
        self.progress['value'] = 0
        download_ui(
            save_dir=save_dir,
            output_filename=output_filename,
            meta={"progress": self.progress, "root": self.root}
        )
        messagebox.showinfo("Success", f"Download completed for {output_filename}")
