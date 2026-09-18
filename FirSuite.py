import io
import json
import os
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import fitz
from PIL import Image, ImageTk
from pypdf import PdfReader, PdfWriter
from reportlab.lib.colors import Color
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas as rl_canvas

DB_FILE = 'fir_anagrafiche_db.json'
SENZA_TARGA = '<SENZA TARGA>'

FIELDS_BASE = {
    'RegistroNO': {'type': 'x', 'x': 239.67, 'y': 792.57},
    'RifiutoSpeciale': {'type': 'x', 'x': 547.20, 'y': 490.70},
    'RifiutoRinfusa': {'type': 'x', 'x': 546.00, 'y': 444.90},
    'RifiutoKg': {'type': 'x', 'x': 220.50, 'y': 443.90},
    'RifiutoStatoFisico': {'type': 'text', 'x': 240.20, 'y': 472.70, 'value': 'S', 'font': 'Helvetica', 'font_size': 10},
    'RifiutoDestinazioneR': {'type': 'text', 'x': 504.33, 'y': 624.00, 'value': '13', 'font': 'Helvetica', 'font_size': 10},
    'DestinatarioDenominazione': {'type': 'text', 'x': 109.00, 'y': 664.70, 'value': 'TRUCCOLO ANGELO S.R.L.', 'font': 'Helvetica', 'font_size': 10},
    'DestinatarioUnitaLocale': {'type': 'text', 'x': 107.50, 'y': 641.15, 'value': 'Via Giacomo Puccini, 88 - Fontanafredda (PORDENONE)', 'font': 'Helvetica', 'font_size': 8},
    'DestinatarioCodiceFiscale': {'type': 'text', 'x': 107.75, 'y': 621.40, 'value': '01794110930', 'font': 'Helvetica', 'font_size': 10},
    'DestinatarioNumAut': {'type': 'text', 'x': 108.00, 'y': 609.90, 'value': 'DEC. 394/AMB', 'font': 'Helvetica', 'font_size': 9},
    'DestinatarioTipoAut': {'type': 'fit_text', 'x': 359.71, 'y': 610.47, 'value': 'Autorizzazione unica per i nuovi impianti di recupero/smaltimento - Art. 208 D.lgs. 152/06', 'font': 'Helvetica', 'max_width': 175, 'max_font': 7.5, 'min_font': 4.9},
}

COORDS_DYNAMIC = {
    'ProduttoreDenominazione': {'type': 'text', 'x': 107.00, 'y': 760.90, 'font': 'Helvetica', 'font_size': 10},
    'ProduttoreUnitaLocale': {'type': 'text', 'x': 107.33, 'y': 736.40, 'font': 'Helvetica', 'font_size': 8},
    'ProduttoreCodiceFiscale': {'type': 'text', 'x': 106.83, 'y': 706.23, 'font': 'Helvetica', 'font_size': 10},
    'TrasportatoreDenominazione': {'type': 'text', 'x': 109.00, 'y': 578.90, 'font': 'Helvetica', 'font_size': 10},
    'TrasportatoreCodiceFiscale': {'type': 'text', 'x': 108.33, 'y': 551.23, 'font': 'Helvetica', 'font_size': 10},
    'TrasportatoreAlbo': {'type': 'text', 'x': 361.00, 'y': 550.90, 'font': 'Helvetica', 'font_size': 10},
    'TrasportatoreAutomezzo': {'type': 'text', 'x': 92.67, 'y': 347.90, 'font': 'Helvetica', 'font_size': 10},
    'Conducente': {'type': 'text', 'x': 57.00, 'y': 302.90, 'font': 'Helvetica', 'font_size': 10},
    'Annotazioni': {'type': 'text', 'x': 36.00, 'y': 164.90, 'font': 'Helvetica', 'font_size': 10},
}

DEFAULT_DB = {'anagrafiche': []}


def sort_anagrafiche(data):
    if 'anagrafiche' in data and isinstance(data['anagrafiche'], list):
        data['anagrafiche'].sort(key=lambda x: x.get('denominazione', '').lower())


