import json

class Neo4jLoggerMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Process the request
        response = self.get_response(request)

        # Check if there are any Neo4j logs in the session
        if 'neo4j_log' in request.session:
            try:
                log_data = json.loads(request.session['neo4j_log'])
                
                # Add the script to the response
                if 'text/html' in response.get('Content-Type', ''):
                    script = f"""
                    <script>
                    (function() {{
                        console.log("Neo4j Operation: {log_data['operation']} completed [{log_data['timestamp']}]");
                        
                        // Dispatch event for the logger
                        if (document.readyState === 'complete' || document.readyState === 'interactive') {{
                            const neo4jEvent = new CustomEvent('neo4j-operation', {{
                                detail: {{
                                    operation: "{log_data['operation']}",
                                    timestamp: "{log_data['timestamp']}"
                                }}
                            }});
                            document.dispatchEvent(neo4jEvent);
                        }} else {{
                            document.addEventListener('DOMContentLoaded', function() {{
                                const neo4jEvent = new CustomEvent('neo4j-operation', {{
                                    detail: {{
                                        operation: "{log_data['operation']}",
                                        timestamp: "{log_data['timestamp']}"
                                    }}
                                }});
                                document.dispatchEvent(neo4jEvent);
                            }});
                        }}
                    }})();
                    </script>
                    """
                    
                    response_content = response.content.decode('utf-8')
                    body_pos = response_content.find('</body>')
                    
                    if body_pos > 0:
                        new_content = response_content[:body_pos] + script + response_content[body_pos:]
                        response.content = new_content.encode('utf-8')
                
                # Remove the log from the session so it's only logged once
                del request.session['neo4j_log']
                request.session.modified = True
            except Exception as e:
                print(f"Error in Neo4jLoggerMiddleware: {e}")
            
        return response 