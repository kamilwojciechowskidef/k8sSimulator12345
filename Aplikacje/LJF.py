import yaml
from collections import OrderedDict
import heapq
from datetime import datetime, timedelta
from prettytable import PrettyTable
import os  # Potrzebne do sprawdzania istnienia plików


# === Konfiguracja YAML ===
# Funkcja pomocnicza dla PyYAML, aby zachować kolejność kluczy w OrderedDict.
def represent_ordereddict(dumper, data):
    value = []
    for item_key, item_value in data.items():
        node_key = dumper.represent_data(item_key)
        node_value = dumper.represent_data(item_value)
        value.append((node_key, node_value))
    return yaml.nodes.MappingNode("tag:yaml.org,2002:map", value)


yaml.add_representer(OrderedDict, represent_ordereddict)


# === Funkcje pomocnicze ===
# Wczytuje dane z pliku YAML.
def load_yaml_file(file_path):
    if not os.path.exists(file_path):
        print(f"BŁĄD: Plik {file_path} nie istnieje.")
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"BŁĄD: Nie można wczytać pliku YAML {file_path}: {e}")
        return None


# Formatuje czas jako string (np. 0001-01-01 00:04:30) na podstawie offsetu w sekundach.
def format_time(seconds_offset):
    base_time = datetime(1, 1, 1, 0, 0, 0)
    return (base_time + timedelta(seconds=seconds_offset)).strftime("%Y-%m-%d %H:%M:%S")


# Parsuje wartość zasobu (np. "1000Mi", "1.0", "800m") do ujednoliconej formy.
def parse_resource_value(value_str):
    if not value_str:
        return 0
    value_str = str(value_str)
    num_part_str = "".join(filter(lambda c: c.isdigit() or c == ".", value_str))
    unit_part_str = "".join(filter(str.isalpha, value_str)).upper()
    if not num_part_str:
        return 0
    num_val = float(num_part_str)
    if not unit_part_str:
        return num_val
    if unit_part_str == "M":
        return num_val / 1000.0
    if unit_part_str == "MI":
        return int(num_val)
    if unit_part_str == "GI":
        return int(num_val * 1024)
    if unit_part_str == "KI":
        return int(num_val / 1024)
    return num_val


# === Estymacja czasu i zasobów ===
# Estymuje czas przetwarzania dla pojedynczego poda. DOSTOSUJ TĘ FUNKCJĘ!
def estimate_pod_processing_time(pod_resources_requests, job_def=None, task_def=None):
    # Przykładowa implementacja - musisz ją dostosować, aby uzyskać czasy z przykładu.
    # Może zależeć od komendy, etykiet joba/taska itp.
    # Poniżej bardzo prosta estymacja, która nie da wyników z przykładu.
    # W przykładzie masz czasy typu 270s, 343s. Skąd one pochodzą?
    # Jeśli `command` zawiera `--epochs=X`, można to wykorzystać:
    epochs = 7  # Domyślnie
    if task_def:
        container_def = (
            task_def.get("template", {}).get("spec", {}).get("containers", [{}])[0]
        )
        command = container_def.get("command", [])
        for item in command:
            if isinstance(item, str) and "--epochs=" in item:
                try:
                    epochs = int(item.split("=")[-1])
                except ValueError:
                    pass

    # Bardzo prosta formuła, wymaga kalibracji
    base_time_per_epoch = 30  # sekund
    time = (
        epochs * base_time_per_epoch
        + pod_resources_requests.get("cpu", 0) * 10
        + pod_resources_requests.get("gpu", 0) * 20
    )
    return max(time, 30)  # Minimalny czas


# Pobiera definicje zasobów (requests i limits) dla kontenera (poda).
def get_pod_resources(container_def):
    res = {"requests": {}, "limits": {}}
    raw_resources = container_def.get("resources", {})
    for res_type in ["requests", "limits"]:
        for res_name_yaml, res_name_internal in [
            ("cpu", "cpu"),
            ("memory", "memory_mb"),
            ("nvidia.com/gpu", "gpu"),
        ]:
            val_str = raw_resources.get(res_type, {}).get(res_name_yaml)
            if val_str:
                parsed_val = parse_resource_value(val_str)
                if res_name_internal == "gpu":
                    parsed_val = int(parsed_val)
                res[res_type][res_name_internal] = parsed_val
    return res


