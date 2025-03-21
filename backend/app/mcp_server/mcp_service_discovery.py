import requests

class MCPServiceDiscovery:
    def __init__(self, registry_url):
        self.registry_url = registry_url
        
    def discover_services(self):
        """Connect to registry and get a snapshot of available services"""
        # Make a request to get current service catalog
        # No need for persistent SSE connection
        response = requests.get(f"{self.registry_url}/services")
        return response.json()
        
    def get_service_capabilities(self, service_name):
        """Get capabilities for a specific service"""
        response = requests.get(f"{self.registry_url}/services/{service_name}/capabilities")
        return response.json()
        
    def generate_service_config(self, selected_services):
        """Generate YAML configuration for selected services"""
        services_config = []
        for service_name in selected_services:
            capabilities = self.get_service_capabilities(service_name)
            services_config.append({
                "name": service_name,
                "capabilities": capabilities,
                "fallback_behavior": "continue"  # Default value, user can change
            })
        return services_config