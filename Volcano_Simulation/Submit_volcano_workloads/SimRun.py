from common.utils.json_http_client import JsonHttpClient
import time
import datetime
import csv
import json
import munch
import os
import math
import shutil
import heapq
from typing import List, Tuple, Dict
#from figures.draw_pod_figures import draw_pods_figures
import prettytable
from figures.figures import draw_job_figures
from figures.figures import draw_job_figures1
from figures.figures import draw_job_figures2
import matplotlib.pyplot as plt
import numpy as np

def _get_key_or_empty(data, key):
    pods = munch.munchify(data[key])
    return pods if pods is not None else []

def reset(sim_base_url, node_file_url, workload_file_url):
    client = JsonHttpClient(sim_base_url)

    with open(node_file_url, 'r', encoding='utf-8') as file:
        nodes_file = file.read()

    with open(workload_file_url, 'r', encoding='utf-8') as file:
        workload_file = file.read()

    dicData = client.get_json('/reset', json={
        'period': "-1",
        'nodes': nodes_file,
        'workload': workload_file,
    })

    if str(dicData) == "0":
        print("still job runs，can not reset")
    else:
        print("---Simualtion Reset---")

def step(sim_base_url, conf_file_url, pods_result_url, jobs_result_url, figures_result_url, scheduler):
    with plt.style.context('default'):
        client = JsonHttpClient(sim_base_url)

        succeed_headers = ["Pod_name", "Job_name", "Job_submit", "Pod_create", "Pod_start", "Pod_end", "Pod_wait_create", "Pod_wait_run", "Pod_wait_total",
                           "Pod_running_time", "Pod_total_time", "Running node", "Requests_memory", "Limits_memory", "Requests_cpu", "Limits_cpu", "Requests_gpu", "Limits_gpu"]
        succeed_table = prettytable.PrettyTable(succeed_headers)

        JCTheaders = ['Job Name', 'Job Completed Time(s)']
        JCT_table = prettytable.PrettyTable(JCTheaders)

        with open(conf_file_url, 'r', encoding='utf-8') as file:  # conf2 to nodeorder
            conf_file = file.read()
        data = client.get_json('/step', json={
            'conf': conf_file,
        })

        wait = 0.2
        alljoblists = []
        while True:
            time.sleep(wait)
            resultdata = client.get_json('/stepResult', json={
                'none': "",
            })
            if str(resultdata) == '0':
                continue
            else:
                print("---Simulation Start---")
                pod_result = os.path.join(pods_result_url, 'tasksSUM.csv')

                with open(pod_result, "w", encoding='utf-8', newline='') as file0:
                    succeed = []
                    writer = csv.writer(file0)
                    writer.writerow(succeed_headers)

                    job_result = os.path.join(jobs_result_url, 'coutJCT.csv')
                    with open(job_result, "w", encoding='utf-8', newline='') as file1:
                        writer1 = csv.writer(file1)
                        writer1.writerow(JCTheaders)

                        joblist = []
                        countJct = []
                        alljobstarttime = []
                        alljobendtime = []
                        allpodruntime = []
                        jobsublist = []

                        for jobName, job in resultdata["Jobs"].items():
                            job_sub = job["CreationTimestamp"]
                            if job_sub is None:
                                job_sub = "0001-01-01T00:00:00Z"
                            job_sub = datetime.datetime.strptime(job_sub, "%Y-%m-%dT%H:%M:%SZ")
                            joblist.append(jobName)

                            job_completes_flag = False
                            jobstarttime = []
                            jobendtime = []
                            job_completed_podnumber = 0

                            while not job_completes_flag:
                                jobstarttime = []
                                jobendtime = []
                                job_completed_podnumber = 0
                                for taskName, task in job["Tasks"].items():
                                    if job_completed_podnumber < int(task["Pod"]["metadata"]["labels"]["jobTaskNumber"]):
                                        if task["Pod"]["status"]["phase"] == "Succeeded":
                                            job_completed_podnumber += 1
                                            create = task["Pod"]["metadata"]["creationTimestamp"]
                                            start = task["Pod"]["status"]["containerStatuses"][0]["state"]["terminated"]["startedAt"]
                                            end = task["SimEndTimestamp"]
                                            if create is None:
                                                create = "0001-01-01T00:00:00Z"
                                            if start is None:
                                                start = "0001-01-01T00:00:00Z"
                                            if end is None:
                                                end = "0001-01-01T00:00:00Z"
                                            create_time = datetime.datetime.strptime(create, "%Y-%m-%dT%H:%M:%SZ")
                                            start_time = datetime.datetime.strptime(start, "%Y-%m-%dT%H:%M:%SZ")
                                            end_time = datetime.datetime.strptime(end, "%Y-%m-%dT%H:%M:%SZ")
                                            pending_create_time = (create_time - job_sub).total_seconds()
                                            pending_execute_time = (start_time - create_time).total_seconds()
                                            pending_total_time = (start_time - job_sub).total_seconds()
                                            run_time = (end_time - start_time).total_seconds()
                                            total_time = pending_total_time + run_time
                                            row = [taskName, task["Pod"]["metadata"]["labels"]["job"], job_sub, create_time, start_time, end_time,
                                                   pending_create_time, pending_execute_time, pending_total_time, run_time, total_time, task["NodeName"],
                                                   task["Pod"]["spec"]["containers"][0]["resources"]["requests"]["cpu"],
                                                   task["Pod"]["spec"]["containers"][0]["resources"]["limits"]["cpu"],
                                                   task["Pod"]["spec"]["containers"][0]["resources"]["requests"]["memory"],
                                                   task["Pod"]["spec"]["containers"][0]["resources"]["limits"]["memory"],
                                                   task["Pod"]["spec"]["containers"][0]["resources"]["requests"]["nvidia.com/gpu"],
                                                   task["Pod"]["spec"]["containers"][0]["resources"]["limits"]["nvidia.com/gpu"]]
                                            writer.writerow(row)
                                            succeed.append(row)
                                            succeed_table.add_row(row)

                                            jobstarttime.append(create_time)
                                            jobendtime.append(end_time)

                                            alljobstarttime.append(create_time)
                                            alljobendtime.append(end_time)
                                            allpodruntime.append(total_time)

                                            if job_completed_podnumber == int(task["Pod"]["metadata"]["labels"]["jobTaskNumber"]) - int(task["Pod"]["metadata"]["labels"]["terminationLimit"]):
                                                job_completes_flag = True
                                        else:
                                            pass
                                    else:
                                        break

                            job_jct = (max(jobendtime) - min(jobstarttime)).total_seconds()
                            countJct.append(job_jct)
                        row1 = ['job1', max(countJct)]
                        alljoblists.append(row1)
                        writer1.writerow(row1)
                        JCT_table.add_row(row1)

                print(succeed_table)
                print(JCT_table)

                tail_allpodruntime1 = []
                colorid = []
                tail_allpodruntime2 = sorted(allpodruntime)[int(len(allpodruntime) * math.pow(0.99, len(alljoblists))): len(allpodruntime)]
                task_id = []
                for i, podruntime in enumerate(allpodruntime):
                    if podruntime in tail_allpodruntime2:
                        colorid.append('red')
                    else:
                        colorid.append('steelblue')
                    task_id.append(i)

                task_id.reverse()

                plt.barh(range(len(allpodruntime)), allpodruntime, color=colorid, tick_label=task_id, height=0.2)
                plt.yticks(np.arange(len(allpodruntime)), ())
                plt.xticks(size=8, font='Times New Roman')
                plt.xlim(0)
                save_filename = scheduler + ".pdf"
                plt.savefig(os.path.join(figures_result_url, save_filename), dpi=1600)
                plt.show()

                pod_result_1 = os.path.join(pods_result_url, 'tasksSUM.md')
                file2 = open(pod_result_1, 'w', encoding='utf-8')
                file2.write(str(succeed_table) + "\n")
                file2.write(f'TotalTask: {len(allpodruntime)}\n')
                file2.write(
                    'Task average time: %.2fs, Minimum time: %.2fs, Maximum time: %.2fs.\n' % (
                        sum(allpodruntime) / len(allpodruntime),
                        min(allpodruntime),
                        max(allpodruntime)
                    )
                )
                file2.close()

                job_result_1 = os.path.join(jobs_result_url, 'coutJCT.md')
                file3 = open(job_result_1, 'w', encoding='utf-8')
                file3.write(str(JCT_table) + "\n")
                file3.write('Summary: ' + "\n")
                file3.write(f'TotalJob: {len(countJct)}\n')
                file3.write(
                    'Job average time：%.2fs，Minimum time：%.2fs，Maximum time：%.2fs。\n' % (
                        sum(countJct) / len(countJct),
                        min(countJct),
                        max(countJct)
                    )
                )
                file3.write('Jobs MakeSpan is：%.2fs。\n' % max(countJct))
                file3.close()

                time.sleep(0.5)
                break

        time.sleep(0.5)

