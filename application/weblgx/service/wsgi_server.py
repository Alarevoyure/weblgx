import warnings
import weblgx.http


def application(environ, start_response):

    warnings.warn("The WSGI application entrypoint moved from "
                  "weblgx.service.wsgi_server.application to weblgx.http.root "
                  "in 15.3.",
                  DeprecationWarning, stacklevel=1)
    return weblgx.http.root(environ, start_response)
