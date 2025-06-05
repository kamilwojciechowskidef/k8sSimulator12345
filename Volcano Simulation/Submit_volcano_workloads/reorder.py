# -*- coding: utf-8 -*-
import os
import subprocess
import yaml
import pandas as pd
import re

# ------------------------------------------------------------
# 1) FUNKCJA reorder_lpt
# ------------------------------------------------------------
def reorder_lpt(tasks: list) -> list:
    """
    Zwraca listę 'tasks' posortowaną malejąco po polu 'duration'.
    Jeśli Twoje zadania używają innego klucza (np. 'run_time'),
    zmień po prostu task['duration'] na task['run_time'] itp.
    """
    return sorted(tasks, key=lambda task: task["duration"], reverse=True)

def reorder_lpt_workload(input_path: str, output_path: str):
    """
    Wczytuje plik YAML, sortuje data['tasks'] malejąco przez reorder_lpt(...),
    i zapisuje wynik do output_path.
    """
    with open(input_path, 'r') as f:
        data = yaml.safe_load(f)

    tasks = data.get("tasks", [])
    if not isinstance(tasks, list):
        raise ValueError(f"Oczekiwałem listy 'tasks' w pliku {input_path}, ale dostałem: {type(tasks)}")

    sorted_tasks = reorder_lpt(tasks)
    data["tasks"] = sorted_tasks

    with open(output_path, 'w') as f:
        yaml.safe_dump(data, f, default_flow_style=False)

    print(f"✔ Zapisano posortowany YAML: {output_path}")

# ------------------------------------------------------------
# 2) FUNKCJA do uruchomienia SimRun i parsowania metryk
# ------------------------------------------------------------
def run_simulation_and_parse(yaml_path: str) -> dict:
    """
    Wywołuje SimRun.py z podanym plikiem YAML (yaml_path).
    Parsuje ze standardowego wyjścia metryki mean_jct, min_jct, max_jct, makespan.
    Zwraca słownik z kluczami: mean_jct, min_jct, max_jct, makespan.
    """
    # Jeśli w Twoim systemie trzeba użyć 'python3', zamień poniżej 'python' na 'python3'.
    proc = subprocess.run(
        ["python", "SimRun.py", yaml_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    out = proc.stdout

    # Wzorzec szuka linii zaczynającej się od liczb, np.: " 343.0     343.0     343.0     343.0"
    pattern = re.compile(r"^\s*([0-9]+\.?[0-9]*)\s+([0-9]+\.?[0-9]*)\s+([0-9]+\.?[0-9]*)\s+([0-9]+\.?[0-9]*)", re.MULTILINE)
    m = pattern.search(out)

    metrics = {}
    if m:
        metrics["mean_jct"] = float(m.group(1))
        metrics["min_jct"]  = float(m.group(2))
        metrics["max_jct"]  = float(m.group(3))
        metrics["makespan"]= float(m.group(4))
    else:
        metrics["mean_jct"] = None
        metrics["min_jct"]  = None
        metrics["max_jct"]  = None
        metrics["makespan"]= None

    return metrics

# ------------------------------------------------------------
# 3) GŁÓWNY SKRYPT: iteracja po katalogu workloads/
# ------------------------------------------------------------
def batch_test_and_report(workloads_dir: str, sorted_suffix: str = "_sorted.yaml"):
    """
    Dla każdego pliku *.yaml w katalogu workloads_dir:
      1) Generuje wersję posortowaną (LPT) z sufiksem '_sorted.yaml'
      2) Odpala SimRun.py na oryginał i na sorted
      3) Zbiera mean_jct, min_jct, max_jct, makespan
      4) Zapisuje raport do CSV i zwraca DataFrame
    """
    rows = []
    for fname in os.listdir(workloads_dir):
        if not fname.endswith(".yaml"):
            continue
        orig_path = os.path.join(workloads_dir, fname)
        sorted_name = fname.replace(".yaml", sorted_suffix)
        sorted_path = os.path.join(workloads_dir, sorted_name)

        # 1) Wygeneruj plik posortowany (nadpisując jeśli już istnieje)
        reorder_lpt_workload(orig_path, sorted_path)

        # 2) Uruchom symulację na oryginale i na posortowanym
        metrics_orig   = run_simulation_and_parse(orig_path)
        metrics_sorted = run_simulation_and_parse(sorted_path)

        # 3) Dodaj dwa wiersze do tabeli wyników
        rows.append({
            "workload_file": fname,
            "version": "original",
            "mean_jct": metrics_orig["mean_jct"],
            "min_jct":  metrics_orig["min_jct"],
            "max_jct":  metrics_orig["max_jct"],
            "makespan": metrics_orig["makespan"],
        })
        rows.append({
            "workload_file": fname,
            "version": "sorted",
            "mean_jct": metrics_sorted["mean_jct"],
            "min_jct":  metrics_sorted["min_jct"],
            "max_jct":  metrics_sorted["max_jct"],
            "makespan": metrics_sorted["makespan"],
        })

        print(f"✔ Przetworzono {fname}: mean_jct(orig)={metrics_orig['mean_jct']}, mean_jct(sorted)={metrics_sorted['mean_jct']}")

    # 4) Utwórz DataFrame i zapisz CSV
    df = pd.DataFrame(rows)
    csv_path = os.path.join(workloads_dir, "report_comparison.csv")
    df.to_csv(csv_path, index=False)
    print(f"\n✔ Raport zapisany jako {csv_path}")

    return df

if __name__ == "__main__":
    # Ustawiamy bezwzględną ścieżkę do folderu z workloadami:
    katalog = r"C:\Users\kamil\Documents\K8s\k8sSimulator\VolcanoSimulation\Submit_volcano_workloads\common\workloads\AI-workloads"

    if not os.path.isdir(katalog):
        print(f"Nie znalazłem katalogu '{katalog}'. Upewnij się, że podana ścieżka istnieje i zawiera pliki .yaml.")
    else:
        df_result = batch_test_and_report(katalog)
        # (opcjonalnie) możesz tu np. wypisać df_result.head() lub inne statystyki

