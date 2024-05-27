from functools import wraps
from simpy_env.simpy_charge import WirelessCharger
from simpy_env.simpy_produce import DataProducer
from simpy_env.simpy_process import ProcessingUnit

class Controller:
    """
    初始化控制器

    :param env: simpy环境, 用于处理并发事件
    :param wireless_charger: 无线充电站
    :param processing_units: PU列表
    """

    def __init__(self, env,
                 wireless_chargers: list,
                 processing_units: list,
                 data_producers: list
                 ):
        self.env = env
        self.wireless_chargers = wireless_chargers
        self.processing_units = processing_units
        self.data_producers = data_producers

    def process(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            self.env.process(func(self, *args, **kwargs))

        return wrapper

    def _get_processing_unit(self, processing_unit_id) -> ProcessingUnit:
        try:
            return self.processing_units[processing_unit_id]
        except IndexError:
            raise ValueError(f"Invalid battery ID: {processing_unit_id}")

    def _get_data_producer(self, data_producer_id) -> DataProducer:
        try:
            return self.data_producers[data_producer_id]
        except IndexError:
            raise ValueError(f"Invalid message queue ID: {data_producer_id}")

    def _get_wireless_charger(self, wireless_charge_id) -> WirelessCharger:
        try:
            return self.wireless_chargers[wireless_charge_id]
        except IndexError:
            raise ValueError(f"Invalid message queue ID: {wireless_charge_id}")

    @process
    def notify_charge(self, at_time, p_in, duration, battery_id):
        """
            通知无线充电站开始为所有电池无线充电
        """
        yield self.env.timeout(at_time)
        print(f'在时间: {self.env.now:.4f} 通知 (电池: {battery_id}) 开始充电')
        wireless_charger = self._get_wireless_charger(battery_id)
        wireless_charger.charge_event.succeed((p_in, duration))
        wireless_charger.charge_event = self.env.event()

    @process
    def notify_process(self, at_time, processing_unit_id, q_out, duration):
        """
            通知所有的PU开始工作
        """
        yield self.env.timeout(at_time)
        print(f'在时间: {self.env.now:.4f} 通知 (PU: {processing_unit_id}) 开始处理数据')
        processing_unit = self._get_processing_unit(processing_unit_id)
        processing_unit.process_event.succeed((q_out, duration))
        processing_unit.process_event = self.env.event()

    @process
    def notify_produce(self, at_time, data_producer_id, q_in, duration):
        yield self.env.timeout(at_time)
        print(f'在时间: {self.env.now:.4f} 通知 (DU: {data_producer_id}) 开始传入数据')
        produce_unit = self._get_data_producer(data_producer_id)
        produce_unit.produce_event.succeed((q_in, duration))
        produce_unit.produce_event = self.env.event()
        #用队列版，缺点秒入，可能还有其他缺点，还需实验
#         yield self.env.timeout(at_time)
#         print(f"在时间: {self.env.now:.4f} 通知 (DU: {data_producer_id}) 开始传入数据")
#         produce_unit = self._get_data_producer(data_producer_id)
#         num = produce_unit.num
#         produce_unit.produce_event[num].succeed((q_in, duration))
#         produce_unit.produce_event[num] = self.env.event()
#         produce_unit.num = (produce_unit.num + 1) % 10