#!/bin/bash
# FastRDP.sh – Vérifie les dépendances, vérifie la mise à jour et lance l'application FastRDP

if ! command -v zenity >/dev/null 2>&1; then
      sudo apt update && sudo apt install -y zenity || exit 1
  fi

# --- Vérification de Python3 ---
if ! command -v python3 >/dev/null 2>&1; then
  if zenity --question --title="Dépendance manquante" --text="python3 n'est pas installé. Voulez-vous l'installer ?" --width=300; then
      sudo apt update && sudo apt install -y python3 || exit 1
  else
      zenity --error --text="python3 est requis. Arrêt." --width=300
      exit 1
  fi
fi

# --- Vérification de pip3 ---
if ! command -v pip3 >/dev/null 2>&1; then
  if zenity --question --title="Dépendance manquante" --text="pip3 n'est pas installé. Voulez-vous l'installer ?" --width=300; then
      sudo apt update && sudo apt install -y python3-pip || exit 1
  else
      zenity --error --text="pip3 est requis. Arrêt." --width=300
      exit 1
  fi
fi

# --- Vérification de Tkinter ---
python3 -c "import tkinter" 2>/dev/null
if [ $? -ne 0 ]; then
  if zenity --question --title="Dépendance manquante" --text="Tkinter n'est pas disponible. Voulez-vous l'installer ?" --width=300; then
      sudo apt update && sudo apt install -y python3-tk || exit 1
  else
      zenity --error --text="Tkinter est requis. Arrêt." --width=300
      exit 1
  fi
fi

# --- Vérification de xfreerdp ---
if ! command -v xfreerdp >/dev/null 2>&1; then
    sess_type=$(echo "$XDG_SESSION_TYPE")
    if [ "$sess_type" = "wayland" ]; then
        pkg="freerdp2-wayland"
    else
        pkg="freerdp2-x11"
    fi
    if zenity --question --title="Dépendance manquante" --text="Le paquet '$pkg' n'est pas installé. Voulez-vous l'installer ?" --width=300; then
        sudo apt update && sudo apt install -y "$pkg" || exit 1
    else
        zenity --error --text="$pkg est requis. Arrêt." --width=300
        exit 1
    fi
fi

# --- Vérification de wmctrl et git ---
if ! command -v wmctrl >/dev/null 2>&1; then
  if zenity --question --title="Dépendance manquante" --text="wmctrl n'est pas installé. Voulez-vous l'installer ?" --width=300; then
      sudo apt update && sudo apt install -y wmctrl || exit 1
  else
      zenity --error --text="wmctrl est requis. Arrêt." --width=300
      exit 1
  fi
fi

if ! command -v git >/dev/null 2>&1; then
  if zenity --question --title="Dépendance manquante" --text="git n'est pas installé. Voulez-vous l'installer ?" --width=300; then
      sudo apt-get update && sudo apt install -y git || exit 1
  else
      zenity --error --text="git est requis. Arrêt." --width=300
      exit 1
  fi
fi

# --- Lancer l'application Python intégrée ---
PYFILE=$(mktemp /tmp/FastRDP_app.XXXXXX.py)
cat > "$PYFILE" << 'EOF'
#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import subprocess, os, zipfile, shutil, tempfile, threading, time, webbrowser, sys
from datetime import datetime

# Fichiers de données et fichier de version
FILE_CONNS = "connexions.txt"
GROUPS_FILE = "groups.txt"
VERSION_FILE = "/opt/FastRDP/version.txt"  # Ce fichier doit être géré dans votre dépôt

# Mot-clé pour détecter la fenêtre RDP (à adapter si nécessaire)
REMOTE_WINDOW_KEYWORD = "FreeRDP"

# Création des fichiers s'ils n'existent pas
for file in (FILE_CONNS, GROUPS_FILE):
    if not os.path.exists(file):
        open(file, "w").close()

# Pour l'affichage dans la table, tronquer la note (remplacer les sauts de ligne par des espaces)
def format_note(note):
    display = note.replace("\n", " ")
    return display if len(display) <= 30 else display[:30] + "..."

# Fonctions de gestion des connexions
def load_connections():
    conns = []
    with open(FILE_CONNS, "r") as f:
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
    with open(FILE_CONNS, "w") as f:
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

# Fonctions de gestion des groupes
def load_groups():
    groups = []
    with open(GROUPS_FILE, "r") as f:
        for line in f:
            group = line.strip()
            if group:
                groups.append(group)
    return groups

def save_groups(groups):
    with open(GROUPS_FILE, "w") as f:
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

# Fonctions de configuration
def backup_configuration(dest_path, export=False):
    zip_name = "fastrdpexport.zip" if export else "fastrdpsave.zip"
    full_path = os.path.join(dest_path, zip_name)
    with zipfile.ZipFile(full_path, 'w') as zipf:
        for file in [FILE_CONNS, GROUPS_FILE]:
            if os.path.exists(file):
                zipf.write(file)
    return full_path

def import_configuration_func(zip_path):
    with tempfile.TemporaryDirectory() as tmpdirname:
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            zipf.extractall(tmpdirname)
        src_conn = os.path.join(tmpdirname, FILE_CONNS)
        src_groups = os.path.join(tmpdirname, GROUPS_FILE)
        if os.path.exists(src_conn):
            shutil.copy(src_conn, FILE_CONNS)
        if os.path.exists(src_groups):
            shutil.copy(src_groups, GROUPS_FILE)

def delete_configuration():
    conn_deleted = False
    group_deleted = False
    if messagebox.askyesno("Confirmer", "Voulez-vous supprimer toutes les connexions ?", parent=root):
        open(FILE_CONNS, "w").close()
        conn_deleted = True
    if messagebox.askyesno("Confirmer", "Voulez-vous supprimer tous les groupes ?", parent=root):
        open(GROUPS_FILE, "w").close()
        data = load_connections()
        for i, row in enumerate(data):
            row[5] = ""
        save_connections(data)
        group_deleted = True
    if conn_deleted or group_deleted:
        messagebox.showinfo("Info", "Configuration supprimée.", parent=root)

def treeview_sort_column(tv, col, reverse):
    data = [(tv.set(k, col), k) for k in tv.get_children('')]
    data.sort(key=lambda t: t[0].lower(), reverse=reverse)
    for index, (val, k) in enumerate(data):
        tv.move(k, '', index)
    tv.heading(col, command=lambda: treeview_sort_column(tv, col, not reverse))

def window_exists(root, title):
    for win in root.winfo_children():
        if isinstance(win, tk.Toplevel) and win.title() == title:
            win.lift()
            return True
    return False

