import requests
import json
import threading
import time
import socket
import logging

class ServiceRegistrar:
    """
    Helper class for MCP services to register with the service registry
    and periodically send health updates.
    """
    
    def __init__(
        self,
        registry_url="http://localhost:5000",
        service_name=None,
        service_base_url=None,
        health_check_interval=30,
        description=None,
        version="1.0.0"
    ):
        """
        Initialize the service registrar.
        
        Args:
            registry_url: URL of the MCP registry service
            service_name: Name of this service
            service_base_url: Base URL where this service is accessible
            health_check_interval: How often to send health updates (seconds)
            description: Optional service description
            version: Service version
        """
        self.registry_url = registry_url
        self.service_name = service_name
        self.service_base_url = service_base_url
        self.health_check_interval = health_check_interval
        self.description = description or f"{service_name} Service"
        self.version = version
        
        self.service_id = None
        self.endpoints = []
        self.capabilities = []
        self.health_thread = None
        self.running = False
        
        self.logger = logging.getLogger(f"mcp.{service_name}")
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def set_endpoints(self, endpoints):
        """
        Set the service endpoints.
        
        Args:
            endpoints: List of endpoint objects describing this service's API
        """
        self.endpoints = endpoints
        # If already registered, update endpoints
        if self.service_id:
            self._update_endpoints()
    
    def set_capabilities(self, capabilities):
        """
        Set the service capabilities.
        
        Args:
            capabilities: List of capability strings describing what this service can do
        """
        self.capabilities = capabilities
        # If already registered, update service info
        if self.service_id:
            self._update_service_info()
    
    def register(self):
        """
        Register this service with the registry.
        """
        if not self.service_name or not self.service_base_url:
            self.logger.error("Service name and base URL are required for registration")
            raise ValueError("Service name and base URL are required")
        
        service_data = {
            "name": self.service_name,
            "baseUrl": self.service_base_url,
            "description": self.description,
            "version": self.version,
            "capabilities": self.capabilities,
            "endpoints": self.endpoints
        }
        
        try:
            response = requests.post(
                f"{self.registry_url}/api/registry/services",
                json=service_data
            )
            response.raise_for_status()
            result = response.json()
            self.service_id = result["id"]
            self.logger.info(f"Service registered with ID: {self.service_id}")
            return result
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to register service: {str(e)}")
            if hasattr(e, 'response') and e.response:
                self.logger.error(f"Response: {e.response.text}")
            raise
    
    def deregister(self):
        """
        Deregister this service from the registry.
        """
        if not self.service_id:
            self.logger.warning("Service not registered, nothing to deregister")
            return
        
        try:
            response = requests.delete(
                f"{self.registry_url}/api/registry/services/{self.service_id}"
            )
            response.raise_for_status()
            self.logger.info(f"Service deregistered: {self.service_id}")
            self.service_id = None
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to deregister service: {str(e)}")
            if hasattr(e, 'response') and e.response:
                self.logger.error(f"Response: {e.response.text}")
            raise
    
    def _update_service_info(self):
        """
        Update service information in the registry.
        """
        if not self.service_id:
            self.logger.warning("Service not registered, cannot update info")
            return
        
        service_data = {
            "name": self.service_name,
            "baseUrl": self.service_base_url,
            "description": self.description,
            "version": self.version,
            "capabilities": self.capabilities
        }
        
        try:
            response = requests.post(
                f"{self.registry_url}/api/registry/services",
                json=service_data
            )
            response.raise_for_status()
            self.logger.info(f"Service info updated")
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to update service info: {str(e)}")
            if hasattr(e, 'response') and e.response:
                self.logger.error(f"Response: {e.response.text}")
    
    def _update_endpoints(self):
        """
        Update service endpoints in the registry.
        """
        if not self.service_id:
            self.logger.warning("Service not registered, cannot update endpoints")
            return
        
        try:
            response = requests.put(
                f"{self.registry_url}/api/registry/services/{self.service_id}/endpoints",
                json={"endpoints": self.endpoints}
            )
            response.raise_for_status()
            self.logger.info(f"Service endpoints updated")
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to update endpoints: {str(e)}")
            if hasattr(e, 'response') and e.response:
                self.logger.error(f"Response: {e.response.text}")
    
    def _update_health(self, health_status):
        """
        Update service health status in the registry.
        """
        if not self.service_id:
            self.logger.warning("Service not registered, cannot update health")
            return
        
        try:
            response = requests.put(
                f"{self.registry_url}/api/registry/services/{self.service_id}/health",
                json={"health": health_status}
            )
            response.raise_for_status()
            self.logger.debug(f"Health status updated to {health_status}")
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to update health: {str(e)}")
            if hasattr(e, 'response') and e.response:
                self.logger.error(f"Response: {e.response.text}")
    
    def _check_health(self):
        """
        Check if the service is healthy.
        In a real implementation, this would perform actual health checks.
        """
        try:
            # Simple health check - just see if the service is reachable
            service_host = self.service_base_url.split("://")[1].split(":")[0]
            service_port = int(self.service_base_url.split(":")[-1].split("/")[0])
            
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            result = s.connect_ex((service_host, service_port))
            s.close()
            
            if result == 0:
                return "HEALTHY"
            else:
                return "UNHEALTHY"
        except Exception as e:
            self.logger.error(f"Health check failed: {str(e)}")
            return "UNKNOWN"
    
    def _health_monitor_thread(self):
        """
        Background thread that periodically checks and updates health status.
        """
        while self.running:
            try:
                health_status = self._check_health()
                self._update_health(health_status)
            except Exception as e:
                self.logger.error(f"Error in health monitor: {str(e)}")
            
            # Sleep until next check
            time.sleep(self.health_check_interval)
    
    def start_health_monitoring(self):
        """
        Start background health monitoring.
        """
        if self.health_thread and self.health_thread.is_alive():
            self.logger.warning("Health monitoring already running")
            return
        
        self.running = True
        self.health_thread = threading.Thread(
            target=self._health_monitor_thread,
            daemon=True
        )
        self.health_thread.start()
        self.logger.info("Health monitoring started")
    
    def stop_health_monitoring(self):
        """
        Stop background health monitoring.
        """
        self.running = False
        if self.health_thread:
            self.health_thread.join(timeout=1)
        self.logger.info("Health monitoring stopped")
    
    def __enter__(self):
        """
        Support for context manager protocol.
        """
        self.register()
        self.start_health_monitoring()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Support for context manager protocol.
        """
        self.stop_health_monitoring()
        self.deregister()


def extract_flask_endpoints(app, base_url=None):
    """
    Extract endpoint information from a Flask application.
    
    Args:
        app: Flask application instance
        base_url: Base URL where the service is accessible
        
    Returns:
        List of endpoint dictionaries
    """
    endpoints = []
    
    for rule in app.url_map.iter_rules():
        # Skip static and internal endpoints
        if 'static' in rule.endpoint or rule.rule.startswith('/static'):
            continue
        
        # Get HTTP methods
        methods = [m for m in rule.methods if m not in ['HEAD', 'OPTIONS']]
        
        # Skip rules without methods
        if not methods:
            continue
        
        # Extract path parameters
        path_params = [p for p in rule.arguments]
        
        endpoint_info = {
            "path": rule.rule,
            "methods": methods,
            "pathParams": path_params,
            "queryParams": [],  # Cannot extract automatically
            "description": f"Endpoint for {rule.endpoint}",
            "capability": rule.endpoint.replace('.', '_')
        }
        
        if base_url:
            endpoint_info["fullUrl"] = f"{base_url.rstrip('/')}{rule.rule}"
            
        endpoints.append(endpoint_info)
    
    return endpoints


def extract_flask_capabilities(app):
    """
    Extract capability information from a Flask application.
    
    Args:
        app: Flask application instance
        
    Returns:
        List of capability strings
    """
    capabilities = []
    
    for rule in app.url_map.iter_rules():
        # Skip static and internal endpoints
        if 'static' in rule.endpoint or rule.rule.startswith('/static'):
            continue
            
        # Get HTTP methods
        methods = [m for m in rule.methods if m not in ['HEAD', 'OPTIONS']]
        
        # Skip rules without methods
        if not methods:
            continue
            
        # Convert endpoint to capability name
        capability = rule.endpoint.replace('.', '_')
        
        if capability not in capabilities:
            capabilities.append(capability)
    
    return capabilities
