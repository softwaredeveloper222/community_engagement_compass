"""
Custom middleware for ngrok and production support.

This middleware handles:
1. Ngrok forwarded headers (Protocol and Host)
2. Consistent Content-Type handling for JSON and streaming responses
3. Security headers
4. CORS headers for ngrok tunnels
"""

class NgrokMiddleware:
    """
    Middleware to handle ngrok forwarded headers, ensure proper response headers,
    and maintain consistent response formatting across local and ngrok environments.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Handle ngrok forwarded protocol
        if 'HTTP_X_FORWARDED_PROTO' in request.META:
            request.META['wsgi.url_scheme'] = request.META['HTTP_X_FORWARDED_PROTO']
        
        # Handle ngrok forwarded host
        if 'HTTP_X_FORWARDED_HOST' in request.META:
            request.META['HTTP_HOST'] = request.META['HTTP_X_FORWARDED_HOST']
        
        response = self.get_response(request)
        
        # Set security headers that should be present in all responses
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'SAMEORIGIN'
        response['X-XSS-Protection'] = '1; mode=block'
        
        # CRITICAL: Ensure Content-Type is properly preserved
        # This is especially important for ngrok which may strip or modify headers
        is_ngrok_request = 'ngrok' in request.get_host()
        
        if is_ngrok_request:
            # For ngrok requests, ensure we preserve Content-Type headers
            # and add CORS headers to allow proper response handling
            response['Access-Control-Allow-Origin'] = '*'
            response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response['Access-Control-Allow-Headers'] = 'Content-Type, X-CSRFToken, X-Requested-With'
            response['Access-Control-Expose-Headers'] = 'Content-Type'
            
            # Ensure streaming responses maintain proper content-type
            if response.has_header('Content-Type'):
                content_type = response.get('Content-Type', '')
                # Preserve event-stream for streaming endpoints
                if 'text/event-stream' in content_type:
                    response['Content-Type'] = 'text/event-stream; charset=utf-8'
                # Preserve JSON for API endpoints
                elif 'application/json' in content_type:
                    response['Content-Type'] = 'application/json; charset=utf-8'
        
        return response
