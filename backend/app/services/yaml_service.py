import yaml
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

def generate_yaml(agent_config: Dict[str, Any]) -> str:
    """
    Generate a YAML configuration file from the agent configuration.
    
    Args:
        agent_config: Complete agent configuration
        
    Returns:
        Formatted YAML as a string
    """
    try:
        # Create the YAML structure
        yaml_structure = {
            "name": agent_config.get("name", "Unnamed Agent"),
            "description": agent_config.get("description", ""),
            "version": "1.0.0",
            "created_at": "__TIMESTAMP__",  # This will be replaced with the current timestamp in frontend
        }
        
        # Add instruction with proper indentation using pipe symbol
        if "instruction" in agent_config and agent_config["instruction"]:
            yaml_structure["instruction"] = agent_config["instruction"]
        
        # Add memory size and other config
        yaml_structure["config"] = {
            "memory_size": agent_config.get("memory_size", 10),
            "claude_model": "claude-3-7-sonnet-20250219"  # Default model
        }
        
        # Add tools if any
        if "tools" in agent_config and agent_config["tools"]:
            yaml_structure["tools"] = []
            for tool in agent_config["tools"]:
                yaml_structure["tools"].append({
                    "name": tool.get("name"),
                    "endpoint": tool.get("endpoint")
                })
        
        # Add knowledge base if available
        if "knowledge_base" in agent_config and agent_config["knowledge_base"]:
            knowledge_base = agent_config["knowledge_base"]
            storage_type = knowledge_base.get("storage_type", "llamacloud")
            
            # Create knowledge base section in YAML
            yaml_structure["knowledge_base"] = {}
            
            # Handle different storage types
            if storage_type == "llamacloud" and knowledge_base.get("index_name"):
                # LlamaCloud storage
                yaml_structure["knowledge_base"].update({
                    "storage_type": "llamacloud",
                    "index_name": knowledge_base.get("index_name"),
                    "document_count": knowledge_base.get("document_count", 0),
                    "project_name": knowledge_base.get("project_name") or "__PROJECT_NAME__"
                })
                
                # Add code template for using LlamaCloud knowledge base
                knowledge_base_code = f'''
                        # Code to initialize knowledge base retrieval from LlamaCloud
                        from llama_index.indices.managed.llama_cloud import LlamaCloudIndex
                        import os

                        def get_knowledge_base():
                            """Initialize and get the knowledge base for this agent"""
                            # Set API key from environment variable
                            api_key = os.environ.get("LLAMA_CLOUD_API_KEY")
                            if not api_key:
                                return "Error: LLAMA_CLOUD_API_KEY environment variable not set."
                                
                            try:
                                # Initialize the index from LlamaCloud
                                index = LlamaCloudIndex(
                                    index_name="{yaml_structure["knowledge_base"]["index_name"]}",
                                    project_name="{yaml_structure["knowledge_base"]["project_name"]}",
                                    api_key=api_key
                                )
                                return index
                            except Exception as e:
                                return f"Error initializing knowledge base: {{str(e)}}"

                        # This is a reusable knowledge base that can be used across queries
                        knowledge_base = None

                        def query_knowledge_base(query_text):
                            """Query the knowledge base with a specific question"""
                            global knowledge_base
                            
                            # Initialize knowledge base if not already done
                            if knowledge_base is None:
                                knowledge_base = get_knowledge_base()
                                # If an error occurred, return the error message
                                if isinstance(knowledge_base, str):
                                    return knowledge_base
                                    
                            try:
                                # Query the index
                                query_engine = knowledge_base.as_query_engine()
                                response = query_engine.query(query_text)
                                return response
                            except Exception as e:
                                return f"Error querying knowledge base: {{str(e)}}"
                        '''             
                yaml_structure["knowledge_base"]["code_template"] = knowledge_base_code
                yaml_structure["knowledge_base"]["usage_instruction"] = (
                "When a question requires specific knowledge, use the provided code_template to query the "
                "knowledge base. Initialize the knowledge base once and reuse it for subsequent queries. "
                "The query_knowledge_base() function accepts a question and returns relevant information from "
                "the documents that were indexed."
            )

            
            elif storage_type == "local" and knowledge_base.get("local_path"):
                # Local file storage
                yaml_structure["knowledge_base"].update({
                    "storage_type": "local",
                    "local_path": knowledge_base.get("local_path"),
                    "document_count": knowledge_base.get("document_count", 0)
                })
                # yaml_structure["knowledge_base"]["usage_instruction"] = (
                # "When a question requires specific knowledge, use the provided code_template to query the "
                # "knowledge base. Initialize the knowledge base once and reuse it for subsequent queries. "
                # "The query_knowledge_base() function accepts a question and returns relevant information from "
                # "the documents that were indexed."
            # )
                
            else:
                # Default case if storage type is not recognized or missing required fields
                logger.warning(f"Unknown knowledge base storage type or missing required fields: {knowledge_base}")
                return yaml.dump(yaml_structure, sort_keys=False, default_flow_style=False)
            
        
        # Convert to YAML
        yaml_content = yaml.dump(yaml_structure, sort_keys=False, default_flow_style=False)
        
        # Format the instruction to use the YAML pipe syntax
        if "instruction" in agent_config and agent_config["instruction"]:
            # Replace the single line instruction with a proper multiline format
            instruction_line = f"instruction: {agent_config['instruction']}"
            multiline_instruction = f"instruction: |\n"
            
            # Split the instruction into lines and indent them
            for line in agent_config["instruction"].split("\n"):
                multiline_instruction += f"  {line}\n"
                
            # Replace in the generated YAML
            yaml_content = yaml_content.replace(instruction_line, multiline_instruction.rstrip())
            
        # Format the knowledge base code template to use the YAML pipe syntax
        if "knowledge_base" in yaml_structure and "code_template" in yaml_structure["knowledge_base"]:
            # Replace the single line with a proper multiline format
            code_line = f"code_template: {yaml_structure['knowledge_base']['code_template']}"
            multiline_code = f"code_template: |\n"
            
            # Split the code into lines and indent them
            for line in yaml_structure["knowledge_base"]["code_template"].split("\n"):
                multiline_code += f"  {line}\n"
                
            # Replace in the generated YAML
            yaml_content = yaml_content.replace(code_line, multiline_code.rstrip())
            
        # Format the knowledge base usage instruction to use the YAML pipe syntax
        if "knowledge_base" in yaml_structure and "usage_instruction" in yaml_structure["knowledge_base"]:
            # Replace the single line with a proper multiline format
            instruction_line = f"usage_instruction: {yaml_structure['knowledge_base']['usage_instruction']}"
            multiline_instruction = f"usage_instruction: |\n"
            
            # Split the instruction into lines and indent them
            for line in yaml_structure["knowledge_base"]["usage_instruction"].split("\n"):
                multiline_instruction += f"  {line}\n"
                
            # Replace in the generated YAML
            yaml_content = yaml_content.replace(instruction_line, multiline_instruction.rstrip())
        
        return yaml_content
        
    except Exception as e:
        logger.error(f"Error generating YAML: {e}")
        raise Exception(f"Error generating YAML: {str(e)}")