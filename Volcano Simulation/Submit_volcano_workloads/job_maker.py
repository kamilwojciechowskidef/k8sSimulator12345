import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import yaml

from collections import OrderedDict


def represent_ordereddict(dumper, data):
    # Zachowanie kolejności kluczy podczas zapisu do YAML.
    value = []
    for item_key, item_value in data.items():
        node_key = dumper.represent_data(item_key)
        node_value = dumper.represent_data(item_value)
        value.append((node_key, node_value))
    return yaml.nodes.MappingNode("tag:yaml.org,2002:map", value)


yaml.add_representer(OrderedDict, represent_ordereddict)


OPTIONS_API_VERSION = ["", "batch.volcano.sh/v1alpha1"]
OPTIONS_KIND_JOB = ["", "Job"]
OPTIONS_NAMESPACE = ["", "default", "kube-system"]
OPTIONS_SCHEDULER_NAME = ["", "volcano"]
OPTIONS_POLICY_ACTION = ["", "CompleteJob", "RestartTask"]
OPTIONS_POLICY_EVENT = ["", "TaskCompleted", "PodEvicted"]
OPTIONS_IMAGE_PULL_POLICY = ["", "IfNotPresent", "Always", "Never"]
OPTIONS_RESTART_POLICY = ["", "OnFailure", "Always", "Never"]
OPTIONS_CPU_REQUEST_LIMIT = ["", "0.5", "1.0", "2.0", "3.5", "3.6", "4.0"]
OPTIONS_MEMORY_REQUEST_LIMIT = ["", "1000Mi", "800Mi", "6000Mi", "4000Mi", "2Gi", "4Gi"]
OPTIONS_GPU_REQUEST_LIMIT = ["", "1", "2", "0"]


class DynamicListFrame(ttk.Frame):
    def __init__(
        self,
        master,
        item_label_singular,
        field_definitions_func,
        add_button_text=None,
        min_items=0,
    ):
        # Inicjalizuje ramkę, ustawia etykiety, funkcję definicji pól i minimalną liczbę elementów.
        super().__init__(master, padding="5")
        self.item_label_singular = item_label_singular
        self.field_definitions_func = field_definitions_func
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

        # Przycisk do dodawania nowych elementów
        button_text = add_button_text or f"Dodaj {item_label_singular}"
        ttk.Button(self, text=button_text, command=self.add_item_gui).pack(
            pady=5, anchor="w"
        )

    def add_item_gui(self, item_values=None):
        # Dodaje nowy element do listy w GUI, wraz z jego polami.
        item_frame = ttk.LabelFrame(
            self.scrollable_frame,
            text=f"{self.item_label_singular} #{len(self.item_frames) + 1}",
            padding="5",
        )
        item_frame.pack(fill=tk.X, pady=3, padx=3)

        current_item_widgets = (
            OrderedDict()
        )  # Słownik na widgety (StringVar) tego elementu
        field_definitions = (
            self.field_definitions_func()
        )  # Pobiera dynamicznie definicje pól

        # Tworzenie widgetów dla każdego pola zdefiniowanego i ustawienie wartości początkowej widgetu w `field_definitions`
        for (
            key_path,
            label_text,
            widget_type,
            widget_options,
            default_value,
        ) in field_definitions:
            frame = ttk.Frame(item_frame)
            frame.pack(fill=tk.X, pady=1)  # Ramka dla etykiety i widgetu
            ttk.Label(frame, text=label_text, width=20, anchor="w").pack(
                side=tk.LEFT, padx=2
            )

            var = tk.StringVar()
            val_to_set = (
                item_values.get(key_path, default_value)
                if item_values
                else default_value
            )

            widget = None
            actual_options = list(widget_options) if widget_options else []
            if widget_type == "entry":
                widget = ttk.Entry(frame, textvariable=var, width=30)
            elif widget_type == "combobox":
                if "" not in actual_options:
                    actual_options.insert(0, "")
                widget = ttk.Combobox(
                    frame,
                    textvariable=var,
                    values=actual_options,
                    state="readonly",
                    width=28,
                )

            if widget:
                var.set(
                    val_to_set
                    if val_to_set in actual_options or widget_type == "entry"
                    else (actual_options[0] if actual_options else "")
                )
                widget.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
            current_item_widgets[key_path] = var

        # Przycisk do usuwania tego elementu
        ttk.Button(
            item_frame,
            text="Usuń",
            width=6,
            command=lambda f=item_frame, w=current_item_widgets: self.remove_item(f, w),
        ).pack(side=tk.RIGHT, pady=2)

        self.item_frames.append(item_frame)
        self.item_widgets_list.append(current_item_widgets)

    def remove_item(self, frame_to_remove, widgets_to_remove):
        # Usuwa element z listy w GUI.
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

    def _renumber_items(self):
        # Aktualizuje etykiety numeryczne elementów po usunięciu jednego z nich.
        for i, frame in enumerate(self.item_frames):
            frame.config(text=f"{self.item_label_singular} #{i + 1}")

    def get_data(self):
        # Zbiera dane ze wszystkich elementów listy w GUI i zwraca jako listę słowników lub None.
        data_list = []
        for item_widgets_dict in self.item_widgets_list:
            item_data = OrderedDict()
            has_any_value = False
            for key_path, str_var in item_widgets_dict.items():
                value = str_var.get().strip()
                if value:
                    if key_path == "command" and value:
                        commands = [c.strip() for c in value.split(",") if c.strip()]
                        if commands:
                            item_data[key_path] = commands
                            has_any_value = True
                    else:
                        item_data[key_path] = value
                        has_any_value = True
            if has_any_value:
                data_list.append(item_data)
        return data_list if data_list else None


