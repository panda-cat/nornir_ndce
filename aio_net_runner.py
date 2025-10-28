# aio_net_runner.py

import os
import yaml
import argparse
import traceback

# ==================== 1. 解决 PyInstaller 打包问题的显式导入 ====================
# 这些导入对 PyInstaller 至关重要，可以防止 "ImportError"
from nornir.core import Nornir
from nornir.core.configuration import Config
from nornir.plugins.inventory.simple import SimpleInventory
from nornir.plugins.runners.threaded import ThreadedRunner
# ==============================================================================

from nornir import InitNornir
from nornir.core.task import Result
from nornir_netmiko.tasks import netmiko_send_command, netmiko_send_config

# --- 您的所有辅助函数保持不变 ---
OUTPUT_DIR = "reports"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def load_command_map(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f: return yaml.safe_load(f)
    except FileNotFoundError: print(f"!!! 错误: 命令文件 '{file_path}' 未找到。"); return None
    except Exception as e: print(f"!!! 错误: 加载或解析 '{file_path}' 时出错: {e}"); return None

def device_operation_task(task, command_map, nornir_task_function):
    platform = task.host.platform
    commands_to_run = command_map.get(platform)
    if not commands_to_run: print(f"--- 警告: 在命令文件中未找到 {task.host.name} ({platform}) 的命令定义，已跳过。"); return Result(host=task.host, result=f"Platform '{platform}' not supported.", failed=True)
    if nornir_task_function == netmiko_send_config:
        result = task.run(name="Executing Config Set", task=nornir_task_function, config_commands=commands_to_run)
        task.host["op_results"] = result.result
    else:
        for cmd in commands_to_run:
            try:
                result = task.run(name=f"Executing Command: {cmd}", task=nornir_task_function, command_string=cmd, enable=True, read_timeout=90)
                task.host[cmd] = result.result
            except Exception as e: task.host[cmd] = f"--- 命令执行失败: {e} ---"

def generate_report(host, command_map, results, mode):
    hostname, platform = host.name, host.platform
    filename = os.path.join(OUTPUT_DIR, f"{hostname}.log")
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"--- 报告 for {hostname} ({platform}) | Mode: {mode} ---\n\n")
        if results[hostname].failed:
            f.write("!!! 操作失败 !!!\n"); err_result = results[hostname][0]
            f.write(f"任务: {err_result.name}\n")
            if err_result.exception: f.write(f"错误详情: {err_result.exception}\n")
            else: f.write(f"结果: {err_result.result}\n")
            return
        if mode == "config-set":
            f.write("--- 配置命令已下发 ---\n下发命令列表:\n")
            commands_sent = command_map.get(platform, [])
            for cmd in commands_sent: f.write(f"  - {cmd}\n")
            f.write("\n--- 设备返回结果 ---\n"); f.write(host.get("op_results", "无设备返回。"))
        else:
            commands_run = command_map.get(platform, [])
            for cmd in commands_run:
                output = host.get(cmd, f"--- 未找到命令 '{cmd}' 的输出 ---")
                f.write(f"--- 执行命令: {cmd} ---\n{output}\n\n")
    print(f"报告已生成: {filename}")


def main():
    """主函数，包含命令行解析。"""
    # ==================== 2. 强制 Python 使用 UTF-8 编码 =======================
    # 这是解决 Windows 环境下 "UnicodeDecodeError" 的最根本方法
    os.environ["PYTHONUTF8"] = "1"
    # ==============================================================================

    parser = argparse.ArgumentParser(description="多厂商网络设备自动化工具。")
    # ... (argparse 部分保持不变) ...
    parser.add_argument("--cmd-file", required=True, help="[必需] 指定包含命令的 YAML 文件路径。")
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--send-cmd", action="store_true", help="[默认] 使用 'send-cmd' 模式。")
    mode_group.add_argument("--config-set", action="store_true", help="使用 'config-set' 模式。")
    args = parser.parse_args()

    mode, nornir_task = ("config-set", netmiko_send_config) if args.config_set else ("send-cmd", netmiko_send_command)
    print(f"--- 运行模式: {mode} | 命令文件: {args.cmd_file} ---")

    command_map = load_command_map(args.cmd_file)
    if not command_map: return

    try:
        print("DEBUG: Initializing Nornir from config file...")
        
        # =================== 3. 使用您提出的、最标准的方式初始化 Nornir ==============
        nr = InitNornir(config_file="config.yaml")
        # ==============================================================================
        
        print("DEBUG: Nornir initialized successfully.")

    except Exception as e:
        print(f"!!! 致命错误: 加载或初始化时出错: {e}")
        traceback.print_exc()
        return

    results = nr.run(name=f"Device Operation: {mode}", task=device_operation_task, command_map=command_map, nornir_task_function=nornir_task)

    print("操作完成，开始生成报告...")
    for hostname, host_object in nr.inventory.hosts.items():
        generate_report(host_object, command_map, results, mode)
    print("所有报告生成完毕。")

if __name__ == "__main__":
    main()

