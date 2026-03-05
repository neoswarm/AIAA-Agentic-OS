#!/usr/bin/env python3
"""
AIAA Resilience Library

Provides retry logic, timeout handling, circuit breakers, and graceful degradation
patterns for skill scripts.

Usage:
    from _shared.resilience import retry, with_timeout, graceful_fallback
    
    @retry(max_attempts=3, backoff_factor=2)
    def call_api():
        response = requests.get("...")
        return response.json()
    
    @with_timeout(seconds=30)
    def slow_operation():
        # operation logic
        pass
    
    @graceful_fallback(fallback_value={"default": "data"})
    def risky_operation():
        # operation that might fail
        pass
"""

import time
import functools
import signal
from typing import Callable, Any, Tuple, Optional


class TimeoutError(Exception):
    """Raised when a function exceeds its timeout"""
    pass


def retry(
    max_attempts: int = 3,
    backoff_factor: float = 2.0,
    exceptions: Tuple[type, ...] = (Exception,),
    on_retry: Optional[Callable] = None
):
    """
    Retry decorator with exponential backoff.
    
    Args:
        max_attempts: Maximum number of attempts (default: 3)
        backoff_factor: Multiplier for wait time between retries (default: 2.0)
        exceptions: Tuple of exception types to catch (default: all Exception)
        on_retry: Optional callback function called on each retry
    
    Example:
        @retry(max_attempts=3, backoff_factor=2, exceptions=(requests.RequestException,))
        def call_api():
            response = requests.get("https://api.example.com")
            return response.json()
    
    Behavior:
        - Attempt 1: immediate
        - Attempt 2: wait 2^0 = 1 second
        - Attempt 3: wait 2^1 = 2 seconds
        - Attempt 4: wait 2^2 = 4 seconds
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                    
                except exceptions as e:
                    last_exception = e
                    
                    # If this was the last attempt, re-raise
                    if attempt == max_attempts - 1:
                        raise
                    
                    # Calculate wait time with exponential backoff
                    wait_time = backoff_factor ** attempt
                    
                    # Call retry callback if provided
                    if on_retry:
                        on_retry(attempt + 1, max_attempts, wait_time, e)
                    else:
                        print(f"⚠️  Attempt {attempt + 1}/{max_attempts} failed: {e}")
                        print(f"   Retrying in {wait_time}s...")
                    
                    time.sleep(wait_time)
            
            # Should never reach here, but just in case
            if last_exception:
                raise last_exception
            
        return wrapper
    return decorator


def with_timeout(seconds: int):
    """
    Timeout decorator using signal.alarm (Unix-only).
    
    Args:
        seconds: Maximum execution time in seconds
    
    Example:
        @with_timeout(30)
        def slow_api_call():
            response = requests.get("https://slow-api.com")
            return response.json()
    
    Note:
        - Only works on Unix-like systems (Linux, macOS)
        - Cannot be nested (signal.alarm limitation)
        - For Windows, consider using threading-based timeout
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            def timeout_handler(signum, frame):
                raise TimeoutError(f"Function '{func.__name__}' exceeded timeout of {seconds}s")
            
            # Set up signal handler
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(seconds)
            
            try:
                result = func(*args, **kwargs)
            finally:
                # Cancel alarm and restore old handler
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)
            
            return result
        
        return wrapper
    return decorator


