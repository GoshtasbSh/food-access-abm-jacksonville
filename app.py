import os
os.environ['COMBINED_APP'] = '1'
os.environ['DASH_LIVE_PREFIX'] = '/'
os.environ['DASH_DISS_PREFIX'] = '/results/'

from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.serving import run_simple

from live_enhanced_mesa_dash import app as live_app
from abm_dashboard_dissertation import app as diss_app

application = DispatcherMiddleware(live_app.server, {
    '/results': diss_app.server
})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    run_simple('0.0.0.0', port, application, use_reloader=False)
