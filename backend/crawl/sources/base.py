from abc import ABC, abstractmethod
from datetime import datetime

from crawl.types import FetchedPaper, SourceMeta


class CrawlSource(ABC):
    """
    数据源基类。新增数据源只需：
    1. 继承此类
    2. 实现 meta() 和 fetch()
    3. 在 sources/__init__.py 的 REGISTRY 中注册
    """

    @classmethod
    @abstractmethod
    def meta(cls) -> SourceMeta:
        """返回源的元信息（配置 schema、显示名等）。纯声明，不涉及 IO。"""
        ...

    @abstractmethod
    async def fetch(self, config: dict, since: datetime | None) -> list[FetchedPaper]:
        """
        执行爬取。
        - config: 经过 validate_config 校验后的配置
        - since: 上次成功爬取时间，None 表示首次运行
        - 返回: FetchedPaper 列表
        - 网络错误、解析错误应抛异常，由执行器统一捕获
        """
        ...

    def validate_config(self, config: dict) -> dict:
        """校验并规范化配置。默认实现根据 meta().config_fields 做基础校验。"""
        meta = self.meta()
        cleaned = {}
        for f in meta.config_fields:
            value = config.get(f.key, f.default)
            if f.required and value is None:
                raise ValueError(f"Missing required config: {f.key}")
            cleaned[f.key] = value
        return cleaned
