#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import nornir_netmiko
from nornir import InitNornir
from nornir_netmiko import netmiko_multiline
from nornir_utils.plugins.tasks.files import write_file
from nornir_utils.plugins.functions import print_result,print_title
import datetime
import os

nr = InitNornir(config_file="config.yaml")
def exec_cmd(task):
    cmds = task.host.groups[0].data.get('multi_cmds')

    for cmd in cmds:
            result = task.run(netmiko_multiline,commands=cmd,max_loops=500)
            print(result)
            output = result.result

            file_name = datetime.datetime.now().strftime('%Y-%m-%d')
            if not os.path.exists(file_name):
                os.mkdir(file_name)
            write_result = task.run(write_file,
                                    filename=file_name+'/'f'{task.host.hostname}.txt',
                                    content=output,
                                    )


print_title("正在备份交换机配置.....")
results = nr.run(task=exec_cmd)
print_result(results)