# === Symulator Węzła ===
# Reprezentuje węzeł i śledzi jego zasoby oraz czas zwolnienia.
class NodeSimulator:
    def __init__(self, name, capacity_cpu, capacity_gpu, capacity_memory_mb):
        self.name = name
        self.capacity_cpu = float(capacity_cpu)
        self.capacity_gpu = int(capacity_gpu)
        self.capacity_memory_mb = int(capacity_memory_mb)
        self.available_cpu = float(capacity_cpu)
        self.available_gpu = int(capacity_gpu)
        self.available_memory_mb = int(capacity_memory_mb)
        self.free_at_time = 0.0
        self.running_pods_finish_times = (
            []
        )  # (finish_time, pod_id, pod_resources_requests)

    # Tworzy NodeSimulator z definicji węzła Kubernetes.
    @classmethod
    def from_node_definition(cls, node_def):
        meta = node_def.get("metadata", {})
        name = meta.get("name", "unknown")
        alloc = node_def.get("status", {}).get("allocatable", {})
        cpu = parse_resource_value(alloc.get("cpu", "0"))
        gpu = int(parse_resource_value(alloc.get("nvidia.com/gpu", "0")))
        mem_mb = parse_resource_value(alloc.get("memory", "0Mi"))
        return cls(name, cpu, gpu, mem_mb)

    # Sprawdza, czy węzeł ma *aktualnie* wystarczająco zasobów dla poda.
    def can_run_pod(self, pod_res_req, current_time):
        self.release_finished_pods_resources(current_time)
        return (
            self.available_cpu >= pod_res_req.get("cpu", 0)
            and self.available_gpu >= pod_res_req.get("gpu", 0)
            and self.available_memory_mb >= pod_res_req.get("memory_mb", 0)
        )

    # Przydziela poda do węzła.
    def assign_pod(self, pod_id, pod_processing_time, pod_res_req, start_time):
        if not self.can_run_pod(pod_res_req, start_time):
            return float("inf")
        self.available_cpu -= pod_res_req.get("cpu", 0)
        self.available_gpu -= pod_res_req.get("gpu", 0)
        self.available_memory_mb -= pod_res_req.get("memory_mb", 0)
        finish_time = start_time + pod_processing_time
        heapq.heappush(
            self.running_pods_finish_times, (finish_time, pod_id, pod_res_req)
        )
        self.free_at_time = max(self.free_at_time, finish_time)
        return finish_time

    # Zwalnia zasoby podów, które zakończyły się do `current_time`.
    def release_finished_pods_resources(self, current_time):
        while (
            self.running_pods_finish_times
            and self.running_pods_finish_times[0][0] <= current_time
        ):
            _ft, _pid, res = heapq.heappop(self.running_pods_finish_times)
            self.available_cpu += res.get("cpu", 0)
            self.available_gpu += res.get("gpu", 0)
            self.available_memory_mb += res.get("memory_mb", 0)

    # Zwraca czas, kiedy węzeł najwcześniej zwolni jakiekolwiek zasoby.
    def get_earliest_next_free_time(self):
        return (
            self.running_pods_finish_times[0][0]
            if self.running_pods_finish_times
            else 0.0
        )

    # Porównywanie węzłów dla heapq.
    def __lt__(self, other):
        my_free_time = self.get_earliest_next_free_time()
        other_free_time = other.get_earliest_next_free_time()
        if my_free_time == other_free_time:
            return self.available_cpu > other.available_cpu
        return my_free_time < other_free_time


