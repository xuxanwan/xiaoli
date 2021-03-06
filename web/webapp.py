#!/usr/bin/env python
# coding: utf-8
"""
   XiaoLi
   ~~~~~~~

   Integrated Access Network Monitoring.
   :copyright: (c) 2012 by Ery Lee(ery.lee@gmail.com)
"""

from flask import Flask, redirect, url_for, \
    render_template, g, request, abort, current_app

from tango.ui import navbar
from tango.ip import ip_from
from tango import db, cache, login_mgr
from tango.login import current_user
from tango.models import Setting

from users.models import User, Permission
from tango.license.decrypt_license import decrypt_license

app = Flask(__name__)
app.config.from_pyfile('settings.py')
db.init_app(app)
db.app = app
cache.init_app(app)

#加载LICENSE
app.config['license_permit'] = decrypt_license(app.config.get("LICENSE_KEY"))

login_mgr.login_view = "/login"
login_mgr.login_message = u"请先登录系统."
login_mgr.refresh_view = "/reauth"

from flask_sqlalchemy import models_committed, before_models_committed
def record_oplogs(app,changes):
    if request.headers.environ.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
        return
    from system.models import OperationLog, SecurityLog
    for change in changes:
        if isinstance(change[0], OperationLog) or isinstance(change[0], SecurityLog):
            continue
        oplog = OperationLog()
        oplog.user = current_user
        oplog.module = unicode(change[0])
        oplog.action = change[1]
        oplog.terminal_ip = request.remote_addr
        oplog.summary = str(change[0].__dict__)
        db.session.add(oplog)
models_committed.connect(record_oplogs)
before_models_committed.connect(record_oplogs)

@login_mgr.user_loader
def load_user(id):
    return User.query.get(int(id))
    #user = cache.get("user-"+id)
    #if user is None:
    #   user = User.query.get(int(id))
    #   cache.set("user-"+id, user)
    #return user

from tango.login import user_logged_in, user_logged_out
def record_login(app, user):
    #cache.set("user-"+str(user.id), user)
    from system.models import SecurityLog
    from datetime import datetime
    seclog = SecurityLog()
    seclog.user = current_user
    seclog.terminal_ip = request.remote_addr
    seclog.summary = u'登录系统'
    seclog.login_at = datetime.now()
    db.session.add(seclog)
    db.session.commit()

def record_logout(app, user):
    #cache.delete("user-"+str(user.id))
    from system.models import SecurityLog
    from datetime import datetime
    seclog = SecurityLog()
    seclog.user = current_user
    seclog.terminal_ip = request.remote_addr
    seclog.summary = u'登出系统'
    seclog.logout_at = datetime.now()
    db.session.add(seclog)
    db.session.commit()

user_logged_in.connect(record_login)
user_logged_out.connect(record_logout)


login_mgr.init_app(app)

from tango.views import tangoview
from home.views import homeview
from topo.views import topoview
from nodes.views import nodeview
from alarms.views import alarmview
from perf.views import perfview
from report.views import reportview
from users.views import userview
from system.views import sysview
from admin.views import adminview

blueprints = [tangoview,
              homeview,
              topoview,
              nodeview,
              alarmview,
              perfview,
              reportview,
              userview,
              sysview,
              adminview]

for bp in blueprints:
    app.register_blueprint(bp)

    
allowed_ips = ['192.168.1.1/24',
               '192.168.100.1/24',
               '127.0.0.1',]
ip_checker = ip_from(allowed=allowed_ips)
        

def check_ip():
    if ip_checker.is_met({'REMOTE_ADDR':request.remote_addr}) is False:
        print 'IP check failed: ' + str(request.remote_addr)
        abort(403)

def is_ie():
    if 'User-Agent' not in request.headers.keys() \
       or request.headers['User-Agent'].find('MSIE') > -1:
        return True
    return False

def check_permissions():
    permissions_all = [p.endpoint for p in Permission.query.all()]
    permissions = [p.endpoint for p in current_user.role.permissions]
    if request.endpoint in permissions_all and request.endpoint not in permissions:
        print 'Permission check failed'
        abort(403)

from alarms.models import query_severities

@cache.cached(key_prefix="product.brand")
def brand():
    return Setting.find('product', 'brand').value

@cache.cached(key_prefix="product.navrow")
def navrow():
    return Setting.find('product', 'navrow').value

@app.before_request
def before_request():
    if not app.config['DEBUG']:
        check_ip()
        
    g.brand = brand()
    g.navrow = navrow()
    # Equal to @login_required
    if current_user.is_anonymous():
        if request.endpoint not in current_app.config['SAFE_ENDPOINTS']:
            return redirect(url_for('users.login', next=request.url))
            
        return None
        
    # Forbid IE User
    if is_ie():
        return render_template('browsers.html')

    # Not Anonymous User
    # Already Login
    if current_user:
        if not request.is_xhr:
            g.navbar = navbar
            g.severities = query_severities()

        cur_name = current_user.username
        if cur_name in current_app.config['SUPER_USERS'] \
           or request.endpoint in current_app.config['SAFE_ENDPOINTS']:
            return None
        if request.endpoint.split('.')[0] == 'admin' \
           and cur_name not in current_app.config['SUPER_USERS']:
            abort(404)
        check_permissions()

    else:
        abort(403)

@app.errorhandler(403)
def permission_denied(e):
    return render_template('403.html'), 403
        
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(e):
    return render_template('500.html'), 500

@app.template_filter('ifnull')
def ifnull(value, default=""):
    if value is None:
        return default
    else:
        return value

@app.template_filter('datetimeformat')
def datetimeformat(value, format="%Y-%m-%d %H:%M:%S"):
    from datetime import datetime
    if value and isinstance(value,datetime):
        return value.strftime(format)
    else:
        return value

@app.context_processor
def utility_processor():
    def sidebar(title, current_menuid, items):
        from jinja2 import Markup
        html = ['<ul class="nav bs-docs-sidenav">']
        for id, text, href in items:
            if id == '#divider':
                html.append('<li class="divider"></li>')
            else:
                li_class = 'active' if current_menuid and current_menuid ==id else ''
                if app.config["license_permit"].has_key(id):
                    html.append('<li class="%s"><a href="%s"><i class="icon-chevron-right"></i> %s</a></li>' % (
                        li_class, href, text) )
        if title != '' and len(html) > 1:
            html.insert(1, '<li class="nav-header popover-title">%s</li>' % title)
        html.append('</ul>')
        return Markup(u"\n".join(html))
    return dict(sidebar=sidebar)

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)

