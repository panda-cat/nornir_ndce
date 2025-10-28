# aio_net_runner.py

import os
import yaml
import argparse
from nornir import InitNornir
from nornir.core.task import Result
from nornir_netmiko.tasks import netmiko_send_command, netmiko_send_config

# 定义报告输出目录
OUTPUT_DIR = "reports"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def load_command_map(file_path):
    """从指定的 YAML 文件加载命令映射。"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"!!! 错误: 命令文件 '{file_path}' 未找到。")
        return None
    except Exception as e:
        print(f"!!! 错误: 加载或解析 '{file_path}' 时出错: {e}")
        return None

def device_operation_task(task, command_map, nornir_task_function):
    """
    一个通用的 Nornir 任务，可以执行命令或配置。
    
    Args:
        task: Nornir 任务对象.
        command_map: 包含平台->命令映射的字典.
        nornir_task_function: 要执行的 nornir-netmiko 函数
                              (例如, netmiko_send_command 或 netmiko_send_config).
    """
    platform = task.host.platform
    commands_to_run = command_map.get(platform)

    if not commands_to_run:
        print(f"--- 警告: 在命令文件中未找到 {task.host.name} ({platform}) 的命令定义，已跳过。")
        return Result(host=task.host, result=f"Platform '{platform}' not supported.", failed=True)

    # 2. 根据传入的函数动态执行
    if nornir_task_function == netmiko_send_config:
        # netmiko_send_config 接收一个命令列表
        result = task.run(
            name="Executing Config Set",
            task=nornir_task_function,
            config_commands=commands_to_run
        )
        # 将整个配置块的结果存储起来
        task.host["op_results"] = result.result
    else:
        # netmiko_send_command 是一条一条执行的
        task.host["op_results"] = "" # 初始化一个空字符串来累积结果
        for cmd in commands_to_run:
            try:
                result = task.run(
                    name=f"Executing Command: {cmd}",
                    task=nornir_task_function,
                    command_string=cmd,
                    enable=True,
                    read_timeout=90
                )
                # 将每条命令的结果存储起来
                task.host[cmd] = result.result
            except Exception as e:
                task.host[cmd] = f"--- 命令执行失败: {e} ---"

def generate_report(host, command_map, results, mode):
    """为单个主机生成报告文件。"""
    hostname = host.name
    platform = host.platform
    filename = os.path.join(OUTPUT_DIR, f"{hostname}.log")

    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"--- 报告 for {hostname} ({platform}) | Mode: {mode} ---\n\n")

        if results[hostname].failed:
            f.write("!!! 操作失败 !!!\n")
            err_result = results[hostname][0] # 通常第一个任务是失败的根源
            f.write(f"任务: {err_result.name}\n")
            if err_result.exception:
                f.write(f"错误详情: {err_result.exception}\n")
            else:
                f.write(f"结果: {err_result.result}\n")
            return # 失败了就不用继续了

        # 3. 根据模式生成不同的报告内容
        if mode == "config-set":
            f.write("--- 配置命令已下发 ---\n")
            f.write("下发命令列表:\n")
            commands_sent = command_map.get(platform, [])
            for cmd in commands_sent:
                f.write(f"  - {cmd}\n")
            f.write("\n--- 设备返回结果 ---\n")
            f.write(host.get("op_results", "无设备返回。"))
        else: # send-cmd mode
            commands_run = command_map.get(platform, [])
            for cmd in commands_run:
                output = host.get(cmd, f"--- 未找到命令 '{cmd}' 的输出 ---")
                f.write(f"--- 执行命令: {cmd} ---\n")
                f.write(output)
                f.write("\n\n")

    print(f"报告已生成: {filename}")

def load_command_map(file_path):
    """从指定的 YAML 文件加载命令映射。"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"!!! 错误: 命令文件 '{file_path}' 未找到。")
        return None
    except Exception as e:
        print(f"!!! 错误: 加载或解析 '{file_path}' 时出错: {e}")
        return None

def device_operation_task(task, command_map, nornir_task_function):
    """一个通用的 Nornir 任务，可以执行命令或配置。"""
    platform = task.host.platform
    commands_to_run = command_map.get(platform)

    if not commands_to_run:
        print(f"--- 警告: 在命令文件中未找到 {task.host.name} ({platform}) 的命令定义，已跳过。")
        return Result(host=task.host, result=f"Platform '{platform}' not supported.", failed=True)

    if nornir_task_function == netmiko_send_config:
        result = task.run(
            name="Executing Config Set",
            task=nornir_task_function,
            config_commands=commands_to_run
        )
        task.host["op_results"] = result.result
    else:
        task.host["op_results"] = "" 
        for cmd in commands_to_run:
            try:
                result = task.run(
                    name=f"Executing Command: {cmd}",
                    task=nornir_task_function,
                    command_string=cmd,
                    enable=True,
                    read_timeout=90
                )
                task.host[cmd] = result.result
            except Exception as e:
                task.host[cmd] = f"--- 命令执行失败: {e} ---"

