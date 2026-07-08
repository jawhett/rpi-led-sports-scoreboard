import requests
from requests.adapters import HTTPAdapter, Retry

class TimeoutSession(requests.Session):
    def request(self, *args, **kwargs):
        kwargs.setdefault('timeout', 15)
        return super(TimeoutSession, self).request(*args, **kwargs)

# Create a session and define a retry strategy. Used for API calls.
session = TimeoutSession()
retry_strategy = Retry(
    total=10, # Maximum number of retries.
    backoff_factor=0.5, 
    status_forcelist=[429, 500, 502, 503, 504] # HTTP status codes to retry on.
)
session.mount('http://', HTTPAdapter(max_retries=retry_strategy))
session.mount('https://', HTTPAdapter(max_retries=retry_strategy))
