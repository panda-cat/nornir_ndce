from datetime import datetime
import os
import logging

from nornir import InitNornir
from nornir.core.task import Result
from nornir_netmiko import netmiko_send_config
from nornir_utils.plugins.tasks.files import write_file
from tqdm import tqdm

nr = InitNornir(config_file="config.yaml")

def exec_cmd(task):
    try:
        cmds = task.host.groups[0].data.get('multi_cmds')
        name = task.host.name
        ip = task.host.hostname
        time_str = datetime.now().strftime("%H%M%S")

        # 获取 Netmiko 连接
        net_conn = task.host.get_connection('netmiko', task.nornir.config)

        # 特权模式判断
        if net_conn.secret:
            net_conn.enable()

        result = task.run(task=netmiko_send_config, config_commands=cmds)

        output = result[0].result

        file_path = os.path.normpath(
            os.path.join(nr.config.core.inventory.options.host_file,
                         f'{name}_{ip}_{time_str}.txt')
        )

        config_res_write = task.run(task=write_file,
                                    filename=file_path,
                                    content=output,
                                    severity_level=logging.DEBUG)

        pbar.update()
        return Result(host=task.host, result=output, changed=True)

    except Exception as e:
        name = task.host.name
        ip = task.host.hostname
        pbar.update()
        error_message = f"配置失败：设备：{name}，IP：{ip}，错误信息：{str(e)}"
        logging.error(error_message)
        return Result(host=task.host, result=error_message, failed=True)

# 假设 nr 是已经初始化的 Nornir 对象
pbar = tqdm(total=len(nr.inventory.hosts))
results = nr.run(task=exec_cmd)