class JobForm:

    # Tworzenie joba

    def __init__(self, master, job_data_to_edit=None, on_save_callback=None):
        # Inicjalizuje okno formularza Joba.
        self.master = master
        self.on_save_callback = on_save_callback  # Funkcja wywoływana po zapisaniu Joba
        self.job_data_to_edit = (
            job_data_to_edit  # Dane istniejącego Joba do edycji (lub None)
        )

        self.top = tk.Toplevel(master)
        self.top.title("Definicja Joba Volcano")
        self.top.geometry("700x750")
        self.widgets = {}
        self.dynamic_lists = {}

        # Tworzenie zakładek
        notebook = ttk.Notebook(self.top)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        tabs = {
            name: ttk.Frame(notebook, padding="5")
            for name in ["Główne", "Specyfikacja Joba", "Zadanie (Task)"]
        }
        for name, tab_frame in tabs.items():
            notebook.add(tab_frame, text=name)

        # --- Wypełnianie Zakładek Polami ---
        self._create_main_tab_fields(tabs["Główne"])
        self._create_spec_tab_fields(tabs["Specyfikacja Joba"])
        self._create_task_tab_fields(tabs["Zadanie (Task)"])

        # Przyciski Zapisz/Anuluj
        button_frame = ttk.Frame(self.top, padding="10")
        button_frame.pack(fill=tk.X, side=tk.BOTTOM)
        ttk.Button(button_frame, text="Zapisz Job", command=self.save_job).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(button_frame, text="Anuluj", command=self.top.destroy).pack(
            side=tk.RIGHT, padx=5
        )

        if self.job_data_to_edit:
            self.populate_form(
                self.job_data_to_edit
            )  # Wypełnia formularz danymi, jeśli edytujemy

    def _create_main_tab_fields(self, parent_tab):
        # Tworzy pola w zakładce "Główne".
        self.add_combobox(
            parent_tab,
            "apiVersion",
            "apiVersion:",
            OPTIONS_API_VERSION,
            "batch.volcano.sh/v1alpha1",
        )
        self.add_combobox(parent_tab, "kind", "Kind:", OPTIONS_KIND_JOB, "Job")
        meta_frame = ttk.LabelFrame(parent_tab, text="Metadata", padding="5")
        meta_frame.pack(fill=tk.X, pady=3)
        self.add_textfield(meta_frame, "metadata.name", "Name:", "gpu-test-N")
        self.add_combobox(
            meta_frame, "metadata.namespace", "Namespace:", OPTIONS_NAMESPACE, "default"
        )
        job_labels_frame = ttk.LabelFrame(meta_frame, text="Labels (Job)", padding="3")
        job_labels_frame.pack(fill=tk.X, pady=2)
        self.add_textfield(
            job_labels_frame, "metadata.labels.sub-time", "sub-time:", "0"
        )

    def _create_spec_tab_fields(self, parent_tab):
        # Tworzy pola w zakładce "Specyfikacja Joba".
        self.add_textfield(parent_tab, "spec.minAvailable", "Min Available:", "1")
        self.add_combobox(
            parent_tab,
            "spec.schedulerName",
            "Scheduler Name:",
            OPTIONS_SCHEDULER_NAME,
            "volcano",
        )
        policies_frame = ttk.LabelFrame(
            parent_tab, text="Polityki Joba (spec.policies)", padding="5"
        )
        policies_frame.pack(fill=tk.BOTH, expand=True, pady=3)
        self.dynamic_lists["spec.policies"] = DynamicListFrame(
            policies_frame,
            "Polityka",
            [
                ("action", "Action:", "combobox", OPTIONS_POLICY_ACTION, "CompleteJob"),
                ("event", "Event:", "combobox", OPTIONS_POLICY_EVENT, "TaskCompleted"),
            ],
            min_items=0,
        )

    def _create_task_tab_fields(self, parent_tab):
        # Tworzy pola dla pojedynczego Taska.
        task_frame = ttk.LabelFrame(parent_tab, text="Definicja Taska", padding="5")
        task_frame.pack(fill=tk.BOTH, expand=True, pady=3)
        self.add_textfield(task_frame, "task.name", "Task Name:", "test-gpu")
        self.add_textfield(task_frame, "task.replicas", "Task Replicas:", "1")

        task_policies_frame = ttk.LabelFrame(
            task_frame, text="Polityki Taska", padding="5"
        )
        task_policies_frame.pack(fill=tk.X, pady=3)
        self.dynamic_lists["task.policies"] = DynamicListFrame(
            task_policies_frame,
            "Polityka Taska",
            [
                ("action", "Action:", "combobox", OPTIONS_POLICY_ACTION, "CompleteJob"),
                ("event", "Event:", "combobox", OPTIONS_POLICY_EVENT, "TaskCompleted"),
            ],
            min_items=0,
        )

        template_frame = ttk.LabelFrame(task_frame, text="Template Poda", padding="5")
        template_frame.pack(fill=tk.BOTH, expand=True, pady=3)
        self._create_template_fields(template_frame)

    def _create_template_fields(self, parent_template_frame):
        # Tworzy pola dla sekcji Template Poda (metadata i spec).
        # Template Metadata (Labels)
        tmpl_meta_frame = ttk.LabelFrame(
            parent_template_frame, text="Template Metadata", padding="3"
        )
        tmpl_meta_frame.pack(fill=tk.X, pady=2)
        labels_data = [
            ("app", "linc-workload"),
            ("job", "gpu-test-N"),
            ("jobTaskNumber", "1"),
            ("restartTime", "300"),
            ("restartLimit", "0"),
            ("terminationTime", "350"),
            ("terminationLimit", "0"),
        ]
        for key, val in labels_data:
            self.add_textfield(
                tmpl_meta_frame, f"template.metadata.labels.{key}", f"label: {key}", val
            )

        # Template Spec (RestartPolicy, Kontener)
        tmpl_spec_frame = ttk.LabelFrame(
            parent_template_frame, text="Template Spec", padding="3"
        )
        tmpl_spec_frame.pack(fill=tk.BOTH, expand=True, pady=2)
        self.add_combobox(
            tmpl_spec_frame,
            "template.spec.restartPolicy",
            "Restart Policy:",
            OPTIONS_RESTART_POLICY,
            "OnFailure",
        )
        self._create_container_fields(tmpl_spec_frame)

    def _create_container_fields(self, parent_tmpl_spec_frame):
        # Tworzy pola dla pojedynczego Kontenera.
        cont_frame = ttk.LabelFrame(
            parent_tmpl_spec_frame, text="Kontener", padding="5"
        )
        cont_frame.pack(fill=tk.BOTH, expand=True, pady=3)
        self.add_textfield(cont_frame, "container.name", "Container Name:", "task")
        self.add_textfield(
            cont_frame,
            "container.image",
            "Image:",
            "10.1.114.138:5000/pytorchjob-cifar10:v1.0",
        )
        self.add_combobox(
            cont_frame,
            "container.imagePullPolicy",
            "Image Pull Policy:",
            OPTIONS_IMAGE_PULL_POLICY,
            "IfNotPresent",
        )
        self.add_textfield(
            cont_frame,
            "container.command",
            "Command (przecinki):",
            "python3,gpu-test3.py,--epochs=7",
        )

        res_frame = ttk.LabelFrame(cont_frame, text="Zasoby (Resources)", padding="3")
        res_frame.pack(fill=tk.X, pady=2)
        for res_type, defaults in [
            ("limits", {"cpu": "1.0", "mem": "1000Mi", "gpu": "1"}),
            ("requests", {"cpu": "0.5", "mem": "800Mi", "gpu": "1"}),
        ]:
            sub_frame = ttk.LabelFrame(
                res_frame, text=res_type.capitalize(), padding="3"
            )
            sub_frame.pack(fill=tk.X, side=tk.LEFT, expand=True, padx=2)
            self.add_combobox(
                sub_frame,
                f"container.resources.{res_type}.cpu",
                "CPU:",
                OPTIONS_CPU_REQUEST_LIMIT,
                defaults["cpu"],
            )
            self.add_combobox(
                sub_frame,
                f"container.resources.{res_type}.memory",
                "Memory:",
                OPTIONS_MEMORY_REQUEST_LIMIT,
                defaults["mem"],
            )
            self.add_combobox(
                sub_frame,
                f"container.resources.{res_type}.nvidia.com/gpu",
                "nvidia.com/gpu:",
                OPTIONS_GPU_REQUEST_LIMIT,
                defaults["gpu"],
            )

    # --- Metody pomocnicze do tworzenia widgetów ---
    def _add_widget_common(
        self, parent, key_path, label_text, var, widget_creator_func
    ):
        # Wspólna logika dodawania etykiety i widgetu.
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=1)
        ttk.Label(frame, text=label_text, width=20, anchor="w").pack(
            side=tk.LEFT, padx=2
        )
        widget = widget_creator_func(frame, var)
        widget.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        self.widgets[key_path] = var

    def add_textfield(self, parent, key_path, label_text, default="", width=15):
        # Dodaje pole tekstowe (Entry).
        var = tk.StringVar(value=str(default))
        self._add_widget_common(
            parent,
            key_path,
            label_text,
            var,
            lambda f, v: ttk.Entry(f, textvariable=v, width=width),
        )

    def add_combobox(self, parent, key_path, label_text, options, default="", width=15):
        # Dodaje pole wyboru (Combobox).
        var = tk.StringVar()
        actual_options = list(
            options
        )  # Opcje powinny już zawierać "" dla opcjonalności
        var.set(
            default
            if default in actual_options
            else (actual_options[0] if actual_options else "")
        )
        self._add_widget_common(
            parent,
            key_path,
            label_text,
            var,
            lambda f, v: ttk.Combobox(
                f, textvariable=v, values=actual_options, state="readonly", width=width
            ),
        )

    def _get_widget_value(self, key_path):
        # Pobiera wartość z widgetu i zwraca None jeśli puste.
        var = self.widgets.get(key_path)
        val_str = str(var.get()).strip() if var else None
        return val_str if val_str else None

    def populate_form(self, data):
        # Wypełnia formularz danymi z `data` (słownik).
        # Iteruje po self.widgets i ustawia wartości.
        for key_path, var in self.widgets.items():
            current_data_level = data
            found = True
            try:
                for part in key_path.split("."):
                    if isinstance(current_data_level, list) and part.isdigit():
                        current_data_level = (
                            current_data_level[int(part)]
                            if int(part) < len(current_data_level)
                            else None
                        )
                    elif isinstance(current_data_level, dict):
                        current_data_level = current_data_level.get(part)
                    else:
                        current_data_level = None
                    if current_data_level is None:
                        found = False
                        break

                if found and current_data_level is not None:
                    if key_path == "container.command" and isinstance(
                        current_data_level, list
                    ):
                        var.set(",".join(current_data_level))
                    else:
                        var.set(str(current_data_level))
                else:
                    var.set("")
            except (TypeError, AttributeError, IndexError):
                var.set("")  # Błąd podczas dostępu, ustaw na puste

        # Wypełnianie DynamicListFrames
        for dl_key, dl_instance in self.dynamic_lists.items():
            path_parts = dl_key.split(".")
            current_data_level = data
            dl_data = None
            try:
                for part in path_parts:
                    current_data_level = current_data_level.get(part)
                dl_data = current_data_level
            except (TypeError, AttributeError):
                dl_data = None

            if dl_data and isinstance(dl_data, list):
                while len(dl_instance.item_frames) > 0:
                    if (
                        len(dl_instance.item_frames) > dl_instance.min_items
                        or not dl_instance.get_data()
                    ):  # Jeśli są dane lub więcej niż min
                        dl_instance.remove_item(
                            dl_instance.item_frames[-1],
                            dl_instance.item_widgets_list[-1],
                        )
                    else:
                        break
                for item_val_dict in dl_data:
                    dl_instance.add_item_gui(item_val_dict)

    def save_job(self):
        # Zbiera dane z formularza i tworzy słownik OrderedDict reprezentujący Joba.
        job_def = OrderedDict()

        # Pomocnicza funkcja do ustawiania i konwertowania wartości w zagnieżdżonym OrderedDict
        def set_nested(data_dict, path_str, value):
            keys = path_str.split(".")
            current_level = data_dict
            for i, key in enumerate(keys[:-1]):
                if key == "tasks" and not isinstance(current_level.get(key), list):
                    current_level[key] = []
                if key == "containers" and not isinstance(current_level.get(key), list):
                    current_level[key] = []
                if (
                    isinstance(current_level, list)
                    and isinstance(key, str)
                    and key.isdigit()
                ):
                    idx = int(key)
                    while len(current_level) <= idx:
                        current_level.append(OrderedDict())
                    current_level = current_level[idx]
                else:
                    current_level = current_level.setdefault(key, OrderedDict())

            final_key = keys[-1]
            if isinstance(current_level, list) and final_key.isdigit():
                idx = int(final_key)
                while len(current_level) <= idx:
                    current_level.append(None)
                current_level[idx] = value
            elif value is not None:
                if (
                    final_key in ["minAvailable", "replicas", "nvidia.com/gpu"]
                    and isinstance(value, str)
                    and value.isdigit()
                ):
                    current_level[final_key] = int(value)
                elif final_key == "command" and isinstance(value, str):
                    current_level[final_key] = [
                        c.strip() for c in value.split(",") if c.strip()
                    ]
                else:
                    current_level[final_key] = value

        # Zbieranie wartości z głównych widgetów
        for key_path in self.widgets.keys():
            val = self._get_widget_value(key_path)
            if val is not None:
                set_nested(job_def, key_path, val)

        # Zbieranie wartości z DynamicListFrames
        for dl_key, dl_instance in self.dynamic_lists.items():
            dl_data = dl_instance.get_data()
            if dl_data:
                set_nested(job_def, dl_key, dl_data)

        # Składanie struktury Joba

        final_job_def = OrderedDict()
        if "apiVersion" in job_def:
            final_job_def["apiVersion"] = job_def["apiVersion"]
        if "kind" in job_def:
            final_job_def["kind"] = job_def["kind"]

        # Metadata
        if "metadata" in job_def:
            meta_src = job_def["metadata"]
            meta_dest = OrderedDict()
            if "name" in meta_src:
                meta_dest["name"] = meta_src["name"]
            if "namespace" in meta_src:
                meta_dest["namespace"] = meta_src["namespace"]
            if "labels" in meta_src and meta_src["labels"].get("sub-time"):
                meta_dest["labels"] = OrderedDict(
                    [("sub-time", meta_src["labels"]["sub-time"])]
                )
            if meta_dest:
                final_job_def["metadata"] = meta_dest

        # Spec
        if "spec" in job_def:
            spec_src = job_def["spec"]
            spec_dest = OrderedDict()
            if "minAvailable" in spec_src:
                spec_dest["minAvailable"] = int(spec_src["minAvailable"])
            if "schedulerName" in spec_src:
                spec_dest["schedulerName"] = spec_src["schedulerName"]
            if "policies" in spec_src:
                spec_dest["policies"] = spec_src["policies"]  # Z DynamicList

            # Task
            if "task" in job_def:
                task_src = job_def["task"]
                task_dest = OrderedDict()
                if "name" in task_src:
                    task_dest["name"] = task_src["name"]
                if "replicas" in task_src:
                    task_dest["replicas"] = int(task_src["replicas"])
                if "policies" in task_src:
                    task_dest["policies"] = task_src[
                        "policies"
                    ]  # Z DynamicList dla taska

                # Template
                if "template" in job_def:
                    template_src = job_def["template"]
                    template_dest = OrderedDict()
                    # Template Metadata
                    if (
                        "metadata" in template_src
                        and "labels" in template_src["metadata"]
                    ):
                        template_meta_dest = OrderedDict()
                        labels_src = template_src["metadata"]["labels"]
                        labels_dest = OrderedDict()
                        for lbl_key in [
                            "app",
                            "job",
                            "jobTaskNumber",
                            "restartTime",
                            "restartLimit",
                            "terminationTime",
                            "terminationLimit",
                        ]:
                            if lbl_key in labels_src:
                                labels_dest[lbl_key] = labels_src[lbl_key]
                        if labels_dest:
                            template_meta_dest["labels"] = labels_dest
                        if template_meta_dest:
                            template_dest["metadata"] = template_meta_dest

                    # Template Spec
                    if "spec" in template_src:
                        tmpl_spec_src = template_src["spec"]
                        tmpl_spec_dest = OrderedDict()
                        # Kontener
                        if "container" in job_def:
                            cont_src = job_def["container"]
                            cont_dest = OrderedDict()
                            if "name" in cont_src:
                                cont_dest["name"] = cont_src["name"]
                            if "image" in cont_src:
                                cont_dest["image"] = cont_src["image"]
                            if "imagePullPolicy" in cont_src:
                                cont_dest["imagePullPolicy"] = cont_src[
                                    "imagePullPolicy"
                                ]
                            if "command" in cont_src:
                                cont_dest["command"] = cont_src[
                                    "command"
                                ]  # Już jest listą

                            # Resources
                            if "resources" in cont_src:
                                res_src = cont_src["resources"]
                                res_dest = OrderedDict()
                                if "limits" in res_src:
                                    limits_src = res_src["limits"]
                                    limits_dest = OrderedDict()
                                    if "cpu" in limits_src:
                                        limits_dest["cpu"] = limits_src["cpu"]
                                    if "memory" in limits_src:
                                        limits_dest["memory"] = limits_src["memory"]
                                    if "nvidia.com/gpu" in limits_src:
                                        limits_dest["nvidia.com/gpu"] = int(
                                            limits_src["nvidia.com/gpu"]
                                        )
                                    if limits_dest:
                                        res_dest["limits"] = limits_dest
                                if "requests" in res_src:
                                    req_src = res_src["requests"]
                                    req_dest = OrderedDict()
                                    if "cpu" in req_src:
                                        req_dest["cpu"] = req_src["cpu"]
                                    if "memory" in req_src:
                                        req_dest["memory"] = req_src["memory"]
                                    if "nvidia.com/gpu" in req_src:
                                        req_dest["nvidia.com/gpu"] = int(
                                            req_src["nvidia.com/gpu"]
                                        )
                                    if req_dest:
                                        res_dest["requests"] = req_dest
                                if res_dest:
                                    cont_dest["resources"] = res_dest
                            if cont_dest:
                                tmpl_spec_dest["containers"] = [cont_dest]

                        if "restartPolicy" in tmpl_spec_src:
                            tmpl_spec_dest["restartPolicy"] = tmpl_spec_src[
                                "restartPolicy"
                            ]
                        if tmpl_spec_dest:
                            template_dest["spec"] = tmpl_spec_dest
                    if template_dest:
                        task_dest["template"] = template_dest
                if task_dest:
                    spec_dest["tasks"] = [task_dest]
            if spec_dest:
                final_job_def["spec"] = spec_dest

        if self.on_save_callback:
            self.on_save_callback(final_job_def if final_job_def else None)
        self.top.destroy()