# === Implementacja Heurystyki LJF/LPT na poziomie Podów ===
# Szereguje Pody z Jobów na Węzłach używając LJF (dla Jobów) i LPT (dla Podów).
def schedule_ljf_lpt_pods(jobs_definitions, node_simulators_list):
    if not jobs_definitions or not node_simulators_list:
        return 0, {}, {}
    all_pods_to_schedule = []
    job_total_estimated_size = {}
    pod_global_id_counter = 0

    for job_idx, job_def in enumerate(jobs_definitions):
        job_name = job_def.get("metadata", {}).get("name", f"job-{job_idx}")
        job_submit_time = float(
            job_def.get("metadata", {}).get("labels", {}).get("sub-time", "0")
        )
        job_total_estimated_size[job_name] = 0
        if "spec" not in job_def or "tasks" not in job_def["spec"]:
            continue
        for task_idx, task_def in enumerate(job_def["spec"]["tasks"]):
            replicas = task_def.get("replicas", 1)
            container_def = (
                task_def.get("template", {}).get("spec", {}).get("containers", [{}])[0]
            )
            if not container_def:
                continue
            pod_resources = get_pod_resources(container_def)
            # Przekazanie job_def i task_def do estymacji czasu
            pod_processing_time = estimate_pod_processing_time(
                pod_resources["requests"], job_def, task_def
            )
            job_total_estimated_size[job_name] += pod_processing_time * replicas
            for r in range(replicas):
                pod_global_id_counter += 1
                all_pods_to_schedule.append(
                    {
                        "id": pod_global_id_counter,
                        "pod_name": f"{job_def.get('metadata',{}).get('namespace','default')}-{job_name}-{task_def.get('name','task')}-{r}",
                        "job_name": job_name,
                        "job_submit_time": job_submit_time,
                        "task_name": task_def.get("name", f"task-{task_idx}"),
                        "replica_num": r,
                        "processing_time": pod_processing_time,
                        "resources_requests": pod_resources["requests"],
                        "resources_limits": pod_resources["limits"],
                        "original_job_def": job_def,
                    }
                )

    sorted_job_names_ljf = sorted(
        job_total_estimated_size.keys(), key=lambda jn: -job_total_estimated_size[jn]
    )
    final_pod_processing_list = []
    for job_name_ljf in sorted_job_names_ljf:
        final_pod_processing_list.extend(
            sorted(
                [p for p in all_pods_to_schedule if p["job_name"] == job_name_ljf],
                key=lambda p: p["id"],
            )
        )

    pod_schedule_details = []
    makespan = 0.0
    active_nodes_heap = [node for node in node_simulators_list if node.capacity_cpu > 0]
    heapq.heapify(active_nodes_heap)
    current_simulation_time = 0.0
    pending_pods = list(final_pod_processing_list)
    scheduled_pod_count = 0

    while scheduled_pod_count < len(final_pod_processing_list):
        if not active_nodes_heap:
            print("BŁĄD KRYTYCZNY: Brak aktywnych węzłów.")
            break

        ready_to_schedule_pods = sorted(
            [
                p
                for p in pending_pods
                if p["job_submit_time"] <= current_simulation_time
            ],
            key=lambda p: -p["processing_time"],  # LPT dla podów
        )

        assigned_in_this_step = False
        if ready_to_schedule_pods:
            for pod_info in ready_to_schedule_pods:
                if pod_info not in pending_pods:
                    continue
                temp_rejected_nodes = []
                node_assigned_to_pod = None  # Zmienna do śledzenia, czy pod został przypisany w tej iteracji pętli węzłów

                while active_nodes_heap:
                    node = heapq.heappop(active_nodes_heap)
                    potential_start_time_on_node = max(
                        node.get_earliest_next_free_time(),
                        current_simulation_time,
                        pod_info["job_submit_time"],
                    )
                    node.release_finished_pods_resources(potential_start_time_on_node)

                    if node.can_run_pod(
                        pod_info["resources_requests"], potential_start_time_on_node
                    ):
                        actual_start_time = potential_start_time_on_node
                        pod_create_time = pod_info["job_submit_time"]  # Uproszczenie
                        pod_wait_create = max(
                            0, pod_create_time - pod_info["job_submit_time"]
                        )  # Powinno być 0 w tym modelu
                        pod_wait_run = max(0, actual_start_time - pod_create_time)
                        finish_time = node.assign_pod(
                            pod_info["id"],
                            pod_info["processing_time"],
                            pod_info["resources_requests"],
                            actual_start_time,
                        )

                        pod_schedule_details.append(
                            {
                                "Pod_name": pod_info["pod_name"],
                                "Job_name": pod_info["job_name"],
                                "Job_submit": format_time(pod_info["job_submit_time"]),
                                "Pod_create": format_time(pod_create_time),
                                "Pod_start": format_time(actual_start_time),
                                "Pod_end": format_time(finish_time),
                                "Pod_wait_create": pod_wait_create,
                                "Pod_wait_run": pod_wait_run,
                                "Pod_wait_total": pod_wait_create + pod_wait_run,
                                "Pod_running_time": pod_info["processing_time"],
                                "Pod_total_time": (
                                    pod_wait_create
                                    + pod_wait_run
                                    + pod_info["processing_time"]
                                ),
                                "Running_node": node.name,
                                "Requests_cpu": pod_info["resources_requests"].get(
                                    "cpu", 0
                                ),
                                "Limits_cpu": pod_info["resources_limits"].get(
                                    "cpu", 0
                                ),
                                "Requests_memory_mb": pod_info[
                                    "resources_requests"
                                ].get(
                                    "memory_mb", 0
                                ),  # Zmienione na _mb
                                "Limits_memory_mb": pod_info["resources_limits"].get(
                                    "memory_mb", 0
                                ),
                                "Requests_gpu": pod_info["resources_requests"].get(
                                    "gpu", 0
                                ),
                                "Limits_gpu": pod_info["resources_limits"].get(
                                    "gpu", 0
                                ),
                            }
                        )
                        makespan = max(makespan, finish_time)
                        heapq.heappush(active_nodes_heap, node)
                        pending_pods.remove(pod_info)
                        scheduled_pod_count += 1
                        assigned_in_this_step = True
                        node_assigned_to_pod = node  # Oznacz, że pod został przypisany
                        break
                    else:
                        temp_rejected_nodes.append(node)

                for rejected_node in temp_rejected_nodes:
                    heapq.heappush(active_nodes_heap, rejected_node)
                if node_assigned_to_pod:
                    continue  # Jeśli pod został przypisany, kontynuuj pętlę podów (LPT)
                # Jeśli pod nie został przypisany (brak zasobów na żadnym węźle w tej chwili),
                # zostanie rozważony w następnym kroku czasowym.

        if (
            not assigned_in_this_step and pending_pods
        ):  # Jeśli nic nie przypisano, a są oczekujące pody
            next_event_time = float("inf")
            # Czas zgłoszenia następnego nieprzetworzonego poda
            min_next_submit_time = min(
                (
                    p["job_submit_time"]
                    for p in pending_pods
                    if p["job_submit_time"] > current_simulation_time
                ),
                default=float("inf"),
            )
            next_event_time = min(next_event_time, min_next_submit_time)
            # Czas zwolnienia najwcześniejszego węzła
            if active_nodes_heap:
                earliest_node_free_time = min(
                    (n.get_earliest_next_free_time() for n in active_nodes_heap),
                    default=float("inf"),
                )
                next_event_time = min(next_event_time, earliest_node_free_time)

            if next_event_time == float("inf"):
                print("BŁĄD: Nie można ustalić następnego czasu zdarzenia.")
                break
            current_simulation_time = max(
                next_event_time, current_simulation_time + 0.01
            )  # Upewnij się, że czas idzie do przodu
        elif not pending_pods:  # Wszystkie pody uszeregowane
            break

    job_completion_times = {}
    for pd in pod_schedule_details:
        job_name = pd["Job_name"]
        pod_end_s = (
            datetime.strptime(pd["Pod_end"], "%Y-%m-%d %H:%M:%S") - datetime(1, 1, 1)
        ).total_seconds()
        job_completion_times[job_name] = max(
            job_completion_times.get(job_name, 0.0), pod_end_s
        )
    return makespan, pod_schedule_details, job_completion_times


