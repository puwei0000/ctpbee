import time
import pymongo as pg
from pandas import DataFrame
from werkzeug.datastructures import ImmutableDict

from ctpbee.qa_support.abstract import DataSupport
from ctpbee.qa_support.qa_func import QA_util_time_stamp


class QADataSupport(DataSupport):
    price = ["open", "high", "low", "close"]
    config = dict(
        type="mongodb",
        host="localhost",
        port="27017",
        user=None,
        pwd=None,
        future_min="future_min",
        future_tick="future_tick",
        future_list="future_list"
    )

    def __init__(self, **kwargs):
        """
        param in kwargs:
            type: database type : now only support mongodb
            host: database host
            port: database port
            user: database user
            pwd : database password
            future_min: collections of min  default set to "future_min"
            future_tick: collection of tick  default set to "future_tick"
            future_list: collection of  future list  default set to "future_list"
        """
        self.config.update(kwargs)
        self.mongo_client = pg.MongoClient(self._get_link(**self.config))
        {setattr(self, f"_{i}", v) if i.startswith("future") else i for i, v in self.config.items()}

    @property
    def quantaxis(self):
        return self.mongo_client['quantaxis']

    def get_future_list(self, df=False) -> list or DataFrame:
        """
        返回期货产品列表
        :param df: 是否转换成dataframe
        :return: list or DataFrame
        """

        def remove_id(data):
            del data['_id']
            return data

        return list(map(remove_id, list(self.quantaxis[self._future_list].find())))

    def get_future_min(self, local_symbol: str, frq: str = "1min", **kwargs):
        # 此处需要一个更加完善的参数检查器 ---> 也许我能通过阅读pip源码获取灵感。

        if local_symbol.count(".") > 1:
            raise ValueError("local_symbol格式错误, 期望: 合约代码.交易所")
        if "." in local_symbol:
            symbol = local_symbol.split(".")[0]
        else:
            symbol = local_symbol
        try:
            exchange = local_symbol.split(".")[1]
        except IndexError:
            exchange = kwargs.get("exchange", None)
            if not exchange:
                raise ValueError("local_symbol中,你仅仅传入了合约名称，请通过exchange参数传入交易所代码")
        start = kwargs.get("start")
        end = kwargs.get("end")

        query = {
            "code": symbol.upper(),
            "type": frq
        }
        if start and end:
            query['time_stamp'] = \
                {
                    "$gte": QA_util_time_stamp(start),
                    "$lte": QA_util_time_stamp(end)
                }
        format_option = dict(open=1, close=1, high=1, low=1, datetime=1, code=1, price=1,
                             _id=0, tradetime=1, trade=1)
        _iterable = self.quantaxis['future_min'].find(query, format_option, batch_size=10000)

        def pack(data: dict):
            data['symbol'] = data.pop("code")
            data['local_symbol'] = data['symbol'] + "." + exchange
            data['volume'] = data.pop("trade")
            for key in self.price:
                data[key + "_price"] = data.pop(key)
            return data

        return list(map(pack, _iterable))

    def get_future_tick(self, local_symbol: str, **kwargs):
        pass

    def covert_index(self, type_="future"):
        """ 更新下标"""
        pass


if __name__ == '__main__':
    support = QADataSupport(host="127.0.0.1")
    li = support.get_future_list()
    ctime = time.time()
    rst = support.get_future_min("rb2001.SHFE", start="2019-8-1 10:00:10", end="2019-10-1 10:00:10")
    print(rst[0])
    print(f"cost: {time.time() - ctime}s")
