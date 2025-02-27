#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import subprocess, os, zipfile, shutil, tempfile, threading, time, webbrowser, sys, hashlib, socket, fcntl
from datetime import datetime
from functools import partial

######################################
# Dossiers et chemins
######################################
PROJECT_DIR = "/opt/SwiftRDP"  # Fichiers du projet
CONFIG_DIR  = "/usr/local/share/appdata/.SwiftRDP"  # Fichiers de configuration

if not os.path.exists(CONFIG_DIR):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    subprocess.call(["sudo", "chown", "-R", f"{os.environ.get('USER')}:{os.environ.get('USER')}", CONFIG_DIR])

# Chemins de configuration (dans CONFIG_DIR)
LANGUAGE_FILE     = os.path.join(CONFIG_DIR, "language.conf")
THEME_FILE        = os.path.join(CONFIG_DIR, "theme.conf")
FILE_CONNS        = os.path.join(CONFIG_DIR, "connexions.txt")
GROUPS_FILE       = os.path.join(CONFIG_DIR, "groups.txt")
PASSWORD_FILE     = os.path.join(CONFIG_DIR, "password.conf")
SHORTCUTS_FILE    = os.path.join(CONFIG_DIR, "shortcuts.conf")
DISPLAY_MODE_FILE = os.path.join(CONFIG_DIR, "display_mode.conf")
DEFAULT_RDP_FILE  = os.path.join(CONFIG_DIR, "default_rdp.conf")  # Contiendra "yes" ou "no"

# Fichiers du projet (dans PROJECT_DIR)
CHANGELOG_FILE    = os.path.join(PROJECT_DIR, "CHANGELOG")
CHANGELOG_HIDE    = os.path.join(PROJECT_DIR, "CHANGELOGHIDE")
VERSION_FILE      = os.path.join(PROJECT_DIR, "version.txt")
ICON_FILE         = os.path.join(PROJECT_DIR, "icon.png")
PATCH_NOTE_FLAG   = os.path.join(PROJECT_DIR, "PATCH_NOTE_PENDING")

######################################
# Fonctions utilitaires
######################################
def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def ask_password_custom(parent, title, prompt):
    dlg = tk.Toplevel(parent)
    dlg.title(title)
    dlg.transient(parent)
    dlg.grab_set()
    dlg.attributes("-topmost", True)
    dlg.focus_force()
    tk.Label(dlg, text=prompt, font=parent.font_main).pack(padx=20, pady=10)
    entry = tk.Entry(dlg, show="*")
    entry.pack(padx=20, pady=10)
    result = {"value": None}
    def on_ok():
        result["value"] = entry.get()
        dlg.destroy()
    def on_cancel():
        dlg.destroy()
    btn_frame = tk.Frame(dlg)
    btn_frame.pack(pady=10)
    tk.Button(btn_frame, text="OK", command=on_ok, font=parent.font_main).pack(side="left", padx=10)
    tk.Button(btn_frame, text="Annuler", command=on_cancel, font=parent.font_main).pack(side="left", padx=10)
    parent.wait_window(dlg)
    return result["value"]

def check_password(parent):
    if os.path.exists(PASSWORD_FILE):
        with open(PASSWORD_FILE, "r", encoding="utf-8") as f:
            stored_hash = f.read().strip()
        pwd = simpledialog.askstring("Mot de passe", "Entrez le mot de passe pour lancer SwiftRDP:", show="*", parent=parent)
        if not pwd or hash_password(pwd) != stored_hash:
            messagebox.showerror("Erreur", "Mot de passe incorrect.", parent=parent)
            return False
    return True

def make_modal(win, parent):
    win.transient(parent)
    win.grab_set()
    win.focus_force()
    win.attributes("-topmost", True)

######################################
# Gestion de la single instance via socket
######################################
def send_instance_message():
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(("127.0.0.1", 50000))
        if len(sys.argv) > 1:
            msg = " ".join(sys.argv[1:])
            client.sendall(msg.encode())
        client.close()
        return True
    except Exception:
        return False

if send_instance_message():
    sys.exit(0)

def socket_listener(app):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 50000))
    s.listen(1)
    print("Socket listener démarré sur le port 50000")
    while True:
        try:
            conn, addr = s.accept()
            data = conn.recv(1024).decode().strip()
            print("Message reçu via socket :", data)
            if data.startswith("rdp://"):
                ip = data[len("rdp://"):]
                subprocess.Popen(["/bin/bash", os.path.join(PROJECT_DIR, "SwiftRDP.sh"), f"rdp://{ip}"])
                app.after(200, app.destroy)
            conn.close()
        except Exception as e:
            print("Erreur dans le socket_listener :", e)
            break

######################################
# Configuration RDP par défaut
######################################
if not os.path.exists(DEFAULT_RDP_FILE) or not open(DEFAULT_RDP_FILE, "r", encoding="utf-8").read().strip():
    if messagebox.askyesno("Application par défaut", "Voulez-vous définir SwiftRDP comme application par défaut pour les liens rdp:// ?"):
        with open(DEFAULT_RDP_FILE, "w", encoding="utf-8") as f:
            f.write("yes")
        subprocess.call(["xdg-mime", "default", "SwiftRDP.desktop", "x-scheme-handler/rdp"])
    else:
        with open(DEFAULT_RDP_FILE, "w", encoding="utf-8") as f:
            f.write("no")
else:
    DEFAULT_RDP = open(DEFAULT_RDP_FILE, "r", encoding="utf-8").read().strip().lower() == "yes"
    if DEFAULT_RDP:
        subprocess.call(["xdg-mime", "default", "SwiftRDP.desktop", "x-scheme-handler/rdp"])

######################################
# Chargement de la configuration (langue, thème, mode d'affichage)
######################################
if os.path.exists(LANGUAGE_FILE):
    with open(LANGUAGE_FILE, "r", encoding="utf-8") as f:
         CURRENT_LANG = f.read().strip()
else:
    CURRENT_LANG = "fr"
if os.path.exists(THEME_FILE):
    with open(THEME_FILE, "r", encoding="utf-8") as f:
         CURRENT_THEME = f.read().strip()
else:
    CURRENT_THEME = "dark"
if os.path.exists(DISPLAY_MODE_FILE):
    with open(DISPLAY_MODE_FILE, "r", encoding="utf-8") as f:
         CONN_DISPLAY_MODE = f.read().strip()
else:
    CONN_DISPLAY_MODE = "fenetres"

def get_theme():
    if CURRENT_THEME == "light":
         return {
             "bg": "#ffffff",
             "fg": "#000000",
             "entry_bg": "#f0f0f0",
             "button_bg": "#e0e0e0",
             "button_fg": "#000000",
             "tree_bg": "#ffffff",
             "tree_fg": "#000000"
         }
    else:
         return {
             "bg": "#2b2b2b",
             "fg": "#ffffff",
             "entry_bg": "#3a3a3a",
             "button_bg": "#3a3a3a",
             "button_fg": "#ffffff",
             "tree_bg": "#2b2b2b",
             "tree_fg": "#c0c0c0"
         }

