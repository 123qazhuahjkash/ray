import simpy
from simpy_env import Battery
from simpy_env import Queue
from simpy_env.simpy_Controller import Controller
from simpy_env.simpy_charge import WirelessCharger
from simpy_env.simpy_produce import DataProducer
from simpy_env.simpy_process import ProcessingUnit
import csv
def make_decision(batteries, queues, data_producers, wireless_charger):
    alpha = 0.3  # 充电占一个时间片的长度
    beta = 0.5  # 放电周期，处理任务的百分比
    tau = 0.8  # 处理任务运行时长占放电时长的百分比
    gamma = 0.5  # 分配给一个处理中心的算力
    return alpha, beta, tau, gamma

def run():
    # run是一个运行实例，它的作用是告诉模拟环境，在什么时刻要去charge, process
    env = simpy.Environment()
    batteries = [Battery(env, 100000, 0, i) for i in range(7)]
    queues = [Queue(env, 500000, 0,i) for i in range(7)]
    data_producers = [
        DataProducer(env, queues[i], data_source=f"test_{i}.csv", data_producer_id=i)
        for i in range(7)
    ]
    process_units = [
        ProcessingUnit(env, battery=batteries[i], queue=queues[i], processing_unit_id=i)
        for i in range(7)
    ]
    wireless_chargers = [
        WirelessCharger(env, battery=batteries[i], battery_id=i) for i in range(7)
    ]

    controller = Controller(env, wireless_chargers, process_units, data_producers)
    file_path = "dataset/finial_data.csv"

    # 模拟请求数据，在时间轴上注册（1:2MB, 5:6MB...）
    with open(file_path, mode="r", newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # print(f"id: {row['id']}, start_time: {row['start_time']}, end_time: {row['end_time']}, rate: {row['rate']}, duration: {row['duration']}, total: {row['total']}")
            # controller.notify_produce(at_time=float(row['start_time']), data_producer_id=int(row['id']) - 1,
            # p_in=float(row['rate']), duration=float(row['duration']))
            controller.notify_produce(
                at_time=float(row["start_time"]),
                data_producer_id=int(row["num_id"]) - 1,
                q_in=float(row["rate"]),
                duration=float(row["duration"]),
            )

    T = 471 #划分为471个时间片，一个时间片1200秒，20分钟
    end_time = 565200  # 数据集内内最后的end_time为565083.288
    start_time = 0
    time_slot_duration = (end_time - start_time) / T  # 事件片长度1200
    process_computing_power = 1000 #一个处理中心的总算力
    for time_slot in range(T):
        # alpha = 0.3
        (alpha, beta, tau, gamma) = make_decision(
            batteries, queues, data_producers, wireless_chargers
        )  # 根据context求解最优的决策变量
        # 注册充电事件
        charge_time_at = time_slot * time_slot_duration
        for i in range(7):
            controller.notify_charge(
                at_time=charge_time_at,
                p_in=250,
                duration=(alpha * time_slot_duration),
                battery_id=i,
            )

        # 注册处理事件
        process_time_at = time_slot * time_slot_duration + alpha * time_slot_duration
        for i in range(7):
            controller.notify_process(
                at_time=process_time_at,
                processing_unit_id=i,
                q_out=gamma * process_computing_power,
                duration=((1 - alpha) * time_slot_duration * tau),
            )
    #env.run(until=14) # set until = 10 11 12 13 观察queue[0]的变化
    env.run(until=2500)
#     env.run(until = 10000)
#     env.run(until = 30000)
#     env.run()

if __name__ == "__main__":
    run()