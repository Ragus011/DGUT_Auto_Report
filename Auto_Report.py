import json
import os

from gevent import monkey;monkey.patch_all()
import gevent
import click
import requests
from dgut_requests import DgutIllness
from retry import retry


CUSTOM_DATA_FILENAME = "custom_data.json"
DEFAULT_CUSTOM_DATA = {
    "body_temperature": 36.5,
    "health_situation": 1,
    "is_in_school": 1
}


def get_custom_data(filename: str) -> dict:
    """
    获取配置信息
    :param filename: 配置文件名
    :return: dict
    """
    # 文件不存在，返回默认配置
    if not os.path.exists(filename):
        return DEFAULT_CUSTOM_DATA
    
    # 读取文件配置
    with open(filename, encoding='utf-8') as f:
        config = json.load(f)
        for key in DEFAULT_CUSTOM_DATA.keys():
            if key not in config:
                config[key] = DEFAULT_CUSTOM_DATA[key]
    
    return config


@retry(tries=20, delay=2, backoff=3, max_delay=60)
def clock(u: DgutIllness, custom_data: dict = None, key: str = None) -> None:
    """
    打卡并输出结果
    :param u: 指定打卡的DgutIllness对象
    :param custom_data: 用户自定义数据
    :param key: 指定Server酱的key
    :return: None
    """
    result = u.report(custom_data=custom_data, priority=True).get("message")
    print(u.username[-4:], '-', result) 
    if key and not "今日已打卡" in result:
        headers = {
            'Content-type': "application/x-www-form-urlencoded"
        }
        data = {
            "title": u.username + result[1:],
        }
        res = requests.post(f'https://sctapi.ftqq.com/{key}.send', data=data, headers=headers)
        if res.status_code == 200 and res.json().get("code") == 0:
            print(u.username[-4:]+"推送成功")


@click.command()
@click.option('-U', '--username', required=True, help="中央认证账号用户名", type=str)
@click.option('-P', '--password', required=True, help="中央认证账号密码", type=str)
@click.option('-K', '--key', help="server酱的key值", type=str)
def main(username: str, password: str, key: str) -> None:
    """主函数，封装成终端命令
    :param username: 用户名
    :param password: 密码
    :param key: Server酱key
    :return: None
    """
    custom_data = get_custom_data(CUSTOM_DATA_FILENAME)
    users = username.split(",")
    pwds = password.split(",")
    if key:
        keys = key.split(",")
    if len(users) != len(pwds):
        exit("账号和密码个数不一致")
    tasks = []
    for i in range(len(users)):
        if key and i < len(keys) and keys[i] != '0':
            tasks.append(gevent.spawn(clock, u=DgutIllness(users[i], pwds[i]), custom_data=custom_data, key=keys[i]))
        else:
            tasks.append(gevent.spawn(clock, u=DgutIllness(users[i], pwds[i]), custom_data=custom_data))
    gevent.joinall(tasks)


if __name__ == '__main__':
    main()
