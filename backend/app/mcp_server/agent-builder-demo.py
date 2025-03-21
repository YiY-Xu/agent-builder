import yaml
import time
import argparse
import logging
from mcp_client_with_sse import MCPClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('agent_builder')

class AgentBuilder:
    """
    Demonstration of an agent builder platform that discovers MCP services
    and generates agent configurations.
    """
    
    def __init__(self, registry_url):
        """
        Initialize the agent builder.
        
        Args:
            registry_url: URL of the MCP registry
        """
        self.registry_url = registry_url
        self.mcp_client = MCPClient(registry_url)
        self.discovered_services = {}
        self.selected_services = []
    
    def discover_services(self, discovery_time=10):
        """
        Discover available MCP services.
        
        Args:
            discovery_time: Time to spend discovering services (seconds)
        """
        logger.info(f"Starting service discovery (will run for {discovery_time} seconds)")
        
        # Start the discovery process
        self.mcp_client.start_discovery()
        
        # Wait for discoveries to come in
        try:
            time.sleep(discovery_time)
        except KeyboardInterrupt:
            logger.info("Discovery interrupted by user")
        
        # Stop discovery
        self.mcp_client.stop_discovery()
        
        # Store discovered services
        self.discovered_services = {
            name: service for name, service in 
            [(s.name, s) for s in self.mcp_client.get_available_services()]
        }
        
        logger.info(f"Discovered {len(self.discovered_services)} services:")
        for name, service in self.discovered_services.items():
            logger.info(f"  - {name} (v{service.version}): {service.description}")
            if service.capabilities:
                logger.info(f"    Capabilities: {', '.join(service.capabilities)}")
    
    def select_service(self, service_name):
        """
        Select a service to include in the agent.
        
        Args:
            service_name: Name of the service to select
        """
        if service_name in self.discovered_services:
            if service_name not in self.selected_services:
                self.selected_services.append(service_name)
                logger.info(f"Selected service: {service_name}")
            else:
                logger.warning(f"Service already selected: {service_name}")
        else:
            logger.warning(f"Unknown service: {service_name}")
    
    def deselect_service(self, service_name):
        """
        Deselect a service from the agent.
        
        Args:
            service_name: Name of the service to deselect
        """
        if service_name in self.selected_services:
            self.selected_services.remove(service_name)
            logger.info(f"Deselected service: {service_name}")
        else:
            logger.warning(f"Service not selected: {service_name}")
    
    def generate_agent_yaml(self, agent_name, description, output_file=None):
        """
        Generate YAML configuration for an agent.
        
        Args:
            agent_name: Name of the agent
            description: Description of the agent
            output_file: File to write YAML to (if None, print to console)
            
        Returns:
            YAML string representation of the agent configuration
        """
        # Build the agent configuration
        agent_config = {
            "agent": {
                "name": agent_name,
                "description": description,
                "version": "1.0.0"
            },
            "mcp": {
                "registry": [
                    {
                        "url": self.registry_url,
                        "priority": 1
                    }
                ],
                "required_services": []
            },
            "workflows": []
        }
        
        # Add selected services and their capabilities
        for service_name in self.selected_services:
            if service_name in self.discovered_services:
                service = self.discovered_services[service_name]
                
                service_config = {
                    "name": service_name,
                    "capabilities": service.capabilities,
                    "fallback_behavior": "continue"
                }
                
                agent_config["mcp"]["required_services"].append(service_config)
        
        # If service includes flight-booking and hotel-booking, create a trip planning workflow
        has_flight = "flight-booking" in self.selected_services
        has_hotel = "hotel-booking" in self.selected_services
        has_weather = "weather-forecast" in self.selected_services
        has_car = "car-rental" in self.selected_services
        
        if has_flight and has_hotel:
            plan_trip_workflow = {
                "name": "plan_trip",
                "trigger": {
                    "type": "user_intent",
                    "patterns": [
                        "plan a trip",
                        "travel from {origin} to {destination}",
                        "find flights and hotels"
                    ]
                },
                "parameters": [
                    {
                        "name": "origin",
                        "required": True,
                        "prompt": "Where will you be departing from?"
                    },
                    {
                        "name": "destination",
                        "required": True,
                        "prompt": "Where would you like to go?"
                    },
                    {
                        "name": "start_date",
                        "required": True,
                        "type": "date",
                        "prompt": "What is your departure date?"
                    },
                    {
                        "name": "end_date",
                        "required": True,
                        "type": "date",
                        "prompt": "What is your return date?"
                    },
                    {
                        "name": "travelers",
                        "required": False,
                        "type": "number",
                        "prompt": "How many people are traveling?",
                        "default": 1
                    }
                ],
                "steps": []
            }
            
            step_id = 1
            
            # Add weather check if available
            if has_weather:
                plan_trip_workflow["steps"].append({
                    "id": f"step{step_id}",
                    "service": "weather-forecast",
                    "operation": "get_forecast",
                    "parameters": {
                        "city": "{destination}",
                        "days": 7
                    }
                })
                step_id += 1
            
            # Add flight search
            plan_trip_workflow["steps"].append({
                "id": f"step{step_id}",
                "service": "flight-booking",
                "operation": "search_flights",
                "parameters": {
                    "origin": "{origin}",
                    "destination": "{destination}",
                    "date": "{start_date}"
                }
            })
            step_id += 1
            
            # Add return flight search
            plan_trip_workflow["steps"].append({
                "id": f"step{step_id}",
                "service": "flight-booking",
                "operation": "search_flights",
                "parameters": {
                    "origin": "{destination}",
                    "destination": "{origin}",
                    "date": "{end_date}"
                }
            })
            step_id += 1
            
            # Add hotel search
            plan_trip_workflow["steps"].append({
                "id": f"step{step_id}",
                "service": "hotel-booking",
                "operation": "search_hotels",
                "parameters": {
                    "city": "{destination}",
                    "check_in": "{start_date}",
                    "check_out": "{end_date}",
                    "guests": "{travelers}"
                }
            })
            step_id += 1
            
            # Add car rental if available
            if has_car:
                plan_trip_workflow["steps"].append({
                    "id": f"step{step_id}",
                    "service": "car-rental",
                    "operation": "search_cars",
                    "parameters": {
                        "location": "{destination}"
                    }
                })
                step_id += 1
            
            # Add the workflow
            agent_config["workflows"].append(plan_trip_workflow)
        
        # Generate YAML from the configuration
        yaml_str = yaml.dump(agent_config, default_flow_style=False, sort_keys=False)
        
        # Write to file if specified
        if output_file:
            with open(output_file, 'w') as f:
                f.write(yaml_str)
            logger.info(f"Agent configuration written to {output_file}")
        else:
            print("\nGenerated Agent YAML:\n")
            print(yaml_str)
        
        return yaml_str


def main():
    """Main function for the agent builder demo."""
    parser = argparse.ArgumentParser(description="Agent Builder Platform Demo")
    parser.add_argument("--registry", default="http://localhost:5000", help="URL of the MCP registry")
    parser.add_argument("--discovery-time", type=int, default=10, help="Time to spend discovering services (seconds)")
    parser.add_argument("--agent-name", default="TravelPlannerAgent", help="Name of the agent to generate")
    parser.add_argument("--description", default="Plans travel itineraries using available services", help="Description of the agent")
    parser.add_argument("--output", help="Output file for YAML configuration")
    args = parser.parse_args()
    
    # Create agent builder
    builder = AgentBuilder(args.registry)
    
    # Discover services
    builder.discover_services(args.discovery_time)
    
    # Select all discovered services
    for service_name in builder.discovered_services.keys():
        builder.select_service(service_name)
    
    # Generate agent YAML
    builder.generate_agent_yaml(args.agent_name, args.description, args.output)


if __name__ == "__main__":
    main()
