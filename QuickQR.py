# pip install customtkinter qrcode pillow opencv-python pyzbar reportlab

import customtkinter as ctk
import qrcode
from qrcode.image.svg import SvgImage
from PIL import Image, ImageTk
from tkinter import messagebox, filedialog
import cv2
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
import io


# ====================== APP SETTINGS =======================
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.title("⚡QuickQR")
app.geometry("440x610")
app.resizable(False, False)

# ====================== STATE (no temp files!) =======================
entry_var = ctk.StringVar()
current_qr_img = None      # PIL.Image for PNG/PDF
current_qr_svg = None      # qrcode SVG object for true .svg export
qr_generated = False       # export guard

# ====================== Custom Wi-Fi Dialog =======================
def wifi_name_dialog():
    dialog = ctk.CTkToplevel(app)
    dialog.title("Wi-Fi Name")
    dialog.geometry("320x180")
    dialog.resizable(False, False)
    dialog.grab_set()

    dialog.update_idletasks()
    x = app.winfo_x() + (app.winfo_width() // 2 - 160)
    y = app.winfo_y() + (app.winfo_height() // 2 - 90)
    dialog.geometry(f"+{x}+{y}")

    ctk.CTkLabel(dialog, text="Enter your Wi-Fi Network Name (SSID):", font=("Segoe UI", 13, "bold")).pack(pady=(15, 8))
    wifi_entry = ctk.CTkEntry(dialog, placeholder_text="e.g., MyHomeNetwork", width=230, height=30)
    wifi_entry.pack(pady=8)

    result = {"ssid": None}
    def on_ok():
        result["ssid"] = wifi_entry.get().strip()
        dialog.destroy()
    def on_cancel():
        result["ssid"] = None
        dialog.destroy()

    btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    btn_frame.pack(pady=8)
    ctk.CTkButton(btn_frame, text="OK", width=80, command=on_ok).grid(row=0, column=0, padx=8)
    ctk.CTkButton(btn_frame, text="Cancel", width=80, fg_color="#B22222", command=on_cancel).grid(row=0, column=1, padx=8)

    wifi_entry.focus_set()
    dialog.wait_window()
    return result["ssid"]

# ====================== RESET ON INPUT CHANGES =======================
def clear_on_dropdown_change(choice=None):
    """Clear input and invalidate previous QR when type changes."""
    global qr_generated, current_qr_img, current_qr_svg
    entry.delete(0, "end")
    qr_generated = False
    current_qr_img = None
    current_qr_svg = None
    qr_label.configure(image=None, text="Your QR code will appear here")

def on_user_typing(event=None):
    """Invalidate previous QR when user edits text."""
    global qr_generated
    qr_generated = False

# ====================== QR GENERATION =======================
def create_qr():
    global current_qr_img, current_qr_svg, qr_generated

    data = entry.get().strip()
    qr_type = qr_type_dropdown.get()

    if not data:
        messagebox.showwarning("Warning", "Please write something first!")
        return

    # Build QR payload
    if qr_type == "Text":
        qr_data = data
    elif qr_type == "URL / Link":
        qr_data = data if data.startswith(("http://", "https://")) else "https://" + data
    elif qr_type == "Email":
        qr_data = f"mailto:{data}"
    elif qr_type == "Phone":
        qr_data = f"tel:{data}"
    elif qr_type == "WhatsApp":
        number = data.replace("+", "").replace(" ", "")
        if not number.startswith("880"):
            number = "880" + number[-10:]
        qr_data = f"https://wa.me/{number}"
    elif qr_type == "Wi-Fi":
        password = data
        ssid = wifi_name_dialog()
        if not ssid:
            messagebox.showinfo("Cancelled", "Wi-Fi name not entered.")
            return
        qr_data = f"WIFI:T:WPA;S:{ssid};P:{password};;"
    else:
        qr_data = data

    # Generate PNG (PIL) image in memory
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(qr_data)
    qr.make(fit=True)
    pil_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")  # ensure RGB
    current_qr_img = pil_img

    # Also generate true SVG in memory (for .svg export)
    current_qr_svg = qrcode.make(qr_data, image_factory=SvgImage)

    # Show resized preview in UI
    preview = pil_img.resize((280, 280))
    preview_photo = ImageTk.PhotoImage(preview)
    qr_label.configure(image=preview_photo, text="")
    qr_label.image = preview_photo

    qr_generated = True  # now safe to export

# ====================== SCAN QR =======================
def scan_qr():
    cap = cv2.VideoCapture(0)
    detector = cv2.QRCodeDetector()
    messagebox.showinfo("QR Scanner", "Press 'Q' to stop scanning.")

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        data, bbox, _ = detector.detectAndDecode(frame)
        if bbox is not None:
            # Draw green box
            pts = bbox.astype(int).reshape(-1, 2)
            for i in range(len(pts)):
                cv2.line(frame, tuple(pts[i]), tuple(pts[(i + 1) % len(pts)]), (0, 255, 0), 2)

            if data:
                messagebox.showinfo("Scanned QR", f"QR Data:\n{data}")
                break

        cv2.imshow("QR Scanner - Press Q to Quit", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


# ====================== EXPORT (uses in-memory images) =======================
def export_options():
    if not qr_generated or current_qr_img is None:
        messagebox.showwarning("Warning", "No QR code generated yet!")
        return

    export_win = ctk.CTkToplevel(app)
    export_win.title("Export QR")
    export_win.geometry("300x250")
    export_win.resizable(False, False)
    export_win.grab_set()

    ctk.CTkLabel(export_win, text="Export Your QR", font=("Segoe UI", 15, "bold")).pack(pady=10)

    def save_image():
        path = filedialog.asksaveasfilename(defaultextension=".png", title="Save QR Image")
        if path:
            current_qr_img.save(path, format="PNG")
            messagebox.showinfo("Saved", f"QR Image saved at:\n{path}")
            export_win.destroy()

    def export_pdf_centered():
        path = filedialog.asksaveasfilename(defaultextension=".pdf", title="Save as PDF")
        if path:
            width, height = A4
            c = canvas.Canvas(path, pagesize=A4)
            # draw PIL image centered via ImageReader
            reader = ImageReader(current_qr_img)
            qr_width, qr_height = 300, 300
            x_center, y_center = (width - qr_width) / 2, (height - qr_height) / 2
            c.drawImage(reader, x_center, y_center, width=qr_width, height=qr_height, mask='auto')
            c.save()
            messagebox.showinfo("Saved", f"QR PDF saved at:\n{path}")
            export_win.destroy()

    def export_svg():
        if current_qr_svg is None:
            messagebox.showwarning("Warning", "SVG not available.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".svg", title="Save as SVG")
        if path:
            # current_qr_svg has a .save method
            current_qr_svg.save(path)
            messagebox.showinfo("Saved", f"QR SVG saved at:\n{path}")
            export_win.destroy()

    ctk.CTkButton(export_win, text="Export as PNG", command=save_image, width=180).pack(pady=5)
    ctk.CTkButton(export_win, text="Export as PDF", command=export_pdf_centered, width=180).pack(pady=5)
    ctk.CTkButton(export_win, text="Export as SVG", command=export_svg, width=180).pack(pady=5)

# ====================== GUI DESIGN =======================
main = ctk.CTkFrame(app, corner_radius=15)
main.pack(padx=15, pady=15, fill="both", expand=True)

title = ctk.CTkLabel(main, text="⚡QuickQR — Scan the Future.", font=("Segoe UI", 20, "bold"))
title.pack(pady=(15, 10))

qr_type_dropdown = ctk.CTkOptionMenu(
    main,
    values=["Text", "URL / Link", "Email", "Phone", "WhatsApp", "Wi-Fi"],
    width=300,
    font=("Segoe UI", 13),
    command=clear_on_dropdown_change
)
qr_type_dropdown.pack(pady=8)
qr_type_dropdown.set("Text")

entry = ctk.CTkEntry(main, textvariable=entry_var, width=300, height=36, font=("Segoe UI", 12))
entry.pack(pady=8)
entry.bind("<KeyRelease>", on_user_typing)

buttons = ctk.CTkFrame(main, fg_color="transparent")
buttons.pack(pady=8)

ctk.CTkButton(buttons, text="Generate", command=create_qr, width=100).grid(row=0, column=0, padx=6)
ctk.CTkButton(buttons, text="Scan QR", command=scan_qr, width=110).grid(row=0, column=1, padx=6)
ctk.CTkButton(buttons, text="Export", command=export_options, width=130).grid(row=0, column=2, padx=6)

qr_label = ctk.CTkLabel(main, text="Your QR code will appear here", width=300, height=300, corner_radius=10, fg_color="#2B2B2B")
qr_label.pack(pady=15, expand=True)

footer = ctk.CTkLabel(app, text="Developed by Badhan Goswamy", font=("Segoe UI", 10))
footer.pack(side="bottom", pady=(0, 10))

exit_btn = ctk.CTkButton(app, text="Exit", command=app.quit, fg_color="#B22222", width=90)
exit_btn.place(relx=1.0, rely=1.0, x=-12, y=-12, anchor="se")

app.mainloop()