if __name__ == '__main__':
    sim_base_url = 'http://localhost:8006'
    node_file_url = 'common/nodes/nodes_7-0.yaml'
    workload_file_url = 'common/workloads/AI-workloads/wsl_test_mrp-2.yaml'

    if os.path.exists(os.path.join(os.getcwd(), "volcano-sim-result/")):
        shutil.rmtree(os.path.join(os.getcwd(), "volcano-sim-result/"))
    os.makedirs(os.path.join(os.getcwd(), "volcano-sim-result/"), exist_ok=False)
    print("Delete history folder！！！\n")

    for i in range(1):
        print("**************************************************** " + str(i+1) + " test: ****************************************************")

        schedulers = ["SLA_LRP", "SLA_MRP", "SLA_BRA", "DRF_LRP", "DRF_MRP", "DRF_BRA", "GANG_LRP", "GANG_MRP", "GANG_BRA",
                       "GANG_DRF_LRP", "GANG_DRF_MRP", "GANG_DRF_BRA", "GANG_DRF_BINPACK"]
        for scheduler in schedulers:
            now = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
            conf_file_url = 'common/scheduler_conf_sim/' + str(scheduler) + '.yaml'
            pods_result_url = "volcano-sim-result/tasks/" + str(now) + "-" + str(scheduler)
            jobs_result_url = "volcano-sim-result/jobs/" + str(now) + "-" + str(scheduler)
            figures_result_url = "volcano-sim-result/figures/" + str(now) + "-" + str(scheduler)

            os.makedirs(pods_result_url, exist_ok=True)
            os.makedirs(jobs_result_url, exist_ok=True)
            os.makedirs(figures_result_url, exist_ok=True)

            print("-----------------------------------------------------------------")
            print("In scheduling algorithm: " + str(scheduler) + "， simulation test：")
            reset(sim_base_url, node_file_url, workload_file_url)
            time.sleep(1)
            step(sim_base_url, conf_file_url, pods_result_url, jobs_result_url, figures_result_url, scheduler)
            time.sleep(1)
            print("-----------------------------------------------------------------")
            print("")

    print("****************************************************！！！Simulation Stop！！！****************************************************")

    time.sleep(1)
    draw_job_figures2(
        'volcano-sim-result/jobs',
        'volcano-sim-result/figures/JCTmakespan'
    )