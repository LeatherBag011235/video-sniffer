import tkinter as tk
from tkinter import filedialog


def main():
    import tkinter as tk
    from tkinter import filedialog

    # Initialize main window
    root = tk.Tk()
    root.title("VideoSniffer")
    root.geometry("400x300")

    # Label at the top
    label = tk.Label(root, text="VideoSniffer", font=("Arial", 18))
    label.pack(pady=10)

    # Function to open folder dialog
    def select_folder():
        folderpath = filedialog.askdirectory()
        if folderpath:
            folder_label.config(text=f"Folder: {folderpath}")

    # Button to select folder
    select_button = tk.Button(root, text="Select Folder", command=select_folder)
    select_button.pack(pady=5)

    # Label to show selected folder
    folder_label = tk.Label(root, text="No folder selected", font=("Arial", 10), fg="grey")
    folder_label.pack(pady=5)

    # Entry for filename
    filename_label = tk.Label(root, text="Filename:", font=("Arial", 10))
    filename_label.pack(pady=(10, 0))
    filename_entry = tk.Entry(root, font=("Arial", 12), width=30)
    filename_entry.pack(pady=5)

    # Large Download button
    download_button = tk.Button(
        root, text="SEARCH MOVIE", font=("Arial", 14), width=20, height=2,
        command=partial()
    )
    download_button.pack(pady=20)

    # Run the app
    root.mainloop()


if __name__ == "__main__":
    main()
