import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import yaml
from collections import OrderedDict


# Zachowanie kolejności kluczy podczas zapisu do YAML.
def represent_ordereddict(dumper, data):
    value = []
    for item_key, item_value in data.items():
        node_key = dumper.represent_data(item_key)
        node_value = dumper.represent_data(item_value)
        value.append((node_key, node_value))
    return yaml.nodes.MappingNode("tag:yaml.org,2002:map", value)


yaml.add_representer(OrderedDict, represent_ordereddict)

OPTIONS_OS = ["", "simulated", "cloud", "edge1"]
OPTIONS_TAINT_KEY = ["", "node-role.kubernetes.io/master"]
OPTIONS_TAINT_EFFECT = ["", "NoSchedule", "NoExecute", "PreferNoSchedule"]
OPTIONS_CPU_VALUES = ["", "1", "2", "3.8", "4", "5", "7.9", "8", "10", "16"]
OPTIONS_MEMORY_NUM_VALUES = ["", "4", "8", "10", "16", "20", "32"]
OPTIONS_MEMORY_UNITS = ["", "Ki", "Mi", "Gi"]
OPTIONS_GPU_VALUES = ["", "0", "4", "8", "10", "16", "32", "40", "64"]
OPTIONS_PODS_VALUES = ["", "50", "110", "220"]
OPTIONS_CALC_SPEED = ["", "0.75", "0.80", "1.0"]
OPTIONS_CTN_TIME = ["", "2", "6"]
OPTIONS_CTN_EXTRA_TIME = ["", "0.5", "2.0" "2.5"]
OPTIONS_CTN_INTERVAL = ["", "1", "2"]


class DynamicListFrame(ttk.Frame):
    def __init__(
        self,
        master,
        item_label_singular,
        field_definitions,
        initial_data,
        min_items=0,
    ):
        # Inicjalizuje ramkę, ustawia etykiety, funkcję definicji pól i minimalną liczbę elementów.
        super().__init__(master, padding="5")
        self.item_label_singular = item_label_singular
        self.field_definitions = field_definitions
        self.min_items = min_items
        self.item_frames = []
        self.item_widgets_list = []

        # Konfiguracja okna aplikacji
        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(
            self, orient="vertical", command=self.canvas.yview
        )
        self.scrollable_frame = ttk.Frame(self.canvas)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        ttk.Button(
            self, text=f"Dodaj {self.item_label_singular}", command=self.add_item_gui
        ).pack(pady=5, anchor="w")

    def add_item_gui(self, item_values=None):
        # Dodaje nowy element do listy w GUI, wraz z jego polami.
        item_frame = ttk.LabelFrame(
            self.scrollable_frame,
            text=f"{self.item_label_singular} #{len(self.item_frames) + 1}",
            padding="5",
        )
        item_frame.pack(fill=tk.X, pady=3, padx=3)
        current_item_widgets = OrderedDict()

        for (
            field_name,
            label_text,
            widget_type,
            widget_options,
            default_value,
        ) in self.field_definitions:
            frame = ttk.Frame(item_frame)
            frame.pack(fill=tk.X, pady=1)
            ttk.Label(frame, text=label_text, width=15, anchor="w").pack(
                side=tk.LEFT, padx=2
            )
            var = tk.StringVar(
                value=(
                    item_values.get(field_name, default_value)
                    if item_values
                    else default_value
                )
            )

            widget = None
            actual_options = list(widget_options) if widget_options else []
            if widget_type == "entry":
                widget = ttk.Entry(frame, textvariable=var, width=20)
            elif widget_type == "combobox":
                if "" not in actual_options:
                    actual_options.insert(0, "")
                widget = ttk.Combobox(
                    frame,
                    textvariable=var,
                    values=actual_options,
                    state="readonly",
                    width=18,
                )
                var.set(
                    var.get()
                    if var.get() in actual_options
                    else (actual_options[0] if actual_options else "")
                )

            if widget:
                widget.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
            current_item_widgets[field_name] = var

        # Przycisk do usuwania tego elementu
        ttk.Button(
            item_frame,
            text="Usuń",
            width=6,
            command=lambda f=item_frame, w=current_item_widgets: self.remove_item(f, w),
        ).pack(side=tk.RIGHT, pady=2)
        self.item_frames.append(item_frame)
        self.item_widgets_list.append(current_item_widgets)

    # Usuwa element z listy w GUI.
    def remove_item(self, frame_to_remove, widgets_to_remove):
        if len(self.item_frames) <= self.min_items:
            messagebox.showinfo(
                "Informacja",
                f"Wymagana jest przynajmniej {self.min_items} {self.item_label_singular}.",
            )
            return
        frame_to_remove.destroy()
        self.item_frames.remove(frame_to_remove)
        self.item_widgets_list.remove(widgets_to_remove)
        self._renumber_items()

    # Aktualizuje etykiety numeryczne elementów po usunięciu.
    def _renumber_items(self):
        for i, frame in enumerate(self.item_frames):
            frame.config(text=f"{self.item_label_singular} #{i + 1}")

    # Zbiera dane ze wszystkich elementów listy w GUI i zwraca jako listę słowników lub None.
    def get_data(self):
        data_list = []
        for item_widgets_dict in self.item_widgets_list:
            item_data = OrderedDict()
            has_any_value = False
            for field_name, str_var in item_widgets_dict.items():
                value = str_var.get().strip()
                if value:
                    item_data[field_name] = value
                    has_any_value = True
            if has_any_value:
                data_list.append(item_data)
        return data_list if data_list else None


