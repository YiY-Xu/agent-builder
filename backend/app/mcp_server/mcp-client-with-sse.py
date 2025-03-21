import requests
import json
import threading
import time
import logging
import sseclient
import importlib.util

# Check if we have the required packages
if not importlib.util.find_spec("sseclient"):
    raise ImportError("This code requires the sseclient package. Install with 'pip install sseclient-py'")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('mcp_client')

class ServiceDescriptor:
    """
    Descriptor for a discovered microservice.
    """
    
    def __init__(self, data):
        """
        Initialize the service descriptor from discovery data.
        
        Args:
            data: Service descriptor data from registry
        """
        self.id = data.get("id")
        self.name = data.get("name")
        self.version = data.get("version")
        self.base_url = data.get("baseUrl")
        self.health = data.get("health", "UNKNOWN")
        self.description = data.get("description", "")
        self.endpoints = self._parse_endpoints(data.get("endpoints", []))
        self.capabilities = data.get("capabilities", [])
        self.last_updated = data.get("lastUpdated")
        
    def _parse_endpoints(self, endpoints_data):
        """
        Parse endpoint data into structured endpoint objects.
        
        Args:
            endpoints_data: Raw endpoint data from registry
            
        Returns:
            Dictionary of structured endpoint objects
        """
        endpoints = {}
        
        for endpoint in endpoints_data:
            path = endpoint.get("path")
            capability = endpoint.get("capability")
            
            if path and capability:
                endpoints[capability] = endpoint
                
        return endpoints
    
    def get_endpoint_for_capability(self, capability_name):
        """
        Get the endpoint that provides a specific capability.
        
        Args:
            capability_name: Name of the capability to find
            
        Returns:
            Endpoint object or None if not found
        """
        return self.endpoints.get(capability_name)
    
    def can_perform(self, operation_name):
        """
        Check if the service can perform a specific operation.
        
        Args:
            operation_name: Name of the operation to check
            
        Returns:
            Boolean indicating if the operation is supported
        """
        # Check if the operation is in the capabilities list
        if operation_name in self.capabilities:
            return True
            
        # Check if there's an endpoint for this capability
        if operation_name in self.endpoints:
            return True
            
        return False
    
    def is_healthy(self):
        """
        Check if the service is currently healthy.
        
        Returns:
            Boolean indicating health status
        """
        return self.health == "HEALTHY"
    
    def __str__(self):
        """String representation of the service."""
        return f"{self.name} (v{self.version}) - {self.health} at {self.base_url}"


class ServiceProxy:
    """
    Dynamic proxy for interacting with a discovered service.
    """
    
    def __init__(self, descriptor, client):
        """
        Initialize the service proxy.
        
        Args:
            descriptor: Service descriptor object
            client: Reference to the parent MCP client
        """
        self.descriptor = descriptor
        self.client = client
        
    def __getattr__(self, name):
        """
        Dynamically handle method calls by mapping them to service operations.
        
        Args:
            name: Name of the operation to invoke
            
        Returns:
            Function that, when called, invokes the operation
        """
        if not self.descriptor.can_perform(name):
            raise AttributeError(f"Service {self.descriptor.name} does not support operation {name}")
            
        def operation_invoker(**kwargs):
            return self.client.invoke_operation(self.descriptor.name, name, **kwargs)
            
        return operation_invoker


