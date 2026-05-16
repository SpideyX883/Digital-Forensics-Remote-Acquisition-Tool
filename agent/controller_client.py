import requests
import json
import time
from config import debug_print, log_error

class ControllerClient:
    def __init__(self, controller_url, debug_mode=False):
        self.controller_url = controller_url
        self.debug_mode = debug_mode
        self.session = requests.Session()
        self.session.timeout = 10
        self.max_retries = 3
        self.retry_delay = 5
    
    def _make_request(self, method, endpoint, **kwargs):
        """Make HTTP request with retry logic"""
        url = f"{self.controller_url}{endpoint}"
        
        for attempt in range(self.max_retries):
            try:
                debug_print(f"Request {method} {url} (attempt {attempt + 1}/{self.max_retries})")
                
                response = self.session.request(method, url, **kwargs)
                
                if response.status_code == 200:
                    debug_print(f"✅ Request successful: {response.status_code}")
                    return response
                else:
                    debug_print(f"❌ Request failed: {response.status_code} - {response.text[:100]}")
                    
                    # Don't retry on client errors (4xx) except 429 (rate limit)
                    if 400 <= response.status_code < 500 and response.status_code != 429:
                        return response
                    
                    # Retry on server errors (5xx) and rate limits
                    if attempt < self.max_retries - 1:
                        debug_print(f"Retrying in {self.retry_delay} seconds...")
                        time.sleep(self.retry_delay)
                
            except requests.RequestException as e:
                debug_print(f"Request exception: {e}")
                if attempt < self.max_retries - 1:
                    debug_print(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                else:
                    log_error(f"Request failed after {self.max_retries} attempts", e)
        
        return None
    
    def register(self, agent_id, agent_name=None, debug_mode=False):
        """Register with controller"""
        try:
            from agent.system_utils import SystemInfo
            
            debug_print(f"Registering agent {agent_id} with controller...")
            
            data = {
                'agent_id': agent_id,
                'hostname': SystemInfo.get_hostname(),
                'os': SystemInfo.get_os_info()
            }
            
            if agent_name:
                data['agent_name'] = agent_name
            
            response = self._make_request(
                'POST',
                '/api/agents/register',
                json=data
            )
            
            if response and response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    debug_print(f"✅ Agent {agent_id} registered successfully")
                    return True
                else:
                    debug_print(f"❌ Registration failed: {result.get('error')}")
                    return False
            else:
                debug_print(f"❌ Registration failed with status: {response.status_code if response else 'No response'}")
                return False
                
        except Exception as e:
            log_error("Agent registration failed", e)
            return False
    
    def get_tasks(self, agent_id):
        """Get pending tasks, including disk acquisition tasks"""
        try:
            debug_print(f"Fetching tasks for agent {agent_id}...")
            response = self._make_request(
                'GET',
                f'/api/agents/{agent_id}/tasks'
            )
            
            if response and response.status_code == 200:
                result = response.json()
                if result.get('success', False):
                    tasks = result.get('tasks', [])
                    debug_print(f"Found {len(tasks)} pending tasks")
                    return tasks
                else:
                    debug_print(f"No tasks or error: {result.get('error', 'Unknown error')}")
                    return []
            else:
                debug_print("Failed to fetch tasks")
                return []
                
        except Exception as e:
            log_error("Failed to get tasks", e)
            return []
    
    def upload_evidence(self, task_id, archive_path, verification_data, case_id, evidence_type, agent_id):
        """Upload evidence to controller after disk acquisition"""
        try:
            debug_print(f"Uploading evidence for task {task_id}...")
            
            with open(archive_path, 'rb') as f:
                files = {'archive': (archive_path, f)}
                
                data = {
                    'task_id': str(task_id),
                    'evidence_type': evidence_type,
                    'case_id': case_id,
                    'original_hash': verification_data['original_hash'],
                    'archive_hash': verification_data['archive_hash'],
                    'verification_data': json.dumps(verification_data),
                    'agent_id': agent_id
                }
                
                response = self._make_request(
                    'POST',
                    '/api/evidence/upload_forensic',
                    files=files,
                    data=data,
                    timeout=120
                )
            
            if response and response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    debug_print(f"✅ Upload successful: {result.get('evidence_id')}")
                    return True
                else:
                    debug_print(f"❌ Upload failed: {result.get('error')}")
                    return False
            else:
                debug_print(f"❌ Upload failed with status: {response.status_code if response else 'No response'}")
                return False
                
        except Exception as e:
            log_error("Evidence upload failed", e)
            return False
    
    def report_task_status(self, task_id, status, result=None):
        """Report task status"""
        try:
            debug_print(f"Reporting task {task_id} status: {status}")
            
            data = {'status': status}
            if result:
                data['result'] = result
            
            response = self._make_request(
                'POST',
                f'/api/tasks/{task_id}/update',
                json=data
            )
            
            if response and response.status_code == 200:
                debug_print(f"✅ Task status reported: {status}")
                return True
            else:
                debug_print(f"❌ Failed to report task status: {response.status_code if response else 'No response'}")
                return False
                
        except Exception as e:
            debug_print(f"Failed to report task status: {e}")
            return False
    
    def send_heartbeat(self, agent_id):
        """Send heartbeat to controller"""
        try:
            # We'll simulate heartbeat by fetching tasks (which updates last_seen)
            response = self._make_request(
                'GET',
                f'/api/agents/{agent_id}/tasks'
            )
            
            if response and response.status_code == 200:
                debug_print(f"✅ Heartbeat sent for agent {agent_id}")
                return True
            else:
                debug_print(f"❌ Heartbeat failed for agent {agent_id}")
                return False
                
        except Exception as e:
            debug_print(f"Heartbeat failed: {e}")
            return False
