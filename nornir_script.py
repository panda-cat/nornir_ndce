#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from nornir import InitNornir
from nornir_netmiko import netmiko_send_command
from nornir_utils.plugins.tasks.files import write_file
from nornir_utils.plugins.functions import print_result, print_title
import datetime
import os

nr = InitNornir(config_file="config.yaml")

def exec_cmd(task):
    cmds = task.host.groups[0].data.get('multi_cmds')

    if cmds:
        for cmd in cmds:
            result = task.run(netmiko_send_command, command_string=cmd, max_loops=500)
            if result[0].failed:
                task.host["failed"] = True
                task.host["failed_cmd"] = cmd
                print(f"Error running command '{cmd}' on {task.host.hostname}: {result[0].exception}")
                continue # Skip to next command after failure.
            output = result.result

            file_name = datetime.datetime.now().strftime('%Y-%m-%d')
            if not os.path.exists(file_name):
                os.mkdir(file_name)
            write_result = task.run(
                write_file,
                filename=f"{file_name}/{task.host.hostname}.txt",
                content=output,
            )
    else:
        print(f"No multi_cmds defined for {task.host.hostname}")
        task.host["failed"] = True
        task.host["failed_cmd"] = "No commands defined"
        return

print_title("正在执行.....")
results = nr.run(task=exec_cmd)

for hostname, result in results.items():
    if result.failed:
        print(f"Execution failed for {hostname}. Failed command: {results[hostname][0].host['failed_cmd']}")
    else:
        print(f"Execution successful for {hostname}")

# Optionally print detailed results if needed.
# print_result(results)