######################################
# Traductions
######################################
translations = {
    "fr": {
         "title": "SwiftRDP",
         "search": "Recherche:",
         "connect": "Se connecter",
         "add": "Ajouter",
         "modify": "Modifier",
         "delete": "Supprimer",
         "manage_groups": "Gérer Groupes",
         "options": "Options",
         "preferences": "Préférences",
         "patch_note": "Notes de mise à jour",
         "dont_show_again": "Ne plus afficher",
         "view_patch_note": "Voir les notes de mise à jour",
         "patch_note_empty": "Aucune note de mise à jour disponible.",
         "error": "Erreur",
         "warning": "Avertissement",
         "info": "Info",
         "confirm": "Confirmer",
         "all_fields_required": "Tous les champs (sauf note) doivent être remplis.",
         "error_duplicate_name": "Le nom '{name}' existe déjà. Veuillez en choisir un autre.",
         "warning_duplicate_ip": "L'IP '{ip}' est déjà enregistrée. Voulez-vous continuer ?",
         "connection_added": "Connexion ajoutée.",
         "connection_modified": "Connexion modifiée.",
         "language_saved_restart": "La langue, le thème et les raccourcis ont été enregistrés. L'application va redémarrer automatiquement.",
         "new_version_available": "Une nouvelle version est disponible. Voulez-vous mettre à jour SwiftRDP ?",
         "no_update_available": "Aucune mise à jour disponible.",
         "update_failed": "La mise à jour a échoué",
         "update_complete": "Mise à jour et redémarrage.",
         "update_in_progress_t": "Mise à jour en cours...",
         "select_connection": "Veuillez sélectionner une connexion.",
         "delete_connection": "Supprimer la connexion",
         "connection_deleted": "Connexion supprimée.",
         "note_full": "Note complète",
         "note_for": "Note pour",
         "password": "Mot de passe",
         "enter_password_for": "Entrez le mot de passe pour",
         "no_password": "Aucun mot de passe fourni.",
         "launch_error": "Erreur lors du lancement de SwiftRDP",
         "connecting": "Connexion en cours...",
         "please_wait": "Connexion en cours, veuillez patienter...",
         "connection_failed": "Connexion échouée",
         "new_group": "Nouveau groupe",
         "enter_new_group": "Entrez le nom du nouveau groupe:",
         "add_connection_title": "Ajouter Connexion",
         "modify_connection_title": "Modifier Connexion",
         "add_note_title": "Ajouter une note",
         "modify_note_title": "Modifier la Note",
         "name": "Nom:",
         "ip": "IP:",
         "login": "Login:",
         "group": "Groupe:",
         "last_connection": "Dernière connexion",
         "return": "Retour",
         "add_note": "Ajouter une note",
         "manage_groups_title": "Gérer Groupes",
         "add_group_option": "Ajouter Groupe",
         "existing_groups": "Groupes existants:",
         "select_group": "Veuillez sélectionner un groupe.",
         "save_configuration_option": "Sauvegarder la configuration",
         "export_configuration_option": "Exporter la configuration",
         "import_configuration_option": "Importer la configuration",
         "delete_configuration_option": "Supprimer la configuration",
         "update_option": "Mettre à jour SwiftRDP",
         "support_option": "Support",
         "choose_backup_directory": "Choisissez le dossier de sauvegarde",
         "choose_export_directory": "Choisissez le dossier d'exportation",
         "select_import_file": "Sélectionnez le fichier de configuration à importer",
         "configuration_saved": "Configuration sauvegardée dans : {path}",
         "configuration_exported": "Configuration exportée dans : {path}",
         "configuration_imported": "Configuration importée.",
         "language": "Langue:",
         "theme": "Thème:",
         "dark": "Sombre",
         "light": "Clair",
         "shortcuts": "Raccourcis",
         "switch_shortcut": "Switcher entre connexions",
         "set_password": "Définir/modifier mot de passe SwiftRDP",
         "display_mode": "Mode d'affichage des connexions",
         "fenetres": "Fenêtres séparées",
         "onglets": "Onglets",
         "default_rdp_label": "Définir comme application RDP par défaut",
         "delete_all_connections": "Voulez-vous supprimer toutes les connexions ?",
         "delete_all_groups": "Voulez-vous supprimer tous les groupes ?",
         "save": "Enregistrer"
    },
    "en": {
         "title": "SwiftRDP",
         "search": "Search:",
         "connect": "Connect",
         "add": "Add",
         "modify": "Modify",
         "delete": "Delete",
         "manage_groups": "Manage Groups",
         "options": "Options",
         "preferences": "Preferences",
         "patch_note": "Patch Notes",
         "dont_show_again": "Don't show again",
         "view_patch_note": "View Patch Notes",
         "patch_note_empty": "No patch notes available.",
         "error": "Error",
         "warning": "Warning",
         "info": "Info",
         "confirm": "Confirm",
         "all_fields_required": "All fields (except note) are required.",
         "error_duplicate_name": "The name '{name}' already exists. Please choose another.",
         "warning_duplicate_ip": "The IP '{ip}' already exists. Do you want to continue?",
         "connection_added": "Connection added.",
         "connection_modified": "Connection modified.",
         "language_saved_restart": "Language, theme and shortcuts saved. The application will restart automatically.",
         "new_version_available": "A new version is available. Do you want to update SwiftRDP?",
         "no_update_available": "No update available.",
         "update_failed": "Update failed",
         "update_complete": "Update and restart.",
         "update_in_progress_t": "Update in progress...",
         "select_connection": "Please select a connection.",
         "delete_connection": "Delete connection",
         "connection_deleted": "Connection deleted.",
         "note_full": "Full Note",
         "note_for": "Note for",
         "password": "Password",
         "enter_password_for": "Enter password for",
         "no_password": "No password provided.",
         "launch_error": "Error launching SwiftRDP",
         "connecting": "Connecting...",
         "please_wait": "Please wait while connecting...",
         "connection_failed": "Connection failed",
         "new_group": "New group",
         "enter_new_group": "Enter the new group name:",
         "add_connection_title": "Add Connection",
         "modify_connection_title": "Modify Connection",
         "add_note_title": "Add Note",
         "modify_note_title": "Modify Note",
         "name": "Name:",
         "ip": "IP:",
         "login": "Username:",
         "group": "Group:",
         "last_connection": "Last connection",
         "return": "Back",
         "add_note": "Add Note",
         "manage_groups_title": "Manage Groups",
         "add_group_option": "Add Group",
         "existing_groups": "Existing groups:",
         "select_group": "Please select a group.",
         "save_configuration_option": "Save Configuration",
         "export_configuration_option": "Export Configuration",
         "import_configuration_option": "Import Configuration",
         "delete_configuration_option": "Delete Configuration",
         "update_option": "Update SwiftRDP",
         "support_option": "Support",
         "choose_backup_directory": "Choose backup directory",
         "choose_export_directory": "Choose export directory",
         "select_import_file": "Select configuration file to import",
         "configuration_saved": "Configuration saved in: {path}",
         "configuration_exported": "Configuration exported in: {path}",
         "configuration_imported": "Configuration imported.",
         "language": "Language:",
         "theme": "Theme:",
         "dark": "Dark",
         "light": "Light",
         "shortcuts": "Shortcuts",
         "switch_shortcut": "Switch between connections",
         "set_password": "Set/Change SwiftRDP Password",
         "display_mode": "Connection display mode",
         "fenetres": "Separate windows",
         "onglets": "Tabs",
         "default_rdp_label": "Set as default RDP application",
         "save": "Save"
    }
}

def t(key, **kwargs):
    text = translations.get(CURRENT_LANG, translations["fr"]).get(key, key)
    return text.format(**kwargs)

######################################
# Fichiers de configuration et projet
######################################
PROJECT_DIR = "/opt/SwiftRDP"
ICON_FILE = os.path.join(PROJECT_DIR, "icon.png")
for file in (FILE_CONNS, GROUPS_FILE):
    if not os.path.exists(file):
        open(file, "w", encoding="utf-8").close()

def format_note(note):
    display = note.replace("\n", " ")
    return display if len(display) <= 30 else display[:30] + "..."