class MCPClient:
    """
    Dynamic Microservice Control Plane client that discovers and interacts with
    services using SSE-based service discovery.
    """
    
    def __init__(self, registry_url):
        """
        Initialize the MCP client with the URL of the service registry.
        
        Args:
            registry_url: URL of the MCP registry that provides SSE updates
        """
        self.registry_url = registry_url
        self.services = {}  # Dictionary of discovered services by name
        self.services_by_id = {}  # Dictionary of discovered services by ID
        self.discovery_thread = None
        self.running = False
        self.service_callbacks = {}  # Callbacks for service events
    
    def start_discovery(self):
        """
        Start the service discovery process by connecting to the registry's
        SSE endpoint and processing service events.
        """
        if self.discovery_thread and self.discovery_thread.is_alive():
            logger.warning("Service discovery already running")
            return
            
        self.running = True
        self.discovery_thread = threading.Thread(
            target=self._discovery_thread,
            daemon=True
        )
        self.discovery_thread.start()
        logger.info("Service discovery started")
    
    def stop_discovery(self):
        """
        Stop the service discovery process and close SSE connections.
        """
        self.running = False
        if self.discovery_thread:
            self.discovery_thread.join(timeout=1)
        logger.info("Service discovery stopped")
    
    def _discovery_thread(self):
        """
        Background thread that listens for SSE events from the registry.
        """
        while self.running:
            try:
                # Connect to the SSE endpoint
                logger.info(f"Connecting to SSE endpoint: {self.registry_url}/api/registry/events")
                response = requests.get(
                    f"{self.registry_url}/api/registry/events",
                    stream=True,
                    headers={'Accept': 'text/event-stream'}
                )
                response.raise_for_status()
                
                # Create SSE client
                client = sseclient.SSEClient(response)
                
                # Process events
                for event in client.events():
                    if not self.running:
                        break
                        
                    self._process_event(event)
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Error connecting to registry: {str(e)}")
                if not self.running:
                    break
                    
                # Wait before retrying
                time.sleep(5)
            
            except Exception as e:
                logger.error(f"Error in discovery thread: {str(e)}")
                if not self.running:
                    break
                    
                # Wait before retrying
                time.sleep(5)
    
    def _process_event(self, event):
        """
        Process an SSE event from the registry.
        
        Args:
            event: SSE event object
        """
        try:
            # Parse the event data
            data = json.loads(event.data)
            event_type = event.event
            
            logger.debug(f"Received event: {event_type}")
            
            if event_type == "INITIAL_CATALOG":
                # Process initial catalog of services
                services_data = data.get("data", [])
                for service_data in services_data:
                    self._add_or_update_service(service_data)
                logger.info(f"Initialized with {len(services_data)} services")
                
            elif event_type == "SERVICE_REGISTERED" or event_type == "SERVICE_UPDATED":
                # Process service registration or update
                service_data = data.get("data", {})
                service_name = service_data.get("name")
                
                if service_name:
                    self._add_or_update_service(service_data)
                    logger.info(f"Service {service_name} registered/updated")
                    
            elif event_type == "SERVICE_DEREGISTERED":
                # Process service deregistration
                service_data = data.get("data", {})
                service_id = service_data.get("id")
                service_name = service_data.get("name")
                
                if service_id and service_id in self.services_by_id:
                    self._remove_service(service_id)
                    logger.info(f"Service {service_name} deregistered")
                    
            elif event_type == "SERVICE_HEALTH_CHANGED":
                # Process service health change
                service_data = data.get("data", {})
                service_id = service_data.get("id")
                
                if service_id and service_id in self.services_by_id:
                    self._update_service_health(service_data)
                    
            elif event_type == "SERVICE_ENDPOINTS_UPDATED":
                # Process service endpoints update
                service_data = data.get("data", {})
                service_id = service_data.get("id")
                
                if service_id and service_id in self.services_by_id:
                    self._add_or_update_service(service_data)
                    
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing event data: {str(e)}")
        except Exception as e:
            logger.error(f"Error processing event: {str(e)}")
    
    def _add_or_update_service(self, service_data):
        """
        Add a new service or update an existing one.
        
        Args:
            service_data: Service data from registry
        """
        service_id = service_data.get("id")
        service_name = service_data.get("name")
        
        if not service_id or not service_name:
            logger.warning("Received service data without ID or name")
            return
            
        # Create service descriptor
        descriptor = ServiceDescriptor(service_data)
        
        # Check if this is a new service or an update
        is_new = service_name not in self.services
        
        # Store the service
        self.services[service_name] = descriptor
        self.services_by_id[service_id] = descriptor
        
        # Trigger callbacks
        if is_new:
            self._trigger_service_callbacks(service_name, "available")
        else:
            self._trigger_service_callbacks(service_name, "updated")
    
    def _remove_service(self, service_id):
        """
        Remove a service from the discovered services.
        
        Args:
            service_id: ID of the service to remove
        """
        if service_id in self.services_by_id:
            descriptor = self.services_by_id[service_id]
            service_name = descriptor.name
            
            # Remove from dictionaries
            del self.services_by_id[service_id]
            if service_name in self.services:
                del self.services[service_name]
                
            # Trigger callbacks
            self._trigger_service_callbacks(service_name, "unavailable")
    
    def _update_service_health(self, service_data):
        """
        Update the health status of a service.
        
        Args:
            service_data: Service data from registry
        """
        service_id = service_data.get("id")
        
        if service_id in self.services_by_id:
            descriptor = self.services_by_id[service_id]
            old_health = descriptor.health
            
            # Update descriptor
            descriptor.health = service_data.get("health", "UNKNOWN")
            
            # If health changed from healthy to unhealthy (or vice versa), trigger callbacks
            if (old_health == "HEALTHY" and descriptor.health != "HEALTHY") or \
               (old_health != "HEALTHY" and descriptor.health == "HEALTHY"):
                self._trigger_service_callbacks(descriptor.name, "health_changed")
    
    def _trigger_service_callbacks(self, service_name, event_type):
        """
        Trigger callbacks for a service event.
        
        Args:
            service_name: Name of the service
            event_type: Type of event (available, unavailable, updated, health_changed)
        """
        # Get callbacks for this service
        service_callbacks = self.service_callbacks.get(service_name, {})
        
        # Get callbacks for this event type
        callbacks = service_callbacks.get(event_type, [])
        
        # Trigger callbacks
        for callback in callbacks:
            try:
                if event_type == "available":
                    callback(self.services[service_name])
                elif event_type == "unavailable":
                    callback(service_name)
                elif event_type == "updated" or event_type == "health_changed":
                    callback(self.services[service_name])
            except Exception as e:
                logger.error(f"Error in service callback: {str(e)}")
    
    def get_service(self, service_name):
        """
        Get a dynamic proxy for a discovered service by name.
        
        Args:
            service_name: Name of the service to access
            
        Returns:
            A dynamic proxy object for the requested service
        
        Raises:
            ValueError: If the requested service is not discovered
        """
        if service_name not in self.services:
            raise ValueError(f"Service {service_name} not discovered")
            
        return ServiceProxy(self.services[service_name], self)
    
    def invoke_operation(self, service_name, operation_name, **parameters):
        """
        Invoke an operation on a service directly.
        
        Args:
            service_name: Name of the service to call
            operation_name: Name of the operation to invoke
            parameters: Operation parameters as keyword arguments
            
        Returns:
            Operation result object
            
        Raises:
            ValueError: If the service is not discovered
            AttributeError: If the operation is not supported by the service
            requests.exceptions.RequestException: If the operation fails
        """
        if service_name not in self.services:
            raise ValueError(f"Service {service_name} not discovered")
            
        descriptor = self.services[service_name]
        
        if not descriptor.can_perform(operation_name):
            raise AttributeError(f"Service {service_name} does not support operation {operation_name}")
            
        # Find the endpoint for this operation
        endpoint = descriptor.get_endpoint_for_capability(operation_name)
        
        if not endpoint:
            # If there's no specific endpoint for this capability, try to derive it from the operation name
            # This is a fallback for services that don't provide detailed endpoint information
            method = "GET"  # Default method
            path = f"/api/{operation_name.replace('_', '/')}"
            
            # Try to infer method from operation name
            if operation_name.startswith("get_"):
                method = "GET"
            elif operation_name.startswith("search_"):
                method = "GET"
            elif operation_name.startswith("create_") or operation_name.startswith("add_"):
                method = "POST"
            elif operation_name.startswith("update_"):
                method = "PUT"
            elif operation_name.startswith("delete_") or operation_name.startswith("remove_"):
                method = "DELETE"
            elif operation_name.startswith("book_") or operation_name.startswith("reserve_"):
                method = "POST"
        else:
            # Use the discovered endpoint
            path = endpoint.get("path")
            methods = endpoint.get("methods", ["GET"])
            method = methods[0]  # Use the first method
            
        # Prepare the request
        url = f"{descriptor.base_url}{path}"
        
        # Make the request
        try:
            if method == "GET":
                response = requests.get(url, params=parameters)
            elif method == "POST":
                response = requests.post(url, json=parameters)
            elif method == "PUT":
                response = requests.put(url, json=parameters)
            elif method == "DELETE":
                response = requests.delete(url, params=parameters)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
                
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error invoking operation {operation_name} on service {service_name}: {str(e)}")
            raise
    
    def on_service_available(self, service_name, callback):
        """
        Register a callback to be called when a service becomes available.
        
        Args:
            service_name: Name of the service to watch
            callback: Function to call when the service becomes available
        """
        self._register_service_callback(service_name, "available", callback)
        
        # If the service is already available, call the callback immediately
        if service_name in self.services:
            try:
                callback(self.services[service_name])
            except Exception as e:
                logger.error(f"Error in service callback: {str(e)}")
    
    def on_service_unavailable(self, service_name, callback):
        """
        Register a callback to be called when a service becomes unavailable.
        
        Args:
            service_name: Name of the service to watch
            callback: Function to call when the service becomes unavailable
        """
        self._register_service_callback(service_name, "unavailable", callback)
    
    def on_service_updated(self, service_name, callback):
        """
        Register a callback to be called when a service is updated.
        
        Args:
            service_name: Name of the service to watch
            callback: Function to call when the service is updated
        """
        self._register_service_callback(service_name, "updated", callback)
    
    def on_service_health_changed(self, service_name, callback):
        """
        Register a callback to be called when a service's health status changes.
        
        Args:
            service_name: Name of the service to watch
            callback: Function to call when the service's health changes
        """
        self._register_service_callback(service_name, "health_changed", callback)
    
    def _register_service_callback(self, service_name, event_type, callback):
        """
        Register a callback for a service event.
        
        Args:
            service_name: Name of the service to watch
            event_type: Type of event (available, unavailable, updated, health_changed)
            callback: Function to call when the event occurs
        """
        if service_name not in self.service_callbacks:
            self.service_callbacks[service_name] = {}
            
        if event_type not in self.service_callbacks[service_name]:
            self.service_callbacks[service_name][event_type] = []
            
        self.service_callbacks[service_name][event_type].append(callback)
    
    def get_available_services(self):
        """
        Get a list of all currently available services.
        
        Returns:
            List of service descriptor objects
        """
        return list(self.services.values())
    
    def get_service_names(self):
        """
        Get a list of names of all currently available services.
        
        Returns:
            List of service names
        """
        return list(self.services.keys())
    
    def get_services_with_capability(self, capability_name):
        """
        Get a list of services that support a specific capability.
        
        Args:
            capability_name: Name of the capability to look for
            
        Returns:
            List of service descriptor objects
        """
        return [
            service for service in self.services.values()
            if service.can_perform(capability_name)
        ]
    
    def __enter__(self):
        """Support for context manager protocol."""
        self.start_discovery()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Support for context manager protocol."""
        self.stop_discovery()


# Example usage
if __name__ == "__main__":
    # Create MCP client
    client = MCPClient("http://localhost:5000")
    
    # Define callback for service availability
    def on_flight_service_available(service):
        print(f"Flight service is available: {service}")
        
        # Try to search for flights
        try:
            flights = client.invoke_operation(
                "flight-booking",
                "search_flights",
                origin="SanFrancisco",
                destination="NewYork",
                date="2025-04-01"
            )
            print(f"Found {len(flights.get('flights', []))} flights")
        except Exception as e:
            print(f"Error searching for flights: {str(e)}")
    
    # Register for service events
    client.on_service_available("flight-booking", on_flight_service_available)
    
    # Start discovery
    client.start_discovery()
    
    # Wait for events
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping discovery")
        client.stop_discovery()
