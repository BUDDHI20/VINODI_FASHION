import os
import sys
import threading
import time
import zipfile
import shutil
import requests
import subprocess
import stat
import sqlite3
import psutil
import customtkinter as ctk
from tkinter import Tk, Label, ttk, messagebox
from PIL import Image, ImageTk


APP_TITLE = "Thisaru Fashion Updater"
MAIN_APP_EXE_NAME = "Thisaru_Fashion.exe"


import socket

def get_updater_single_instance_lock():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        s.bind(("127.0.0.1", 54321)) 
        return s
    except socket.error:
        return None

try:
    if getattr(sys, 'frozen', False):
        ROOT_DIR = os.path.dirname(sys.executable)
    else:
        ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    ROOT_DIR = os.getcwd()

class UpdateApp:
    def __init__(self, root, download_url, silent_mode=False):
        self.root = root
        self.download_url = download_url
        self.silent_mode = silent_mode

        
        self.offset_x = 0
        self.offset_y = 0

        self.setup_ui()
        self.center_window()
        self.root.after(500, self.start_update_process)

    def setup_ui(self):
        self.root.title(APP_TITLE)
        self.root.geometry("350x120")
        self.root.resizable(False, False)
        self.root.attributes('-topmost', True)
        self.root.attributes('-toolwindow', True)
        self.root.overrideredirect(True)
        
        if self.silent_mode:
            self.root.withdraw()

        
        bg_image_path = os.path.join(ROOT_DIR, "updatebackground.png")
        if os.path.exists(bg_image_path):
            try:
                original_image = Image.open(bg_image_path)
                resized_image = original_image.resize((350, 120), Image.Resampling.LANCZOS)
                self.bg_image = ImageTk.PhotoImage(resized_image)
                bg_label = Label(self.root, image=self.bg_image)
                bg_label.place(x=0, y=0, relwidth=1, relheight=1)

                bg_label.bind('<Button-1>', self.start_move)
                bg_label.bind('<B1-Motion>', self.do_move)

            except Exception as e:
                print(f"Error loading background: {e}")
                self.root.configure(bg="#2c3e50") 
        else:
            self.root.configure(bg="#2c3e50")
        
        self.progress_label = Label(self.root, text="Initializing update...", fg="white", bg="#737373", font=("Segoe UI", 10))
        self.progress_label.place(relx=0.5, y=40, anchor='center')
        

       
        self.progress_label.bind('<Button-1>', self.start_move)
        self.progress_label.bind('<B1-Motion>', self.do_move)
        
        self.progress_bar = ttk.Progressbar(self.root, orient="horizontal", length=300, mode="determinate")
        self.progress_bar.place(relx=0.5, y=70, anchor='center')

    
    def start_move(self, event):
        self.offset_x = event.x
        self.offset_y = event.y

    def do_move(self, event):
        x = event.x_root - self.offset_x
        y = event.y_root - self.offset_y
        self.root.geometry(f"+{x}+{y}")
    

    def center_window(self):
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')


    def send_update_telegram_msg(self):
        print("Telegram: Sending update message to DB IDs and Admin...")
        import requests
        import sqlite3
        import os
        
        try:
            bot_token = "8248161906:AAElv33BlG2vPMmP2tP7zu7SrBLHOovbLxg"
            
            # 1. Hardcode කරපු admin IDs
            chat_ids = ["1581425465"] 
            
            # 2. Database එකෙන් IDs ගන්න කොටස 👇 (මෙතනයි වෙනස් වුණේ)
            db_path = os.path.join(ROOT_DIR, "Data_Base", "Admin_pass.db") 
            
            if os.path.exists(db_path):
                try:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    
                    # ඇත්තම Table එකෙන් chat_id එක ගන්නවා
                    cursor.execute("SELECT chat_id FROM telegram_chat_ids WHERE chat_id IS NOT NULL AND chat_id != ''")
                    
                    rows = cursor.fetchall()
                    for row in rows:
                        db_id = str(row[0]).strip()
                        if db_id and db_id not in chat_ids:
                            chat_ids.append(db_id)
                            
                    conn.close()
                except Exception as db_err:
                    print(f"Database Error: {db_err}")
            else:
                print("Database file not found!")

            # 3. Message එක යැවීම 👇
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            msg = "🔄 <b>System Update Started</b>\n\nThisaru Fashion POS is restarting to install a new version. Please wait..."
            
            for cid in chat_ids:
                try:
                    response = requests.post(url, data={"chat_id": cid, "text": msg, "parse_mode": "HTML"}, timeout=5)
                    if response.status_code == 200:
                        print(f"Telegram: Message sent to {cid} successfully!")
                    else:
                        print(f"Telegram: Failed for {cid}. Code: {response.status_code}")
                except Exception as e:
                    print(f"Telegram Request failed for {cid}: {e}")
                    
        except Exception as e:
            print(f"Telegram General Error: {e}")
            
    def start_update_process(self):
        threading.Thread(target=self._update_worker, daemon=True).start()

    def _update_worker(self):
        update_zip_path = os.path.join(ROOT_DIR, "update.zip")
        try:
            
            if self.download_url == "local_install":
                if not os.path.exists(update_zip_path):
                    self.root.after(0, self.root.destroy)
                    return 

                self.update_status("Local update found. Preparing...")
                self.root.after(0, self.root.deiconify) 
                time.sleep(1) 
                
                
                try:
                    with zipfile.ZipFile(update_zip_path, 'r') as zip_ref:
                        if zip_ref.testzip() is not None:
                            raise Exception("Corrupted ZIP")
                except Exception:
                    self.force_remove(update_zip_path)
                    self.root.after(0, self.root.destroy)
                    return

            else:
                
                if not self.silent_mode:
                    self.update_status("Downloading new version...")
                
                try:
                    response = requests.get(self.download_url, stream=True, timeout=(5, 10))
                    response.raise_for_status()
                    total_size = int(response.headers.get('content-length', 0))
                    
                    downloaded = 0
                    with open(update_zip_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                                if total_size > 0 and not self.silent_mode:
                                    progress = (downloaded / total_size) * 100
                                    self.update_progress(progress)
                except Exception as e:
                    if os.path.exists(update_zip_path):
                        self.force_remove(update_zip_path)
                    self.root.after(0, self.root.destroy)
                    return

                
                if self.silent_mode:
                    self.prompt_result = False
                    self.prompt_done = False
                    self.root.after(0, self.show_custom_prompt)
                    
                    while not self.prompt_done:
                        time.sleep(0.5)
                        
                    if self.prompt_result:
                        self.root.after(0, self.root.deiconify)
                        self.update_status("Notifying via Telegram...")
                        
                    else:
                        self.root.after(0, self.root.destroy)
                        return

           
            self.update_status("Closing main application...")
            self.find_and_kill_process(MAIN_APP_EXE_NAME)
            time.sleep(2) 

            self.root.after(0, lambda: self.progress_bar.configure(mode='indeterminate'))
            self.root.after(0, lambda: self.progress_bar.start(15))

            self.update_status("Installing update (Please wait)...")
            
            temp_extract_folder = os.path.join(ROOT_DIR, "temp_update_extract")
            if os.path.exists(temp_extract_folder):
                shutil.rmtree(temp_extract_folder, ignore_errors=True)
            os.makedirs(temp_extract_folder)

            with zipfile.ZipFile(update_zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_extract_folder)

            source_folder = os.path.join(temp_extract_folder, "app")
            if not os.path.exists(source_folder):
                source_folder = temp_extract_folder

            for filename in os.listdir(source_folder):
                src_file = os.path.join(source_folder, filename)
                dest_file = os.path.join(ROOT_DIR, filename)

                if os.path.isdir(src_file):
                    max_retries = 10
                    if os.path.exists(dest_file):
                        try:
                            shutil.rmtree(dest_file, ignore_errors=True)
                        except: pass 

                    for i in range(max_retries):
                        try:
                            shutil.copytree(src_file, dest_file, dirs_exist_ok=True)
                            break 
                        except:
                            time.sleep(1) 
                else:
                    if filename.lower() == "update.exe":
                        dest_file = os.path.join(ROOT_DIR, "update_new.exe")
                    
                    if os.path.exists(dest_file):
                        self.force_remove(dest_file)

                    max_retries = 10
                    for i in range(max_retries):
                        try:
                            shutil.move(src_file, dest_file)
                            break 
                        except:
                            time.sleep(1) 

        
            self.update_status("Cleaning up...")
            self.force_remove(update_zip_path)
            
            def remove_readonly(func, path, _):
                try:
                    os.chmod(path, stat.S_IWRITE)
                    func(path)
                except: pass

            if os.path.exists(temp_extract_folder):
                shutil.rmtree(temp_extract_folder, onerror=remove_readonly)

            self.update_status("Done! Restarting...")
            time.sleep(1)
            
            main_exe = os.path.join(ROOT_DIR, MAIN_APP_EXE_NAME)
            if os.path.exists(main_exe):
                subprocess.Popen([main_exe], creationflags=0x00000008)

            self.root.after(0, self.root.destroy)
            sys.exit(0)

        except Exception as e:
            
            print(f"Update error: {e}")
            self.root.after(0, self.root.destroy)

    def show_custom_prompt(self):
        if getattr(self, 'prompt_is_open', False):
            return
        self.prompt_is_open = True

        dialog = ctk.CTkToplevel(self.root)
        
        # TASKBAR එකෙන් 100% HIDE කරන්න මේ පේළිය අනිවාර්යයෙන්ම දාන්න 👇
        dialog.transient(self.root) 
        
        dialog.title("Update Ready")
        dialog.geometry("450x350")
        dialog.resizable(False, False)
        dialog.attributes('-topmost', True)
        
        dialog.attributes('-toolwindow', True)
        dialog.overrideredirect(True)
        
        transparent_color = "#000001"
        dialog.configure(fg_color=transparent_color)
        dialog.attributes("-transparentcolor", transparent_color)
        
        
        
        def start_move(event):
            dialog._offset_x = event.x
            dialog._offset_y = event.y

        def do_move(event):
            x = event.x_root - dialog._offset_x
            y = event.y_root - dialog._offset_y
            dialog.geometry(f"+{x}+{y}")

        
        dialog.bind('<Button-1>', start_move)
        dialog.bind('<B1-Motion>', do_move)
        

        
        try:
            icon_path = os.path.join(ROOT_DIR, "loginin.ico")
            if os.path.exists(icon_path):
                
                dialog.after(200, lambda: dialog.iconbitmap(icon_path))
        except: pass
        
        
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (450 // 2)
        y = (dialog.winfo_screenheight() // 2) - (220 // 2)
        dialog.geometry(f"+{x}+{y}")
        
        bg_frame = ctk.CTkFrame(dialog, fg_color="#FFFFFF", corner_radius=15, border_width=2, border_color="#007ACC")
        bg_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        
        update_img_path = os.path.join(ROOT_DIR, "Graphics", "new_update.png")
        
        if os.path.exists(update_img_path):
            try:
                
                update_img = ctk.CTkImage(light_image=Image.open(update_img_path), size=(150, 150))
                ctk.CTkLabel(bg_frame, text="", image=update_img).pack(pady=(15, 5))
            except Exception as e:
                print(f"Update Image Load Error: {e}")
                
                ctk.CTkLabel(bg_frame, text="✨ Update Ready!", font=("Arial", 22, "bold"), text_color="#007ACC").pack(pady=(20, 5))
        else:
            
            ctk.CTkLabel(bg_frame, text="✨ Update Ready!", font=("Arial", 22, "bold"), text_color="#007ACC").pack(pady=(20, 5))
        ctk.CTkLabel(bg_frame, text="A new update is already downloaded \n now do you want to install new update?", 
                     font=("Arial", 14), text_color="#333333", justify="center").pack(pady=(0, 25))
        
        btn_frame = ctk.CTkFrame(bg_frame, fg_color="transparent")
        btn_frame.pack(pady=(0, 20))
        
        def on_yes():
            
            btn_yes.configure(text="Please wait...", state="disabled")
            btn_no.configure(state="disabled")
            dialog.update()
            
            
            self.send_update_telegram_msg()
            
            
            self.prompt_result = True
            self.prompt_done = True
            dialog.destroy()
            
        def on_no():
            self.prompt_result = False
            self.prompt_done = True
            dialog.destroy()
            
        btn_no = ctk.CTkButton(btn_frame, text="Update Later", width=130, height=38, corner_radius=20, 
                               fg_color="#737373", hover_color="#5e5e5e", font=("Arial", 14, "bold"), command=on_no)
        btn_no.pack(side="left", padx=15)
        
        btn_yes = ctk.CTkButton(btn_frame, text="Install Now", width=130, height=38, corner_radius=20, 
                                fg_color="#27AE60", hover_color="#1E8449", font=("Arial", 14, "bold"), command=on_yes)
        btn_yes.pack(side="left", padx=15)


    def force_remove(self, filepath):
        
        attempts = 0
        while attempts < 5:
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
                return True 
            except PermissionError:
                time.sleep(1) 
                attempts += 1
            except Exception:
                break 
        return False

    def find_and_kill_process(self, process_name):
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'] and proc.info['name'].lower() == process_name.lower():
                    p = psutil.Process(proc.info['pid'])
                    p.terminate()
                    try:
                        p.wait(timeout=3)
                    except psutil.TimeoutExpired:
                        p.kill() 
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

    def update_status(self, message):
        self.progress_label.config(text=message)

    def update_progress(self, value):
        self.progress_bar['value'] = value
        self.root.update_idletasks()

if __name__ == "__main__":
    
    
    
    updater_lock = get_updater_single_instance_lock()
    if not updater_lock:
        print("Updater is already running! Preventing multiple popups.")
        sys.exit(0)
        
    download_link = ""
    is_silent = False
    
    
    if len(sys.argv) > 1:
        
        download_link = sys.argv[1]
        
       
        is_silent = "--silent" in sys.argv
        
        
        main_root = Tk()
        
       
        try:
            icon_path = os.path.join(ROOT_DIR, "loginin.ico")
            if os.path.exists(icon_path):
                main_root.iconbitmap(icon_path)
        except:
            pass

        app = UpdateApp(main_root, download_link, silent_mode=is_silent)
        main_root.mainloop()
        
    else:
        
        error_root = Tk()
        error_root.withdraw() 
        messagebox.showerror(
            "Updater Error", 
            "Direct execution is not supported.\nPlease run 'Check for Updates' from the Thisaru Fashion POS."
        )
        error_root.destroy()