def load_connections():
    conns = []
    with open(FILE_CONNS, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            parts = line.split("|")
            if len(parts) >= 5:
                parts[4] = parts[4].replace("<NL>", "\n")
            while len(parts) < 6:
                parts.append("")
            conns.append(parts)
    return conns

def save_connections(data):
    with open(FILE_CONNS, "w", encoding="utf-8") as f:
        for row in data:
            row[4] = row[4].replace("\n", "<NL>")
            f.write("|".join(row) + "\n")

def update_connection_by_value(original_row, new_row):
    data = load_connections()
    for i, r in enumerate(data):
        if r == original_row:
            data[i] = new_row
            break
    save_connections(data)

def delete_connection(key):
    data = load_connections()
    new_data = [row for row in data if (row[0], row[5]) != key]
    save_connections(new_data)

def load_groups():
    groups = []
    with open(GROUPS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            group = line.strip()
            if group:
                groups.append(group)
    return groups

def save_groups(groups):
    with open(GROUPS_FILE, "w", encoding="utf-8") as f:
        for group in groups:
            f.write(group + "\n")

def get_existing_groups():
    return load_groups()

def delete_group_from_storage(grp):
    groups = get_existing_groups()
    if grp in groups:
        groups.remove(grp)
    save_groups(groups)
    data = load_connections()
    for i, row in enumerate(data):
        if row[5] == grp:
            data[i][5] = ""
    save_connections(data)

def backup_configuration(dest_path, export=False):
    zip_name = "SwiftRDPexport.zip" if export else "SwiftRDPsave.zip"
    full_path = os.path.join(dest_path, zip_name)
    with zipfile.ZipFile(full_path, 'w') as zipf:
        for file in (FILE_CONNS, GROUPS_FILE):
            if os.path.exists(file):
                zipf.write(file, os.path.basename(file))
    return full_path

def import_configuration_func(zip_path):
    with tempfile.TemporaryDirectory() as tmpdirname:
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            zipf.extractall(tmpdirname)
        src_conn = os.path.join(tmpdirname, os.path.basename(FILE_CONNS))
        src_groups = os.path.join(tmpdirname, os.path.basename(GROUPS_FILE))
        if os.path.exists(src_conn):
            shutil.copy(src_conn, FILE_CONNS)
        if os.path.exists(src_groups):
            shutil.copy(src_groups, GROUPS_FILE)

def delete_configuration():
    conn_deleted = False
    group_deleted = False
    if messagebox.askyesno(t("confirm"), t("delete_all_connections"), parent=app):
        open(FILE_CONNS, "w", encoding="utf-8").close()
        conn_deleted = True
    if messagebox.askyesno(t("confirm"), t("delete_all_groups"), parent=app):
        open(GROUPS_FILE, "w", encoding="utf-8").close()
        data = load_connections()
        for i, row in enumerate(data):
            row[5] = ""
        save_connections(data)
        group_deleted = True
    if conn_deleted or group_deleted:
        app.lift()
        app.attributes("-topmost", True)
        messagebox.showinfo(t("info"), t("configuration_deleted"), parent=app)
        app.attributes("-topmost", False)
    app.refresh_table()

def treeview_sort_column(tv, col, reverse):
    data = [(tv.set(k, col), k) for k in tv.get_children('')]
    data.sort(key=lambda t: t[0].lower(), reverse=reverse)
    for index, (val, k) in enumerate(data):
        tv.move(k, '', index)
    tv.heading(col, command=partial(treeview_sort_column, tv, col, not reverse))

def window_exists(root, title):
    for win in root.winfo_children():
        if isinstance(win, tk.Toplevel) and win.title() == title:
            win.lift()
            return True
    return False

######################################
# Fonctions pour le patch note
######################################
def get_version():
    try:
        with open(VERSION_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    except:
        return ""

def read_patch_note():
    if os.path.exists(CHANGELOG_FILE):
        with open(CHANGELOG_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            return content if content else t("patch_note_empty")
    return t("patch_note_empty")

######################################
# Fonction pour switcher entre fenêtres (Ctrl+1 à Ctrl+9)
######################################
def switch_to_window(n):
    try:
        output = subprocess.check_output(["wmctrl", "-l"], text=True)
    except Exception:
        return
    windows = []
    for line in output.splitlines():
        if "swiftrdp:" in line.lower():
            parts = line.split()
            if parts:
                windows.append(parts[0])
    windows.sort()
    if 0 <= n-1 < len(windows):
        subprocess.call(["wmctrl", "-i", "-a", windows[n-1]])

######################################
# Fonctions pour la mise à jour (barre de progression)
######################################
def check_for_update(app, from_menu=False):
    repo_url = "https://github.com/Equinoxx83/SwiftRDP.git"
    temp_dir = tempfile.mkdtemp()
    try:
        subprocess.check_call(["git", "clone", "--depth", "1", repo_url, temp_dir])
        remote_version_file = os.path.join(temp_dir, "version.txt")
        if not os.path.exists(remote_version_file):
            remote_version = ""
        else:
            with open(remote_version_file, "r", encoding="utf-8") as f:
                remote_version = f.read().strip()
    except Exception:
        remote_version = ""
    finally:
        shutil.rmtree(temp_dir)
    try:
        with open(VERSION_FILE, "r", encoding="utf-8") as vf:
            local_version = vf.read().strip()
    except Exception:
        local_version = ""
    if remote_version and remote_version != local_version:
        if messagebox.askyesno(t("update_option"), t("new_version_available"), parent=app):
            update_app(app, repo_url, remote_version)
    else:
        if from_menu:
            messagebox.showinfo(t("update_option"), t("no_update_available"), parent=app)

def update_app(app, repo_url, remote_version):
    temp_dir = tempfile.mkdtemp()
    try:
        subprocess.check_call(["git", "clone", "--depth", "1", repo_url, temp_dir])
        dest_dir = PROJECT_DIR
        for item in os.listdir(dest_dir):
            s = os.path.join(dest_dir, item)
            if os.path.isdir(s):
                shutil.rmtree(s)
            else:
                os.remove(s)
        for item in os.listdir(temp_dir):
            s = os.path.join(temp_dir, item)
            d = os.path.join(dest_dir, item)
            if os.path.isdir(s):
                shutil.copytree(s, d)
            else:
                shutil.copy2(s, d)
        with open(os.path.join(dest_dir, "version.txt"), "w", encoding="utf-8") as vf:
            vf.write(remote_version)
        os.chmod(os.path.join(dest_dir, "SwiftRDP.sh"), 0o755)
        if os.path.exists(CHANGELOG_HIDE):
            os.remove(CHANGELOG_HIDE)
        with open(os.path.join(PROJECT_DIR, "PATCH_NOTE_PENDING"), "w", encoding="utf-8") as f:
            f.write("1")
    except Exception as e:
        messagebox.showerror(t("error"), f"{t('update_failed')}\n{e}", parent=app)
        return
    finally:
        shutil.rmtree(temp_dir)
    def progress_and_restart():
        progress_win = tk.Toplevel(app)
        progress_win.title(t("update_complete"))
        progress_win.geometry("400x100")
        progress_win.configure(bg=app.theme["bg"])
        tk.Label(progress_win, text=t("update_in_progress_t"), font=app.font_main,
                 bg=app.theme["bg"], fg=app.theme["fg"]).pack(pady=10)
        pb = ttk.Progressbar(progress_win, mode="determinate", maximum=100)
        pb.pack(fill=tk.X, padx=20, pady=10)
        for i in range(101):
            pb['value'] = i
            progress_win.update()
            time.sleep(0.1)
        progress_win.destroy()
        subprocess.Popen(["/bin/bash", os.path.join(PROJECT_DIR, "SwiftRDP.sh")])
        app.destroy()
        sys.exit(0)
    threading.Thread(target=progress_and_restart, daemon=True).start()

######################################
# Classe principale de l'application
######################################
class RDPApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.connection_in_progress = False
        self.theme = get_theme()
        self.logo = tk.PhotoImage(file=ICON_FILE)
        self.iconphoto(False, self.logo)
        self.title(t("title"))
        self.geometry("1600x900")
        self.configure(bg=self.theme["bg"])
        self.font_main = ("Segoe Script", 12)
        self.font_heading = ("Segoe Script", 12)
        self.create_widgets()
        self.refresh_table()
        threading.Thread(target=socket_listener, args=(self,), daemon=True).start()
        for i in range(1, 10):
            self.bind_all(f"<Control-Key-{i}>", lambda event, n=i: switch_to_window(n))
        if os.path.exists(PATCH_NOTE_FLAG):
            self.after(2000, lambda: self.show_patch_note_dialog(read_patch_note()))
            os.remove(PATCH_NOTE_FLAG)
        # Vérification de mise à jour au lancement (ajoutée ici)
        self.after(2000, lambda: check_for_update(self))
    
    def prompt_rdp_connection(self, ip):
        login = simpledialog.askstring("Login", "Entrez votre login :", parent=self)
        pwd = simpledialog.askstring("Mot de passe", "Entrez votre mot de passe :", show="*", parent=self)
        if login and pwd:
            row = [ip, ip, login, "N/A", "", ""]
            self.connect_connection(row, pwd_provided=pwd)
        else:
            messagebox.showerror("Erreur", "Login ou mot de passe non fourni.", parent=self)
    
    def connect_connection(self, row, pwd_provided=None):
        if self.connection_in_progress:
            return
        self.connection_in_progress = True
        start_time = time.time()
        timeout = 15
        if pwd_provided is None:
            pwd = simpledialog.askstring(t("password"), f"{t('enter_password_for')} {row[0]}:", show="*", parent=self)
        else:
            pwd = pwd_provided
        if not pwd:
            messagebox.showerror(t("error"), t("no_password"), parent=self)
            self.connection_in_progress = False
            return
        try:
            rdp_proc = subprocess.Popen(
                ["xfreerdp", f"/v:{row[1]}", f"/u:{row[2]}", f"/p:{pwd}",
                 "/dynamic-resolution", "/cert-ignore", f"/title:SwiftRDP: {row[1]}"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, start_new_session=True)
        except Exception as e:
            messagebox.showerror(t("error"), f"{t('launch_error')}:\n{e}", parent=self)
            self.connection_in_progress = False
            return
        self.update_idletasks()
        main_x = self.winfo_x()
        main_y = self.winfo_y()
        main_width = self.winfo_width()
        main_height = self.winfo_height()
        win_width = 400
        win_height = 150
        pos_x = main_x + (main_width - win_width) // 2
        pos_y = main_y + (main_height - win_height) // 2
        progress_win = tk.Toplevel(self)
        progress_win.iconphoto(False, self.logo)
        progress_win.title(t("connecting"))
        progress_win.geometry(f"{win_width}x{win_height}+{pos_x}+{pos_y}")
        progress_win.configure(bg=self.theme["bg"])
        progress_win.update_idletasks()
        tk.Label(progress_win, text=t("please_wait"),
                 font=("Segoe Script", 12), bg=self.theme["bg"], fg=self.theme["fg"]).pack(pady=20)
        style = ttk.Style(progress_win)
        style.theme_use("clam")
        style.configure("grey.Horizontal.TProgressbar", foreground="grey", background="grey")
        pb = ttk.Progressbar(progress_win, mode="determinate", maximum=100,
                             style="grey.Horizontal.TProgressbar")
        pb.pack(fill=tk.X, padx=20, pady=10)
        def update_progress(count=0):
            if count <= 100:
                pb['value'] = count
                self.after(150, update_progress, count+1)
            else:
                progress_win.destroy()
        update_progress()
        def check_window():
            found = False
            while time.time() - start_time < timeout:
                try:
                    output = subprocess.check_output(["wmctrl", "-l"], text=True)
                except Exception:
                    output = ""
                # Vérifier si la fenêtre RDP est présente
                if f"swiftrdp: {row[1].lower()}" in output.lower():
                    found = True
                    break
                # Sinon, si après 5 secondes le processus est toujours actif, considérer la connexion comme établie
                if time.time() - start_time > 5 and rdp_proc.poll() is None:
                    found = True
                    break
                time.sleep(1)
            if time.time() - start_time < 2:
                time.sleep(2 - (time.time() - start_time))
            try:
                progress_win.destroy()
            except Exception:
                pass
            if found:
                new_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                new_row = row.copy()
                new_row[3] = new_date
                update_connection_by_value(row, new_row)
                self.after(0, self.refresh_table)
            else:
                self.after(0, lambda: messagebox.showerror(t("error"), t("connection_failed"), parent=self))
            self.connection_in_progress = False
        threading.Thread(target=check_window, daemon=True).start()
    
    def show_patch_note_dialog(self, content, show_checkbox=True):
        dialog = tk.Toplevel(self)
        dialog.transient(self)
        dialog.grab_set()
        dialog.attributes("-topmost", True)
        dialog.iconphoto(False, self.logo)
        dialog.title(t("patch_note"))
        dialog.geometry("800x600")
        dialog.configure(bg=self.theme["bg"])
        text = tk.Text(dialog, wrap=tk.WORD, font=self.font_main,
                       bg=self.theme["entry_bg"], fg=self.theme["fg"])
        text.insert(tk.END, content)
        text.config(state="disabled")
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        var_hide = tk.BooleanVar()
        if show_checkbox:
            check = tk.Checkbutton(dialog, text=t("dont_show_again"), variable=var_hide,
                                     bg=self.theme["bg"], fg=self.theme["fg"], font=("Segoe Script", 14),
                                     selectcolor="lightblue")
            check.pack(anchor="w", padx=10, pady=5)
        def close_dialog():
            if show_checkbox and var_hide.get():
                with open(os.path.join(PROJECT_DIR, "CHANGELOGHIDE"), "w", encoding="utf-8") as f:
                    f.write(get_version())
            dialog.destroy()
        tk.Button(dialog, text=t("return"), command=close_dialog, font=self.font_main,
                  bg=self.theme["button_bg"], fg=self.theme["button_fg"], relief="flat", width=12).pack(pady=10)
        dialog.attributes("-topmost", False)
    
    def add_group(self, parent, combobox, var):
        new_grp = simpledialog.askstring(t("new_group"), t("enter_new_group"), parent=parent)
        if new_grp:
            groups = get_existing_groups()
            if new_grp not in groups:
                groups.append(new_grp)
                with open(GROUPS_FILE, "a", encoding="utf-8") as gf:
                    gf.write(new_grp + "\n")
            combobox["values"] = groups
            var.set(new_grp)
    
    def create_widgets(self):
        self.theme = get_theme()
        search_frame = tk.Frame(self, bg=self.theme["bg"])
        search_frame.pack(fill=tk.X, padx=15, pady=10)
        tk.Label(search_frame, text=t("search"), font=self.font_main, bg=self.theme["bg"], fg=self.theme["fg"]).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *args: self.refresh_table())
        tk.Entry(search_frame, textvariable=self.search_var, font=self.font_main, bg=self.theme["entry_bg"],
                 fg=self.theme["fg"], insertbackground=self.theme["fg"], relief="flat").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        columns = (t("name").strip(":"), t("ip").strip(":"), t("login").strip(":"), t("last_connection"), t("add_note").strip(), t("group").strip(":"))
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Treeview", background=self.theme["tree_bg"], fieldbackground=self.theme["tree_bg"],
                        foreground=self.theme["tree_fg"], font=self.font_main, borderwidth=0)
        heading_bg = "#e0e0e0" if CURRENT_THEME == "light" else "#1b1b1b"
        style.configure("Treeview.Heading", font=self.font_heading, background=heading_bg,
                        foreground=self.theme["fg"], relief="ridge", borderwidth=1)
        self.tree = ttk.Treeview(self, columns=columns, show="headings", selectmode="browse")
        for col, width in zip(columns, (300,150,150,200,300,150)):
            self.tree.heading(col, text=col, command=partial(treeview_sort_column, self.tree, col, False))
            self.tree.column(col, width=width, anchor="w")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        self.tree.bind("<Double-1>", self.on_double_click)
        btn_frame = tk.Frame(self, bg=self.theme["bg"])
        btn_frame.pack(fill=tk.X, padx=15, pady=10)
        btn_texts = [t("connect"), t("add"), t("modify"), t("delete"), t("manage_groups"), t("options")]
        btn_commands = [self.action_connect, self.action_add, self.action_modify, self.action_delete, self.manage_groups, self.options_menu]
        for i, (txt, cmd) in enumerate(zip(btn_texts, btn_commands)):
            tk.Button(btn_frame, text=txt, command=cmd, font=self.font_main,
                      bg=self.theme["button_bg"], fg=self.theme["button_fg"], relief="flat").grid(row=0, column=i, padx=10, sticky="ew")
        for i in range(len(btn_texts)):
            btn_frame.grid_columnconfigure(i, weight=1)
    
    def on_double_click(self, event):
        col = self.tree.identify_column(event.x)
        if col == "#5":
            self.action_view_note()
        else:
            region = self.tree.identify("region", event.x, event.y)
            if region == "heading":
                return
            row = self.get_selected_row()
            if row:
                self.connect_connection(row)
    
    def refresh_table(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        data = load_connections()
        filter_text = self.search_var.get().lower()
        if filter_text:
            data = [row for row in data if any(filter_text in str(field).lower() for field in row)]
        for row in data:
            display_row = row.copy()
            display_row[4] = format_note(row[4])
            self.tree.insert("", tk.END, values=display_row)
        for col in self.tree["columns"]:
            self.tree.heading(col, command=partial(treeview_sort_column, self.tree, col, False))
    
    def get_selected_row(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo(t("info"), t("select_connection"), parent=self)
            return None
        full_data = load_connections()
        selected = self.tree.item(sel[0])["values"]
        for row in full_data:
            if row[0] == selected[0] and row[5] == selected[5]:
                return row
        return selected
    
    def action_connect(self):
        row = self.get_selected_row()
        if row:
            self.connect_connection(row)
    
    def action_add(self):
        if window_exists(self, t("add_connection_title")):
            return
        self.add_connection()
    
    def action_modify(self):
        row = self.get_selected_row()
        if row:
            if window_exists(self, t("modify_connection_title")):
                return
            self.modify_connection(row)
    
    def action_delete(self):
        row = self.get_selected_row()
        if row and messagebox.askyesno(t("confirm"), f"{t('delete_connection')} {row[0]} ?", parent=self):
            delete_connection((row[0], row[5]))
            messagebox.showinfo(t("info"), t("connection_deleted"), parent=self)
            self.refresh_table()
    
    def action_view_note(self):
        row = self.get_selected_row()
        if row:
            full_note = ""
            for r in load_connections():
                if r[0] == row[0] and r[5] == row[5]:
                    full_note = r[4]
                    break
            top = tk.Toplevel(self)
            top.transient(self)
            top.iconphoto(False, self.logo)
            top.title(t("note_full"))
            top.geometry("600x400")
            top.configure(bg=self.theme["bg"])
            tk.Label(top, text=f"{t('note_for')} {row[0]}:", font=("Segoe Script", 12),
                     bg=self.theme["bg"], fg=self.theme["button_fg"]).pack(pady=10)
            text = tk.Text(top, font=("Segoe Script", 12), bg=self.theme["entry_bg"], fg=self.theme["button_fg"],
                            wrap=tk.WORD, height=15, width=70, relief="flat")
            text.insert(tk.END, full_note)
            text.config(state="disabled")
            text.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)
            tk.Button(top, text=t("return"), command=top.destroy, font=("Segoe Script", 12),
                      bg=self.theme["button_bg"], fg=self.theme["button_fg"], relief="flat", width=12).pack(pady=10)
    
    def prompt_rdp_connection(self, ip):
        login = simpledialog.askstring("Login", "Entrez votre login :", parent=self)
        pwd = simpledialog.askstring("Mot de passe", "Entrez votre mot de passe :", show="*", parent=self)
        if login and pwd:
            row = [ip, ip, login, "N/A", "", ""]
            self.connect_connection(row, pwd_provided=pwd)
        else:
            messagebox.showerror("Erreur", "Login ou mot de passe non fourni.", parent=self)
    
    def add_connection(self):
        if window_exists(self, t("add_connection_title")):
            return
        top = tk.Toplevel(self)
        top.transient(self)
        top.iconphoto(False, self.logo)
        top.title(t("add_connection_title"))
        top.geometry("650x300")
        top.configure(bg=self.theme["bg"])
        top.resizable(False, False)
        tk.Label(top, text=t("name"), font=("Segoe Script", 12), bg=self.theme["bg"], fg=self.theme["button_fg"]).grid(row=0, column=0, padx=15, pady=8, sticky="e")
        e_name = tk.Entry(top, font=("Segoe Script", 12), bg=self.theme["entry_bg"], fg=self.theme["button_fg"], relief="flat", width=50)
        e_name.grid(row=0, column=1, padx=15, pady=8, sticky="w")
        tk.Label(top, text=t("ip"), font=("Segoe Script", 12), bg=self.theme["bg"], fg=self.theme["button_fg"]).grid(row=1, column=0, padx=15, pady=8, sticky="e")
        e_ip = tk.Entry(top, font=("Segoe Script", 12), bg=self.theme["entry_bg"], fg=self.theme["button_fg"], relief="flat", width=50)
        e_ip.grid(row=1, column=1, padx=15, pady=8, sticky="w")
        tk.Label(top, text=t("login"), font=("Segoe Script", 12), bg=self.theme["bg"], fg=self.theme["button_fg"]).grid(row=2, column=0, padx=15, pady=8, sticky="e")
        e_login = tk.Entry(top, font=("Segoe Script", 12), bg=self.theme["entry_bg"], fg=self.theme["button_fg"], relief="flat", width=50)
        e_login.grid(row=2, column=1, padx=15, pady=8, sticky="w")
        tk.Label(top, text=t("group"), font=("Segoe Script", 12), bg=self.theme["bg"], fg=self.theme["button_fg"]).grid(row=3, column=0, padx=15, pady=8, sticky="e")
        existing_groups = get_existing_groups()
        group_var = tk.StringVar()
        group_options = existing_groups if existing_groups else []
        group_frame = tk.Frame(top, bg=self.theme["bg"])
        group_frame.grid(row=3, column=1, padx=15, pady=8, sticky="w")
        group_cb = ttk.Combobox(group_frame, textvariable=group_var, values=group_options, font=("Segoe Script", 12), width=45, state="readonly")
        group_cb.grid(row=0, column=0, sticky="w")
        if group_options:
            group_cb.set(group_options[0])
        app = self
        plus_btn = tk.Button(group_frame, text="+", command=lambda: app.add_group(top, group_cb, group_var),
                              font=("Segoe Script", 10), bg=self.theme["button_bg"], fg=self.theme["button_fg"], relief="flat", width=1)
        plus_btn.grid(row=0, column=1, padx=(5,0), sticky="w")
        top.note = ""
        note_frame = tk.Frame(top, bg=self.theme["bg"])
        note_frame.grid(row=4, column=0, columnspan=2, pady=8)
        tk.Button(note_frame, text=t("add_note"), command=lambda: self.open_note_window(top),
                  font=("Segoe Script", 12), bg=self.theme["button_bg"], fg=self.theme["button_fg"], relief="flat", width=20).pack(pady=5)
        btn_frame_top = tk.Frame(top, bg=self.theme["bg"])
        btn_frame_top.grid(row=5, column=0, columnspan=2, pady=8)
        tk.Button(btn_frame_top, text=t("save"), command=lambda: self.save_new_connection(top, e_name, e_ip, e_login, group_var, top.note),
                  font=("Segoe Script", 12), bg=self.theme["button_bg"], fg=self.theme["button_fg"], relief="flat", width=12).pack(side=tk.LEFT, padx=15, expand=True)
        tk.Button(btn_frame_top, text=t("return"), command=top.destroy,
                  font=("Segoe Script", 12), bg=self.theme["button_bg"], fg=self.theme["button_fg"], relief="flat", width=12).pack(side=tk.LEFT, padx=15, expand=True)
    
    def open_note_window(self, parent):
        if window_exists(self, t("add_note_title")):
            return
        top = tk.Toplevel(self)
        top.transient(self)
        top.iconphoto(False, self.logo)
        top.title(t("add_note_title"))
        top.geometry("600x350")
        top.configure(bg=self.theme["bg"])
        tk.Label(top, text=t("add_note"), font=("Segoe Script", 12), bg=self.theme["bg"], fg=self.theme["button_fg"]).pack(pady=10)
        text = tk.Text(top, font=("Segoe Script", 12), bg=self.theme["entry_bg"], fg=self.theme["button_fg"],
                        wrap=tk.WORD, height=10, width=70, relief="flat")
        text.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)
        btn_frame = tk.Frame(top, bg=self.theme["bg"])
        btn_frame.pack(pady=20)
        def save_note():
            parent.note = text.get("1.0", tk.END).strip()
            top.destroy()
        tk.Button(btn_frame, text=t("save"), command=save_note,
                  font=("Segoe Script", 12), bg=self.theme["button_bg"], fg=self.theme["button_fg"], relief="flat", width=12).pack(side=tk.LEFT, padx=20, expand=True)
        tk.Button(btn_frame, text=t("return"), command=top.destroy,
                  font=("Segoe Script", 12), bg=self.theme["button_bg"], fg=self.theme["button_fg"], relief="flat", width=12).pack(side=tk.LEFT, padx=20, expand=True)
    
    def save_new_connection(self, top, e_name, e_ip, e_login, group_var, note_value):
        name_val = e_name.get().strip()
        ip_val = e_ip.get().strip()
        login_val = e_login.get().strip()
        group_val = group_var.get().strip()
        if not name_val or not ip_val or not login_val or not group_val:
            messagebox.showerror(t("error"), t("all_fields_required"), parent=top)
            return
        for r in load_connections():
            if r[0] == name_val:
                messagebox.showerror(t("error"), t("error_duplicate_name", name=name_val), parent=top)
                return
        if any(r[1] == ip_val for r in load_connections()):
            if not messagebox.askyesno(t("warning"), t("warning_duplicate_ip", ip=ip_val), parent=top):
                return
        new_row = [name_val, ip_val, login_val, "N/A", note_value, group_val]
        data = load_connections()
        data.append(new_row)
        save_connections(data)
        messagebox.showinfo(t("info"), t("connection_added"), parent=top)
        top.destroy()
        self.refresh_table()
    
    def modify_connection(self, original_row):
        if window_exists(self, t("modify_connection_title")):
            return
        top = tk.Toplevel(self)
        top.transient(self)
        top.iconphoto(False, self.logo)
        top.title(t("modify_connection_title"))
        top.geometry("650x300")
        top.configure(bg=self.theme["bg"])
        top.resizable(False, False)
        tk.Label(top, text=t("name"), font=("Segoe Script", 12), bg=self.theme["bg"], fg=self.theme["button_fg"]).grid(row=0, column=0, padx=15, pady=8, sticky="e")
        e_name = tk.Entry(top, font=("Segoe Script", 12), bg=self.theme["entry_bg"], fg=self.theme["button_fg"], relief="flat", width=50)
        e_name.insert(0, original_row[0])
        e_name.grid(row=0, column=1, padx=15, pady=8, sticky="w")
        tk.Label(top, text=t("ip"), font=("Segoe Script", 12), bg=self.theme["bg"], fg=self.theme["button_fg"]).grid(row=1, column=0, padx=15, pady=8, sticky="e")
        e_ip = tk.Entry(top, font=("Segoe Script", 12), bg=self.theme["entry_bg"], fg=self.theme["button_fg"], relief="flat", width=50)
        e_ip.insert(0, original_row[1])
        e_ip.grid(row=1, column=1, padx=15, pady=8, sticky="w")
        tk.Label(top, text=t("login"), font=("Segoe Script", 12), bg=self.theme["bg"], fg=self.theme["button_fg"]).grid(row=2, column=0, padx=15, pady=8, sticky="e")
        e_login = tk.Entry(top, font=("Segoe Script", 12), bg=self.theme["entry_bg"], fg=self.theme["button_fg"], relief="flat", width=50)
        e_login.insert(0, original_row[2])
        e_login.grid(row=2, column=1, padx=15, pady=8, sticky="w")
        tk.Label(top, text=t("group"), font=("Segoe Script", 12), bg=self.theme["bg"], fg=self.theme["button_fg"]).grid(row=3, column=0, padx=15, pady=8, sticky="e")
        existing_groups = get_existing_groups()
        group_var = tk.StringVar(value=original_row[5] if original_row[5] else "")
        group_options = existing_groups if existing_groups else []
        group_frame = tk.Frame(top, bg=self.theme["bg"])
        group_frame.grid(row=3, column=1, padx=15, pady=8, sticky="w")
        group_cb = ttk.Combobox(group_frame, textvariable=group_var, values=group_options, font=("Segoe Script", 12), width=45, state="readonly")
        group_cb.grid(row=0, column=0, sticky="w")
        if original_row[5] in group_options:
            group_cb.set(original_row[5])
        app = self
        plus_btn = tk.Button(group_frame, text="+", command=lambda: app.add_group(top, group_cb, group_var),
                              font=("Segoe Script", 10), bg=self.theme["button_bg"], fg=self.theme["button_fg"], relief="flat", width=1)
        plus_btn.grid(row=0, column=1, padx=(5,0), sticky="w")
        btn_frame_top = tk.Frame(top, bg=self.theme["bg"])
        btn_frame_top.grid(row=4, column=0, columnspan=2, pady=8)
        tk.Button(btn_frame_top, text=t("modify_note_title"), command=lambda: self.edit_connection_note(original_row),
                  font=("Segoe Script", 12), bg=self.theme["button_bg"], fg=self.theme["button_fg"], relief="flat", width=15).pack(side=tk.LEFT, padx=10)
        btn_frame_bottom = tk.Frame(top, bg=self.theme["bg"])
        btn_frame_bottom.grid(row=5, column=0, columnspan=2, pady=8)
        tk.Button(btn_frame_bottom, text=t("save"), command=lambda: self.save_modification(top, e_name, e_ip, e_login, group_var, original_row),
                  font=("Segoe Script", 12), bg=self.theme["button_bg"], fg=self.theme["button_fg"], relief="flat", width=12).pack(side=tk.LEFT, padx=10, expand=True)
        tk.Button(btn_frame_bottom, text=t("return"), command=top.destroy,
                  font=("Segoe Script", 12), bg=self.theme["button_bg"], fg=self.theme["button_fg"], relief="flat", width=12).pack(side=tk.LEFT, padx=10, expand=True)
    
    def save_modification(self, top, e_name, e_ip, e_login, group_var, original_row):
        new_name = e_name.get().strip() or original_row[0]
        new_ip = e_ip.get().strip() or original_row[1]
        new_login = e_login.get().strip() or original_row[2]
        new_group = group_var.get().strip() or original_row[5]
        if new_name != original_row[0]:
            for r in load_connections():
                if r[0] == new_name:
                    messagebox.showerror(t("error"), t("error_duplicate_name", name=new_name), parent=top)
                    return
        if new_ip != original_row[1]:
            if any(r[1] == new_ip for r in load_connections()):
                if not messagebox.askyesno(t("warning"), t("warning_duplicate_ip", ip=new_ip), parent=top):
                    return
        new_row = [new_name, new_ip, new_login, original_row[3], original_row[4], new_group]
        data = load_connections()
        for i, r in enumerate(data):
            if r == original_row:
                data[i] = new_row
                break
        save_connections(data)
        messagebox.showinfo(t("info"), t("connection_modified"), parent=top)
        top.destroy()
        self.refresh_table()
    
    def manage_groups(self):
        if window_exists(self, t("manage_groups_title")):
            return
        top = tk.Toplevel(self)
        top.transient(self)
        top.grab_set()
        top.attributes("-topmost", True)
        top.iconphoto(False, self.logo)
        top.title(t("manage_groups_title"))
        top.geometry("500x400")
        top.configure(bg=self.theme["bg"])
        tk.Label(top, text=t("existing_groups"), font=self.font_main, bg=self.theme["bg"], fg=self.theme["button_fg"]).pack(pady=10)
        listbox = tk.Listbox(top, font=self.font_main, bg=self.theme["entry_bg"], fg=self.theme["button_fg"], selectmode=tk.SINGLE)
        listbox.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        groups = get_existing_groups()
        for grp in groups:
            listbox.insert(tk.END, grp)
        btn_frame = tk.Frame(top, bg=self.theme["bg"])
        btn_frame.pack(pady=10)
        def add_new_group():
            new_grp = simpledialog.askstring(t("add_group_option"), t("enter_new_group"), parent=top)
            if new_grp:
                groups = get_existing_groups()
                if new_grp not in groups:
                    groups.append(new_grp)
                    with open(GROUPS_FILE, "a", encoding="utf-8") as gf:
                        gf.write(new_grp + "\n")
                    listbox.insert(tk.END, new_grp)
        def delete_selected():
            sel = listbox.curselection()
            if not sel:
                messagebox.showinfo(t("info"), t("select_group"), parent=top)
                return
            grp = listbox.get(sel[0])
            if messagebox.askyesno(t("confirm"), f"{t('delete')} '{grp}' ?", parent=top):
                delete_group_from_storage(grp)
                listbox.delete(sel[0])
                messagebox.showinfo(t("info"), f"{grp} {t('delete')}.\nLes connexions l'utilisant seront vidées.", parent=top)
                self.refresh_table()
        tk.Button(btn_frame, text=t("add_group_option"), command=add_new_group, font=self.font_main,
                  bg=self.theme["button_bg"], fg=self.theme["button_fg"], relief="flat", width=12).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text=t("delete"), command=delete_selected, font=self.font_main,
                  bg=self.theme["button_bg"], fg=self.theme["button_fg"], relief="flat", width=12).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text=t("return"), command=top.destroy, font=self.font_main,
                  bg=self.theme["button_bg"], fg=self.theme["button_fg"], relief="flat", width=12).pack(side=tk.LEFT, padx=10)
    
    def options_menu(self):
        if window_exists(self, t("options")):
            return
        top = tk.Toplevel(self)
        top.transient(self)
        top.grab_set()
        top.attributes("-topmost", True)
        top.iconphoto(False, self.logo)
        top.title(t("options"))
        top.geometry("450x390")
        top.configure(bg=self.theme["bg"])
        btn_frame = tk.Frame(top, bg=self.theme["bg"])
        btn_frame.pack(expand=True, fill=tk.BOTH, pady=10)
        tk.Button(btn_frame, text=t("save_configuration_option"), command=lambda: [top.destroy(), self.save_configuration()], font=self.font_main,
                  bg=self.theme["button_bg"], fg=self.theme["button_fg"], relief="flat", width=30).pack(pady=5)
        tk.Button(btn_frame, text=t("export_configuration_option"), command=lambda: [top.destroy(), self.export_configuration()], font=self.font_main,
                  bg=self.theme["button_bg"], fg=self.theme["button_fg"], relief="flat", width=30).pack(pady=5)
        tk.Button(btn_frame, text=t("import_configuration_option"), command=lambda: [top.destroy(), self.import_configuration()], font=self.font_main,
                  bg=self.theme["button_bg"], fg=self.theme["button_fg"], relief="flat", width=30).pack(pady=5)
        tk.Button(btn_frame, text=t("delete_configuration_option"), command=lambda: [top.destroy(), self.delete_configuration()], font=self.font_main,
                  bg=self.theme["button_bg"], fg=self.theme["button_fg"], relief="flat", width=30).pack(pady=5)
        tk.Button(btn_frame, text=t("update_option"), command=lambda: [top.destroy(), threading.Thread(target=check_for_update, args=(self, True), daemon=True).start()], font=self.font_main,
                  bg=self.theme["button_bg"], fg=self.theme["button_fg"], relief="flat", width=30).pack(pady=5)
        tk.Button(btn_frame, text=t("support_option"), command=lambda: [top.destroy(), webbrowser.open("https://github.com/Equinoxx83/SwiftRDP/issues")], font=self.font_main,
                  bg=self.theme["button_bg"], fg=self.theme["button_fg"], relief="flat", width=30).pack(pady=5)
        tk.Button(btn_frame, text=t("view_patch_note"),
                  command=lambda: [top.destroy(), self.show_patch_note_dialog(read_patch_note(), show_checkbox=False)], font=self.font_main,
                  bg=self.theme["button_bg"], fg=self.theme["button_fg"], relief="flat", width=30).pack(pady=5)
        tk.Button(btn_frame, text=t("preferences"), command=lambda: [top.destroy(), self.preferences_menu()], font=self.font_main,
                  bg=self.theme["button_bg"], fg=self.theme["button_fg"], relief="flat", width=30).pack(pady=5)
    
    def display_mode_menu(self):
        top = tk.Toplevel(self)
        top.transient(self)
        top.grab_set()
        top.attributes("-topmost", True)
        top.iconphoto(False, self.logo)
        top.title(t("display_mode"))
        top.geometry("400x220")
        top.configure(bg=self.theme["bg"])
        mode_var = tk.StringVar(value=CONN_DISPLAY_MODE)
        tk.Radiobutton(top, text=t("fenetres"), variable=mode_var, value="fenetres",
                       bg=self.theme["bg"], fg=self.theme["button_fg"], font=self.font_main).pack(anchor="w", padx=20, pady=10)
        tk.Radiobutton(top, text=t("onglets"), variable=mode_var, value="onglets",
                       bg=self.theme["bg"], fg=self.theme["button_fg"], font=self.font_main).pack(anchor="w", padx=20, pady=10)
        def save_mode():
            global CONN_DISPLAY_MODE
            CONN_DISPLAY_MODE = mode_var.get()
            with open(DISPLAY_MODE_FILE, "w", encoding="utf-8") as f:
                f.write(CONN_DISPLAY_MODE)
            if CONN_DISPLAY_MODE == "onglets":
                messagebox.showinfo(t("info"), "Option 'Onglets' non supportée pour l'instant.\nLes connexions s'ouvriront dans des fenêtres séparées.", parent=top)
            else:
                messagebox.showinfo(t("info"), "Mode d'affichage enregistré.", parent=top)
            top.destroy()
        tk.Button(top, text=t("save"), command=save_mode, font=self.font_main,
                  bg=self.theme["button_bg"], fg=self.theme["button_fg"], relief="flat", width=12).pack(pady=20)
        top.lift()
        top.attributes("-topmost", True)
    
    def preferences_menu(self):
        if window_exists(self, t("preferences")):
            return
        top = tk.Toplevel(self)
        top.transient(self)
        top.grab_set()
        top.attributes("-topmost", True)
        top.iconphoto(False, self.logo)
        top.title(t("preferences"))
        top.geometry("420x450")
        top.configure(bg=self.theme["bg"])
        # Section Langue
        lang_frame = tk.Frame(top, bg=self.theme["bg"])
        lang_frame.pack(pady=10)
        tk.Label(lang_frame, text=t("language"), font=self.font_main, bg=self.theme["bg"], fg=self.theme["button_fg"]).pack(anchor="w", padx=10)
        lang_var = tk.StringVar(value=CURRENT_LANG)
        if CURRENT_THEME=="dark":
            sel_color = "#dddddd"
            unsel_color = "#555555"
        else:
            sel_color = "#d0d0d0"
            unsel_color = "#eeeeee"
        btn_lang_fr = tk.Button(lang_frame, text="Français", font=self.font_main, width=10,
                                 command=lambda: [lang_var.set("fr"), btn_lang_fr.config(bg=sel_color), btn_lang_en.config(bg=unsel_color)],
                                 bg=sel_color if CURRENT_LANG=="fr" else unsel_color, fg="black")
        btn_lang_en = tk.Button(lang_frame, text="English", font=self.font_main, width=10,
                                 command=lambda: [lang_var.set("en"), btn_lang_en.config(bg=sel_color), btn_lang_fr.config(bg=unsel_color)],
                                 bg=sel_color if CURRENT_LANG=="en" else unsel_color, fg="black")
        btn_lang_fr.pack(side=tk.LEFT, padx=10)
        btn_lang_en.pack(side=tk.LEFT, padx=10)
    
        # Section Thème
        theme_frame = tk.Frame(top, bg=self.theme["bg"])
        theme_frame.pack(pady=10)
        tk.Label(theme_frame, text=t("theme"), font=self.font_main, bg=self.theme["bg"], fg=self.theme["button_fg"]).pack(anchor="w", padx=10)
        theme_var = tk.StringVar(value=CURRENT_THEME)
        btn_theme_dark = tk.Button(theme_frame, text=t("dark"), font=self.font_main, width=10,
                                   command=lambda: [theme_var.set("dark"), btn_theme_dark.config(bg=sel_color), btn_theme_light.config(bg=unsel_color)],
                                   bg=sel_color if CURRENT_THEME=="dark" else unsel_color, fg="black")
        btn_theme_light = tk.Button(theme_frame, text=t("light"), font=self.font_main, width=10,
                                    command=lambda: [theme_var.set("light"), btn_theme_light.config(bg=sel_color), btn_theme_dark.config(bg=unsel_color)],
                                    bg=sel_color if CURRENT_THEME=="light" else unsel_color, fg="black")
        btn_theme_dark.pack(side=tk.LEFT, padx=10)
        btn_theme_light.pack(side=tk.LEFT, padx=10)
    
        # Section Mot de passe
        pwd_frame = tk.Frame(top, bg=self.theme["bg"])
        pwd_frame.pack(pady=10, padx=10, fill=tk.X)
        tk.Label(pwd_frame, text="Définir/modifier mot de passe de l'application :", font=self.font_main, bg=self.theme["bg"], fg=self.theme["button_fg"]).pack(anchor="w", pady=5)
        sub_pwd_frame = tk.Frame(pwd_frame, bg=self.theme["bg"])
        sub_pwd_frame.pack(pady=5)
        tk.Label(sub_pwd_frame, text="Mot de passe actuel :", font=self.font_main, bg=self.theme["bg"], fg=self.theme["button_fg"]).grid(row=0, column=0, padx=5, pady=2, sticky="e")
        current_pwd = tk.Entry(sub_pwd_frame, show="*", width=20)
        current_pwd.grid(row=0, column=1, padx=5, pady=2)
        tk.Label(sub_pwd_frame, text="Nouveau mot de passe :", font=self.font_main, bg=self.theme["bg"], fg=self.theme["button_fg"]).grid(row=1, column=0, padx=5, pady=2, sticky="e")
        new_pwd = tk.Entry(sub_pwd_frame, show="*", width=20)
        new_pwd.grid(row=1, column=1, padx=5, pady=2)
        tk.Label(sub_pwd_frame, text="Confirmez :", font=self.font_main, bg=self.theme["bg"], fg=self.theme["button_fg"]).grid(row=2, column=0, padx=5, pady=2, sticky="e")
        conf_pwd = tk.Entry(sub_pwd_frame, show="*", width=20)
        conf_pwd.grid(row=2, column=1, padx=5, pady=2)
    
        def prompt_default_rdp():
            if messagebox.askyesno("Application par défaut", t("default_rdp_label"), parent=top):
                with open(DEFAULT_RDP_FILE, "w", encoding="utf-8") as f:
                    f.write("yes")
                subprocess.call(["xdg-mime", "default", "SwiftRDP.desktop", "x-scheme-handler/rdp"])
                messagebox.showinfo(t("info"), "SwiftRDP est désormais défini comme application RDP par défaut.", parent=top)
            else:
                with open(DEFAULT_RDP_FILE, "w", encoding="utf-8") as f:
                    f.write("no")
        tk.Button(top, text=t("default_rdp_label"), command=prompt_default_rdp, font=self.font_main,
                  bg=self.theme["button_bg"], fg=self.theme["button_fg"], relief="flat", width=35).pack(pady=10)
    
        def save_preferences():
            global CURRENT_LANG, CURRENT_THEME
            if current_pwd.get().strip() or new_pwd.get().strip() or conf_pwd.get().strip():
                if os.path.exists(PASSWORD_FILE):
                    with open(PASSWORD_FILE, "r", encoding="utf-8") as f:
                        stored_hash = f.read().strip()
                    if not current_pwd.get().strip() or hash_password(current_pwd.get().strip()) != stored_hash:
                        messagebox.showerror("Erreur", "Mot de passe actuel incorrect.", parent=top)
                        return
                if new_pwd.get().strip():
                    if new_pwd.get().strip() != conf_pwd.get().strip():
                        messagebox.showerror("Erreur", "Les mots de passe ne correspondent pas.", parent=top)
                        return
                    else:
                        with open(PASSWORD_FILE, "w", encoding="utf-8") as f:
                            f.write(hash_password(new_pwd.get().strip()))
                else:
                    if os.path.exists(PASSWORD_FILE):
                        os.remove(PASSWORD_FILE)
            new_lang = lang_var.get()
            new_theme = theme_var.get()
            changed = (new_lang != CURRENT_LANG) or (new_theme != CURRENT_THEME)
            if changed:
                CURRENT_LANG = new_lang
                CURRENT_THEME = new_theme
                with open(LANGUAGE_FILE, "w", encoding="utf-8") as f:
                    f.write(CURRENT_LANG)
                with open(THEME_FILE, "w", encoding="utf-8") as f:
                    f.write(CURRENT_THEME)
                messagebox.showinfo(t("info"), t("language_saved_restart"), parent=top)
                top.destroy()
                subprocess.Popen(["/bin/bash", os.path.join(PROJECT_DIR, "SwiftRDP.sh")])
                self.destroy()
                sys.exit(0)
            else:
                top.destroy()
        tk.Button(top, text=t("save"), command=save_preferences, font=self.font_main,
                  bg=self.theme["button_bg"], fg=self.theme["button_fg"], relief="flat", width=12).pack(pady=10)
    
    def set_app_password(self):
        messagebox.showinfo("Info", "Le changement de mot de passe se fait dans l'onglet Préférences.", parent=self)
    
    def save_configuration(self):
        dest = filedialog.askdirectory(title=t("choose_backup_directory"), parent=self)
        if dest:
            zip_path = backup_configuration(dest, export=False)
            messagebox.showinfo(t("info"), t("configuration_saved", path=zip_path), parent=self)
    
    def export_configuration(self):
        self.tk.call('tk', 'scaling', 2.5)
        dest = filedialog.askdirectory(title=t("choose_export_directory"), parent=self)
        self.tk.call('tk', 'scaling', 1.0)
        if dest:
            zip_path = backup_configuration(dest, export=True)
            messagebox.showinfo(t("info"), t("configuration_exported", path=zip_path), parent=self)
    
    def import_configuration(self):
        self.tk.call('tk', 'scaling', 2.5)
        zip_file = filedialog.askopenfilename(title=t("select_import_file"),
                                              filetypes=[("Fichiers Zip", "*.zip")], parent=self)
        self.tk.call('tk', 'scaling', 1.0)
        if zip_file:
            import_configuration_func(zip_file)
            messagebox.showinfo(t("info"), t("configuration_imported"), parent=self)
            self.refresh_table()
    
    def delete_configuration(self):
        conn_deleted = messagebox.askyesno(t("confirm"), t("delete_all_connections"), parent=self)
        if conn_deleted:
            open(FILE_CONNS, "w", encoding="utf-8").close()
        group_deleted = messagebox.askyesno(t("confirm"), t("delete_all_groups"), parent=self)
        if group_deleted:
            open(GROUPS_FILE, "w", encoding="utf-8").close()
            data = load_connections()
            for i, row in enumerate(data):
                row[5] = ""
            save_connections(data)
        if conn_deleted or group_deleted:
            self.lift()
            self.attributes("-topmost", True)
            messagebox.showinfo(t("info"), t("configuration_deleted"), parent=self)
            self.attributes("-topmost", False)
        self.refresh_table()
    
    def update_SwiftRDP(self):
        def progress_and_restart():
            progress_win = tk.Toplevel(self)
            progress_win.title(t("update_complete"))
            progress_win.geometry("400x100")
            progress_win.configure(bg=self.theme["bg"])
            tk.Label(progress_win, text=t("update_in_progress_t"), font=self.font_main,
                     bg=self.theme["bg"], fg=self.theme["button_fg"]).pack(pady=10)
            pb = ttk.Progressbar(progress_win, mode="determinate", maximum=100)
            pb.pack(fill=tk.X, padx=20, pady=10)
            for i in range(101):
                pb['value'] = i
                progress_win.update()
                time.sleep(0.1)
            progress_win.destroy()
            subprocess.Popen(["/bin/bash", os.path.join(PROJECT_DIR, "SwiftRDP.sh")])
            self.destroy()
            sys.exit(0)
        threading.Thread(target=progress_and_restart, daemon=True).start()
    
    def support(self):
        webbrowser.open("https://github.com/Equinoxx83/SwiftRDP/issues")
    
    def edit_connection_note(self, row):
        if window_exists(self, t("modify_note_title")):
            return
        top = tk.Toplevel(self)
        top.transient(self)
        top.iconphoto(False, self.logo)
        top.title(t("modify_note_title"))
        top.geometry("600x350")
        top.configure(bg=self.theme["bg"])
        tk.Label(top, text=f"{t('note_for')} {row[0]}:", font=("Segoe Script", 12),
                 bg=self.theme["bg"], fg=self.theme["button_fg"]).pack(pady=10)
        text = tk.Text(top, font=("Segoe Script", 12), bg=self.theme["entry_bg"], fg=self.theme["button_fg"],
                        wrap=tk.WORD, height=10, width=70, relief="flat")
        text.insert(tk.END, row[4])
        text.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)
        btn_frame = tk.Frame(top, bg=self.theme["bg"])
        btn_frame.pack(pady=20)
        tk.Button(btn_frame, text=t("save"), command=lambda: self.save_note(top, text, row),
                  font=("Segoe Script", 12), bg=self.theme["button_bg"], fg=self.theme["button_fg"], relief="flat", width=12).pack(side=tk.LEFT, padx=20, expand=True)
        tk.Button(btn_frame, text=t("return"), command=top.destroy,
                  font=("Segoe Script", 12), bg=self.theme["button_bg"], fg=self.theme["button_fg"], relief="flat", width=12).pack(side=tk.LEFT, padx=20, expand=True)
    
    def save_note(self, top, text, row):
        new_note = text.get("1.0", tk.END).strip()
        new_row = row.copy()
        new_row[4] = new_note
        update_connection_by_value(row, new_row)
        messagebox.showinfo(t("info"), "Note mise à jour.", parent=top)
        top.destroy()
        self.refresh_table()

if __name__ == "__main__":
    app = RDPApp()
    threading.Thread(target=socket_listener, args=(app,), daemon=True).start()
    if len(sys.argv) > 1 and sys.argv[1].startswith("rdp://"):
        ip = sys.argv[1][len("rdp://"):]
        app.after(100, lambda: app.prompt_rdp_connection(ip))
    app.withdraw()
    if not check_password(app):
        sys.exit(1)
    app.deiconify()
    app.mainloop()
