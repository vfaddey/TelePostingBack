from observers.observer import Observer
from subjects.post_publisher import Subject


class SavePostObserver(Observer, Subject):
    def __init__(self, posts_collection):
        self._observers = []
        self.posts_collection = posts_collection
        self._data = None

    async def update(self, data):
        try:
            result = await self.posts_collection.insert_one(data)
            data['_id'] = result.inserted_id
            self.create_post(data)
        except Exception as e:
            print(f"Error inserting data into MongoDB: {str(e)}")

    def attach(self, observer: Observer):
        self._observers.append(observer)

    def detach(self, observer: Observer):
        self._observers.remove(observer)

    def notify(self):
        for observer in self._observers:
            observer.update(self._data)

    def create_post(self, post_data):
        self._data = post_data
        self.notify()
