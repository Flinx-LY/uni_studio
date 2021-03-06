from flask.helpers import url_for
from flask.templating import render_template
from .init import console
from flask import redirect, request, flash
from studio.utils.send_mail import send_mail


@console.route('/mail')
def mail_index():
    return render_template('mail_index.html')


@console.route('/mail', methods=['POST'])
def mail_post():
    to = request.values['to']
    content = request.values['content']
    subject = request.values['subject']
    try:
        send_mail(to=to, content=content, subject=subject)
        flash('发送成功')
    except Exception as e:
        flash(e)
    return redirect(url_for('console.mail_index'))