# Vérification et mise à jour
def check_for_update(app, from_menu=False):
    repo_url = "https://maj:gldt-E5ehzz8Fys-9RWZCo9dy@gitlab.com/schneider_dorian/FastRDP.git"
    temp_dir = tempfile.mkdtemp()
    try:
        subprocess.check_call(["git", "clone", "--depth", "1", repo_url, temp_dir])
        remote_version_file = os.path.join(temp_dir, "version.txt")
        if not os.path.exists(remote_version_file):
            remote_version = ""
        else:
            with open(remote_version_file, "r") as f:
                remote_version = f.read().strip()
    except Exception:
        remote_version = ""
    finally:
        shutil.rmtree(temp_dir)
    try:
        with open(VERSION_FILE, "r") as vf:
            local_version = vf.read().strip()
    except Exception:
        local_version = ""
    if remote_version and remote_version != local_version:
        if messagebox.askyesno("Mise à jour", "Une nouvelle version est disponible. Voulez-vous mettre à jour FastRDP ?", parent=app):
            update_app(app, repo_url, remote_version)
    else:
        if from_menu:
            messagebox.showinfo("Mise à jour", "Aucune mise à jour disponible.", parent=app)

def update_app(app, repo_url, remote_version):
    temp_dir = tempfile.mkdtemp()
    try:
        subprocess.check_call(["git", "clone", "--depth", "1", repo_url, temp_dir])
        dest_dir = "/opt/FastRDP"
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
        with open(os.path.join(dest_dir, "version.txt"), "w") as vf:
            vf.write(remote_version)
        os.chmod(os.path.join(dest_dir, "FastRDP.sh"), 0o755)
    except Exception as e:
        messagebox.showerror("Erreur", f"La mise à jour a échoué:\n{e}", parent=app)
        return
    finally:
        shutil.rmtree(temp_dir)
    messagebox.showinfo("Mise à jour", "Mise à jour terminée. L'application va redémarrer.", parent=app)
    subprocess.Popen(["/bin/bash", "/opt/FastRDP/FastRDP.sh"])
    app.destroy()
    sys.exit(0)

