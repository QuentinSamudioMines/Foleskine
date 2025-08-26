import tkinter as tk
from tkinter import ttk, filedialog, simpledialog, messagebox
import json
import os
import sys
import re
import datetime

APP_NAME = "FoleskineNotes"

def get_icon_path():
    """Get the path to the icon file, works both in development and when compiled with PyInstaller"""
    if getattr(sys, 'frozen', False):
        # Running in a PyInstaller bundle
        base_path = sys._MEIPASS
    else:
        # Running in development
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    return os.path.join(base_path, "icons/icon.ico")

# ---------------------- Utilitaires chemins & fichiers ----------------------
def get_data_dir():
    """Retourne un dossier de données par-OS, ex:
    - Windows: %APPDATA%/FoleskineNotes
    - macOS: ~/Library/Application Support/FoleskineNotes
    - Linux: ~/.local/share/FoleskineNotes
    """
    home = os.path.expanduser("~")
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA", os.path.join(home, "AppData", "Roaming"))
        return os.path.join(base, APP_NAME)
    elif sys.platform == "darwin":
        return os.path.join(home, "Library", "Application Support", APP_NAME)
    else:
        # linux / autres UNIX
        return os.path.join(home, ".local", "share", APP_NAME)

DATA_DIR = get_data_dir()
LIB_DIR = os.path.join(DATA_DIR, "notebooks")

os.makedirs(LIB_DIR, exist_ok=True)

# ---------------------- Modèle de données ----------------------
# Format d'un carnet (JSON):
# {
#   "title": "Mon carnet",
#   "created_at": "2025-08-26T12:00:00",
#   "updated_at": "2025-08-26T12:34:56",
#   "pages": ["texte page 1", "texte page 2", ...]
# }

def slugify(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9_-]+", "-", name.strip()).strip("-")
    return s or "carnet"

class Notebook:
    def __init__(self, path: str, data: dict):
        self.path = path
        self.data = data
        if "pages" not in self.data:
            self.data["pages"] = [""]
        if not self.data["pages"]:
            self.data["pages"].append("")

    @property
    def title(self) -> str:
        return self.data.get("title", os.path.splitext(os.path.basename(self.path))[0])

    def save(self):
        self.data["updated_at"] = datetime.datetime.now().isoformat(timespec="seconds")
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    @staticmethod
    def create_new(title: str):
        fname = f"{slugify(title)}.json"
        path = os.path.join(LIB_DIR, fname)
        ts = datetime.datetime.now().isoformat(timespec="seconds")
        data = {
            "title": title,
            "created_at": ts,
            "updated_at": ts,
            "pages": [""]
        }
        nb = Notebook(path, data)
        nb.save()
        return nb

    @staticmethod
    def load(path: str):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Notebook(path, data)