def generate_report(host, command_map, results, mode):
    """为单个主机生成报告文件。"""
    hostname = host.name
    platform = host.platform
    filename = os.path.join(OUTPUT_DIR, f"{hostname}.log")

    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"--- 报告 for {hostname} ({platform}) | Mode: {mode} ---\n\n")

        if results[hostname].failed:
            f.write("!!! 操作失败 !!!\n")
            err_result = results[hostname][0]
            f.write(f"任务: {err_result.name}\n")
            if err_result.exception:
                f.write(f"错误详情: {err_result.exception}\n")
            else:
                f.write(f"结果: {err_result.result}\n")
            return

        if mode == "config-set":
            f.write("--- 配置命令已下发 ---\n")
            f.write("下发命令列表:\n")
            commands_sent = command_map.get(platform, [])
            for cmd in commands_sent:
                f.write(f"  - {cmd}\n")
            f.write("\n--- 设备返回结果 ---\n")
            f.write(host.get("op_results", "无设备返回。"))
        else: 
            commands_run = command_map.get(platform, [])
            for cmd in commands_run:
                output = host.get(cmd, f"--- 未找到命令 '{cmd}' 的输出 ---")
                f.write(f"--- 执行命令: {cmd} ---\n")
                f.write(output)
                f.write("\n\n")

    print(f"报告已生成: {filename}")

OUTPUT_DIR = "reports"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def main():
    """主函数，包含命令行解析。"""
    parser = argparse.ArgumentParser(
        description="多厂商网络设备自动化工具。默认执行 'send-cmd' (巡检) 模式。",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--cmd-file",
        required=True,
        help="[必需] 指定包含命令的 YAML 文件路径。"
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--send-cmd",
        action="store_true",
        help="[默认] 使用 'send-cmd' 模式 (netmiko_send_command) 执行巡检类命令。"
    )
    mode_group.add_argument(
        "--config-set",
        action="store_true",
        help="使用 'config-set' 模式 (netmiko_send_config) 下发配置类命令。"
    )
    args = parser.parse_args()

    if args.config_set:
        mode = "config-set"
        nornir_task = netmiko_send_config
    else:
        mode = "send-cmd"
        nornir_task = netmiko_send_command
    
    print(f"--- 运行模式: {mode} | 命令文件: {args.cmd_file} ---")

    command_map = load_command_map(args.cmd_file)
    if not command_map:
        print("无法加载命令，程序退出。")
        return

    # ======================== 终极解决方案代码 ========================
    try:
        print("DEBUG: Manually loading inventory files with UTF-8 encoding...")
        
        # 1. 手动加载所有清单文件
        with open("inventory/hosts.yaml", "r", encoding="utf-8") as f:
            hosts_dict = yaml.safe_load(f) or {} # 如果文件为空，则返回空字典
            
        with open("inventory/groups.yaml", "r", encoding="utf-8") as f:
            groups_dict = yaml.safe_load(f) or {}

        with open("inventory/defaults.yaml", "r", encoding="utf-8") as f:
            defaults_dict = yaml.safe_load(f) or {}

        print("DEBUG: All inventory files loaded successfully.")

        # 2. 构建 DictInventory 需要的配置字典
        nornir_config = {
            "core": {"num_workers": 100},
            "inventory": {
                "plugin": "DictInventory",
                "options": {
                    "hosts": hosts_dict,
                    "groups": groups_dict,
                    "defaults": defaults_dict
                }
            }
        }
        
        # 3. 将构建好的配置字典传递给 Nornir
        print("DEBUG: Initializing Nornir from dictionary...")
        nr = InitNornir(config=nornir_config)
        print("DEBUG: Nornir initialized successfully.")

    except FileNotFoundError as e:
        print(f"!!! 致命错误: 找不到清单文件 {e.filename}。请确保 inventory 目录及文件存在。")
        return
    except Exception as e:
        print(f"!!! 致命错误: 加载清单文件时出错: {e}")
        return
    # =================================================================

    results = nr.run(
        name=f"Device Operation: {mode}",
        task=device_operation_task,
        command_map=command_map,
        nornir_task_function=nornir_task
    )

    print("操作完成，开始生成报告...")
    for hostname, host_object in nr.inventory.hosts.items():
        generate_report(host_object, command_map, results, mode)
    
    print("所有报告生成完毕。")

if __name__ == "__main__":
    main()
