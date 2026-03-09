# Community Engagement Compass - Technical Documentation

## Overview

Django-based AI assistant for community engagement frameworks. Features natural language processing, document processing, and vector search for contextual, evidence-based responses.

## Architecture

**Technology Stack:**
- **Backend**: Django 5.2.5 (Python 3.12+)
- **Database**: PostgreSQL (production), SQLite (development)
- **AI/ML**: Transformers, Sentence Transformers, PyTorch, FAISS
- **Frontend**: Bootstrap 5, JavaScript (ES6+)
- **Document Processing**: PyPDF2, pdfplumber
- **Authentication**: Django Allauth
- **Rich Text Editor**: Django CKEditor
- **Deployment**: Gunicorn, Nginx

## Project Structure

**Key Directories:**
- `config/` - Django configuration and settings
- `chat/` - Main application (models, views, services, admin)
- `knowledgeassistant/` - Project package (users, static, templates)
- `models/phi-2/` - AI model storage
- `requirements/` - Python dependencies
- `utility/` - Utility scripts

## Core Models

**Key Models:**
- **PDFDocument**: Document metadata, file paths, processing status
- **DocumentChunk**: Text chunks with embeddings for vector search
- **ChatSession**: User conversation sessions
- **ChatMessage**: Individual chat messages (user/assistant)
- **AboutContent/HowItWorksContent**: Dynamic content management

## AI Services

**PDFProcessingService**: Document ingestion, text extraction (PyPDF2), chunking (512 chars, 50 overlap)

**EmbeddingService**: Vector embeddings (SentenceTransformer), FAISS index, similarity search

**ChatService**: AI responses (Microsoft Phi-2), context integration, streaming support

## API Endpoints

**Chat**: `/chat/` (home), `/chat/send-message/` (send), `/chat/session/<uuid>/` (view)

**Documents**: `/chat/user/dashboard/` (user), `/chat/admin/dashboard/` (admin), upload endpoints

**Content**: `/chat/api/about/`, `/chat/api/how-it-works/` (AJAX)

## Frontend Architecture

**Templates**: `base.html`, `chatbot/` (chat, dashboards, feedback), `users/` (profile)

**JavaScript**: EnhancedChatInterface for session management, message sending, streaming responses

## Configuration

**Environment Variables**: DATABASE_URL, DJANGO_SECRET_KEY, DJANGO_ALLOWED_HOSTS, EMAIL_* (optional), REDIS_URL (optional)

**Django Settings**: Debug mode, database connections, static files, installed apps (Django core, third-party, custom)

**CKEditor**: Custom toolbar, dimensions, rich text editing plugins

## Installation & Setup

### Prerequisites
- Python 3.12+
- PostgreSQL 12+ (for production)
- Redis (optional, for caching)
- CUDA-compatible GPU (recommended for AI processing)

### Development Setup

1. **Clone Repository**
```bash
git clone <repository-url>
cd knowledgeassistant
```

2. **Create Virtual Environment**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows
```

3. **Install Dependencies**
```bash
pip install -r requirements/local.txt
```

4. **Environment Configuration**
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Database Setup**
```bash
python manage.py migrate
python manage.py createsuperuser
```

6. **Download AI Model**
```bash
python utility/download_phi2.py
```

7. **Run Development Server**
```bash
python manage.py runserver
```

### Production Deployment

1. **Install System Dependencies**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.12 python3.12-venv postgresql postgresql-contrib nginx redis-server

# Install CUDA (for GPU acceleration)
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/cuda-ubuntu2004.pin
sudo mv cuda-ubuntu2004.pin /etc/apt/preferences.d/cuda-repository-pin-600
wget https://developer.download.nvidia.com/compute/cuda/12.1.0/local_installers/cuda-repo-ubuntu2004-12-1-local_12.1.0-525.60.13-1_amd64.deb
sudo dpkg -i cuda-repo-ubuntu2004-12-1-local_12.1.0-525.60.13-1_amd64.deb
sudo cp /var/cuda-repo-ubuntu2004-12-1-local/cuda-*-keyring.gpg /usr/share/keyrings/
sudo apt-get update
sudo apt-get -y install cuda
```

