
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor

from mixtura.core.concurrency import ProviderLock

class TestProviderLock(unittest.TestCase):
    def setUp(self):
        self.lock = ProviderLock()
        
    def test_shared_access(self):
        """Test that multiple threads can acquire shared lock simultaneously."""
        counter = 0
        started_event = threading.Event()
        
        def reader():
            nonlocal counter
            with self.lock.shared():
                counter += 1
                started_event.wait() # Wait for signal to continue
                
        t1 = threading.Thread(target=reader)
        t2 = threading.Thread(target=reader)
        
        t1.start()
        t2.start()
        
        time.sleep(0.1)
        self.assertEqual(counter, 2)
        
        started_event.set()
        t1.join()
        t2.join()
        
    def test_exclusive_access_blocks_readers(self):
        """Test that exclusive lock blocks readers."""
        state = "init"
        
        def writer():
            nonlocal state
            with self.lock.exclusive():
                state = "locked"
                time.sleep(0.2)
                state = "unlocked"
                
        def reader():
            with self.lock.shared():
                return state
                
        t_writer = threading.Thread(target=writer)
        t_reader = threading.Thread(target=reader)
        
        t_writer.start()
        time.sleep(0.05) # Ensure writer gets lock
        
        self.assertEqual(state, "locked")
        
        t_reader.start()
        t_reader.join()
        
        self.assertEqual(state, "unlocked")
        t_writer.join()

    def test_escalation(self):
        """Test that a thread holding shared lock can escalate to exclusive safely."""
        events = []
        
        def escalating_reader():
            with self.lock.shared():
                events.append("shared_acquired")
                # Now escalate
                with self.lock.exclusive():
                    events.append("exclusive_acquired")
                    time.sleep(0.1)
                events.append("exclusive_released")
            events.append("shared_released")
            
        t = threading.Thread(target=escalating_reader)
        t.start()
        t.join()
        
        self.assertEqual(events, [
            "shared_acquired", 
            "exclusive_acquired", 
            "exclusive_released", 
            "shared_released"
        ])

    def test_escalation_with_contention(self):
        """Test escalation when other readers are present."""
        # 1. Thread A takes shared.
        # 2. Thread B takes shared.
        # 3. Thread A tries to escalate -> Should temporarily release shared, wait for B to finish shared?
        #    Wait, if A releases shared, B is still holding shared.
        #    A tries to take exclusive. It MUST wait for B to release shared.
        #    So A is blocked until B moves on.
        
        events = []
        b_can_finish = threading.Event()
        
        def thread_a():
            with self.lock.shared():
                events.append("A_shared")
                time.sleep(0.1)
                # Escalate
                try:
                    with self.lock.exclusive():
                        events.append("A_exclusive")
                except Exception as e:
                    events.append(f"A_error: {e}")
        
        def thread_b():
            with self.lock.shared():
                events.append("B_shared")
                # Wait a bit to ensure A has started trying to escalate
                time.sleep(0.2)
                events.append("B_finishing")
                
        t_a = threading.Thread(target=thread_a)
        t_b = threading.Thread(target=thread_b)
        
        t_a.start()
        t_b.start()
        
        t_a.join()
        t_b.join()
        
        # Order: 
        # A_shared, B_shared (unordered)
        # A tries to escalate -> releases shared -> tries exclusive -> waits for B
        # B finishes -> releases shared
        # A wakes up -> takes exclusive -> finishes
        
        self.assertIn("A_shared", events)
        self.assertIn("B_shared", events)
        self.assertIn("B_finishing", events)
        self.assertIn("A_exclusive", events)
        
        # Verify B finished before A got exclusive
        b_finish_idx = events.index("B_finishing")
        a_excl_idx = events.index("A_exclusive")
        self.assertLess(b_finish_idx, a_excl_idx)

if __name__ == "__main__":
    unittest.main()
