"""
Punto de entrada de la aplicacion para AWS Elastic Beanstalk.

Beanstalk con la plataforma Python busca por defecto un objeto WSGI llamado
`application` en un modulo `application.py` en la raiz del codigo.
"""
from src.main import create_app

application = create_app()

if __name__ == "__main__":
    application.run(host="0.0.0.0", port=5000)
