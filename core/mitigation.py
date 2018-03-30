import radix
from webapp.models import Hijack
import _thread
from multiprocessing import Queue
from sqlalchemy import and_, exc
from webapp.shared import db_session
import traceback
import time


class Mitigation():

    def __init__(self, confparser):
        self.confparser = confparser
        self.hijack_queue = Queue()
        self.prefix_tree = radix.Radix()
        self.flag = False

    def init_mitigation(self):
        configs = self.confparser.get_obj()
        for config in configs:
            for prefix in configs[config]['prefixes']:
                node = self.prefix_tree.add(str(prefix))
                node.data['mitigation'] = configs[config]['mitigation']

    def start(self):
        if not self.flag:
            self.flag = True
            _thread.start_new_thread(self.parse_queue, ())

    def stop(self):
        if self.flag:
            self.flag = False
            self.hijack_queue.put(None)

    def parse_queue(self):
        print('Mitigation Mechanism Started...')
        self.init_mitigation()

        to_mitigate_events = Hijack.query.filter_by(to_mitigate=True).all()

        for hijack_event in to_mitigate_events:
            try:
                if hijack_event is None:
                    continue

                hijack_event.mitigation_started = time.time()
                # TODO: here the mitigation magic happens
                print("WILL MITIGATE HIJACK {} (DB)".format(hijack_event.id))
                hijack_event.to_mitigate = False

                db_session.commit()
                db_session.expunge(hijack_event)
            except Exception as e:
                traceback.print_exc()

        while self.flag:
            try:
                hijack_id = self.hijack_queue.get()
                print('QUEUE')
                print(hijack_id)
                if hijack_id is None:
                    continue

                hijack_event = Hijack.query.filter(
                                    Hijack.hijack_id.like(hijack_id)
                               ).first()

                try:
                    db_session.add(hijack_event)
                except exc.InvalidRequestError:
                    db_session.rollback()

                hijack_event.mitigation_started = time.time()
                # TODO: here the mitigation magic happens
                print("WILL MITIGATE HIJACK {} (QUEUE)".format(hijack_event.id))
                hijack_event.to_mitigate = False

                db_session.commit()
                db_session.expunge(hijack_event)
            except Exception as e:
                traceback.print_exc()
        print('Mitigation Mechanism Stopped...')