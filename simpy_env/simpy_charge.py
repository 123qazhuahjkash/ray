from simpy_env import Battery

class WirelessCharger():
    def __init__(self, env, battery: Battery, battery_id: int):
        self.env = env
        self.battery_id = battery_id
        self.battery = battery
        self.charge_event = env.event()
        self.charge_proc = env.process(self.charge())

    def charge(self):
        """充电过程。"""
        while True:
            (p_in, duration) = yield self.charge_event
            self.battery.start_battery_level = self.battery.level
            print(f"开始充电level:{self.battery.start_battery_level}")
            charge_amount = p_in * duration
            if self.battery.level + charge_amount > self.battery.capacity:
                print(
                    f"在时间: {self.env.now:.4f} 开始对电池({self.battery_id}) 充电，当前电量: {self.battery.level:.4f}"
                )
                actual_charge_amount = self.battery.capacity - self.battery.level
                actual_duration = actual_charge_amount / p_in
                self.battery.state = (
                    "charge",
                    self.env.now,
                    p_in,
                    actual_duration,
                )
                if actual_charge_amount != 0:  # 等于0会error
                    yield self.battery.put(actual_charge_amount)
#                     self.Battery.one_slot_battery = self.Battery.one_slot_battery + actual_charge_amount
                yield self.env.timeout(actual_duration)
                print(
                    f"在时间: {self.env.now:.4f} 电池({self.battery_id}) 已充满，充电量: {actual_charge_amount:.4f}"
                )
                idle = duration - actual_duration
                # ____.full_battery.succeed()  # 触发“FullBattery”事件
                yield self.env.timeout(idle)
                print(
                    f"在时间: {self.env.now:.4f} 结束电池({self.battery_id}) 充电，当前电量: {self.battery.level:.4f}, 空闲时间：{idle:.4f}"
                )
            else:
                print(
                    f"在时间: {self.env.now:.4f} 开始电池({self.battery_id}) 充电，当前电量: {self.battery.level:.4f}"
                )
                self.battery.state = (
                    "charge",
                    self.env.now,
                    p_in,
                    duration,
                )
                yield self.battery.put(charge_amount)
#                 self.Battery.one_slot_battery = self.Battery.one_slot_battery + charge_amount
                yield self.env.timeout(duration)
                print(
                    f"在时间: {self.env.now:.4f} 结束电池({self.battery_id}) 充电，当前电量: {self.battery.level:.4f}, 充电量: {charge_amount:.4f}"
                )