def load_db():
    if not os.path.exists(DB_FILE):
        save_db(DEFAULT_DB)
        return {'anagrafiche': []}
    with open(DB_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
        sort_anagrafiche(data)
        return data


def save_db(data):
    sort_anagrafiche(data)
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def normalize_lines(text):
    return [line.strip() for line in text.replace('\r', '').split('\n') if line.strip()]


def build_unita_locale(record):
    indirizzo = record.get('indirizzo', '').strip()
    cap = record.get('cap_citta_prov', '').strip()
    return f'{indirizzo} {cap}'.strip()


def build_fields(record, selected_targa):
    fields = {k: dict(v) for k, v in FIELDS_BASE.items()}
    tipo = record.get('tipo_iscrizione', '2BIS').upper().strip()
    if tipo == '2BIS':
        fields['RegistroNO'] = dict(FIELDS_BASE['RegistroNO'])
        fields['ProduttoreDenominazione'] = {**COORDS_DYNAMIC['ProduttoreDenominazione'], 'value': record.get('denominazione', '')}
        fields['ProduttoreUnitaLocale'] = {**COORDS_DYNAMIC['ProduttoreUnitaLocale'], 'value': build_unita_locale(record)}
        fields['ProduttoreCodiceFiscale'] = {**COORDS_DYNAMIC['ProduttoreCodiceFiscale'], 'value': record.get('codice_fiscale', '')}
    fields['TrasportatoreDenominazione'] = {**COORDS_DYNAMIC['TrasportatoreDenominazione'], 'value': record.get('denominazione', '')}
    fields['TrasportatoreCodiceFiscale'] = {**COORDS_DYNAMIC['TrasportatoreCodiceFiscale'], 'value': record.get('codice_fiscale', '')}
    fields['TrasportatoreAlbo'] = {**COORDS_DYNAMIC['TrasportatoreAlbo'], 'value': record.get('numero_iscrizione', '')}
    
    targa_val = '' if selected_targa == SENZA_TARGA else (selected_targa or '')
    fields['TrasportatoreAutomezzo'] = {**COORDS_DYNAMIC['TrasportatoreAutomezzo'], 'value': targa_val}
    fields['Conducente'] = {**COORDS_DYNAMIC['Conducente'], 'value': record.get('conducente', '')}
    if tipo == '4BIS':
        fields['Annotazioni'] = {**COORDS_DYNAMIC['Annotazioni'], 'value': 'RIFIUTO DI PROPRIETÀ DEL TRASPORTATORE'}
    return fields


class MixedModeDialog(tk.Toplevel):
    def __init__(self, parent, available_targhe, total_pdf_pages, current_allocations, on_save):
        super().__init__(parent)
        self.title("Configurazione Modalità Mista Targhe")
        self.geometry("540x460")
        self.resizable(False, False)
        self.grab_set()

        self.available_targhe = available_targhe
        self.total_pdf_pages = total_pdf_pages
        self.total_firs = total_pdf_pages // 4 if total_pdf_pages > 0 else 0
        self.allocations = [dict(a) for a in current_allocations]
        self.on_save = on_save

        self._build_ui()

    def _build_ui(self):
        main = ttk.Frame(self, padding=14)
        main.pack(fill='both', expand=True)

        info_text = f"Formulari totali stimati nel PDF: {self.total_firs} ({self.total_pdf_pages} pagine)" if self.total_pdf_pages > 0 else "Nessun PDF caricato (definisci i blocchi liberamente)."
        ttk.Label(main, text=info_text, font=('Segoe UI Semibold', 10)).pack(anchor='w', pady=(0, 10))

        # Form di inserimento
        form_frame = ttk.LabelFrame(main, text="Aggiungi Blocco Formulario", padding=10)
        form_frame.pack(fill='x', pady=(0, 10))

        ttk.Label(form_frame, text="Targa:").grid(row=0, column=0, sticky='w')
        self.cbo_targa_dlg = ttk.Combobox(form_frame, values=self.available_targhe, width=16, state='readonly')
        self.cbo_targa_dlg.grid(row=0, column=1, padx=(6, 12))
        if self.available_targhe:
            self.cbo_targa_dlg.set(self.available_targhe[0])

        ttk.Label(form_frame, text="N° Formulari:").grid(row=0, column=2, sticky='w')
        self.ent_qty = ttk.Entry(form_frame, width=8)
        self.ent_qty.insert(0, "50")
        self.ent_qty.grid(row=0, column=3, padx=(6, 12))

        ttk.Button(form_frame, text="Aggiungi", command=self.add_allocation).grid(row=0, column=4)

        # Tabella Allocazioni
        self.tree = ttk.Treeview(main, columns=('targa', 'firs', 'pages'), show='headings', height=8)
        self.tree.heading('targa', text='Targa')
        self.tree.heading('firs', text='N° Formulari')
        self.tree.heading('pages', text='Pagine Coperta')
        self.tree.column('targa', width=160)
        self.tree.column('firs', width=120, anchor='center')
        self.tree.column('pages', width=180, anchor='center')
        self.tree.pack(fill='both', expand=True, pady=(0, 10))

        btn_row = ttk.Frame(main)
        btn_row.pack(fill='x')

        ttk.Button(btn_row, text="Rimuovi Selezionato", command=self.remove_allocation).pack(side='left')
        ttk.Button(btn_row, text="Conferma e Salva", command=self.save_and_close, style='Accent.TButton').pack(side='right')

        self.lbl_summary = ttk.Label(main, text="", font=('Segoe UI', 9))
        self.lbl_summary.pack(anchor='w', pady=(6, 0))

        self.refresh_tree()

    def refresh_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        current_page_start = 1
        total_assigned_firs = 0

        for alloc in self.allocations:
            firs = alloc['count']
            pages_count = firs * 4
            p_start = current_page_start
            p_end = current_page_start + pages_count - 1
            current_page_start += pages_count
            total_assigned_firs += firs

            self.tree.insert('', 'end', values=(alloc['targa'], firs, f"Pag. {p_start} - {p_end} ({pages_count} pag.)"))

        summary_txt = f"Totale formulari configurati: {total_assigned_firs}"
        if self.total_firs > 0:
            summary_txt += f" / {self.total_firs} formulari del PDF"
        self.lbl_summary.config(text=summary_txt)

    def add_allocation(self):
        targa = self.cbo_targa_dlg.get()
        try:
            qty = int(self.ent_qty.get().strip())
            if qty <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Errore", "Inserire un numero valido di formulari.")
            return

        self.allocations.append({'targa': targa, 'count': qty})
        self.refresh_tree()

    def remove_allocation(self):
        selected = self.tree.selection()
        if not selected:
            return
        idx = self.tree.index(selected[0])
        del self.allocations[idx]
        self.refresh_tree()

    def save_and_close(self):
        self.on_save(self.allocations)
        self.destroy()


class FIRSuiteApp:
    def __init__(self, root):
        self.root = root
        self.root.title('FIR Suite')
        self.root.geometry('1680x980')
        self.root.minsize(1380, 860)
        self.db = load_db()
        self.selected_index = None
        self.input_pdf = None
        self.preview_pdf = None
        self.doc = None
        self.page_index = 0
        self.zoom = 1.15
        self.tk_img = None
        self.mixed_allocations = []

        self._apply_theme()
        self._build_ui()
        self.refresh_anagrafica_list()
        self.refresh_generator_list()

    def _apply_theme(self):
        self.colors = {
            'bg': '#f4f1eb',
            'panel': '#fbfaf7',
            'panel_alt': '#efebe4',
            'text': '#201d18',
            'muted': '#716b63',
            'border': '#d8d1c7',
            'accent': '#0d6b68',
            'accent_soft': '#d8ebe9',
            'danger': '#b82525',
            'canvas': '#c8c0b5',
            'white': '#ffffff',
        }
        self.root.configure(bg=self.colors['bg'])
        style = ttk.Style()
        try:
            style.theme_use('clam')
        except tk.TclError:
            pass
        style.configure('.', background=self.colors['bg'], foreground=self.colors['text'], fieldbackground=self.colors['white'])
        style.configure('App.TFrame', background=self.colors['bg'])
        style.configure('Panel.TFrame', background=self.colors['panel'])
        style.configure('Soft.TFrame', background=self.colors['panel_alt'])
        style.configure('App.TLabel', background=self.colors['bg'], foreground=self.colors['text'], font=('Segoe UI', 10))
        style.configure('Muted.TLabel', background=self.colors['panel'], foreground=self.colors['muted'], font=('Segoe UI', 9))
        style.configure('Title.TLabel', background=self.colors['bg'], foreground=self.colors['text'], font=('Segoe UI Semibold', 19))
        style.configure('Section.TLabel', background=self.colors['panel'], foreground=self.colors['text'], font=('Segoe UI Semibold', 11))
        style.configure('TNotebook', background=self.colors['bg'], borderwidth=0)
        style.configure('TNotebook.Tab', padding=(16, 10), font=('Segoe UI Semibold', 10), background=self.colors['panel_alt'])
        style.map('TNotebook.Tab', background=[('selected', self.colors['panel'])], foreground=[('selected', self.colors['accent'])])
        style.configure('TButton', padding=(12, 8), font=('Segoe UI Semibold', 10), borderwidth=0)
        style.map('TButton', background=[('active', self.colors['accent_soft'])])
        style.configure('Accent.TButton', background=self.colors['accent'], foreground=self.colors['white'])
        style.map('Accent.TButton', background=[('active', '#095754')])
        style.configure('TEntry', padding=7)
        style.configure('TCombobox', padding=6)
        style.configure('TLabelframe', background=self.colors['panel'], bordercolor=self.colors['border'])
        style.configure('TLabelframe.Label', background=self.colors['panel'], foreground=self.colors['text'], font=('Segoe UI Semibold', 10))
        style.configure('TCheckbutton', background=self.colors['bg'], foreground=self.colors['text'])

    def _build_ui(self):
        shell = ttk.Frame(self.root, style='App.TFrame', padding=14)
        shell.pack(fill='both', expand=True)

        hero = ttk.Frame(shell, style='Panel.TFrame', padding=(18, 14))
        hero.pack(fill='x', pady=(0, 12))
        ttk.Label(hero, text='FIR Suite', style='Title.TLabel').pack(anchor='w')
        ttk.Label(hero, text='Gestione anagrafiche e generazione PDF FIR in un solo programma.', style='Muted.TLabel').pack(anchor='w', pady=(4, 0))

        self.notebook = ttk.Notebook(shell)
        self.notebook.pack(fill='both', expand=True)
        self.tab_anag = ttk.Frame(self.notebook, style='App.TFrame')
        self.tab_gen = ttk.Frame(self.notebook, style='App.TFrame')
        self.notebook.add(self.tab_anag, text='Anagrafiche')
        self.notebook.add(self.tab_gen, text='Genera PDF')
        self._build_anagrafiche_tab()
        self._build_generator_tab()

    def _build_anagrafiche_tab(self):
        top = ttk.Frame(self.tab_anag, style='App.TFrame', padding=6)
        top.pack(fill='both', expand=True)

        left_card = ttk.Frame(top, style='Panel.TFrame', padding=14)
        left_card.pack(side='left', fill='y', padx=(0, 10))
        ttk.Label(left_card, text='Archivio anagrafiche', style='Section.TLabel').pack(anchor='w')
        ttk.Label(left_card, text='Seleziona, modifica o crea un soggetto.', style='Muted.TLabel').pack(anchor='w', pady=(2, 10))
        self.listbox = tk.Listbox(left_card, width=38, height=30, relief='flat', bd=0, highlightthickness=1,
                                  bg=self.colors['white'], fg=self.colors['text'], selectbackground=self.colors['accent'],
                                  selectforeground=self.colors['white'], highlightbackground=self.colors['border'])
        self.listbox.pack(fill='y', expand=True)
        self.listbox.bind('<<ListboxSelect>>', self.on_select_anagrafica)
        btns = ttk.Frame(left_card, style='Panel.TFrame')
        btns.pack(fill='x', pady=(12, 0))
        ttk.Button(btns, text='Nuova', command=self.new_record).pack(side='left')
        ttk.Button(btns, text='Salva', command=self.save_record, style='Accent.TButton').pack(side='left', padx=(8, 0))
        ttk.Button(btns, text='Elimina', command=self.delete_record).pack(side='left', padx=(8, 0))

        right = ttk.Frame(top, style='App.TFrame')
        right.pack(side='left', fill='both', expand=True)

        form_card = ttk.Frame(right, style='Panel.TFrame', padding=16)
        form_card.pack(fill='x')
        ttk.Label(form_card, text='Scheda anagrafica', style='Section.TLabel').grid(row=0, column=0, columnspan=2, sticky='w', pady=(0, 10))
        self.tipo_iscrizione = tk.StringVar(value='2BIS')
        self.numero_iscrizione = tk.StringVar()
        self.denominazione = tk.StringVar()
        self.codice_fiscale = tk.StringVar()
        self.indirizzo = tk.StringVar()
        self.cap_citta_prov = tk.StringVar()
        self.conducente = tk.StringVar()
        self.targa = tk.StringVar()
        self._row(form_card, 1, 'Tipo iscrizione', ttk.Combobox(form_card, textvariable=self.tipo_iscrizione, values=['2BIS', '4BIS'], width=14, state='readonly'))
        self._row(form_card, 2, 'Numero iscrizione', ttk.Entry(form_card, textvariable=self.numero_iscrizione, width=42))
        self._row(form_card, 3, 'Denominazione', ttk.Entry(form_card, textvariable=self.denominazione, width=72))
        self._row(form_card, 4, 'Codice fiscale', ttk.Entry(form_card, textvariable=self.codice_fiscale, width=42))
        self._row(form_card, 5, 'Indirizzo', ttk.Entry(form_card, textvariable=self.indirizzo, width=72))
        self._row(form_card, 6, 'CAP Città Prov', ttk.Entry(form_card, textvariable=self.cap_citta_prov, width=72))
        self._row(form_card, 7, 'Conducente', ttk.Entry(form_card, textvariable=self.conducente, width=42))
        ttk.Label(form_card, text='Targhe', style='App.TLabel').grid(row=8, column=0, sticky='nw', pady=6, padx=(0, 10))
        targhe_frame = ttk.Frame(form_card, style='Panel.TFrame')
        targhe_frame.grid(row=8, column=1, sticky='w')
        ttk.Entry(targhe_frame, textvariable=self.targa, width=20).pack(side='left')
        ttk.Button(targhe_frame, text='Aggiungi targa', command=self.add_targa).pack(side='left', padx=(8, 0))
        self.targhe_listbox = tk.Listbox(form_card, width=22, height=5, relief='flat', bd=0, highlightthickness=1,
                                         bg=self.colors['white'], fg=self.colors['text'], selectbackground=self.colors['accent'],
                                         selectforeground=self.colors['white'], highlightbackground=self.colors['border'])
        self.targhe_listbox.grid(row=9, column=1, sticky='w', pady=(6, 0))
        ttk.Button(form_card, text='Rimuovi targa', command=self.remove_targa).grid(row=10, column=1, sticky='w', pady=(8, 0))

        paste_box = ttk.LabelFrame(right, text='Importa testo Albo', padding=14)
        paste_box.pack(fill='both', expand=True, pady=(12, 0))
        self.raw_text = tk.Text(paste_box, height=10, relief='flat', bd=0, highlightthickness=1,
                                bg=self.colors['white'], fg=self.colors['text'], insertbackground=self.colors['text'],
                                highlightbackground=self.colors['border'])
        self.raw_text.pack(fill='both', expand=True)
        paste_btns = ttk.Frame(paste_box, style='Panel.TFrame')
        paste_btns.pack(fill='x', pady=(10, 0))
        ttk.Button(paste_btns, text='Importa da testo', command=self.import_from_text, style='Accent.TButton').pack(side='left')
        ttk.Button(paste_btns, text='Pulisci testo', command=lambda: self.raw_text.delete('1.0', 'end')).pack(side='left', padx=(8, 0))
        self.status_anag = tk.StringVar(value='Pronto.')
        ttk.Label(right, textvariable=self.status_anag, style='Muted.TLabel').pack(fill='x', pady=(8, 0))

    def _build_generator_tab(self):
        wrapper = ttk.Frame(self.tab_gen, style='App.TFrame', padding=6)
        wrapper.pack(fill='both', expand=True)

        top_card = ttk.Frame(wrapper, style='Panel.TFrame', padding=14)
        top_card.pack(fill='x', pady=(0, 10))

        self.gen_selected_anagrafica = tk.StringVar()
        self.gen_tipo_iscrizione = tk.StringVar()
        self.gen_selected_targa = tk.StringVar()
        self.mixed_mode = tk.BooleanVar(value=False)
        self.x_size = tk.DoubleVar(value=4.0)
        self.x_width = tk.DoubleVar(value=1.2)
        self.default_text_font = tk.IntVar(value=10)
        self.debug_mode = tk.BooleanVar(value=True)

        ttk.Label(top_card, text='Generazione FIR', style='Section.TLabel').grid(row=0, column=0, columnspan=8, sticky='w', pady=(0, 10))
        
        ttk.Label(top_card, text='Anagrafica', style='App.TLabel').grid(row=1, column=0, sticky='w')
        self.cbo_anag = ttk.Combobox(top_card, textvariable=self.gen_selected_anagrafica, width=34, state='readonly')
        self.cbo_anag.grid(row=1, column=1, sticky='w', padx=(6, 14))
        self.cbo_anag.bind('<<ComboboxSelected>>', self.on_generator_select_anagrafica)

        ttk.Label(top_card, text='Tipo', style='App.TLabel').grid(row=1, column=2, sticky='w')
        # Tipo iscrizione visibile ma NON modificabile (state='disabled')
        self.cbo_tipo = ttk.Combobox(top_card, textvariable=self.gen_tipo_iscrizione, values=['2BIS', '4BIS'], width=8, state='disabled')
        self.cbo_tipo.grid(row=1, column=3, sticky='w', padx=(6, 14))

        ttk.Label(top_card, text='Targa', style='App.TLabel').grid(row=1, column=4, sticky='w')
        self.cbo_targa = ttk.Combobox(top_card, textvariable=self.gen_selected_targa, width=16, state='readonly')
        self.cbo_targa.grid(row=1, column=5, sticky='w', padx=(6, 14))
        self.cbo_targa.bind('<<ComboboxSelected>>', self._on_targa_changed)

        ttk.Button(top_card, text='Apri PDF modello', command=self.open_pdf).grid(row=1, column=6, sticky='w')
        ttk.Button(top_card, text='Esporta PDF', command=self.export_pdf, style='Accent.TButton').grid(row=1, column=7, sticky='w', padx=(8, 0))

        # Mini avviso senza targa e Modalità Mista
        row2_frame = ttk.Frame(top_card, style='Panel.TFrame')
        row2_frame.grid(row=2, column=0, columnspan=8, sticky='w', pady=(10, 0))

        self.lbl_targa_warning = tk.Label(row2_frame, text='', font=('Segoe UI Semibold', 9), fg=self.colors['danger'], bg=self.colors['panel'])
        self.lbl_targa_warning.pack(side='left', padx=(0, 20))

        ttk.Checkbutton(row2_frame, text='Modalità Mista (Ripartizione Targhe)', variable=self.mixed_mode, command=self._on_mixed_mode_toggle).pack(side='left')
        self.btn_config_mixed = ttk.Button(row2_frame, text='Configura Blocchi Targhe', command=self.open_mixed_mode_dialog, state='disabled')
        self.btn_config_mixed.pack(side='left', padx=(10, 0))

        controls_card = ttk.Frame(wrapper, style='Soft.TFrame', padding=12)
        controls_card.pack(fill='x', pady=(0, 10))
        ttk.Label(controls_card, text='Controlli preview', style='Section.TLabel').pack(side='left')
        ttk.Label(controls_card, text='Dimensione X', style='App.TLabel').pack(side='left', padx=(18, 4))
        ttk.Entry(controls_card, textvariable=self.x_size, width=6).pack(side='left')
        ttk.Label(controls_card, text='Spessore X', style='App.TLabel').pack(side='left', padx=(16, 4))
        ttk.Entry(controls_card, textvariable=self.x_width, width=6).pack(side='left')
        ttk.Label(controls_card, text='Font base', style='App.TLabel').pack(side='left', padx=(16, 4))
        ttk.Entry(controls_card, textvariable=self.default_text_font, width=6).pack(side='left')
        ttk.Checkbutton(controls_card, text='Debug visivo', variable=self.debug_mode, command=self.refresh_preview).pack(side='left', padx=(18, 0))
        
        ttk.Button(controls_card, text='Aggiorna preview', command=self.refresh_preview).pack(side='right')
        ttk.Button(controls_card, text='Pagina successiva', command=self.next_page).pack(side='right', padx=(0, 8))
        ttk.Button(controls_card, text='Pagina precedente', command=self.prev_page).pack(side='right', padx=(0, 8))

        preview_card = ttk.Frame(wrapper, style='Panel.TFrame', padding=10)
        preview_card.pack(fill='both', expand=True)
        self.info = tk.StringVar(value='Seleziona anagrafica, targa e PDF modello.')
        ttk.Label(preview_card, textvariable=self.info, style='Muted.TLabel').pack(fill='x', pady=(0, 8))
        canvas_wrap = ttk.Frame(preview_card, style='Panel.TFrame')
        canvas_wrap.pack(fill='both', expand=True)
        self.canvas = tk.Canvas(canvas_wrap, bg=self.colors['canvas'], relief='flat', bd=0, highlightthickness=0)
        self.v_scroll = ttk.Scrollbar(canvas_wrap, orient='vertical', command=self.canvas.yview)
        self.h_scroll = ttk.Scrollbar(canvas_wrap, orient='horizontal', command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=self.v_scroll.set, xscrollcommand=self.h_scroll.set)
        self.canvas.grid(row=0, column=0, sticky='nsew')
        self.v_scroll.grid(row=0, column=1, sticky='ns')
        self.h_scroll.grid(row=1, column=0, sticky='ew')
        canvas_wrap.rowconfigure(0, weight=1)
        canvas_wrap.columnconfigure(0, weight=1)
        self.canvas.bind('<MouseWheel>', self._on_mousewheel)
        self.canvas.bind('<Shift-MouseWheel>', self._on_shift_mousewheel)

    def _row(self, parent, row, label, widget):
        ttk.Label(parent, text=label, style='App.TLabel').grid(row=row, column=0, sticky='w', pady=6, padx=(0, 10))
        widget.grid(row=row, column=1, sticky='w', pady=6)

    def refresh_anagrafica_list(self):
        sort_anagrafiche(self.db)
        self.listbox.delete(0, 'end')
        for rec in self.db['anagrafiche']:
            self.listbox.insert('end', f"{rec.get('denominazione','')} [{rec.get('tipo_iscrizione','')}]")

    def refresh_generator_list(self):
        sort_anagrafiche(self.db)
        labels = [r.get('denominazione', '') for r in self.db['anagrafiche']]
        self.cbo_anag['values'] = labels
        if labels:
            if self.gen_selected_anagrafica.get() not in labels:
                self.gen_selected_anagrafica.set(labels[0])
            self.on_generator_select_anagrafica()

    def clear_form(self):
        self.selected_index = None
        self.tipo_iscrizione.set('2BIS')
        self.numero_iscrizione.set('')
        self.denominazione.set('')
        self.codice_fiscale.set('')
        self.indirizzo.set('')
        self.cap_citta_prov.set('')
        self.conducente.set('')
        self.targa.set('')
        self.targhe_listbox.delete(0, 'end')
        self.status_anag.set('Nuova anagrafica.')

    def new_record(self):
        self.clear_form()

    def on_select_anagrafica(self, event=None):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        rec = self.db['anagrafiche'][idx]
        self.selected_index = idx
        self.tipo_iscrizione.set(rec.get('tipo_iscrizione', '2BIS'))
        self.numero_iscrizione.set(rec.get('numero_iscrizione', ''))
        self.denominazione.set(rec.get('denominazione', ''))
        self.codice_fiscale.set(rec.get('codice_fiscale', ''))
        self.indirizzo.set(rec.get('indirizzo', ''))
        self.cap_citta_prov.set(rec.get('cap_citta_prov', ''))
        self.conducente.set(rec.get('conducente', ''))
        self.targhe_listbox.delete(0, 'end')
        for t in rec.get('targhe', []):
            self.targhe_listbox.insert('end', t)
        self.status_anag.set('Anagrafica caricata.')

    def add_targa(self):
        val = self.targa.get().strip().upper()
        if not val:
            return
        existing = list(self.targhe_listbox.get(0, 'end'))
        if val not in existing:
            self.targhe_listbox.insert('end', val)
        self.targa.set('')

    def remove_targa(self):
        sel = self.targhe_listbox.curselection()
        if not sel:
            return
        self.targhe_listbox.delete(sel[0])

    def save_record(self):
        denominazione = self.denominazione.get().strip()
        if not denominazione:
            messagebox.showerror('Errore', 'La denominazione è obbligatoria.')
            return
        rec = {
            'tipo_iscrizione': self.tipo_iscrizione.get().strip(),
            'numero_iscrizione': self.numero_iscrizione.get().strip(),
            'denominazione': denominazione,
            'codice_fiscale': self.codice_fiscale.get().strip(),
            'indirizzo': self.indirizzo.get().strip(),
            'cap_citta_prov': self.cap_citta_prov.get().strip(),
            'conducente': self.conducente.get().strip(),
            'targhe': list(self.targhe_listbox.get(0, 'end')),
        }
        if self.selected_index is None:
            self.db['anagrafiche'].append(rec)
        else:
            self.db['anagrafiche'][self.selected_index] = rec
        save_db(self.db)
        self.refresh_anagrafica_list()
        self.refresh_generator_list()
        self.status_anag.set('Anagrafica salvata.')

    def delete_record(self):
        if self.selected_index is None:
            return
        rec = self.db['anagrafiche'][self.selected_index]
        if not messagebox.askyesno('Conferma', f"Eliminare {rec.get('denominazione','')}?"):
            return
        del self.db['anagrafiche'][self.selected_index]
        save_db(self.db)
        self.refresh_anagrafica_list()
        self.refresh_generator_list()
        self.clear_form()
        self.status_anag.set('Anagrafica eliminata.')

    def import_from_text(self):
        text = self.raw_text.get('1.0', 'end').strip()
        if not text:
            return
        lines = normalize_lines(text)
        if not lines:
            return
        numero = ''
        denominazione = ''
        codice_fiscale = ''
        indirizzo = ''
        cap_citta_prov = ''
        targhe = []
        for line in lines:
            low = line.lower()
            if low.startswith('numero iscrizione'):
                numero = line.split(':', 1)[1].strip() if ':' in line else line.replace('Numero iscrizione', '').strip()
            elif low.startswith('codice fiscale'):
                codice_fiscale = line.split(':', 1)[1].strip() if ':' in line else line.replace('Codice fiscale', '').strip()
            elif not denominazione and 'codice fiscale' not in low and 'numero iscrizione' not in low:
                denominazione = line.strip()
            elif not indirizzo and any(ch.isdigit() for ch in line) and '(' not in line and len(line) > 6:
                indirizzo = line.strip()
            elif not cap_citta_prov and '(' in line and ')' in line:
                cap_citta_prov = line.strip()
            else:
                token = line.strip().upper().replace(' ', '')
                if 5 <= len(token) <= 10 and any(c.isdigit() for c in token) and any(c.isalpha() for c in token):
                    targhe.append(token)
        self.numero_iscrizione.set(numero)
        self.denominazione.set(denominazione)
        self.codice_fiscale.set(codice_fiscale)
        self.indirizzo.set(indirizzo)
        self.cap_citta_prov.set(cap_citta_prov)
        self.targhe_listbox.delete(0, 'end')
        for t in targhe:
            if t not in self.targhe_listbox.get(0, 'end'):
                self.targhe_listbox.insert('end', t)
        self.status_anag.set('Dati importati dal testo. Controlla e salva.')

    def get_generator_record(self):
        name = self.gen_selected_anagrafica.get()
        for r in self.db['anagrafiche']:
            if r.get('denominazione', '') == name:
                rec = dict(r)
                rec['tipo_iscrizione'] = self.gen_tipo_iscrizione.get() or r.get('tipo_iscrizione', '2BIS')
                return rec
        return None

    def on_generator_select_anagrafica(self, event=None):
        rec = None
        for r in self.db['anagrafiche']:
            if r.get('denominazione', '') == self.gen_selected_anagrafica.get():
                rec = r
                break
        if not rec:
            self.cbo_targa['values'] = [SENZA_TARGA]
            self.gen_selected_targa.set(SENZA_TARGA)
            self._update_targa_warning()
            return

        self.gen_tipo_iscrizione.set(rec.get('tipo_iscrizione', '2BIS'))
        targhe = rec.get('targhe', [])
        options = [SENZA_TARGA] + targhe
        self.cbo_targa['values'] = options
        self.gen_selected_targa.set(options[1] if len(options) > 1 else SENZA_TARGA)

        self._update_targa_warning()
        self.info.set(f"Selezionata anagrafica: {rec.get('denominazione','')} | Tipo: {self.gen_tipo_iscrizione.get()} | Targa: {self.gen_selected_targa.get()}")

    def _on_targa_changed(self, event=None):
        self._update_targa_warning()

    def _update_targa_warning(self):
        if self.gen_selected_targa.get() == SENZA_TARGA or not self.gen_selected_targa.get():
            self.lbl_targa_warning.config(text="⚠️ ATTENZIONE: Generazione SENZA TARGA!")
        else:
            self.lbl_targa_warning.config(text="")

    def _on_mixed_mode_toggle(self):
        if self.mixed_mode.get():
            self.btn_config_mixed.config(state='normal')
            if not self.mixed_allocations:
                self.open_mixed_mode_dialog()
        else:
            self.btn_config_mixed.config(state='disabled')

    def open_mixed_mode_dialog(self):
        rec = self.get_generator_record()
        available_targhe = [SENZA_TARGA] + (rec.get('targhe', []) if rec else [])
        total_pages = len(self.doc) if self.doc else 0

        def save_callback(allocations):
            self.mixed_allocations = allocations
            if self.doc:
                self.refresh_preview()

        MixedModeDialog(self.root, available_targhe, total_pages, self.mixed_allocations, save_callback)

    def get_targa_for_page(self, page_index):
        if self.mixed_mode.get() and self.mixed_allocations:
            fir_index = page_index // 4  # 1 formulario = 4 pagine (duplice copia x2)
            current_count = 0
            for alloc in self.mixed_allocations:
                targa = alloc['targa']
                count = alloc['count']
                if current_count <= fir_index < current_count + count:
                    return targa
                current_count += count
            if self.mixed_allocations:
                return self.mixed_allocations[-1]['targa']

        return self.gen_selected_targa.get()

    def open_pdf(self):
        path = filedialog.askopenfilename(filetypes=[('PDF files', '*.pdf')])
        if not path:
            return
        self.input_pdf = path
        self.page_index = 0
        self.refresh_preview()

    def prev_page(self):
        if self.doc and self.page_index > 0:
            self.page_index -= 1
            self.render_current_page()

    def next_page(self):
        if self.doc and self.page_index < len(self.doc) - 1:
            self.page_index += 1
            self.render_current_page()

    def is_target_page(self, zero_based_index):
        # Il programma lavora solo sulle pagine dispari (1, 3, 5, 7 -> indici 0, 2, 4, 6...)
        return zero_based_index % 2 == 0

    def draw_fit_text(self, c, field, debug=False, name=''):
        x = field['x']
        y = field['y']
        text = str(field.get('value', ''))
        font_name = field.get('font', 'Helvetica')
        max_width = float(field.get('max_width', 100))
        max_font = float(field.get('max_font', 8))
        min_font = float(field.get('min_font', 4))
        font_size = max_font
        while font_size > min_font and stringWidth(text, font_name, font_size) > max_width:
            font_size -= 0.2
        if font_size < min_font:
            font_size = min_font
        c.setFont(font_name, font_size)
        c.setFillColorRGB(0, 0, 0)
        c.drawString(x, y, text)
        if debug:
            c.setStrokeColor(Color(0, 0.45, 0.25, alpha=0.9))
            c.setLineWidth(0.6)
            c.rect(x - 2, y - 2, max_width, font_size + 4, stroke=1, fill=0)
            c.setFont('Helvetica', 6)
            c.setFillColorRGB(0, 0.45, 0.25)
            c.drawString(x + max_width + 4, y + 2, f'{name} ({font_size:.1f}pt)')

    def create_overlay_for_page(self, page_width, page_height, page_index, debug=False):
        packet = io.BytesIO()
        c = rl_canvas.Canvas(packet, pagesize=(page_width, page_height))
        x_size = float(self.x_size.get())
        x_width = float(self.x_width.get())
        default_text_font = int(self.default_text_font.get())
        record = self.get_generator_record()
        if not record:
            c.showPage()
            c.save()
            packet.seek(0)
            return packet

        targa_for_page = self.get_targa_for_page(page_index)
        fields = build_fields(record, targa_for_page)

        if self.is_target_page(page_index):
            for name, field in fields.items():
                x, y = field['x'], field['y']
                if name == 'RegistroNO' and record.get('tipo_iscrizione', '').upper() != '2BIS':
                    continue
                if field['type'] == 'x':
                    c.saveState()
                    c.setLineWidth(x_width)
                    c.setStrokeColorRGB(0, 0, 0)
                    c.line(x - x_size, y - x_size, x + x_size, y + x_size)
                    c.line(x - x_size, y + x_size, x + x_size, y - x_size)
                    if debug:
                        c.setStrokeColor(Color(0.84, 0.15, 0.15, alpha=0.9))
                        c.setLineWidth(0.6)
                        c.circle(x, y, x_size + 3, stroke=1, fill=0)
                        c.setFont('Helvetica', 6)
                        c.setFillColorRGB(0.84, 0.15, 0.15)
                        c.drawString(x + 6, y + 4, name)
                    c.restoreState()
                elif field['type'] == 'text':
                    c.saveState()
                    font_name = field.get('font', 'Helvetica-Bold')
                    font_size = field.get('font_size', default_text_font)
                    c.setFont(font_name, font_size)
                    c.setFillColorRGB(0, 0, 0)
                    c.drawString(x, y, str(field.get('value', '')))
                    if debug:
                        debug_w = max(18, stringWidth(str(field.get('value', '')), font_name, font_size) + 4)
                        c.setStrokeColor(Color(0.1, 0.32, 0.75, alpha=0.9))
                        c.setLineWidth(0.6)
                        c.rect(x - 2, y - 2, debug_w, font_size + 4, stroke=1, fill=0)
                        c.setFont('Helvetica', 6)
                        c.setFillColorRGB(0.1, 0.32, 0.75)
                        c.drawString(x + debug_w + 2, y + 2, name)
                    c.restoreState()
                elif field['type'] == 'fit_text':
                    c.saveState()
                    self.draw_fit_text(c, field, debug=debug, name=name)
                    c.restoreState()
        c.showPage()
        c.save()
        packet.seek(0)
        return packet

    def build_output_pdf(self, output_path, debug=False):
        reader = PdfReader(self.input_pdf)
        writer = PdfWriter()
        for i, src_page in enumerate(reader.pages):
            page = src_page
            width = float(page.mediabox.width)
            height = float(page.mediabox.height)
            overlay_stream = self.create_overlay_for_page(width, height, i, debug=debug)
            overlay_pdf = PdfReader(overlay_stream)
            if len(overlay_pdf.pages) > 0:
                page.merge_page(overlay_pdf.pages[0])
            writer.add_page(page)
        with open(output_path, 'wb') as f:
            writer.write(f)

    def refresh_preview(self):
        if not self.input_pdf:
            messagebox.showwarning('Attenzione', 'Apri prima il PDF modello.')
            return
        if not self.get_generator_record():
            messagebox.showwarning("Attenzione", "Seleziona prima un'anagrafica.")
            return
        if self.doc is not None:
            self.doc.close()
            self.doc = None
        if self.preview_pdf and os.path.exists(self.preview_pdf):
            try:
                os.remove(self.preview_pdf)
            except OSError:
                pass
        fd, temp_path = tempfile.mkstemp(suffix='.pdf')
        os.close(fd)
        self.preview_pdf = temp_path
        self.build_output_pdf(self.preview_pdf, debug=self.debug_mode.get())
        self.doc = fitz.open(self.preview_pdf)
        if self.page_index >= len(self.doc):
            self.page_index = 0
        self.render_current_page()

    def render_current_page(self):
        if not self.doc:
            return
        page = self.doc[self.page_index]
        mat = fitz.Matrix(self.zoom, self.zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes('RGB', [pix.width, pix.height], pix.samples)
        self.tk_img = ImageTk.PhotoImage(img)
        self.canvas.delete('all')
        total_w = pix.width + 36
        total_h = pix.height + 36
        self.canvas.config(scrollregion=(0, 0, total_w, total_h))
        self.canvas.create_rectangle(8, 8, pix.width + 28, pix.height + 28, outline='#b9b0a4', width=1, fill='#fdfcf9')
        self.canvas.create_image(18, 18, anchor='nw', image=self.tk_img)
        self.canvas.xview_moveto(0)
        self.canvas.yview_moveto(0)

        lato = 'Dispari' if (self.page_index + 1) % 2 == 1 else 'Pari'
        targa_corrente = self.get_targa_for_page(self.page_index)
        self.info.set(
            f"Pagina {self.page_index + 1}/{len(self.doc)} • {lato} • Debug: {self.debug_mode.get()} • "
            f"Anagrafica: {self.gen_selected_anagrafica.get()} • Tipo: {self.gen_tipo_iscrizione.get()} • Targa Pagina: {targa_corrente}"
        )

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')

    def _on_shift_mousewheel(self, event):
        self.canvas.xview_scroll(int(-1 * (event.delta / 120)), 'units')

    def export_pdf(self):
        if not self.input_pdf:
            messagebox.showwarning('Attenzione', 'Apri prima il PDF modello.')
            return
        record = self.get_generator_record()
        if not record:
            messagebox.showwarning("Attenzione", "Seleziona prima un'anagrafica.")
            return

        targa_lbl = 'MISTA' if self.mixed_mode.get() else (self.gen_selected_targa.get() or 'SENZA_TARGA')
        suggested = f"FIR_{record.get('denominazione','').replace(' ', '_')}_{targa_lbl}.pdf"
        output_path = filedialog.asksaveasfilename(
            defaultextension='.pdf',
            filetypes=[('PDF files', '*.pdf')],
            initialfile=suggested
        )
        if not output_path:
            return
        self.build_output_pdf(output_path, debug=False)
        messagebox.showinfo("Completato", f"PDF esportato:\n{output_path}")


root = tk.Tk()
app = FIRSuiteApp(root)
root.mainloop()