2. **Application Setup**
```bash
# Create application user
sudo useradd -m -s /bin/bash knowledgeassistant
sudo su - knowledgeassistant

# Clone and setup application
git clone <repository-url>
cd knowledgeassistant
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements/production.txt
```

3. **Database Configuration**
```bash
# Create PostgreSQL database
sudo -u postgres psql
CREATE DATABASE knowledgeassistant;
CREATE USER knowledgeassistant WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE knowledgeassistant TO knowledgeassistant;
\q
```

4. **Static Files & Media**
```bash
python manage.py collectstatic --noinput
python manage.py migrate
```

5. **Gunicorn Configuration**
```bash
# Create gunicorn service file
sudo nano /etc/systemd/system/knowledgeassistant.service
```

```ini
[Unit]
Description=Knowledge Assistant Gunicorn daemon
After=network.target

[Service]
User=knowledgeassistant
Group=www-data
WorkingDirectory=/home/knowledgeassistant/knowledgeassistant
ExecStart=/home/knowledgeassistant/knowledgeassistant/venv/bin/gunicorn --workers 3 --bind unix:/home/knowledgeassistant/knowledgeassistant/knowledgeassistant.sock config.wsgi:application
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always

[Install]
WantedBy=multi-user.target
```

6. **Nginx Configuration**
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location = /favicon.ico { access_log off; log_not_found off; }
    
    location /static/ {
        root /home/knowledgeassistant/knowledgeassistant;
    }
    
    location /media/ {
        root /home/knowledgeassistant/knowledgeassistant;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/home/knowledgeassistant/knowledgeassistant/knowledgeassistant.sock;
    }
}
```

7. **Start Services**
```bash
sudo systemctl start knowledgeassistant
sudo systemctl enable knowledgeassistant
sudo systemctl restart nginx
```

## Management Commands

### Document Processing Commands
```bash
# Process pending documents
python manage.py process_pending_docs

# Rebuild search index
python manage.py rebuild_index

# Optimized index rebuild
python manage.py rebuild_index_optimized

# Chat statistics
python manage.py chat_stats
```

### Database Commands
```bash
# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic
```

### Development Commands
```bash
# Run development server
python manage.py runserver

# Run tests
python manage.py test

# Start Django shell
python manage.py shell

# Check project
python manage.py check
```

## Performance Optimization

**Database**: PostgreSQL, connection pooling, indexes, VACUUM/ANALYZE

**AI Models**: GPU acceleration, model caching, batch processing, optimized chunk sizes

**Caching**: Redis integration, django-redis backend, multiple cache databases

## Security Considerations

**Authentication**: Django Allauth, CSRF protection, secure sessions, password validation

**Data Protection**: Encrypted storage, secure processing, user isolation, security updates

**Production**: XSS protection, HSTS, SSL/TLS, secure cookies

## Monitoring & Logging

**Logging**: Configured log levels, file handlers, separate loggers, log rotation

**Health Checks**: Database connectivity, AI model availability, file system access

## Testing

**Configuration**: Test execution, coverage reporting, CI/CD integration

**Categories**: Unit tests, integration tests, API tests, AI service tests

## Troubleshooting

**Common Issues**: CUDA memory, PDF processing, database connections, model loading

**Debug Mode**: Development settings, verbose logging, detailed error handling

## Contributing

**Workflow**: Fork → Feature branch → Changes with tests → Pull request

**Standards**: PEP 8, type hints, comprehensive tests, documentation

**Pre-commit**: Code quality hooks, manual validation, formatting enforcement

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For technical support or questions:
- Create an issue in the repository
- Contact the development team
- Check the documentation wiki

---
 