# Classe principale de l'application FastRDP
class RDPApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.logo = tk.PhotoImage(file="/opt/FastRDP/icon.png")
        self.iconphoto(False, self.logo)
        self.title("FastRDP")
        self.geometry("1600x900")
        self.configure(bg="#2b2b2b")
        self.font_main = ("Segoe Script", 12)
        self.font_heading = ("Segoe Script", 12)
        self.create_widgets()
        self.refresh_table()
        threading.Thread(target=check_for_update, args=(self,), daemon=True).start()

    # Méthode add_group (utilisée par le bouton "+")
    def add_group(self, parent, combobox, var):
        new_grp = simpledialog.askstring("Nouveau groupe", "Entrez le nom du nouveau groupe:", parent=parent)
        if new_grp:
            groups = get_existing_groups()
            if new_grp not in groups:
                groups.append(new_grp)
                with open(GROUPS_FILE, "a") as gf:
                    gf.write(new_grp + "\n")
            combobox["values"] = groups
            var.set(new_grp)

    def create_widgets(self):
        search_frame = tk.Frame(self, bg="#2b2b2b")
        search_frame.pack(fill=tk.X, padx=15, pady=10)
        tk.Label(search_frame, text="Recherche:", font=self.font_main, bg="#2b2b2b", fg="#c0c0c0").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *args: self.refresh_table())
        tk.Entry(search_frame, textvariable=self.search_var, font=self.font_main, bg="#3b3b3b", fg="#c0c0c0",
                 insertbackground="#c0c0c0", relief="flat").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        columns = ("Nom", "IP", "Login", "Dernière connexion", "Note", "Groupe")
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Treeview", background="#2b2b2b", fieldbackground="#2b2b2b", foreground="#c0c0c0",
                        font=self.font_main, borderwidth=0)
        style.configure("Treeview.Heading", font=self.font_heading, background="#1b1b1b",
                        foreground="#c0c0c0", relief="ridge", borderwidth=1)
        self.tree = ttk.Treeview(self, columns=columns, show="headings", selectmode="browse")
        for col, width in zip(columns, (300,150,150,200,300,150)):
            self.tree.heading(col, text=col, command=lambda _col=col: treeview_sort_column(self.tree, _col, False))
            self.tree.column(col, width=width, anchor="w")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        self.tree.bind("<Double-1>", self.on_double_click)
        # Barre de boutons : le bouton "Voir note" a été remplacé par la possibilité de double-cliquer sur la colonne "Note"
        btn_frame = tk.Frame(self, bg="#2b2b2b")
        btn_frame.pack(fill=tk.X, padx=15, pady=10)
        btn_texts = ["Se connecter", "Ajouter", "Modifier", "Supprimer", "Gérer Groupes", "Options"]
        btn_commands = [self.action_connect, self.action_add, self.action_modify, self.action_delete, self.manage_groups, self.options_menu]
        for i, (txt, cmd) in enumerate(zip(btn_texts, btn_commands)):
            tk.Button(btn_frame, text=txt, command=cmd, font=self.font_main,
                      bg="#3a3a3a", fg="#c0c0c0", relief="flat").grid(row=0, column=i, padx=10, sticky="ew")
        for i in range(len(btn_texts)):
            btn_frame.grid_columnconfigure(i, weight=1)

    def on_double_click(self, event):
        col = self.tree.identify_column(event.x)
        # Si l'utilisateur double-clique sur la colonne "Note" (colonne #5)
        if col == "#5":
            self.action_view_note()
        else:
            # Sinon, on lance la connexion
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
            self.tree.heading(col, command=lambda _col=col: treeview_sort_column(self.tree, _col, False))

    def get_selected_row(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Info", "Veuillez sélectionner une connexion.", parent=self)
            return None
        # On recherche la ligne complète dans le fichier
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
        if window_exists(self, "Ajouter Connexion"):
            return
        self.add_connection()

    def action_modify(self):
        row = self.get_selected_row()
        if row:
            if window_exists(self, "Modifier Connexion"):
                return
            self.modify_connection(row)

    def action_delete(self):
        row = self.get_selected_row()
        if row and messagebox.askyesno("Confirmer", f"Supprimer la connexion {row[0]} ?", parent=self):
            delete_connection((row[0], row[5]))
            messagebox.showinfo("Info", "Connexion supprimée.", parent=self)
            self.refresh_table()

    def action_view_note(self):
        row = self.get_selected_row()
        if row:
            # Recherche la note complète depuis le fichier
            full_note = ""
            for r in load_connections():
                if r[0] == row[0] and r[5] == row[5]:
                    full_note = r[4]
                    break
            top = tk.Toplevel(self)
            top.title("Note complète")
            top.geometry("600x400")
            top.configure(bg="#2b2b2b")
            tk.Label(top, text=f"Note pour {row[0]}:", font=("Segoe Script", 12),
                     bg="#2b2b2b", fg="#c0c0c0").pack(pady=10)
            text = tk.Text(top, font=("Segoe Script", 12), bg="#3a3a3a", fg="#c0c0c0",
                            wrap=tk.WORD, height=15, width=70, relief="flat")
            text.insert(tk.END, full_note)
            text.config(state="disabled")
            text.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)
            tk.Button(top, text="Fermer", command=top.destroy, font=("Segoe Script", 12),
                      bg="#3a3a3a", fg="#c0c0c0", relief="flat", width=12).pack(pady=10)

    def connect_connection(self, row):
        pwd = simpledialog.askstring("Mot de passe",
                                     f"Entrez le mot de passe pour {row[0]}:",
                                     show="*", parent=self)
        if not pwd:
            messagebox.showerror("Erreur", "Aucun mot de passe fourni.", parent=self)
            return
        try:
            proc = subprocess.Popen(
                ["xfreerdp", f"/v:{row[1]}", f"/u:{row[2]}", f"/p:{pwd}",
                 "/dynamic-resolution", "/cert-ignore"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, start_new_session=True)
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du lancement de xfreerdp:\n{e}", parent=self)
            return

        # Création d'une fenêtre de progression centrée
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
        progress_win.title("Connexion en cours...")
        progress_win.geometry(f"{win_width}x{win_height}+{pos_x}+{pos_y}")
        progress_win.configure(bg="#2b2b2b")
        progress_win.update_idletasks()
        tk.Label(progress_win,
                 text="Connexion en cours, veuillez patienter...",
                 font=("Segoe Script", 12), bg="#2b2b2b", fg="#c0c0c0").pack(pady=20)

        style = ttk.Style(progress_win)
        style.theme_use("clam")
        style.configure("grey.Horizontal.TProgressbar", foreground="grey", background="grey")
        pb = ttk.Progressbar(progress_win, mode="determinate", maximum=100,
                             style="grey.Horizontal.TProgressbar")
        pb.pack(fill=tk.X, padx=20, pady=10)

        progress_done = False
        def update_progress(count=0):
            nonlocal progress_done
            if progress_done:
                return
            if count <= 100:
                pb['value'] = count
                self.after(100, update_progress, count+1)
            else:
                progress_win.destroy()
        update_progress()

        def check_window():
            nonlocal progress_done
            timeout = 10
            interval = 0.5
            elapsed = 0
            found = False
            while elapsed < timeout:
                try:
                    output = subprocess.check_output(["wmctrl", "-l"], text=True)
                except Exception:
                    output = ""
                if REMOTE_WINDOW_KEYWORD.lower() in output.lower():
                    found = True
                    break
                time.sleep(interval)
                elapsed += interval
            progress_done = True
            try:
                progress_win.destroy()
            except:
                pass
            if found:
                new_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                new_row = row.copy()
                new_row[3] = new_date
                update_connection_by_value(row, new_row)
                self.after(0, self.refresh_table)
            else:
                self.after(0, lambda: messagebox.showerror("Erreur", "Connexion échouée.", parent=self))
        threading.Thread(target=check_window, daemon=True).start()

    def add_connection(self):
        if window_exists(self, "Ajouter Connexion"):
            return
        top = tk.Toplevel(self)
        top.iconphoto(False, self.logo)
        top.title("Ajouter Connexion")
        top.geometry("650x300")
        top.configure(bg="#2b2b2b")
        top.resizable(False, False)
        tk.Label(top, text="Nom:", font=("Segoe Script", 12), bg="#2b2b2b", fg="#c0c0c0").grid(row=0, column=0, padx=15, pady=8, sticky="e")
        e_name = tk.Entry(top, font=("Segoe Script", 12), bg="#3a3a3a", fg="#c0c0c0", relief="flat", width=50)
        e_name.grid(row=0, column=1, padx=15, pady=8, sticky="w")
        tk.Label(top, text="IP:", font=("Segoe Script", 12), bg="#2b2b2b", fg="#c0c0c0").grid(row=1, column=0, padx=15, pady=8, sticky="e")
        e_ip = tk.Entry(top, font=("Segoe Script", 12), bg="#3a3a3a", fg="#c0c0c0", relief="flat", width=50)
        e_ip.grid(row=1, column=1, padx=15, pady=8, sticky="w")
        tk.Label(top, text="Login:", font=("Segoe Script", 12), bg="#2b2b2b", fg="#c0c0c0").grid(row=2, column=0, padx=15, pady=8, sticky="e")
        e_login = tk.Entry(top, font=("Segoe Script", 12), bg="#3a3a3a", fg="#c0c0c0", relief="flat", width=50)
        e_login.grid(row=2, column=1, padx=15, pady=8, sticky="w")
        tk.Label(top, text="Groupe:", font=("Segoe Script", 12), bg="#2b2b2b", fg="#c0c0c0").grid(row=3, column=0, padx=15, pady=8, sticky="e")
        from tkinter import ttk
        existing_groups = get_existing_groups()
        group_var = tk.StringVar()
        group_options = existing_groups if existing_groups else []
        group_frame = tk.Frame(top, bg="#2b2b2b")
        group_frame.grid(row=3, column=1, padx=15, pady=8, sticky="w")
        group_cb = ttk.Combobox(group_frame, textvariable=group_var, values=group_options, font=("Segoe Script", 12), width=45, state="readonly")
        group_cb.grid(row=0, column=0, sticky="w")
        if group_options:
            group_cb.set(group_options[0])
        # Bouton "+" avec largeur ajustée (width=1)
        app = self
        plus_btn = tk.Button(group_frame, text="+", command=lambda: app.add_group(top, group_cb, group_var),
                              font=("Segoe Script", 10), bg="#3a3a3a", fg="#c0c0c0", relief="flat", width=1)
        plus_btn.grid(row=0, column=1, padx=(5,0), sticky="w")
        top.note = ""
        note_frame = tk.Frame(top, bg="#2b2b2b")
        note_frame.grid(row=4, column=0, columnspan=2, pady=8)
        tk.Button(note_frame, text="Ajouter une note", command=lambda: self.open_note_window(top),
                  font=("Segoe Script", 12), bg="#3a3a3a", fg="#c0c0c0", relief="flat", width=20).pack(pady=5)
        btn_frame_top = tk.Frame(top, bg="#2b2b2b")
        btn_frame_top.grid(row=5, column=0, columnspan=2, pady=8)
        tk.Button(btn_frame_top, text="Enregistrer", command=lambda: self.save_new_connection(top, e_name, e_ip, e_login, group_var, top.note),
                  font=("Segoe Script", 12), bg="#3a3a3a", fg="#c0c0c0", relief="flat", width=12).pack(side=tk.LEFT, padx=15, expand=True)
        tk.Button(btn_frame_top, text="Retour", command=top.destroy,
                  font=("Segoe Script", 12), bg="#3a3a3a", fg="#c0c0c0", relief="flat", width=12).pack(side=tk.LEFT, padx=15, expand=True)

    def open_note_window(self, parent):
        if window_exists(self, "Ajouter une note"):
            return
        top = tk.Toplevel(self)
        top.iconphoto(False, self.logo)
        top.title("Ajouter une note")
        top.geometry("600x350")
        top.configure(bg="#2b2b2b")
        tk.Label(top, text="Entrez votre note :", font=("Segoe Script", 12), bg="#2b2b2b", fg="#c0c0c0").pack(pady=10)
        text = tk.Text(top, font=("Segoe Script", 12), bg="#3a3a3a", fg="#c0c0c0",
                        wrap=tk.WORD, height=10, width=70, relief="flat")
        text.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)
        btn_frame = tk.Frame(top, bg="#2b2b2b")
        btn_frame.pack(pady=20)
        def save_note():
            parent.note = text.get("1.0", tk.END).strip()
            top.destroy()
        tk.Button(btn_frame, text="Enregistrer", command=save_note,
                  font=("Segoe Script", 12), bg="#3a3a3a", fg="#c0c0c0", relief="flat", width=12).pack(side=tk.LEFT, padx=20, expand=True)
        tk.Button(btn_frame, text="Retour", command=top.destroy,
                  font=("Segoe Script", 12), bg="#3a3a3a", fg="#c0c0c0", relief="flat", width=12).pack(side=tk.LEFT, padx=20, expand=True)

    def save_new_connection(self, top, e_name, e_ip, e_login, group_var, note_value):
        name_val = e_name.get().strip()
        ip_val = e_ip.get().strip()
        login_val = e_login.get().strip()
        group_val = group_var.get().strip()
        if not name_val or not ip_val or not login_val or not group_val:
            messagebox.showerror("Erreur", "Tous les champs (sauf note) doivent être remplis.", parent=top)
            return
        for r in load_connections():
            if r[1] == ip_val:
                messagebox.showerror("Erreur", f"L'IP {ip_val} est déjà enregistrée.", parent=top)
                return
        new_row = [name_val, ip_val, login_val, "N/A", note_value, group_val]
        data = load_connections()
        data.append(new_row)
        save_connections(data)
        messagebox.showinfo("Info", "Connexion ajoutée.", parent=top)
        top.destroy()
        self.refresh_table()

    def modify_connection(self, original_row):
        if window_exists(self, "Modifier Connexion"):
            return
        top = tk.Toplevel(self)
        top.iconphoto(False, self.logo)
        top.title("Modifier Connexion")
        top.geometry("650x300")
        top.configure(bg="#2b2b2b")
        top.resizable(False, False)
        tk.Label(top, text="Nom:", font=("Segoe Script", 12), bg="#2b2b2b", fg="#c0c0c0").grid(row=0, column=0, padx=15, pady=8, sticky="e")
        e_name = tk.Entry(top, font=("Segoe Script", 12), bg="#3a3a3a", fg="#c0c0c0", relief="flat", width=50)
        e_name.insert(0, original_row[0])
        e_name.grid(row=0, column=1, padx=15, pady=8, sticky="w")
        tk.Label(top, text="IP:", font=("Segoe Script", 12), bg="#2b2b2b", fg="#c0c0c0").grid(row=1, column=0, padx=15, pady=8, sticky="e")
        e_ip = tk.Entry(top, font=("Segoe Script", 12), bg="#3a3a3a", fg="#c0c0c0", relief="flat", width=50)
        e_ip.insert(0, original_row[1])
        e_ip.grid(row=1, column=1, padx=15, pady=8, sticky="w")
        tk.Label(top, text="Login:", font=("Segoe Script", 12), bg="#2b2b2b", fg="#c0c0c0").grid(row=2, column=0, padx=15, pady=8, sticky="e")
        e_login = tk.Entry(top, font=("Segoe Script", 12), bg="#3a3a3a", fg="#c0c0c0", relief="flat", width=50)
        e_login.insert(0, original_row[2])
        e_login.grid(row=2, column=1, padx=15, pady=8, sticky="w")
        tk.Label(top, text="Groupe:", font=("Segoe Script", 12), bg="#2b2b2b", fg="#c0c0c0").grid(row=3, column=0, padx=15, pady=8, sticky="e")
        from tkinter import ttk
        existing_groups = get_existing_groups()
        group_var = tk.StringVar(value=original_row[5] if original_row[5] else "")
        group_options = existing_groups if existing_groups else []
        group_frame = tk.Frame(top, bg="#2b2b2b")
        group_frame.grid(row=3, column=1, padx=15, pady=8, sticky="w")
        group_cb = ttk.Combobox(group_frame, textvariable=group_var, values=group_options, font=("Segoe Script", 12), width=45, state="readonly")
        group_cb.grid(row=0, column=0, sticky="w")
        if original_row[5] in group_options:
            group_cb.set(original_row[5])
        app = self
        plus_btn = tk.Button(group_frame, text="+", command=lambda: app.add_group(top, group_cb, group_var),
                              font=("Segoe Script", 10), bg="#3a3a3a", fg="#c0c0c0", relief="flat", width=1)
        plus_btn.grid(row=0, column=1, padx=(5,0), sticky="w")
        btn_frame_top = tk.Frame(top, bg="#2b2b2b")
        btn_frame_top.grid(row=4, column=0, columnspan=2, pady=8)
        tk.Button(btn_frame_top, text="Modifier la note", command=lambda: self.edit_connection_note(original_row),
                  font=("Segoe Script", 12), bg="#3a3a3a", fg="#c0c0c0", relief="flat", width=15).pack(side=tk.LEFT, padx=10)
        btn_frame_bottom = tk.Frame(top, bg="#2b2b2b")
        btn_frame_bottom.grid(row=5, column=0, columnspan=2, pady=8)
        tk.Button(btn_frame_bottom, text="Enregistrer", command=lambda: self.save_modification(top, e_name, e_ip, e_login, group_var, original_row),
                  font=("Segoe Script", 12), bg="#3a3a3a", fg="#c0c0c0", relief="flat", width=12).pack(side=tk.LEFT, padx=10, expand=True)
        tk.Button(btn_frame_bottom, text="Retour", command=top.destroy,
                  font=("Segoe Script", 12), bg="#3a3a3a", fg="#c0c0c0", relief="flat", width=12).pack(side=tk.LEFT, padx=10, expand=True)

    def save_modification(self, top, e_name, e_ip, e_login, group_var, original_row):
        new_name = e_name.get().strip() or original_row[0]
        new_ip = e_ip.get().strip() or original_row[1]
        new_login = e_login.get().strip() or original_row[2]
        new_group = group_var.get().strip() or original_row[5]
        new_row = [new_name, new_ip, new_login, original_row[3], original_row[4], new_group]
        data = load_connections()
        for i, r in enumerate(data):
            if r == original_row:
                data[i] = new_row
                break
        save_connections(data)
        messagebox.showinfo("Info", "Connexion modifiée.", parent=top)
        top.destroy()
        self.refresh_table()

    def manage_groups(self):
        if window_exists(self, "Gérer Groupes"):
            return
        top = tk.Toplevel(self)
        top.iconphoto(False, self.logo)
        top.title("Gérer Groupes")
        top.geometry("500x400")
        top.configure(bg="#2b2b2b")
        tk.Label(top, text="Groupes existants:", font=self.font_main, bg="#2b2b2b", fg="#c0c0c0").pack(pady=10)
        listbox = tk.Listbox(top, font=self.font_main, bg="#3b3b3b", fg="#c0c0c0", selectmode=tk.SINGLE)
        listbox.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        groups = get_existing_groups()
        for grp in groups:
            listbox.insert(tk.END, grp)
        btn_frame = tk.Frame(top, bg="#2b2b2b")
        btn_frame.pack(pady=10)
        def add_new_group():
            new_grp = simpledialog.askstring("Ajouter Groupe", "Entrez le nom du groupe à ajouter:", parent=top)
            if new_grp:
                groups = get_existing_groups()
                if new_grp not in groups:
                    groups.append(new_grp)
                    with open(GROUPS_FILE, "a") as gf:
                        gf.write(new_grp + "\n")
                    listbox.insert(tk.END, new_grp)
        def delete_selected():
            sel = listbox.curselection()
            if not sel:
                messagebox.showinfo("Info", "Veuillez sélectionner un groupe.", parent=top)
                return
            grp = listbox.get(sel[0])
            if messagebox.askyesno("Confirmer", f"Supprimer le groupe '{grp}' ?", parent=top):
                delete_group_from_storage(grp)
                listbox.delete(sel[0])
                messagebox.showinfo("Info", f"Groupe '{grp}' supprimé.\nLes connexions l'utilisant seront vidées.", parent=top)
                self.refresh_table()
        tk.Button(btn_frame, text="Ajouter", command=add_new_group, font=self.font_main, bg="#3a3a3a", fg="#c0c0c0", relief="flat", width=12).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="Supprimer", command=delete_selected, font=self.font_main, bg="#3a3a3a", fg="#c0c0c0", relief="flat", width=12).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="Retour", command=top.destroy, font=self.font_main, bg="#3a3a3a", fg="#c0c0c0", relief="flat", width=12).pack(side=tk.LEFT, padx=10)

    def options_menu(self):
        if window_exists(self, "Options"):
            return
        top = tk.Toplevel(self)
        top.iconphoto(False, self.logo)
        top.title("Options")
        top.geometry("450x300")
        top.configure(bg="#2b2b2b")
        btn_frame = tk.Frame(top, bg="#2b2b2b")
        btn_frame.pack(expand=True, fill=tk.BOTH, pady=10)
        tk.Button(btn_frame, text="Sauvegarder la configuration", command=self.save_configuration, font=self.font_main,
                  bg="#3a3a3a", fg="#c0c0c0", relief="flat", width=30).pack(pady=5)
        tk.Button(btn_frame, text="Exporter la configuration", command=self.export_configuration, font=self.font_main,
                  bg="#3a3a3a", fg="#c0c0c0", relief="flat", width=30).pack(pady=5)
        tk.Button(btn_frame, text="Importer la configuration", command=self.import_configuration, font=self.font_main,
                  bg="#3a3a3a", fg="#c0c0c0", relief="flat", width=30).pack(pady=5)
        tk.Button(btn_frame, text="Supprimer la configuration", command=self.delete_configuration, font=self.font_main,
                  bg="#3a3a3a", fg="#c0c0c0", relief="flat", width=30).pack(pady=5)
        tk.Button(btn_frame, text="Mettre à jour FastRDP", command=lambda: threading.Thread(target=check_for_update, args=(self, True), daemon=True).start(), font=self.font_main,
                  bg="#3a3a3a", fg="#c0c0c0", relief="flat", width=30).pack(pady=5)
        tk.Button(btn_frame, text="Support", command=lambda: webbrowser.open("https://gitlab.com/schneider_dorian/FastRDP/-/issues"), font=self.font_main,
                  bg="#3a3a3a", fg="#c0c0c0", relief="flat", width=30).pack(pady=5)

    def save_configuration(self):
        dest = filedialog.askdirectory(title="Choisissez le dossier de sauvegarde")
        if dest:
            zip_path = backup_configuration(dest, export=False)
            messagebox.showinfo("Sauvegarde", f"Configuration sauvegardée dans : {zip_path}", parent=self)

    def export_configuration(self):
        self.tk.call('tk', 'scaling', 2.5)
        dest = filedialog.askdirectory(title="Choisissez le dossier d'exportation")
        self.tk.call('tk', 'scaling', 1.0)
        if dest:
            zip_path = backup_configuration(dest, export=True)
            messagebox.showinfo("Exportation", f"Configuration exportée dans : {zip_path}", parent=self)

    def import_configuration(self):
        self.tk.call('tk', 'scaling', 2.5)
        zip_file = filedialog.askopenfilename(title="Sélectionnez le fichier de configuration à importer",
                                              filetypes=[("Fichiers Zip", "*.zip")])
        self.tk.call('tk', 'scaling', 1.0)
        if zip_file:
            import_configuration_func(zip_file)
            messagebox.showinfo("Importation", "Configuration importée.", parent=self)
            self.refresh_table()

    def delete_configuration(self):
        conn_deleted = messagebox.askyesno("Confirmer", "Voulez-vous supprimer toutes les connexions ?", parent=self)
        if conn_deleted:
            open(FILE_CONNS, "w").close()
        group_deleted = messagebox.askyesno("Confirmer", "Voulez-vous supprimer tous les groupes ?", parent=self)
        if group_deleted:
            open(GROUPS_FILE, "w").close()
            data = load_connections()
            for i, row in enumerate(data):
                row[5] = ""
            save_connections(data)
        if conn_deleted or group_deleted:
            messagebox.showinfo("Info", "Configuration supprimée.", parent=self)
        self.refresh_table()

    def update_fastrdp(self):
        threading.Thread(target=check_for_update, args=(self, True), daemon=True).start()

    def support(self):
        webbrowser.open("https://gitlab.com/schneider_dorian/FastRDP/-/issues")

    # Méthode pour modifier la note d'une connexion
    def edit_connection_note(self, row):
        if window_exists(self, "Modifier la Note"):
            return
        top = tk.Toplevel(self)
        top.iconphoto(False, self.logo)
        top.title("Modifier la Note")
        top.geometry("600x350")
        top.configure(bg="#2b2b2b")
        tk.Label(top, text=f"Note pour {row[0]}:", font=("Segoe Script", 12),
                 bg="#2b2b2b", fg="#c0c0c0").pack(pady=10)
        text = tk.Text(top, font=("Segoe Script", 12), bg="#3a3a3a", fg="#c0c0c0",
                        wrap=tk.WORD, height=10, width=70, relief="flat")
        text.insert(tk.END, row[4])
        text.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)
        btn_frame = tk.Frame(top, bg="#2b2b2b")
        btn_frame.pack(pady=20)
        tk.Button(btn_frame, text="Enregistrer", command=lambda: self.save_note(top, text, row),
                  font=("Segoe Script", 12), bg="#3a3a3a", fg="#c0c0c0", relief="flat", width=12).pack(side=tk.LEFT, padx=20, expand=True)
        tk.Button(btn_frame, text="Retour", command=top.destroy,
                  font=("Segoe Script", 12), bg="#3a3a3a", fg="#c0c0c0", relief="flat", width=12).pack(side=tk.LEFT, padx=20, expand=True)

    def save_note(self, top, text, row):
        new_note = text.get("1.0", tk.END).strip()
        new_row = row.copy()
        new_row[4] = new_note
        update_connection_by_value(row, new_row)
        messagebox.showinfo("Info", "Note mise à jour.", parent=top)
        top.destroy()
        self.refresh_table()

    def save_new_connection(self, top, e_name, e_ip, e_login, group_var, note_value):
        name_val = e_name.get().strip()
        ip_val = e_ip.get().strip()
        login_val = e_login.get().strip()
        group_val = group_var.get().strip()
        if not name_val or not ip_val or not login_val or not group_val:
            messagebox.showerror("Erreur", "Tous les champs (sauf note) doivent être remplis.", parent=top)
            return
        for r in load_connections():
            if r[1] == ip_val:
                messagebox.showerror("Erreur", f"L'IP {ip_val} est déjà enregistrée.", parent=top)
                return
        new_row = [name_val, ip_val, login_val, "N/A", note_value, group_val]
        data = load_connections()
        data.append(new_row)
        save_connections(data)
        messagebox.showinfo("Info", "Connexion ajoutée.", parent=top)
        top.destroy()
        self.refresh_table()

    def modify_connection(self, original_row):
        if window_exists(self, "Modifier Connexion"):
            return
        top = tk.Toplevel(self)
        top.iconphoto(False, self.logo)
        top.title("Modifier Connexion")
        top.geometry("650x300")
        top.configure(bg="#2b2b2b")
        top.resizable(False, False)
        tk.Label(top, text="Nom:", font=("Segoe Script", 12), bg="#2b2b2b", fg="#c0c0c0").grid(row=0, column=0, padx=15, pady=8, sticky="e")
        e_name = tk.Entry(top, font=("Segoe Script", 12), bg="#3a3a3a", fg="#c0c0c0", relief="flat", width=50)
        e_name.insert(0, original_row[0])
        e_name.grid(row=0, column=1, padx=15, pady=8, sticky="w")
        tk.Label(top, text="IP:", font=("Segoe Script", 12), bg="#2b2b2b", fg="#c0c0c0").grid(row=1, column=0, padx=15, pady=8, sticky="e")
        e_ip = tk.Entry(top, font=("Segoe Script", 12), bg="#3a3a3a", fg="#c0c0c0", relief="flat", width=50)
        e_ip.insert(0, original_row[1])
        e_ip.grid(row=1, column=1, padx=15, pady=8, sticky="w")
        tk.Label(top, text="Login:", font=("Segoe Script", 12), bg="#2b2b2b", fg="#c0c0c0").grid(row=2, column=0, padx=15, pady=8, sticky="e")
        e_login = tk.Entry(top, font=("Segoe Script", 12), bg="#3a3a3a", fg="#c0c0c0", relief="flat", width=50)
        e_login.insert(0, original_row[2])
        e_login.grid(row=2, column=1, padx=15, pady=8, sticky="w")
        tk.Label(top, text="Groupe:", font=("Segoe Script", 12), bg="#2b2b2b", fg="#c0c0c0").grid(row=3, column=0, padx=15, pady=8, sticky="e")
        from tkinter import ttk
        existing_groups = get_existing_groups()
        group_var = tk.StringVar(value=original_row[5] if original_row[5] else "")
        group_options = existing_groups if existing_groups else []
        group_frame = tk.Frame(top, bg="#2b2b2b")
        group_frame.grid(row=3, column=1, padx=15, pady=8, sticky="w")
        group_cb = ttk.Combobox(group_frame, textvariable=group_var, values=group_options, font=("Segoe Script", 12), width=45, state="readonly")
        group_cb.grid(row=0, column=0, sticky="w")
        if original_row[5] in group_options:
            group_cb.set(original_row[5])
        app = self
        plus_btn = tk.Button(group_frame, text="+", command=lambda: app.add_group(top, group_cb, group_var),
                              font=("Segoe Script", 10), bg="#3a3a3a", fg="#c0c0c0", relief="flat", width=1)
        plus_btn.grid(row=0, column=1, padx=(5,0), sticky="w")
        btn_frame_top = tk.Frame(top, bg="#2b2b2b")
        btn_frame_top.grid(row=4, column=0, columnspan=2, pady=8)
        tk.Button(btn_frame_top, text="Modifier la note", command=lambda: self.edit_connection_note(original_row),
                  font=("Segoe Script", 12), bg="#3a3a3a", fg="#c0c0c0", relief="flat", width=15).pack(side=tk.LEFT, padx=10)
        btn_frame_bottom = tk.Frame(top, bg="#2b2b2b")
        btn_frame_bottom.grid(row=5, column=0, columnspan=2, pady=8)
        tk.Button(btn_frame_bottom, text="Enregistrer", command=lambda: self.save_modification(top, e_name, e_ip, e_login, group_var, original_row),
                  font=("Segoe Script", 12), bg="#3a3a3a", fg="#c0c0c0", relief="flat", width=12).pack(side=tk.LEFT, padx=10, expand=True)
        tk.Button(btn_frame_bottom, text="Retour", command=top.destroy,
                  font=("Segoe Script", 12), bg="#3a3a3a", fg="#c0c0c0", relief="flat", width=12).pack(side=tk.LEFT, padx=10, expand=True)

    def save_modification(self, top, e_name, e_ip, e_login, group_var, original_row):
        new_name = e_name.get().strip() or original_row[0]
        new_ip = e_ip.get().strip() or original_row[1]
        new_login = e_login.get().strip() or original_row[2]
        new_group = group_var.get().strip() or original_row[5]
        new_row = [new_name, new_ip, new_login, original_row[3], original_row[4], new_group]
        data = load_connections()
        for i, r in enumerate(data):
            if r == original_row:
                data[i] = new_row
                break
        save_connections(data)
        messagebox.showinfo("Info", "Connexion modifiée.", parent=top)
        top.destroy()
        self.refresh_table()

    def manage_groups(self):
        if window_exists(self, "Gérer Groupes"):
            return
        top = tk.Toplevel(self)
        top.iconphoto(False, self.logo)
        top.title("Gérer Groupes")
        top.geometry("500x400")
        top.configure(bg="#2b2b2b")
        tk.Label(top, text="Groupes existants:", font=self.font_main, bg="#2b2b2b", fg="#c0c0c0").pack(pady=10)
        listbox = tk.Listbox(top, font=self.font_main, bg="#3b3b3b", fg="#c0c0c0", selectmode=tk.SINGLE)
        listbox.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        groups = get_existing_groups()
        for grp in groups:
            listbox.insert(tk.END, grp)
        btn_frame = tk.Frame(top, bg="#2b2b2b")
        btn_frame.pack(pady=10)
        def add_new_group():
            new_grp = simpledialog.askstring("Ajouter Groupe", "Entrez le nom du groupe à ajouter:", parent=top)
            if new_grp:
                groups = get_existing_groups()
                if new_grp not in groups:
                    groups.append(new_grp)
                    with open(GROUPS_FILE, "a") as gf:
                        gf.write(new_grp + "\n")
                    listbox.insert(tk.END, new_grp)
        def delete_selected():
            sel = listbox.curselection()
            if not sel:
                messagebox.showinfo("Info", "Veuillez sélectionner un groupe.", parent=top)
                return
            grp = listbox.get(sel[0])
            if messagebox.askyesno("Confirmer", f"Supprimer le groupe '{grp}' ?", parent=top):
                delete_group_from_storage(grp)
                listbox.delete(sel[0])
                messagebox.showinfo("Info", f"Groupe '{grp}' supprimé.\nLes connexions l'utilisant seront vidées.", parent=top)
                self.refresh_table()
        tk.Button(btn_frame, text="Ajouter", command=add_new_group, font=self.font_main, bg="#3a3a3a", fg="#c0c0c0", relief="flat", width=12).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="Supprimer", command=delete_selected, font=self.font_main, bg="#3a3a3a", fg="#c0c0c0", relief="flat", width=12).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="Retour", command=top.destroy, font=self.font_main, bg="#3a3a3a", fg="#c0c0c0", relief="flat", width=12).pack(side=tk.LEFT, padx=10)

    def options_menu(self):
        if window_exists(self, "Options"):
            return
        top = tk.Toplevel(self)
        top.iconphoto(False, self.logo)
        top.title("Options")
        top.geometry("450x300")
        top.configure(bg="#2b2b2b")
        btn_frame = tk.Frame(top, bg="#2b2b2b")
        btn_frame.pack(expand=True, fill=tk.BOTH, pady=10)
        tk.Button(btn_frame, text="Sauvegarder la configuration", command=self.save_configuration, font=self.font_main,
                  bg="#3a3a3a", fg="#c0c0c0", relief="flat", width=30).pack(pady=5)
        tk.Button(btn_frame, text="Exporter la configuration", command=self.export_configuration, font=self.font_main,
                  bg="#3a3a3a", fg="#c0c0c0", relief="flat", width=30).pack(pady=5)
        tk.Button(btn_frame, text="Importer la configuration", command=self.import_configuration, font=self.font_main,
                  bg="#3a3a3a", fg="#c0c0c0", relief="flat", width=30).pack(pady=5)
        tk.Button(btn_frame, text="Supprimer la configuration", command=self.delete_configuration, font=self.font_main,
                  bg="#3a3a3a", fg="#c0c0c0", relief="flat", width=30).pack(pady=5)
        tk.Button(btn_frame, text="Mettre à jour FastRDP", command=lambda: threading.Thread(target=check_for_update, args=(self, True), daemon=True).start(), font=self.font_main,
                  bg="#3a3a3a", fg="#c0c0c0", relief="flat", width=30).pack(pady=5)
        tk.Button(btn_frame, text="Support", command=lambda: webbrowser.open("https://gitlab.com/schneider_dorian/FastRDP/-/issues"), font=self.font_main,
                  bg="#3a3a3a", fg="#c0c0c0", relief="flat", width=30).pack(pady=5)

    def save_configuration(self):
        dest = filedialog.askdirectory(title="Choisissez le dossier de sauvegarde")
        if dest:
            zip_path = backup_configuration(dest, export=False)
            messagebox.showinfo("Sauvegarde", f"Configuration sauvegardée dans : {zip_path}", parent=self)

    def export_configuration(self):
        self.tk.call('tk', 'scaling', 2.5)
        dest = filedialog.askdirectory(title="Choisissez le dossier d'exportation")
        self.tk.call('tk', 'scaling', 1.0)
        if dest:
            zip_path = backup_configuration(dest, export=True)
            messagebox.showinfo("Exportation", f"Configuration exportée dans : {zip_path}", parent=self)

    def import_configuration(self):
        self.tk.call('tk', 'scaling', 2.5)
        zip_file = filedialog.askopenfilename(title="Sélectionnez le fichier de configuration à importer",
                                              filetypes=[("Fichiers Zip", "*.zip")])
        self.tk.call('tk', 'scaling', 1.0)
        if zip_file:
            import_configuration_func(zip_file)
            messagebox.showinfo("Importation", "Configuration importée.", parent=self)
            self.refresh_table()

    def delete_configuration(self):
        conn_deleted = messagebox.askyesno("Confirmer", "Voulez-vous supprimer toutes les connexions ?", parent=self)
        if conn_deleted:
            open(FILE_CONNS, "w").close()
        group_deleted = messagebox.askyesno("Confirmer", "Voulez-vous supprimer tous les groupes ?", parent=self)
        if group_deleted:
            open(GROUPS_FILE, "w").close()
            data = load_connections()
            for i, row in enumerate(data):
                row[5] = ""
            save_connections(data)
        if conn_deleted or group_deleted:
            messagebox.showinfo("Info", "Configuration supprimée.", parent=self)
        self.refresh_table()

    def update_fastrdp(self):
        threading.Thread(target=check_for_update, args=(self, True), daemon=True).start()

    def support(self):
        webbrowser.open("https://gitlab.com/schneider_dorian/FastRDP/-/issues")

    def edit_connection_note(self, row):
        if window_exists(self, "Modifier la Note"):
            return
        top = tk.Toplevel(self)
        top.iconphoto(False, self.logo)
        top.title("Modifier la Note")
        top.geometry("600x350")
        top.configure(bg="#2b2b2b")
        tk.Label(top, text=f"Note pour {row[0]}:", font=("Segoe Script", 12),
                 bg="#2b2b2b", fg="#c0c0c0").pack(pady=10)
        text = tk.Text(top, font=("Segoe Script", 12), bg="#3a3a3a", fg="#c0c0c0",
                        wrap=tk.WORD, height=10, width=70, relief="flat")
        text.insert(tk.END, row[4])
        text.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)
        btn_frame = tk.Frame(top, bg="#2b2b2b")
        btn_frame.pack(pady=20)
        tk.Button(btn_frame, text="Enregistrer", command=lambda: self.save_note(top, text, row),
                  font=("Segoe Script", 12), bg="#3a3a3a", fg="#c0c0c0", relief="flat", width=12).pack(side=tk.LEFT, padx=20, expand=True)
        tk.Button(btn_frame, text="Retour", command=top.destroy,
                  font=("Segoe Script", 12), bg="#3a3a3a", fg="#c0c0c0", relief="flat", width=12).pack(side=tk.LEFT, padx=20, expand=True)

    def save_note(self, top, text, row):
        new_note = text.get("1.0", tk.END).strip()
        new_row = row.copy()
        new_row[4] = new_note
        update_connection_by_value(row, new_row)
        messagebox.showinfo("Info", "Note mise à jour.", parent=top)
        top.destroy()
        self.refresh_table()

    def save_new_connection(self, top, e_name, e_ip, e_login, group_var, note_value):
        name_val = e_name.get().strip()
        ip_val = e_ip.get().strip()
        login_val = e_login.get().strip()
        group_val = group_var.get().strip()
        if not name_val or not ip_val or not login_val or not group_val:
            messagebox.showerror("Erreur", "Tous les champs (sauf note) doivent être remplis.", parent=top)
            return
        for r in load_connections():
            if r[1] == ip_val:
                messagebox.showerror("Erreur", f"L'IP {ip_val} est déjà enregistrée.", parent=top)
                return
        new_row = [name_val, ip_val, login_val, "N/A", note_value, group_val]
        data = load_connections()
        data.append(new_row)
        save_connections(data)
        messagebox.showinfo("Info", "Connexion ajoutée.", parent=top)
        top.destroy()
        self.refresh_table()

    def modify_connection(self, original_row):
        if window_exists(self, "Modifier Connexion"):
            return
        top = tk.Toplevel(self)
        top.iconphoto(False, self.logo)
        top.title("Modifier Connexion")
        top.geometry("650x300")
        top.configure(bg="#2b2b2b")
        top.resizable(False, False)
        tk.Label(top, text="Nom:", font=("Segoe Script", 12), bg="#2b2b2b", fg="#c0c0c0").grid(row=0, column=0, padx=15, pady=8, sticky="e")
        e_name = tk.Entry(top, font=("Segoe Script", 12), bg="#3a3a3a", fg="#c0c0c0", relief="flat", width=50)
        e_name.insert(0, original_row[0])
        e_name.grid(row=0, column=1, padx=15, pady=8, sticky="w")
        tk.Label(top, text="IP:", font=("Segoe Script", 12), bg="#2b2b2b", fg="#c0c0c0").grid(row=1, column=0, padx=15, pady=8, sticky="e")
        e_ip = tk.Entry(top, font=("Segoe Script", 12), bg="#3a3a3a", fg="#c0c0c0", relief="flat", width=50)
        e_ip.insert(0, original_row[1])
        e_ip.grid(row=1, column=1, padx=15, pady=8, sticky="w")
        tk.Label(top, text="Login:", font=("Segoe Script", 12), bg="#2b2b2b", fg="#c0c0c0").grid(row=2, column=0, padx=15, pady=8, sticky="e")
        e_login = tk.Entry(top, font=("Segoe Script", 12), bg="#3a3a3a", fg="#c0c0c0", relief="flat", width=50)
        e_login.insert(0, original_row[2])
        e_login.grid(row=2, column=1, padx=15, pady=8, sticky="w")
        tk.Label(top, text="Groupe:", font=("Segoe Script", 12), bg="#2b2b2b", fg="#c0c0c0").grid(row=3, column=0, padx=15, pady=8, sticky="e")
        from tkinter import ttk
        existing_groups = get_existing_groups()
        group_var = tk.StringVar(value=original_row[5] if original_row[5] else "")
        group_options = existing_groups if existing_groups else []
        group_frame = tk.Frame(top, bg="#2b2b2b")
        group_frame.grid(row=3, column=1, padx=15, pady=8, sticky="w")
        group_cb = ttk.Combobox(group_frame, textvariable=group_var, values=group_options, font=("Segoe Script", 12), width=45, state="readonly")
        group_cb.grid(row=0, column=0, sticky="w")
        if original_row[5] in group_options:
            group_cb.set(original_row[5])
        app = self
        plus_btn = tk.Button(group_frame, text="+", command=lambda: app.add_group(top, group_cb, group_var),
                              font=("Segoe Script", 10), bg="#3a3a3a", fg="#c0c0c0", relief="flat", width=1)
        plus_btn.grid(row=0, column=1, padx=(5,0), sticky="w")
        btn_frame_top = tk.Frame(top, bg="#2b2b2b")
        btn_frame_top.grid(row=4, column=0, columnspan=2, pady=8)
        tk.Button(btn_frame_top, text="Modifier la note", command=lambda: self.edit_connection_note(original_row),
                  font=("Segoe Script", 12), bg="#3a3a3a", fg="#c0c0c0", relief="flat", width=15).pack(side=tk.LEFT, padx=10)
        btn_frame_bottom = tk.Frame(top, bg="#2b2b2b")
        btn_frame_bottom.grid(row=5, column=0, columnspan=2, pady=8)
        tk.Button(btn_frame_bottom, text="Enregistrer", command=lambda: self.save_modification(top, e_name, e_ip, e_login, group_var, original_row),
                  font=("Segoe Script", 12), bg="#3a3a3a", fg="#c0c0c0", relief="flat", width=12).pack(side=tk.LEFT, padx=10, expand=True)
        tk.Button(btn_frame_bottom, text="Retour", command=top.destroy,
                  font=("Segoe Script", 12), bg="#3a3a3a", fg="#c0c0c0", relief="flat", width=12).pack(side=tk.LEFT, padx=10, expand=True)

    def save_modification(self, top, e_name, e_ip, e_login, group_var, original_row):
        new_name = e_name.get().strip() or original_row[0]
        new_ip = e_ip.get().strip() or original_row[1]
        new_login = e_login.get().strip() or original_row[2]
        new_group = group_var.get().strip() or original_row[5]
        new_row = [new_name, new_ip, new_login, original_row[3], original_row[4], new_group]
        data = load_connections()
        for i, r in enumerate(data):
            if r == original_row:
                data[i] = new_row
                break
        save_connections(data)
        messagebox.showinfo("Info", "Connexion modifiée.", parent=top)
        top.destroy()
        self.refresh_table()

if __name__ == "__main__":
    root = RDPApp()
    root.mainloop()
EOF

python3 "$PYFILE"
rm "$PYFILE"