from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import include, path
from django.views import defaults as default_views
from django.views.generic import TemplateView
from django.http import HttpResponse
from django.shortcuts import render
import os

def root_redirect(request):
    """Redirect base URL depending on authentication state.

    - If authenticated: go to chat home
    - If not authenticated: go to login page
    """
    if request.user.is_authenticated:
        return redirect("chatbot:chat_home")
    return redirect("account_login")


def technical_readme(request):
    """Serve the technical README file"""
    readme_path = os.path.join(settings.BASE_DIR, 'TECHNICAL_README.md')
    
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Convert markdown to HTML (basic conversion)
        import re
        
        # Convert headers
        content = re.sub(r'^# (.*)$', r'<h1>\1</h1>', content, flags=re.MULTILINE)
        content = re.sub(r'^## (.*)$', r'<h2>\1</h2>', content, flags=re.MULTILINE)
        content = re.sub(r'^### (.*)$', r'<h3>\1</h3>', content, flags=re.MULTILINE)
        content = re.sub(r'^#### (.*)$', r'<h4>\1</h4>', content, flags=re.MULTILINE)
        
        # Convert bold text
        content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', content)
        
        # Convert italic text
        content = re.sub(r'\*(.*?)\*', r'<em>\1</em>', content)
        
        # Convert code blocks
        content = re.sub(r'```(.*?)```', r'<pre><code>\1</code></pre>', content, flags=re.DOTALL)
        
        # Convert inline code
        content = re.sub(r'`(.*?)`', r'<code>\1</code>', content)
        
        # Convert lists
        content = re.sub(r'^- (.*)$', r'<li>\1</li>', content, flags=re.MULTILINE)
        content = re.sub(r'(\n<li>.*</li>\n)+', lambda m: '<ul>' + m.group(0) + '</ul>', content, flags=re.DOTALL)
        
        # Convert line breaks
        content = content.replace('\n', '<br>')
        
        # Clean up multiple line breaks
        content = re.sub(r'<br>{2,}', '<br><br>', content)
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Technical Documentation - Community Engagement Compass</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; }}
                .container {{ max-width: 1000px; margin: 0 auto; padding: 2rem; }}
                h1, h2, h3, h4 {{ color: #2c2e65; margin-top: 2rem; margin-bottom: 1rem; }}
                h1 {{ border-bottom: 3px solid #2c2e65; padding-bottom: 0.5rem; }}
                h2 {{ border-bottom: 1px solid #e5e7eb; padding-bottom: 0.3rem; }}
                pre {{ background: #f8f9fa; padding: 1rem; border-radius: 0.5rem; overflow-x: auto; }}
                code {{ background: #f8f9fa; padding: 0.2rem 0.4rem; border-radius: 0.3rem; font-size: 0.9em; }}
                ul {{ padding-left: 1.5rem; }}
                li {{ margin-bottom: 0.5rem; }}
                .back-link {{ margin-bottom: 2rem; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="back-link">
                    <a href="javascript:history.back()" class="btn btn-outline-primary">
                        ← Back to Application
                    </a>
                </div>
                <div class="content">
                    {content}
                </div>
            </div>
        </body>
        </html>
        """
        
        return HttpResponse(html_content)
    else:
        return HttpResponse("Technical documentation not found.", status=404)

urlpatterns = [
    # Chat application URLs
    path("chat/", include("chat.urls", namespace="chatbot")),

    # Core pages
    path("", root_redirect, name="home"),
    path("about/", TemplateView.as_view(template_name="pages/about.html"), name="about"),
    path("TECHNICAL_README.md", technical_readme, name="technical_readme"),

    # Django Admin
    path(settings.ADMIN_URL, admin.site.urls),

    # User management
    path("users/", include("knowledgeassistant.users.urls", namespace="users")),
    path("accounts/", include("allauth.urls")),
    
    # CKEditor
    path("ckeditor/", include("ckeditor_uploader.urls")),

    # Media files
    *static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT),
]

if settings.DEBUG:
    # Debug toolbar
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns

    # This allows the error pages to be debugged during development
    urlpatterns += [
        path(
            "400/",
            default_views.bad_request,
            kwargs={"exception": Exception("Bad Request!")},
        ),
        path(
            "403/",
            default_views.permission_denied,
            kwargs={"exception": Exception("Permission Denied")},
        ),
        path(
            "404/",
            default_views.page_not_found,
            kwargs={"exception": Exception("Page not Found")},
        ),
        path("500/", default_views.server_error),
    ]

    # Serve media and static files in development
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
