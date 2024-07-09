from abc import ABC, abstractmethod
from observers.observer import Observer


class Subject(ABC):
    @abstractmethod
    def attach(self, observer: Observer):
        pass

    @abstractmethod
    def detach(self, observer: Observer):
        pass

    @abstractmethod
    def notify(self):
        pass


class PostPublisher(Subject):
    def __init__(self):
        self._observers = []
        self._data = None

    def attach(self, observer: Observer):
        self._observers.append(observer)

    def detach(self, observer: Observer):
        self._observers.remove(observer)

    async def notify(self):
        for observer in self._observers:
            await observer.update(self._data)

    async def create_post(self, post_data):
        self._data = post_data
        await self.notify()