# ---------------------- UI Application ----------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Carnets")
        self.geometry("1000x650")
        
        # Set window icon (replace "path/to/your/icon.ico" with your actual path)
        try:
            self.iconbitmap(get_icon_path())
        except tk.TclError:
            # If icon file not found, continue without it
            pass

        # Style "Foleskine" light/sépia
        self.configure(bg="#f7f2e7")  # fond général

        # Thème ttk
        style = ttk.Style(self)
        if sys.platform.startswith("win"):
            style.theme_use("vista")
        else:
            # 'clam' est portable
            style.theme_use("clam")
        style.configure("TButton", padding=6)
        style.configure("TLabel", background="#f7f2e7")
        style.configure("TFrame", background="#f7f2e7")

        # Etat
        self.current_notebook: Notebook | None = None
        self.current_page_index = 0
        self._autosave_after_id = None
        self.is_fullscreen = False
        self.fullscreen_window = None

        # Layout principal: sidebar (bibliothèque) + zone d'édition
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        self.sidebar = ttk.Frame(self)
        self.sidebar.grid(row=0, column=0, sticky="nsw")
        self.sidebar.configure(width=260)

        self.main = ttk.Frame(self)
        self.main.grid(row=0, column=1, sticky="nsew", padx=(4, 8), pady=8)
        self.main.rowconfigure(2, weight=1)
        self.main.columnconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main()

        self.refresh_library()

        # Autosave périodique (toutes les 30s)
        self.after(30_000, self.periodic_autosave)

    # ---------------------- Sidebar: Bibliothèque ----------------------
    def _build_sidebar(self):
        header = ttk.Label(self.sidebar, text="📚 Mes carnets", font=("Georgia", 14, "bold"))
        header.pack(anchor="w", padx=12, pady=(12, 6))

        btns = ttk.Frame(self.sidebar)
        btns.pack(fill="x", padx=10)
        ttk.Button(btns, text="Nouveau", command=self.new_notebook).grid(row=0, column=0, padx=2, pady=4)
        ttk.Button(btns, text="Renommer", command=self.rename_notebook).grid(row=0, column=1, padx=2, pady=4)
        ttk.Button(btns, text="Supprimer", command=self.delete_notebook).grid(row=0, column=2, padx=2, pady=4)

        self.listbox = tk.Listbox(self.sidebar, activestyle="dotbox", height=20)
        self.listbox.pack(fill="both", expand=True, padx=10, pady=(6, 10))
        self.listbox.bind("<<ListboxSelect>>", self.on_select_notebook)

        foot = ttk.Frame(self.sidebar)
        foot.pack(fill="x", padx=10, pady=(0,10))
        ttk.Button(foot, text="Importer…", command=self.import_notebook).grid(row=0, column=0, padx=2)
        ttk.Button(foot, text="Exporter…", command=self.export_notebook).grid(row=0, column=1, padx=2)

    def refresh_library(self):
        items = []
        for name in sorted(os.listdir(LIB_DIR)):
            if name.lower().endswith(".json"):
                items.append(os.path.join(LIB_DIR, name))
        self.listbox.delete(0, tk.END)
        for p in items:
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    title = data.get("title") or os.path.splitext(os.path.basename(p))[0]
            except Exception:
                title = os.path.splitext(os.path.basename(p))[0]
            self.listbox.insert(tk.END, title)
            self.listbox.itemconfig(tk.END, foreground="#333")
        # Sélectionner le premier élément si rien d'ouvert
        if items and not self.current_notebook:
            self.listbox.selection_set(0)
            self.open_notebook_by_index(0)

    def lib_paths(self):
        paths = []
        for name in os.listdir(LIB_DIR):
            if name.lower().endswith(".json"):
                paths.append(os.path.join(LIB_DIR, name))
        return sorted(paths)

    def on_select_notebook(self, event=None):
        idxs = self.listbox.curselection()
        if not idxs:
            return
        self.open_notebook_by_index(idxs[0])

    def open_notebook_by_index(self, idx: int):
        paths = self.lib_paths()
        if 0 <= idx < len(paths):
            self.open_notebook(paths[idx])

    def open_notebook(self, path: str):
        if not self.confirm_save_changes():
            return
        try:
            nb = Notebook.load(path)
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible d'ouvrir le carnet:\n{e}")
            return
        self.current_notebook = nb
        self.current_page_index = 0
        self.update_title()
        self.load_page()

    def new_notebook(self):
        title = simpledialog.askstring("Nouveau carnet", "Titre du carnet:")
        if not title:
            return
        nb = Notebook.create_new(title)
        self.current_notebook = nb
        self.current_page_index = 0
        self.refresh_library()
        self.select_current_in_list()
        self.update_title()
        self.load_page()

    def rename_notebook(self):
        if not self.current_notebook:
            return
        title = simpledialog.askstring("Renommer", "Nouveau titre:", initialvalue=self.current_notebook.title)
        if not title:
            return
        # renommer le fichier aussi (slug)
        new_path = os.path.join(LIB_DIR, f"{slugify(title)}.json")
        if os.path.abspath(new_path) != os.path.abspath(self.current_notebook.path):
            if os.path.exists(new_path):
                messagebox.showerror("Conflit", "Un carnet avec ce nom existe déjà.")
                return
            try:
                os.replace(self.current_notebook.path, new_path)
            except Exception as e:
                messagebox.showerror("Erreur", f"Impossible de renommer:\n{e}")
                return
            self.current_notebook.path = new_path
        self.current_notebook.data["title"] = title
        self.current_notebook.save()
        self.refresh_library()
        self.select_current_in_list()
        self.update_title()

    def delete_notebook(self):
        if not self.current_notebook:
            return
        if not messagebox.askyesno("Supprimer", f"Supprimer définitivement '{self.current_notebook.title}' ?"):
            return
        try:
            os.remove(self.current_notebook.path)
        except Exception as e:
            messagebox.showerror("Erreur", f"Suppression impossible:\n{e}")
            return
        self.current_notebook = None
        self.current_page_index = 0
        self.refresh_library()
        self.update_title()
        self.clear_editor()

    def export_notebook(self):
        if not self.current_notebook:
            return
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")],
                                            initialfile=f"{slugify(self.current_notebook.title)}.json")
        if not path:
            return
        try:
            self.ensure_page_saved()
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.current_notebook.data, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("Export", "Carnet exporté ✅")
        except Exception as e:
            messagebox.showerror("Erreur", f"Export impossible:\n{e}")

    def import_notebook(self):
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            title = data.get("title") or os.path.splitext(os.path.basename(path))[0]
            dest = os.path.join(LIB_DIR, f"{slugify(title)}.json")
            # éviter collision
            base = os.path.splitext(dest)[0]
            i = 1
            while os.path.exists(dest):
                dest = f"{base}-{i}.json"
                i += 1
            with open(dest, "w", encoding="utf-8") as out:
                json.dump(data, out, ensure_ascii=False, indent=2)
            self.refresh_library()
            messagebox.showinfo("Import", "Carnet importé ✅")
        except Exception as e:
            messagebox.showerror("Erreur", f"Import impossible:\n{e}")

    def select_current_in_list(self):
        if not self.current_notebook:
            return
        titles = []
        for p in self.lib_paths():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    titles.append(d.get("title") or os.path.splitext(os.path.basename(p))[0])
            except Exception:
                titles.append(os.path.splitext(os.path.basename(p))[0])
        try:
            idx = titles.index(self.current_notebook.title)
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(idx)
            self.listbox.see(idx)
        except ValueError:
            pass

    # ---------------------- Zone principale ----------------------
    def _build_main(self):
        # Barre titre + commandes
        self.header = ttk.Frame(self.main)
        self.header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self.header.columnconfigure(1, weight=1)

        self.title_var = tk.StringVar(value="(aucun carnet)")
        ttk.Label(self.header, textvariable=self.title_var, font=("Georgia", 16, "bold")).grid(row=0, column=0, sticky="w")

        toolbar = ttk.Frame(self.header)
        toolbar.grid(row=0, column=2, sticky="e")
        ttk.Button(toolbar, text="◀", width=3, command=self.prev_page).grid(row=0, column=0, padx=2)
        self.page_label_var = tk.StringVar(value="—/—")
        ttk.Label(toolbar, textvariable=self.page_label_var, font=("Georgia", 11)).grid(row=0, column=1, padx=4)
        ttk.Button(toolbar, text="▶", width=3, command=self.next_page).grid(row=0, column=2, padx=2)
        ttk.Button(toolbar, text="+ Page", command=self.add_page).grid(row=0, column=3, padx=6)
        ttk.Button(toolbar, text="Aller…", command=self.goto_page_dialog).grid(row=0, column=4, padx=2)
        ttk.Button(toolbar, text="🖥️", width=4, command=self.toggle_fullscreen).grid(row=0, column=5, padx=6)

        # Cadre "papier"
        paper_frame = tk.Frame(self.main, bg="#f3ebd9", bd=0, highlightthickness=1, highlightbackground="#e0d8c6")
        paper_frame.grid(row=2, column=0, sticky="nsew")

        # Marges internes
        inner = tk.Frame(paper_frame, bg="#f3ebd9")
        inner.pack(expand=True, fill="both", padx=24, pady=18)

        self.text = tk.Text(inner, wrap="word", font=("Georgia", 14), bg="#f3ebd9", relief="flat", undo=True)
        self.text.pack(expand=True, fill="both")
        self.text.bind("<KeyRelease>", self.on_text_change)

        # Bind undo/redo
        self.text.bind("<Control-z>", lambda e: self.text.edit_undo())
        self.text.bind("<Control-y>", lambda e: self.text.edit_redo())

        # Barre de statut
        self.status_var = tk.StringVar(value="Prêt")
        status = ttk.Label(self.main, textvariable=self.status_var)
        status.grid(row=3, column=0, sticky="ew", pady=(6,0))

    def update_title(self):
        if self.current_notebook:
            self.title_var.set(self.current_notebook.title)
        else:
            self.title_var.set("(aucun carnet)")

    def clear_editor(self):
        self.text.delete("1.0", tk.END)
        self.page_label_var.set("—/—")

    def load_page(self):
        if not self.current_notebook:
            self.clear_editor()
            return
        pages = self.current_notebook.data.get("pages", [""])
        self.text.delete("1.0", tk.END)
        try:
            content = pages[self.current_page_index]
        except IndexError:
            content = ""
        self.text.insert("1.0", content)
        self.page_label_var.set(f"Page {self.current_page_index+1} / {len(pages)}")
        self.status_var.set("")

    def ensure_page_saved(self):
        if not self.current_notebook:
            return
        content = self.text.get("1.0", "end-1c")
        pages = self.current_notebook.data["pages"]
        while self.current_page_index >= len(pages):
            pages.append("")
        if pages[self.current_page_index] != content:
            pages[self.current_page_index] = content
            self.current_notebook.save()
            self.status_var.set("✅ Sauvegardé")

    def on_text_change(self, event=None):
        # Autosave après 1 seconde sans frappe
        if self._autosave_after_id is not None:
            self.after_cancel(self._autosave_after_id)
        self._autosave_after_id = self.after(1000, self.ensure_page_saved)

    def periodic_autosave(self):
        self.ensure_page_saved()
        self.after(30_000, self.periodic_autosave)

    def prev_page(self):
        if not self.current_notebook:
            return
        self.ensure_page_saved()
        if self.current_page_index > 0:
            self.current_page_index -= 1
            self.load_page()

    def next_page(self):
        if not self.current_notebook:
            return
        self.ensure_page_saved()
        if self.current_page_index < len(self.current_notebook.data["pages"]) - 1:
            self.current_page_index += 1
        else:
            self.add_page()
            return
        self.load_page()

    def add_page(self):
        if not self.current_notebook:
            return
        self.ensure_page_saved()
        self.current_notebook.data["pages"].append("")
        self.current_page_index = len(self.current_notebook.data["pages"]) - 1
        self.current_notebook.save()
        self.load_page()

    def goto_page_dialog(self):
        if not self.current_notebook:
            return
        n_pages = len(self.current_notebook.data["pages"])
        val = simpledialog.askinteger("Aller à la page", f"Numéro (1..{n_pages}) :", minvalue=1, maxvalue=n_pages)
        if val:
            self.ensure_page_saved()
            self.current_page_index = val - 1
            self.load_page()

    # ---------------------- Mode pleine écran ----------------------
    def toggle_fullscreen(self):
        if not self.current_notebook:
            messagebox.showwarning("Attention", "Ouvrez d'abord un carnet pour utiliser le mode pleine écran.")
            return
        
        if not self.is_fullscreen:
            self.enter_fullscreen()
        else:
            self.exit_fullscreen()

    def enter_fullscreen(self):
        # Sauvegarder le contenu actuel avant de passer en pleine écran
        self.sync_text_content()
        
        # Créer la fenêtre pleine écran
        self.fullscreen_window = tk.Toplevel(self)
        self.fullscreen_window.title(f"✍️ {self.current_notebook.title} - Page {self.current_page_index + 1}")
        self.fullscreen_window.configure(bg="#2c2c2c")  # fond sombre et minimaliste
        
        # Set the same icon for fullscreen window
        try:
            self.fullscreen_window.iconbitmap(get_icon_path())
        except tk.TclError:
            pass
        
        # Mettre en pleine écran
        self.fullscreen_window.attributes("-fullscreen", True)
        
        # Créer l'interface minimaliste
        self.create_fullscreen_interface()
        
        # Gérer les événements clavier
        self.fullscreen_window.bind("<Escape>", lambda e: self.exit_fullscreen())
        self.fullscreen_window.bind("<F11>", lambda e: self.exit_fullscreen())
        self.fullscreen_window.focus_set()
        
        self.is_fullscreen = True

    def create_fullscreen_interface(self):
        # Zone de texte centrée avec beaucoup d'espace
        main_frame = tk.Frame(self.fullscreen_window, bg="#2c2c2c")
        main_frame.pack(expand=True, fill="both")
        
        # Conteneur centré pour le texte
        text_container = tk.Frame(main_frame, bg="#2c2c2c")
        text_container.pack(expand=True, fill="both", padx=100, pady=60)
        
        # Barre d'outils discrète en haut
        toolbar = tk.Frame(text_container, bg="#2c2c2c", height=40)
        toolbar.pack(fill="x", pady=(0, 20))
        toolbar.pack_propagate(False)
        
        # Informations discrètes
        info_label = tk.Label(toolbar, 
                             text=f"{self.current_notebook.title} • Page {self.current_page_index + 1}",
                             font=("Georgia", 12), 
                             fg="#888888", 
                             bg="#2c2c2c")
        info_label.pack(side="left")
        
        # Boutons discrets
        button_frame = tk.Frame(toolbar, bg="#2c2c2c")
        button_frame.pack(side="right")
        
        prev_btn = tk.Button(button_frame, text="◀", font=("Georgia", 12),
                            bg="#444444", fg="#cccccc", relief="flat",
                            command=self.fullscreen_prev_page, padx=10)
        prev_btn.pack(side="left", padx=2)
        
        next_btn = tk.Button(button_frame, text="▶", font=("Georgia", 12),
                            bg="#444444", fg="#cccccc", relief="flat",
                            command=self.fullscreen_next_page, padx=10)
        next_btn.pack(side="left", padx=2)
        
        exit_btn = tk.Button(button_frame, text="✕", font=("Georgia", 12),
                            bg="#444444", fg="#cccccc", relief="flat",
                            command=self.exit_fullscreen, padx=10)
        exit_btn.pack(side="left", padx=(20, 0))
        
        # Zone de texte principale
        self.fullscreen_text = tk.Text(text_container, 
                                      wrap="word", 
                                      font=("Georgia", 16, "normal"),
                                      bg="#2c2c2c", 
                                      fg="#e8e8e8",
                                      relief="flat",
                                      bd=0,
                                      insertbackground="#cccccc",
                                      selectbackground="#555555",
                                      undo=True)
        self.fullscreen_text.pack(expand=True, fill="both")

        # Bind undo/redo
        self.fullscreen_text.bind("<Control-z>", lambda e: self.fullscreen_text.edit_undo())
        self.fullscreen_text.bind("<Control-y>", lambda e: self.fullscreen_text.edit_redo())
        
        # Charger le contenu actuel
        content = self.text.get("1.0", "end-1c")
        self.fullscreen_text.insert("1.0", content)
        
        # Synchroniser les changements
        self.fullscreen_text.bind("<KeyRelease>", self.on_fullscreen_text_change)
        
        # Focus sur le texte
        self.fullscreen_text.focus_set()
        
        # Instructions discrètes en bas
        instructions = tk.Label(text_container, 
                               text="Échap ou F11 pour quitter • Les modifications sont sauvegardées automatiquement",
                               font=("Georgia", 10, "italic"), 
                               fg="#666666", 
                               bg="#2c2c2c")
        instructions.pack(pady=(10, 0))

    def sync_text_content(self):
        """Synchronise le contenu entre la fenêtre normale et pleine écran"""
        if self.is_fullscreen and self.fullscreen_text:
            # Copier de pleine écran vers normal
            content = self.fullscreen_text.get("1.0", "end-1c")
            self.text.delete("1.0", tk.END)
            self.text.insert("1.0", content)
        else:
            # Copier de normal vers pleine écran
            content = self.text.get("1.0", "end-1c")
            if hasattr(self, 'fullscreen_text') and self.fullscreen_text:
                self.fullscreen_text.delete("1.0", tk.END)
                self.fullscreen_text.insert("1.0", content)

    def on_fullscreen_text_change(self, event=None):
        # Synchroniser avec la fenêtre principale
        if self.fullscreen_text:
            content = self.fullscreen_text.get("1.0", "end-1c")
            self.text.delete("1.0", tk.END)
            self.text.insert("1.0", content)
            
        # Déclencher la sauvegarde automatique
        self.on_text_change(event)

    def fullscreen_prev_page(self):
        if not self.current_notebook or self.current_page_index <= 0:
            return
        
        self.ensure_page_saved()
        self.current_page_index -= 1
        self.load_fullscreen_page()

    def fullscreen_next_page(self):
        if not self.current_notebook:
            return
        
        self.ensure_page_saved()
        if self.current_page_index < len(self.current_notebook.data["pages"]) - 1:
            self.current_page_index += 1
        else:
            # Ajouter une nouvelle page
            self.current_notebook.data["pages"].append("")
            self.current_page_index = len(self.current_notebook.data["pages"]) - 1
            self.current_notebook.save()
        
        self.load_fullscreen_page()

    def load_fullscreen_page(self):
        if not self.current_notebook or not self.fullscreen_text:
            return
        
        pages = self.current_notebook.data.get("pages", [""])
        try:
            content = pages[self.current_page_index]
        except IndexError:
            content = ""
        
        self.fullscreen_text.delete("1.0", tk.END)
        self.fullscreen_text.insert("1.0", content)
        
        # Mettre à jour le titre de la fenêtre
        self.fullscreen_window.title(f"✍️ {self.current_notebook.title} - Page {self.current_page_index + 1}")
        
        # Synchroniser avec la fenêtre principale
        self.text.delete("1.0", tk.END)
        self.text.insert("1.0", content)
        self.page_label_var.set(f"Page {self.current_page_index+1} / {len(pages)}")

    def exit_fullscreen(self):
        if self.fullscreen_window:
            # Sauvegarder avant de fermer
            self.sync_text_content()
            self.ensure_page_saved()
            
            # Fermer la fenêtre pleine écran
            self.fullscreen_window.destroy()
            self.fullscreen_window = None
            self.fullscreen_text = None
        
        self.is_fullscreen = False
        
        # Remettre le focus sur la fenêtre principale
        self.focus_force()
        self.text.focus_set()

    def confirm_save_changes(self) -> bool:
        # appelé avant d'ouvrir un autre carnet
        if not self.current_notebook:
            return True
        
        # Si on est en pleine écran, synchroniser d'abord
        if self.is_fullscreen:
            self.sync_text_content()
        
        content = self.text.get("1.0", "end-1c")
        current_saved = self.current_notebook.data["pages"][self.current_page_index]
        if content != current_saved:
            res = messagebox.askyesnocancel("Sauvegarder", "Sauvegarder les modifications avant de continuer ?")
            if res is None:
                return False
            if res:
                self.ensure_page_saved()
        return True

    def on_close(self):
        if self.is_fullscreen:
            self.exit_fullscreen()
        
        if not self.confirm_save_changes():
            return
        self.ensure_page_saved()
        self.destroy()

# ---------------------- Lancement ----------------------
if __name__ == "__main__":
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()