class App:

    # Główna klasa aplikacji GUI. Zarządza listą Jobów i eksportem do YAML.

    def __init__(self, root_tk):
        # Inicjalizuje główne okno aplikacji.
        self.root = root_tk
        self.root.title("Generator Jobów Volcano")
        self.root.geometry("500x400")
        self.defined_jobs_data = []

        # Ramki Jobów i przycisków sterujących
        list_control_frame = ttk.Frame(root_tk, padding="10")
        list_control_frame.pack(fill=tk.BOTH, expand=True)
        self.jobs_listbox = tk.Listbox(
            list_control_frame, height=15, exportselection=False
        )
        self.jobs_listbox.pack(pady=5, fill=tk.BOTH, expand=True, side=tk.LEFT)
        list_scrollbar = ttk.Scrollbar(
            list_control_frame, orient="vertical", command=self.jobs_listbox.yview
        )
        list_scrollbar.pack(side=tk.LEFT, fill=tk.Y)
        self.jobs_listbox.config(yscrollcommand=list_scrollbar.set)
        list_button_frame = ttk.Frame(list_control_frame)
        list_button_frame.pack(fill=tk.Y, side=tk.LEFT, padx=10)
        button_actions = [
            ("Dodaj Job", self.open_new_job_form),
            ("Edytuj Zaznaczony", self.edit_selected_job),
            ("Usuń Zaznaczony", self.remove_selected_job),
        ]
        for text, cmd in button_actions:
            ttk.Button(list_button_frame, text=text, command=cmd).pack(
                pady=5, fill=tk.X
            )
        export_frame = ttk.Frame(root_tk, padding="10")
        export_frame.pack(fill=tk.X, side=tk.BOTTOM)
        ttk.Button(
            export_frame, text="Eksportuj YAML Jobów", command=self.export_yaml_file
        ).pack(pady=5)

    # Otwiera formularz do tworzenia nowego Węzła.
    def open_new_job_form(self):
        JobForm(self.root, on_save_callback=self.add_job_to_list)

    def add_job_to_list(self, job_data_dict):
        # Dodaje zdefiniowanego Joba do listy w GUI i do wewnętrznej listy danych.
        if not job_data_dict:  # Jeśli Job jest pusty (np. użytkownik nic nie wybrał)
            messagebox.showinfo(
                "Informacja",
                "Nie zdefiniowano żadnych wartości dla Joba. Job nie został dodany.",
            )
            return
        self.defined_jobs_data.append(job_data_dict)
        job_name = job_data_dict.get("metadata", {}).get(
            "name", f"Job #{len(self.defined_jobs_data)}"
        )
        self.jobs_listbox.insert(tk.END, job_name)  # Dodaje nazwę Joba do Listboxa
        self.jobs_listbox.see(tk.END)
        self.jobs_listbox.selection_clear(0, tk.END)
        self.jobs_listbox.selection_set(tk.END)

    def edit_selected_job(self):
        # Otwiera formularz do edycji zaznaczonego Joba.
        selected_indices = self.jobs_listbox.curselection()
        if not selected_indices:
            messagebox.showinfo("Informacja", "Najpierw zaznacz Joba do edycji.")
            return

        selected_index = selected_indices[0]
        job_to_edit = self.defined_jobs_data[selected_index]

        # Callback wywoływany po zapisaniu zmian w edytowanym Jobie
        def update_callback(updated_job_data):
            if not updated_job_data:
                if messagebox.askyesno(
                    "Potwierdzenie", "Job stał się pusty. Usunąć z listy?"
                ):
                    del self.defined_jobs_data[selected_index]
                    self.jobs_listbox.delete(selected_index)
                return
            # Aktualizuje dane Joba i jego nazwę w Listboxie
            self.defined_jobs_data[selected_index] = updated_job_data
            job_name = updated_job_data.get("metadata", {}).get(
                "name", f"Job #{selected_index+1}"
            )
            self.jobs_listbox.delete(selected_index)
            self.jobs_listbox.insert(selected_index, job_name)
            self.jobs_listbox.selection_set(selected_index)

        JobForm(
            self.root, job_data_to_edit=job_to_edit, on_save_callback=update_callback
        )

    def remove_selected_job(self):
        # Usuwa zaznaczonego Joba z listy.
        selected_indices = self.jobs_listbox.curselection()
        if not selected_indices:
            messagebox.showinfo("Informacja", "Najpierw zaznacz Joba do usunięcia.")
            return
        selected_index = selected_indices[0]
        if messagebox.askyesno(
            "Potwierdzenie", f"Usunąć Joba '{self.jobs_listbox.get(selected_index)}'?"
        ):
            del self.defined_jobs_data[selected_index]
            self.jobs_listbox.delete(selected_index)

    def export_yaml_file(self):
        # Eksportuje wszystkie zdefiniowane Joby do pliku YAML.
        if not self.defined_jobs_data:
            messagebox.showinfo("Informacja", "Brak Jobów do eksportu.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".yaml",
            filetypes=[("YAML files", "*.yaml *.yml"), ("All files", "*.*")],
            title="Zapisz plik YAML Jobów jako...",
        )
        if not file_path:
            return

        jobs_to_export = [job for job in self.defined_jobs_data if job]
        if not jobs_to_export:
            messagebox.showinfo(
                "Informacja", "Wszystkie Joby są puste. Nic do eksportu."
            )
            return

        # Tworzy główną strukturę YAML i zapisuje do pliku
        final_yaml_structure = OrderedDict([("jobs", jobs_to_export)])
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    final_yaml_structure,
                    f,
                    allow_unicode=True,
                    sort_keys=False,
                    indent=2,
                    Dumper=yaml.Dumper,
                )
            messagebox.showinfo("Sukces", f"Plik YAML Jobów zapisany w:\n{file_path}")
        except Exception as e:
            messagebox.showerror(
                "Błąd Zapisu", f"Błąd podczas zapisywania YAML Jobów:\n{e}"
            )


if __name__ == "__main__":
    main_root = tk.Tk()
    app_instance = App(main_root)
    main_root.mainloop()
