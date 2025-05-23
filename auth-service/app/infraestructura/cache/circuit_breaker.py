import pybreaker
import logging
import time
from typing import Any # For generic function wrapping if needed later

# Basic Logging Setup (for demonstration)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
pybreaker_logger = logging.getLogger('pybreaker')
# pybreaker_logger.setLevel(logging.DEBUG) # To see more pybreaker internal logs

# Global Circuit Breaker Listener (Optional Example)
class LoggingBreakerListener(pybreaker.CircuitBreakerListener):
    def state_change(self, cb, old_state, new_state):
        logging.info(f"CircuitBreaker '{cb.name}' changed state from {old_state} to {new_state}")
    def failure(self, cb, exc):
        logging.warning(f"CircuitBreaker '{cb.name}' recorded a failure: {exc}")
    def success(self, cb):
        logging.info(f"CircuitBreaker '{cb.name}' recorded a success.")

# Circuit Breaker Instance
listener = LoggingBreakerListener() # Example listener instance

# Define a circuit breaker for a dummy external service
dummy_external_service_breaker = pybreaker.CircuitBreaker(
    fail_max=3,        # Max failures before opening
    reset_timeout=10,  # Seconds to wait in open state before attempting half-open
    name="DummyExternalServiceCB",
    listeners=[listener] # Add listener
)

# Dummy Function to Protect (decorated)
@dummy_external_service_breaker
def call_dummy_external_service(succeed: bool = True) -> str:
    operation_name = "call_dummy_external_service"
    logging.info(f"Attempting '{operation_name}' (succeed={succeed})... CB State: {dummy_external_service_breaker.current_state}")
    
    if not succeed:
        time.sleep(0.2) # Simulate some delay
        raise ConnectionError(f"Simulated failure in '{operation_name}'")
    
    time.sleep(0.1) # Simulate success delay
    logging.info(f"'{operation_name}' was successful.")
    return f"'{operation_name}' completed successfully."

# Example Usage Block (for testing the setup)
if __name__ == "__main__":
    print("Demonstrating Circuit Breaker behavior...")
    print(f"Initial CB state: {dummy_external_service_breaker.current_state}")

    # Simulate failures to trip the breaker
    print("\n=== Simulating failures to trip the breaker ===")
    for i in range(dummy_external_service_breaker.fail_max + 1): # One more than fail_max to trip
        try:
            print(f"Attempt {i+1}:")
            # Let the first `fail_max` attempts fail
            result = call_dummy_external_service(succeed=(i >= dummy_external_service_breaker.fail_max)) 
            print(f"Result: {result}")
        except pybreaker.CircuitBreakerError as e:
            print(f"Caught CircuitBreakerError: {e}. CB State: {dummy_external_service_breaker.current_state}")
        except ConnectionError as e:
            print(f"Caught ConnectionError: {e}. CB State: {dummy_external_service_breaker.current_state}")
        except Exception as e:
            print(f"Caught unexpected error: {e}. CB State: {dummy_external_service_breaker.current_state}")
        time.sleep(0.1) # Short sleep between calls
    
    print(f"\nAfter {dummy_external_service_breaker.fail_max + 1} attempts (first {dummy_external_service_breaker.fail_max} failing), CB state: {dummy_external_service_breaker.current_state}")
    
    # Attempt another call while breaker is (presumably) open
    print("\n=== Attempting call while breaker should be OPEN ===")
    try:
        print("Attempting call immediately after tripping:")
        result = call_dummy_external_service(succeed=True)
        print(f"Result: {result}")
    except pybreaker.CircuitBreakerError as e:
        print(f"Caught CircuitBreakerError: {e}. CB State: {dummy_external_service_breaker.current_state}")
    except Exception as e:
        print(f"Caught unexpected error: {e}. CB State: {dummy_external_service_breaker.current_state}")

    print(f"\nWaiting for reset_timeout ({dummy_external_service_breaker.reset_timeout}s) for CB to go to HALF-OPEN...")
    time.sleep(dummy_external_service_breaker.reset_timeout + 1) # Wait for it to become half-open

    # Attempt after reset timeout (should be half-open)
    print("\n=== Attempting call in presumed HALF-OPEN state ===")
    try:
        print("Attempting call (should succeed to close breaker):")
        result = call_dummy_external_service(succeed=True)
        print(f"Result in half-open: {result}. CB State: {dummy_external_service_breaker.current_state}")
    except pybreaker.CircuitBreakerError as e:
        print(f"Error in half-open (CB still open?): {e}. CB State: {dummy_external_service_breaker.current_state}")
    except ConnectionError as e: # If the call itself fails
        print(f"ConnectionError in half-open: {e}. CB State: {dummy_external_service_breaker.current_state}")
    except Exception as e:
        print(f"Unexpected error in half-open: {e}. CB State: {dummy_external_service_breaker.current_state}")

    # Attempt another successful call to ensure it's closed
    print("\n=== Attempting another successful call to confirm CB is CLOSED ===")
    if dummy_external_service_breaker.current_state == "closed":
        try:
            print("Attempting call:")
            result = call_dummy_external_service(succeed=True) 
            print(f"Result: {result}. CB State: {dummy_external_service_breaker.current_state}")
        except Exception as e:
            print(f"Error: {e}. CB State: {dummy_external_service_breaker.current_state}")
    else:
        print(f"CB not closed after successful half-open call. Current state: {dummy_external_service_breaker.current_state}. Further test call skipped.")
    
    print("\nDemonstration finished.")
