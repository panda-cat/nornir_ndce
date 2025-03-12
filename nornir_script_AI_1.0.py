import os
import logging

from datetime import datetime
from nornir import InitNornir
from nornir.core.task import Result
from nornir_netmiko import netmiko_send_config
from nornir_netmiko import netmiko_send_command
from tqdm import tqdm

from nornir.core.plugins.connections import ConnectionPluginRegister
from nornir_netmiko.connections import Netmiko

ConnectionPluginRegister.register("netmiko", Netmiko)

# 初始化 Nornir
nr = InitNornir(config_file="config.yaml")

def exec_cmd(task):
    try:
        # 获取命令列表、设备名称和 IP
        cmds = task.host.groups[0].data.get('multi_cmds')
        name = task.host.name
        ip = task.host.hostname

        # 获取当前日期作为文件夹名
        date_str = datetime.now().strftime("%Y-%m-%d")
        output_dir = os.path.normpath(os.path.join(os.getcwd(), date_str))

        # 创建日期命名的文件夹
        os.makedirs(output_dir, exist_ok=True)

        # 获取 Netmiko 连接
        net_conn = task.host.get_connection('netmiko', task.nornir.config)

        # 特权模式判断
        if net_conn.secret:
            net_conn.enable()

        # 初始化结果
        result_output = f"设备: {name}, IP: {ip}\n\n"

        # 依次执行命令并记录
        for cmd in cmds:
            cmd_result = net_conn.send_command(cmd)
            result_output += f"命令: {cmd}\n结果:\n{cmd_result}\n\n"

        # 写入到单独文件
        file_path = os.path.join(output_dir, f"{ip}.txt")
        with open(file_path, "w", encoding="utf-8") as output_file:
            output_file.write(result_output)

        pbar.update()
        return Result(host=task.host, result=result_output, changed=True)

    except Exception as e:
        # 异常处理并记录错误日志
        pbar.update()
        error_message = f"配置失败：设备: {name}, IP: {ip}，错误信息: {str(e)}"
        logging.error(error_message)
        return Result(host=task.host, result=error_message, failed=True)

if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(filename="execution_log.txt",
                        level=logging.INFO,
                        format="%(asctime)s - %(levelname)s - %(message)s")

    # 初始化进度条
    pbar = tqdm(total=len(nr.inventory.hosts), desc="执行进度")

    # 执行任务
    results = nr.run(task=exec_cmd)

    # 关闭进度条
    pbar.close()
