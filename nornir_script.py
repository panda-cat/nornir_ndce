# main.py
from nornir import InitNornir
from nornir_netmiko import netmiko_send_command
from nornir_utils.plugins.functions import print_result

# 初始化Nornir配置
nr = InitNornir(
    runner={
        "plugin": "threaded",
        "options": {
            "num_workers": 20,  # 根据设备数量调整
        },
    },
    inventory={
        "plugin": "SimpleInventory",
        "options": {
            "host_file": "inventory/hosts.yaml",    # 库存文件路径
            "group_file": "inventory/groups.yaml",  # 可选组文件
            "defaults_file": "inventory/defaults.yaml"  # 可选默认文件
        },
    },
    connections={
        "plugin": "netmiko",
        "options": {
            "extras": {
                "secret": "enable_password"  # 特权密码（如果需要）
            }
        }
    }
)

# 设置认证信息（也可以在defaults.yaml中配置）
nr.inventory.defaults.username = "admin"
nr.inventory.defaults.password = "Cisco123!"

# 执行任务
def exec_cmds(task):
    cmds = task.host.groups[0].data.get('multi_cmds')

    for cmd in cmds:
            result = task.run(netmiko_send_command,command_string=cmd,max_loops=500)
            print(result)
            output = result.result

            file_name = datetime.datetime.now().strftime('%Y-%m-%d')
            if not os.path.exists(file_name):
                os.mkdir(file_name)
            write_result = task.run(write_file,
                                    filename=file_name+'/'f'{task.host.hostname}.txt',
                                    content=output,
                                    )

# 运行任务并打印结果
results = nr.run(task=exec_cmds)
print_result(results)

# 手动关闭连接（可选）
nr.close_connections()
