import os
import shutil
from tkinter import messagebox
import customtkinter as ctk
import yt_dlp

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

root = ctk.CTk()
root.title("Video Downloader")
root.geometry("520x420")
root.resizable(False, False)

url_label = ctk.CTkLabel(root, text="Video URL:")
url_label.pack(pady=8)

url_entry = ctk.CTkEntry(root, width=520)
url_entry.pack(pady=4)

format_type_frame = ctk.CTkFrame(root)
format_type_frame.pack(pady=6)

download_type_var = ctk.StringVar(value="video")
video_radio = ctk.CTkRadioButton(format_type_frame, text="Video", variable=download_type_var, value="video", command=lambda: update_quality_menu())
video_radio.grid(row=0, column=0, padx=8)
audio_radio = ctk.CTkRadioButton(format_type_frame, text="Audio", variable=download_type_var, value="audio", command=lambda: update_quality_menu())
audio_radio.grid(row=0, column=1, padx=8)

playlist_checkbox_var = ctk.BooleanVar(value=False)
playlist_checkbox = ctk.CTkCheckBox(format_type_frame, text="Playlist", variable=playlist_checkbox_var)
playlist_checkbox.grid(row=0, column=2, padx=8)

quality_label = ctk.CTkLabel(root, text="Choose available quality:")
quality_label.pack(pady=4)

quality_var = ctk.StringVar(value="Fetch formats first")
quality_menu = ctk.CTkOptionMenu(root, values=["Fetch formats first"], variable=quality_var)
quality_menu.set("Fetch formats first")
quality_menu.pack(pady=4)

status_label = ctk.CTkLabel(root, text="Click 'Fetch Formats' to see available video and audio options.", wraplength=500, anchor="w", justify=ctk.LEFT)
status_label.pack(pady=4)

formats_display = ctk.CTkTextbox(root, height=8, width=520)
formats_display.configure(state="disabled")
formats_display.pack(padx=10, pady=6)

button_frame = ctk.CTkFrame(root)
button_frame.pack(pady=8)

fetch_button = ctk.CTkButton(button_frame, text="Fetch Formats", command=lambda: fetch_formats())
fetch_button.grid(row=0, column=0, padx=12)

download_button = ctk.CTkButton(button_frame, text="Download", command=lambda: download_video())
download_button.grid(row=0, column=1, padx=12)

available_options = {
    "video": {},
    "audio": {}
}


def has_ffmpeg():
    return shutil.which("ffmpeg") is not None or shutil.which("ffmpeg.exe") is not None


def ensure_folder(target_folder):
    os.makedirs(target_folder, exist_ok=True)
    return target_folder


def update_quality_menu():
    current_type = download_type_var.get()
    options = available_options.get(current_type, {})

    if not options:
        quality_menu.configure(values=["Fetch formats first"])
        quality_menu.set("Fetch formats first")
        return

    labels = list(options.keys())
    quality_menu.configure(values=labels)
    quality_menu.set(labels[0])


def update_formats_display(video_lines, audio_lines):
    formats_display.configure(state="normal")
    formats_display.delete("1.0", ctk.END)
    formats_display.insert(ctk.END, "Available video formats:\n")
    if video_lines:
        formats_display.insert(ctk.END, "\n".join(video_lines) + "\n\n")
    else:
        formats_display.insert(ctk.END, "No video-only resolutions found.\n\n")

    formats_display.insert(ctk.END, "Available audio formats:\n")
    if audio_lines:
        formats_display.insert(ctk.END, "\n".join(audio_lines) + "\n")
    else:
        formats_display.insert(ctk.END, "No audio-only formats found.\n")

    formats_display.configure(state="disabled")