# === Główna funkcja ===
# Główna funkcja uruchamiająca symulację.
def main(node_file_url, workload_file_url, algorithm_name="LJF_LPT_Pods_SLA_MRP_Style"):
    print(f"In scheduling algorithm: {algorithm_name}， simulation test：")

    nodes_data = load_yaml_file(node_file_url)
    jobs_data = load_yaml_file(workload_file_url)
    if not nodes_data or not jobs_data:
        return

    node_sims = [
        NodeSimulator.from_node_definition(nd)
        for nd in nodes_data.get("cluster", [])
        if not nd.get("spec", {}).get("unschedulable", False)
    ]
    if not node_sims:
        print("BŁĄD: Nie znaleziono planowalnych węzłów.")
        return

    makespan, pod_details, job_summary = schedule_ljf_lpt_pods(
        jobs_data.get("jobs", []), node_sims
    )

    # Wyświetlanie wyników
    table = PrettyTable()
    table.field_names = [
        "Pod_name",
        "Job_name",
        "Job_submit",
        "Pod_create",
        "Pod_start",
        "Pod_end",
        "Pod_wait_create",
        "Pod_wait_run",
        "Pod_wait_total",
        "Pod_running_time",
        "Pod_total_time",
        "Running node",
        "Requests_cpu",
        "Limits_cpu",
        "Requests_memory",
        "Limits_memory",
        "Requests_gpu",
        "Limits_gpu",
    ]
    for field in table.field_names:  # Ustawienie wyrównania
        if any(s in field.lower() for s in ["time", "wait", "cpu", "gpu", "memory"]):
            table.align[field] = "r"

    pod_details.sort(
        key=lambda x: (x["Job_name"], x["Pod_name"])
    )  # Sortowanie dla spójności
    for pd in pod_details:
        # Funkcja do formatowania CPU/GPU jako string (np. "800m", "1", "0")
        def format_cpu_gpu(val):
            if val == 0:
                return "0"
            return f"{int(val*1000)}m" if val < 1 and val > 0 else str(float(val))

        # Funkcja do formatowania Pamięci jako string (np. "1000Mi")
        def format_mem(val_mb):
            return f"{int(val_mb)}Mi" if val_mb > 0 else "0"

        table.add_row(
            [
                pd["Pod_name"],
                pd["Job_name"],
                pd["Job_submit"],
                pd["Pod_create"],
                pd["Pod_start"],
                pd["Pod_end"],
                f"{pd['Pod_wait_create']:.1f}",
                f"{pd['Pod_wait_run']:.1f}",
                f"{pd['Pod_wait_total']:.1f}",
                f"{pd['Pod_running_time']:.1f}",
                f"{pd['Pod_total_time']:.1f}",
                pd["Running_node"],
                format_cpu_gpu(pd["Requests_cpu"]),
                format_cpu_gpu(pd["Limits_cpu"]),
                format_mem(pd["Requests_memory_mb"]),
                format_mem(pd["Limits_memory_mb"]),
                format_cpu_gpu(pd["Requests_gpu"]),
                format_cpu_gpu(pd["Limits_gpu"]),
            ]
        )
    print(table)

    job_summary_table = PrettyTable()
    job_summary_table.field_names = ["Job Name", "Job Completed Time(s)"]
    job_summary_table.align["Job Completed Time(s)"] = "r"
    for job_name in sorted(job_summary.keys()):
        # W przykładzie jest "job1", a nie nazwa. To wymagałoby mapowania lub innej logiki.
        # Użyję rzeczywistych nazw jobów.
        job_display_name = (
            job_name  # Można zmienić na np. "job" + str(index+1) jeśli trzeba
        )
        job_summary_table.add_row([job_display_name, f"{job_summary[job_name]:.1f}"])
    print(job_summary_table)
    print(f"\nCałkowity czas wykonania (Makespan): {makespan:.2f} sekund")


if __name__ == "__main__":
    node_file_url = "common/nodes/nodes_7-0.yaml"  # Podmień na prawidłową ścieżkę
    workload_file_url = "common/workloads/AI-workloads/wsl_test_mrp-2.yaml"  # Podmień

    main(node_file_url, workload_file_url)