class NodeForm:
    # Tworzenie Węzła.
    def __init__(self, master, node_data_to_edit=None, on_save_callback=None):
        self.master = master
        self.on_save_callback = on_save_callback
        self.node_data_to_edit = node_data_to_edit
        self.top = tk.Toplevel(master)
        self.top.title("Definicja Węzła (Pola Opcjonalne)")
        self.top.geometry("750x800")
        self.widgets = {}
        self.dynamic_lists = {}

        notebook = ttk.Notebook(self.top)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        tabs_names = [
            "Metadata",
            "Spec",
            "Status: Allocatable",
            "Status: Capacity",
            "Dodatkowe",
        ]
        self.tabs = {name: ttk.Frame(notebook, padding="5") for name in tabs_names}
        for name, tab_frame in self.tabs.items():
            notebook.add(tab_frame, text=name)

        self._create_metadata_tab_fields(self.tabs["Metadata"])
        self._create_spec_tab_fields(self.tabs["Spec"])
        self._create_status_tabs_fields()  # Dla Allocatable i Capacity
        self._create_extra_tab_fields(self.tabs["Dodatkowe"])

        button_frame = ttk.Frame(self.top, padding="10")
        button_frame.pack(fill=tk.X, side=tk.BOTTOM)
        ttk.Button(button_frame, text="Zapisz Węzeł", command=self.save_node).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(button_frame, text="Anuluj", command=self.top.destroy).pack(
            side=tk.RIGHT, padx=5
        )

        if self.node_data_to_edit:
            self.populate_form(self.node_data_to_edit)

    # Tworzy pola w zakładce "Metadata".
    def _create_metadata_tab_fields(self, parent_tab):
        self.add_textfield(parent_tab, "metadata.name", "metadata.name:", "")
        labels_frame = ttk.LabelFrame(
            parent_tab, text="metadata.labels (opcjonalne)", padding="5"
        )
        labels_frame.pack(fill=tk.BOTH, expand=True, pady=3)
        self.dynamic_lists["metadata.labels"] = DynamicListFrame(
            labels_frame,
            "Etykieta",
            [
                (
                    "key",
                    "Klucz:",
                    "combobox",
                    ["beta.kubernetes.io/os", "linc/nodeType"],
                    "",
                ),
                ("value", "Wartość:", "combobox", OPTIONS_OS, ""),
            ],
            initial_data=self.get_initial_dynamic_list_data(
                self.node_data_to_edit, ["metadata", "labels"]
            ),
        )

    # Tworzy pola w zakładce "Spec".
    def _create_spec_tab_fields(self, parent_tab):
        self.add_combobox(
            parent_tab,
            "spec.unschedulable",
            "spec.unschedulable:",
            ["", "true", "false"],
            "",
            width=10,
        )
        taints_frame = ttk.LabelFrame(
            parent_tab, text="spec.taints (opcjonalne)", padding="5"
        )
        taints_frame.pack(fill=tk.BOTH, expand=True, pady=3)
        self.dynamic_lists["spec.taints"] = DynamicListFrame(
            taints_frame,
            "Taint",
            [
                ("key", "Klucz:", "combobox", OPTIONS_TAINT_KEY, ""),
                ("effect", "Efekt:", "combobox", OPTIONS_TAINT_EFFECT, ""),
            ],
            initial_data=self.get_initial_dynamic_list_data(
                self.node_data_to_edit, ["spec", "taints"]
            ),
        )

    # Tworzy pola w zakładkach "Status: Allocatable" i "Status: Capacity".
    def _create_status_tabs_fields(self):
        self._add_resource_fields_to_tab(
            self.tabs["Status: Allocatable"], "status.allocatable"
        )
        self._add_resource_fields_to_tab(
            self.tabs["Status: Capacity"], "status.capacity"
        )
        self.copy_alloc_to_cap_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            self.tabs["Status: Capacity"],
            text="Capacity = Allocatable",
            variable=self.copy_alloc_to_cap_var,
        ).pack(pady=10, anchor="w")

    def _add_resource_fields_to_tab(self, parent_tab, base_key):
        self.add_combobox(
            parent_tab, f"{base_key}.cpu", f"{base_key}.cpu:", OPTIONS_CPU_VALUES, ""
        )
        mem_frame = ttk.Frame(parent_tab)
        mem_frame.pack(fill=tk.X, pady=1)
        ttk.Label(mem_frame, text=f"{base_key}.memory:", width=25, anchor="w").pack(
            side=tk.LEFT, padx=2
        )
        self.widgets[f"{base_key}.memory.value"] = tk.StringVar(
            value=""
        )  # Dla wartości liczbowej
        ttk.Combobox(
            mem_frame,
            textvariable=self.widgets[f"{base_key}.memory.value"],
            values=OPTIONS_MEMORY_NUM_VALUES,
            width=8,
        ).pack(side=tk.LEFT)
        self.widgets[f"{base_key}.memory.unit"] = tk.StringVar(
            value="Gi"
        )  # Domyślna jednostka
        ttk.Combobox(
            mem_frame,
            textvariable=self.widgets[f"{base_key}.memory.unit"],
            values=OPTIONS_MEMORY_UNITS,
            state="readonly",
            width=5,
        ).pack(side=tk.LEFT)
        self.add_combobox(
            parent_tab,
            f"{base_key}.nvidia.com/gpu",
            f"{base_key}.nvidia.com/gpu:",
            OPTIONS_GPU_VALUES,
            "",
        )
        self.add_combobox(
            parent_tab, f"{base_key}.pods", f"{base_key}.pods:", OPTIONS_PODS_VALUES, ""
        )

    # Tworzy pola w zakładce "Dodatkowe".
    def _create_extra_tab_fields(self, parent_tab):
        extra_frame = ttk.LabelFrame(
            parent_tab, text="Właściwości dodatkowe (opcjonalne)", padding="5"
        )
        extra_frame.pack(fill=tk.BOTH, expand=True, pady=3)
        fields = [
            ("calculationSpeed", OPTIONS_CALC_SPEED),
            ("ctnCreationTime", OPTIONS_CTN_TIME),
            ("ctnCreationExtraTime", OPTIONS_CTN_EXTRA_TIME),
            ("ctnCreationTimeInterval", OPTIONS_CTN_INTERVAL),
        ]
        for key, opts in fields:
            self.add_combobox(extra_frame, key, f"{key}:", opts, "")

    # Pobiera początkowe dane dla DynamicListFrame z `node_data`.
    def get_initial_dynamic_list_data(self, node_data, path_keys):
        val = node_data
        if not val:
            return None
        try:
            for k in path_keys:
                if k == "labels" and isinstance(val.get(k), dict):
                    return [
                        OrderedDict([("key", lk), ("value", lv)])
                        for lk, lv in val.get(k, {}).items()
                    ]
                val = val.get(k)
            return val
        except:
            return None

    # Dodaje pole tekstowe do formularza.
    def add_textfield(self, parent, key_path, label_text, default="", width=30):
        var = tk.StringVar(value=str(default))
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=1)
        ttk.Label(frame, text=label_text, width=25, anchor="w").pack(
            side=tk.LEFT, padx=2
        )
        ttk.Entry(frame, textvariable=var, width=width).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=2
        )
        self.widgets[key_path] = var

    # Dodaje pole wyboru do formularza.
    def add_combobox(self, parent, key_path, label_text, options, default="", width=28):
        var = tk.StringVar()
        actual_options = list(options)  # `options` powinny już zawierać ""
        var.set(
            default
            if default in actual_options
            else (actual_options[0] if actual_options else "")
        )
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=1)
        ttk.Label(frame, text=label_text, width=25, anchor="w").pack(
            side=tk.LEFT, padx=2
        )
        ttk.Combobox(
            frame,
            textvariable=var,
            values=actual_options,
            state="readonly",
            width=width,
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        self.widgets[key_path] = var

    # Wypełnia formularz istniejącymi danymi `data_to_load`
    def populate_form(self, data_to_load):
        for key_path, var_widget in self.widgets.items():
            path_parts = key_path.split(".")
            current_val = data_to_load
            found = True
            if "memory" in key_path and key_path.endswith((".value", ".unit")):
                base_mem_key = ".".join(path_parts[:-1])
                mem_full_val = data_to_load
                for part in base_mem_key.split("."):
                    mem_full_val = (
                        mem_full_val.get(part, None) if mem_full_val else None
                    )

                if isinstance(mem_full_val, str) and any(
                    u in mem_full_val for u in OPTIONS_MEMORY_UNITS if u
                ):
                    num_part = "".join(filter(str.isdigit, mem_full_val))
                    unit_part = "".join(filter(str.isalpha, mem_full_val))
                    self.widgets[base_mem_key + ".value"].set(num_part)
                    self.widgets[base_mem_key + ".unit"].set(
                        unit_part if unit_part in OPTIONS_MEMORY_UNITS else "Gi"
                    )
                else:
                    self.widgets[base_mem_key + ".value"].set("")
                    self.widgets[base_mem_key + ".unit"].set("Gi")
                continue

            for part in path_parts:
                current_val = (
                    current_val.get(part, None)
                    if isinstance(current_val, dict)
                    else None
                )
                if current_val is None:
                    found = False
                    break

            if found and current_val is not None:
                if key_path == "spec.unschedulable":
                    var_widget.set(
                        str(current_val).lower()
                        if isinstance(current_val, bool)
                        else ""
                    )
                else:
                    var_widget.set(str(current_val))
            else:
                var_widget.set("")

        # Wypełnianie DynamicListFrames
        for dl_key, dl_instance in self.dynamic_lists.items():
            dl_data = self.get_initial_dynamic_list_data(
                data_to_load, dl_key.split(".")
            )
            if dl_data and isinstance(dl_data, list):
                while len(dl_instance.item_frames) > dl_instance.min_items:
                    dl_instance.remove_item(
                        dl_instance.item_frames[-1], dl_instance.item_widgets_list[-1]
                    )
                if (
                    len(dl_instance.item_frames) == dl_instance.min_items
                    and dl_instance.min_items > 0
                ):
                    is_first_item_empty = True
                    first_item_vars = dl_instance.item_widgets_list[0]
                    for var in first_item_vars.values():
                        if var.get():
                            is_first_item_empty = False
                            break
                    if is_first_item_empty and dl_instance.min_items == 1:
                        dl_instance.remove_item(
                            dl_instance.item_frames[0], dl_instance.item_widgets_list[0]
                        )

                for item_val_dict in dl_data:
                    dl_instance.add_item_gui(item_val_dict)

    # Pobiera wartość z widgetu i zwraca None jeśli wartość jest pusta.
    def _get_widget_value(self, key_path, data_type_hint=None):
        var = self.widgets.get(key_path)
        val_str = str(var.get()).strip() if var else None
        if not val_str:
            return None
        if key_path == "spec.unschedulable":
            return (
                True if val_str == "true" else (False if val_str == "false" else None)
            )
        if data_type_hint == int:
            return int(val_str) if val_str.isdigit() else None
        if data_type_hint == float:
            try:
                return float(val_str)
            except ValueError:
                return None
        return val_str

    # Tworzy słownik OrderedDict dla (allocatable/capacity).
    def _get_resource_dict(self, base_key_prefix):
        res_dict = OrderedDict()
        if cpu := self._get_widget_value(f"{base_key_prefix}.cpu", int):
            res_dict["cpu"] = cpu
        mem_val = self.widgets[f"{base_key_prefix}.memory.value"].get().strip()
        mem_unit = self.widgets[f"{base_key_prefix}.memory.unit"].get().strip()
        if mem_val and mem_unit:
            res_dict["memory"] = f"{mem_val}{mem_unit}"
        if gpu := self._get_widget_value(f"{base_key_prefix}.nvidia.com/gpu", int):
            res_dict["nvidia.com/gpu"] = gpu
        if pods := self._get_widget_value(f"{base_key_prefix}.pods", int):
            res_dict["pods"] = pods
        return res_dict if res_dict else None

    # Zbiera dane z formularza i tworzy słownik OrderedDict reprezentujący Węzeł.
    def save_node(self):
        node_def = OrderedDict()
        # Metadata
        meta = OrderedDict()
        if name := self._get_widget_value("metadata.name"):
            meta["name"] = name
        if labels_data := self.dynamic_lists["metadata.labels"].get_data():
            meta["labels"] = OrderedDict(
                (item["key"], item["value"]) for item in labels_data if item.get("key")
            )
        if meta:
            node_def["metadata"] = meta

        # Spec
        spec = OrderedDict()
        if (unsched_val := self._get_widget_value("spec.unschedulable")) is not None:
            spec["unschedulable"] = unsched_val
        if taints_data := self.dynamic_lists["spec.taints"].get_data():
            spec["taints"] = [OrderedDict(t) for t in taints_data if t.get("key")]
        if spec:
            node_def["spec"] = spec

        # Status
        status = OrderedDict()
        if alloc_res := self._get_resource_dict("status.allocatable"):
            status["allocatable"] = alloc_res
        if self.copy_alloc_to_cap_var.get() and alloc_res:
            status["capacity"] = OrderedDict(alloc_res)
        elif cap_res := self._get_resource_dict("status.capacity"):
            status["capacity"] = cap_res
        if status:
            node_def["status"] = status

        # Dodatkowe właściwości na poziomie głównym
        for key in [
            "calculationSpeed",
            "ctnCreationTime",
            "ctnCreationExtraTime",
            "ctnCreationTimeInterval",
        ]:
            is_float = "Speed" in key or "ExtraTime" in key
            if val := self._get_widget_value(key, float if is_float else int):
                node_def[key] = val

        if self.on_save_callback:
            self.on_save_callback(
                node_def if node_def else None
            )  # Przekaż None jeśli pusty
        self.top.destroy()


class App:
    # Główna klasa aplikacji GUI. Zarządza listą Węzłów i eksportem do YAML.

    def __init__(self, root_tk):
        self.root = root_tk
        self.root.title("Generator Węzłów Kubernetes")
        self.root.geometry("600x450")
        self.defined_nodes_data = []

        list_ctrl_frame = ttk.Frame(root_tk, padding="10")
        list_ctrl_frame.pack(fill=tk.BOTH, expand=True)
        self.nodes_listbox = tk.Listbox(
            list_ctrl_frame, height=15, exportselection=False
        )
        self.nodes_listbox.pack(pady=5, fill=tk.BOTH, expand=True, side=tk.LEFT)
        list_scrollbar = ttk.Scrollbar(
            list_ctrl_frame, orient="vertical", command=self.nodes_listbox.yview
        )
        list_scrollbar.pack(side=tk.LEFT, fill=tk.Y)
        self.nodes_listbox.config(yscrollcommand=list_scrollbar.set)

        btn_frame = ttk.Frame(list_ctrl_frame)
        btn_frame.pack(fill=tk.Y, side=tk.LEFT, padx=10)
        actions = [
            ("Dodaj Węzeł", self.open_new_node_form),
            ("Edytuj", self.edit_selected_node),
            ("Usuń", self.remove_selected_node),
        ]
        for txt, cmd in actions:
            ttk.Button(btn_frame, text=txt, command=cmd).pack(pady=5, fill=tk.X)

        export_frame = ttk.Frame(root_tk, padding="10")
        export_frame.pack(fill=tk.X, side=tk.BOTTOM)
        ttk.Button(
            export_frame, text="Eksportuj YAML", command=self.export_yaml_file
        ).pack(pady=5)

    # Otwiera formularz do tworzenia nowego Węzła.
    def open_new_node_form(self):
        NodeForm(self.root, on_save_callback=self.add_node_to_list)

    # Dodaje zdefiniowanego Węzła do listy w GUI.
    def add_node_to_list(self, node_data_dict):
        if not node_data_dict:
            messagebox.showinfo("Info", "Węzeł pusty, nie dodano.")
            return
        self.defined_nodes_data.append(node_data_dict)
        name = node_data_dict.get("metadata", {}).get(
            "name", f"Węzeł #{len(self.defined_nodes_data)}"
        )
        self.nodes_listbox.insert(tk.END, name)
        self.nodes_listbox.see(tk.END)
        self.nodes_listbox.selection_clear(0, tk.END)
        self.nodes_listbox.selection_set(tk.END)

    # Otwiera formularz do edycji zaznaczonego Węzła.
    def edit_selected_node(self):
        sel_idx = self.nodes_listbox.curselection()
        if not sel_idx:
            messagebox.showinfo("Info", "Zaznacz węzeł do edycji.")
            return
        idx = sel_idx[0]
        node_to_edit = self.defined_nodes_data[idx]

        def cb(updated_data):  # Callback po edycji
            if not updated_data:
                if messagebox.askyesno("Potwierdź", "Węzeł pusty po edycji. Usunąć?"):
                    del self.defined_nodes_data[idx]
                    self.nodes_listbox.delete(idx)
                return
            self.defined_nodes_data[idx] = updated_data
            name = updated_data.get("metadata", {}).get("name", f"Węzeł #{idx+1}")
            self.nodes_listbox.delete(idx)
            self.nodes_listbox.insert(idx, name)
            self.nodes_listbox.selection_set(idx)

        NodeForm(self.root, node_data_to_edit=node_to_edit, on_save_callback=cb)

    # Usuwa zaznaczonego Węzła z listy.
    def remove_selected_node(self):
        sel_idx = self.nodes_listbox.curselection()
        if not sel_idx:
            messagebox.showinfo("Info", "Zaznacz węzeł do usunięcia.")
            return
        idx = sel_idx[0]
        if messagebox.askyesno("Potwierdź", f"Usunąć '{self.nodes_listbox.get(idx)}'?"):
            del self.defined_nodes_data[idx]
            self.nodes_listbox.delete(idx)

    # Eksportuje wszystkie zdefiniowane Węzły do pliku YAML.
    def export_yaml_file(self):
        nodes_to_export = [
            n for n in self.defined_nodes_data if n
        ]  # Filtruj puste węzły
        if not nodes_to_export:
            messagebox.showinfo("Info", "Brak węzłów do eksportu.")
            return

        f_path = filedialog.asksaveasfilename(
            defaultextension=".yaml",
            title="Zapisz YAML Węzłów",
            filetypes=[("YAML", "*.yaml *.yml"), ("All", "*.*")],
        )
        if not f_path:
            return

        yaml_struct = OrderedDict([("cluster", nodes_to_export)])
        try:
            with open(f_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    yaml_struct,
                    f,
                    allow_unicode=True,
                    sort_keys=False,
                    indent=2,
                    Dumper=yaml.Dumper,
                )
            messagebox.showinfo("Sukces", f"YAML Węzłów zapisany w:\n{f_path}")
        except Exception as e:
            messagebox.showerror("Błąd Zapisu", f"Błąd zapisu YAML:\n{e}")


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