def fetch_formats():
    url = url_entry.get().strip()
    if not url:
        messagebox.showwarning("Missing URL", "Please enter a video URL before fetching formats.")
        return

    is_playlist = playlist_checkbox_var.get()
    if is_playlist:
        status_label.configure(text="Playlist mode enabled. Click 'Download' to download all videos.")
        formats_display.configure(state="normal")
        formats_display.delete("1.0", ctk.END)
        formats_display.insert(ctk.END, "Playlist mode: All videos will be downloaded in the selected quality.\n")
        formats_display.configure(state="disabled")
        return

    status_label.configure(text="Fetching available formats...")
    root.update_idletasks()

    try:
        with yt_dlp.YoutubeDL({}) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as exc:
        status_label.configure(text="Failed to fetch formats. Check the URL or your internet connection.")
        messagebox.showerror("Fetch Error", f"Could not fetch formats:\n{exc}")
        return

    video_heights = {}
    audio_bitrates = {}

    for fmt in info.get("formats", []):
        vcodec = fmt.get("vcodec")
        acodec = fmt.get("acodec")
        height = fmt.get("height")
        abr = fmt.get("abr") or fmt.get("tbr")
        ext = fmt.get("ext")

        if vcodec != "none" and acodec == "none":
            if height:
                label = f"{height}p | {ext} | {fmt.get('fps', '?')}fps"
                video_heights[height] = label
        elif vcodec != "none" and acodec != "none":
            if height:
                label = f"{height}p (combined) | {ext} | {fmt.get('fps', '?')}fps"
                video_heights[height] = label
        elif vcodec == "none" and acodec != "none":
            if abr:
                bitrate = int(round(abr))
                label = f"{bitrate} kbps | {ext} | {acodec}"
                audio_bitrates[bitrate] = label

    video_lines = [video_heights[h] for h in sorted(video_heights.keys(), reverse=True)]
    audio_lines = [audio_bitrates[b] for b in sorted(audio_bitrates.keys(), reverse=True)]

    available_options["video"].clear()
    available_options["audio"].clear()

    for height in sorted(video_heights.keys(), reverse=True):
        label = video_heights[height]
        available_options["video"][label] = f"bestvideo[height<={height}]+bestaudio/best[height<={height}]"

    for bitrate in sorted(audio_bitrates.keys(), reverse=True):
        label = audio_bitrates[bitrate]
        available_options["audio"][label] = f"bestaudio[abr<={bitrate}]/bestaudio"

    if not available_options["video"] and not available_options["audio"]:
        status_label.configure(text="No downloadable audio or video formats found.")
        return

    update_formats_display(video_lines, audio_lines)
    update_quality_menu()

    status_text = "Formats loaded. "
    status_text += "FFmpeg detected. " if has_ffmpeg() else "FFmpeg not detected. Audio extraction to MP3 will be skipped. "
    status_label.configure(text=status_text + "Select a quality and download.")


def download_video():
    url = url_entry.get().strip()
    if not url:
        messagebox.showwarning("Missing URL", "Please enter a video URL before downloading.")
        return

    is_playlist = playlist_checkbox_var.get()
    selected_type = download_type_var.get()

    if not is_playlist:
        selected_quality = quality_var.get()
        if selected_quality in ("Fetch formats first", "", None) or selected_quality not in available_options.get(selected_type, {}):
            messagebox.showwarning("Select Quality", "Please fetch formats and select a quality option before downloading.")
            return

    target_folder = os.path.expanduser("~/Videos" if selected_type == "video" else "~/Music")
    ensure_folder(target_folder)

    if is_playlist:
        ydl_opts = {
            "outtmpl": os.path.join(target_folder, "%(playlist_title)s", "%(title)s.%(ext)s"),
        }
        if selected_type == "video":
            ydl_opts["format"] = "bestvideo+bestaudio/best"
        else:
            ydl_opts["format"] = "bestaudio/best"
    else:
        ydl_opts = {
            "outtmpl": os.path.join(target_folder, "%(title)s.%(ext)s"),
            "format": available_options[selected_type][quality_var.get()],
            "noplaylist": True
        }

    if selected_type == "audio" and has_ffmpeg():
        ydl_opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192"
        }]

    status_label.configure(text="Downloading... This may take a few moments.")
    root.update_idletasks()

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        status_label.configure(text=f"Download complete. Saved to {target_folder}")
        messagebox.showinfo("Download Finished", f"The download completed successfully.\nSaved to {target_folder}")
    except Exception as exc:
        status_label.configure(text="Download failed. See error message.")
        messagebox.showerror("Download Error", f"Could not download the file:\n{exc}")


root.mainloop()