def graceful_fallback(fallback_value: Any = None, log_errors: bool = True):
    """
    Return fallback value instead of raising exceptions.
    
    Args:
        fallback_value: Value to return if function fails (default: None)
        log_errors: Whether to print error messages (default: True)
    
    Example:
        @graceful_fallback(fallback_value=[])
        def fetch_data_from_api():
            response = requests.get("https://api.example.com")
            return response.json()
        
        # If API fails, returns [] instead of raising exception
        data = fetch_data_from_api()
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_errors:
                    print(f"⚠️  Function '{func.__name__}' failed: {e}")
                    print(f"   Returning fallback value: {fallback_value}")
                return fallback_value
        
        return wrapper
    return decorator


class CircuitBreaker:
    """
    Circuit breaker pattern to prevent cascading failures.
    
    States:
        - CLOSED: Normal operation, requests pass through
        - OPEN: Too many failures, requests fail immediately
        - HALF_OPEN: Testing if service recovered
    
    Example:
        breaker = CircuitBreaker(failure_threshold=5, timeout=60)
        
        @breaker
        def call_unreliable_api():
            response = requests.get("https://unreliable-api.com")
            return response.json()
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: int = 60,
        expected_exception: type = Exception
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Seconds to wait before attempting recovery (HALF_OPEN)
            expected_exception: Exception type to count as failure
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def __call__(self, func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # If circuit is OPEN, check if timeout expired
            if self.state == "OPEN":
                if time.time() - self.last_failure_time >= self.timeout:
                    self.state = "HALF_OPEN"
                    print(f"🔄 Circuit breaker HALF_OPEN: testing {func.__name__}")
                else:
                    raise Exception(
                        f"Circuit breaker OPEN for {func.__name__}. "
                        f"Try again in {int(self.timeout - (time.time() - self.last_failure_time))}s"
                    )
            
            try:
                result = func(*args, **kwargs)
                
                # Success - reset if in HALF_OPEN state
                if self.state == "HALF_OPEN":
                    self.state = "CLOSED"
                    self.failure_count = 0
                    print(f"✅ Circuit breaker CLOSED: {func.__name__} recovered")
                
                return result
                
            except self.expected_exception as e:
                self.failure_count += 1
                self.last_failure_time = time.time()
                
                # Open circuit if threshold exceeded
                if self.failure_count >= self.failure_threshold:
                    self.state = "OPEN"
                    print(f"🚨 Circuit breaker OPEN: {func.__name__} failed {self.failure_count} times")
                
                raise
        
        return wrapper


def rate_limit(calls: int, period: int):
    """
    Rate limiting decorator.
    
    Args:
        calls: Maximum number of calls allowed
        period: Time period in seconds
    
    Example:
        @rate_limit(calls=10, period=60)  # Max 10 calls per minute
        def call_rate_limited_api():
            response = requests.get("https://api.example.com")
            return response.json()
    """
    call_times = []
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            now = time.time()
            
            # Remove old calls outside the time window
            while call_times and call_times[0] <= now - period:
                call_times.pop(0)
            
            # Check if rate limit exceeded
            if len(call_times) >= calls:
                sleep_time = period - (now - call_times[0])
                print(f"⏱️  Rate limit reached. Waiting {sleep_time:.1f}s...")
                time.sleep(sleep_time)
                call_times.pop(0)
            
            # Record this call
            call_times.append(now)
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


if __name__ == "__main__":
    """Test resilience utilities"""
    import requests
    
    print("🧪 Testing AIAA Resilience Library\n")
    
    # Test 1: Retry
    print("Test 1: Retry with exponential backoff")
    attempt_count = 0
    
    @retry(max_attempts=3, backoff_factor=1.5)
    def flaky_function():
        global attempt_count
        attempt_count += 1
        if attempt_count < 3:
            raise ValueError(f"Simulated failure #{attempt_count}")
        return "Success!"
    
    try:
        result = flaky_function()
        print(f"✅ Result: {result}\n")
    except Exception as e:
        print(f"❌ Failed: {e}\n")
    
    # Test 2: Graceful fallback
    print("Test 2: Graceful fallback")
    
    @graceful_fallback(fallback_value={"error": "Could not fetch data"})
    def failing_function():
        raise RuntimeError("API unavailable")
    
    result = failing_function()
    print(f"✅ Fallback result: {result}\n")
    
    # Test 3: Circuit breaker
    print("Test 3: Circuit breaker")
    breaker = CircuitBreaker(failure_threshold=3, timeout=5)
    
    @breaker
    def unreliable_api():
        raise ConnectionError("Service down")
    
    # Try until circuit opens
    for i in range(5):
        try:
            unreliable_api()
        except Exception as e:
            print(f"   Attempt {i+1}: {type(e).__name__}")
    
    print("\n✅ All tests completed")
